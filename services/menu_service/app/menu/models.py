import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


# ─────────────────────────────────────────
# CHOICES
# ─────────────────────────────────────────

class Moneda(models.TextChoices):
    COP = "COP", "Peso colombiano"
    USD = "USD", "Dólar estadounidense"
    EUR = "EUR", "Euro"
    MXN = "MXN", "Peso mexicano"
    ARS = "ARS", "Peso argentino"
    BRL = "BRL", "Real brasileño"
    CLP = "CLP", "Peso chileno"


class UnidadMedida(models.TextChoices):
    KILOGRAMO = "kg",  "Kilogramo"
    GRAMO = "g",   "Gramo"
    LITRO = "l",   "Litro"
    MILILITRO = "ml",  "Mililitro"
    UNIDAD = "und", "Unidad"
    PORCION = "por", "Porción"


# ─────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────

class Restaurante(models.Model):
    """
    Representa un local físico de la cadena.
    La moneda se valida con choices ISO 4217 para consistencia
    con order_service y futuros reportes financieros multi-país.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    nombre = models.CharField(max_length=255)
    pais = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)
    direccion = models.TextField()

    moneda = models.CharField(
        max_length=10,
        choices=Moneda.choices,
        default=Moneda.COP
    )
    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Restaurante"
        verbose_name_plural = "Restaurantes"
        ordering = ["pais", "ciudad", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.ciudad}, {self.pais})"


class Categoria(models.Model):
    """
    Catálogo global de categorías (Entradas, Platos fuertes, Postres...).
    Son globales para toda la cadena — cada restaurante elige qué platos
    de cada categoría activa mediante PrecioPlato.activo.
    El campo 'orden' permite controlar el orden de aparición en el menú.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class Plato(models.Model):
    """
    Catálogo global de platos — Opción A.
    Un plato existe una sola vez en el sistema. Cada restaurante lo activa
    y le asigna su precio mediante PrecioPlato. Esto garantiza un plato_id
    único y estable para order_service (snapshots), inventory_service
    (trazabilidad de ingredientes) y loyalty_service (promociones globales).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    nombre = models.CharField(max_length=255)
    descripcion = models.TextField()

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,  # si se elimina la categoría, el plato no desaparece
        null=True,
        blank=True,
        related_name="platos"
    )

    imagen = models.URLField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(
        auto_now=True)  # auditoría y event sourcing

    class Meta:
        verbose_name = "Plato"
        verbose_name_plural = "Platos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Ingrediente(models.Model):
    """
    Catálogo global de ingredientes.
    Compartido con inventory_service para trazabilidad de lotes
    y control de stock. El campo activo permite descontinuar un
    ingrediente sin eliminar el historial.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    nombre = models.CharField(max_length=255, unique=True)
    unidad_medida = models.CharField(
        max_length=10,
        choices=UnidadMedida.choices,
        default=UnidadMedida.UNIDAD
    )
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Ingrediente"
        verbose_name_plural = "Ingredientes"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.unidad_medida})"


class PlatoIngrediente(models.Model):
    """
    Relación M2M entre Plato e Ingrediente con cantidad.
    unique_together evita duplicar el mismo ingrediente en el mismo plato.
    Esta tabla es la fuente de verdad para inventory_service al calcular
    el consumo de stock por pedido.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    plato = models.ForeignKey(
        Plato, on_delete=models.CASCADE, related_name="ingredientes")
    ingrediente = models.ForeignKey(Ingrediente, on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        verbose_name = "Ingrediente de Plato"
        verbose_name_plural = "Ingredientes de Plato"
        constraints = [
            models.UniqueConstraint(
                fields=["plato", "ingrediente"],
                name="unique_plato_ingrediente"
            )
        ]

    def clean(self):
        if self.cantidad is not None and self.cantidad <= 0:
            raise ValidationError(
                {"cantidad": "La cantidad debe ser mayor a 0."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plato.nombre} — {self.ingrediente.nombre} ({self.cantidad} {self.ingrediente.unidad_medida})"


class PrecioPlato(models.Model):
    """
    Precio de un plato global en un restaurante específico.
    Este modelo es el 'activador' del plato en cada local:
    si no existe un PrecioPlato activo para un restaurante, ese
    plato no aparece en su menú.

    Soporta historial de precios por fechas (fecha_inicio/fecha_fin)
    para auditoría y cumplimiento del documento RestoHub.

    Regla de negocio: solo puede existir un precio activo por
    combinación plato+restaurante en un momento dado.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    plato = models.ForeignKey(
        Plato, on_delete=models.CASCADE, related_name="precios")
    restaurante = models.ForeignKey(
        Restaurante, on_delete=models.CASCADE, related_name="precios")

    precio = models.DecimalField(max_digits=10, decimal_places=2)

    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField(blank=True, null=True)

    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Precio de Plato"
        verbose_name_plural = "Precios de Plato"
        ordering = ["-fecha_inicio"]
        indexes = [
            models.Index(
                fields=["plato", "restaurante", "activo"],
                name="idx_precio_plato_rest_activo"
            ),
        ]

    def clean(self):
        errores = {}

        if self.precio is not None and self.precio <= 0:
            errores["precio"] = "El precio debe ser mayor a 0."

        if self.fecha_fin and self.fecha_inicio and self.fecha_fin <= self.fecha_inicio:
            errores["fecha_fin"] = "La fecha de fin debe ser posterior a la fecha de inicio."

        if not self.pk and self.fecha_inicio and self.fecha_inicio < timezone.now():
            errores["fecha_inicio"] = "La fecha de inicio no puede ser en el pasado."

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def esta_vigente(self):
        """Retorna True si el precio está activo y dentro del rango de fechas."""
        ahora = timezone.now()

        if not self.activo:
            return False

        if self.fecha_inicio and self.fecha_inicio > ahora:
            return False

        if self.fecha_fin and self.fecha_fin < ahora:
            return False

        return True

    def __str__(self):
        return f"{self.plato.nombre} — {self.restaurante.nombre} — {self.precio} {self.restaurante.moneda}"

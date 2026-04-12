# menu_service/app/menu/models.py
# CAMBIO ARQUITECTÓNICO: Ingrediente y Plato ahora tienen FK opcional a Restaurante.
# restaurante = null  → global (visible para todos, creado por admin_central)
# restaurante = X     → local de ese restaurante (creado/gestionado por su gerente)
# Estrategia de query: gerente ve sus propios + los globales.

import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


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


class Restaurante(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=255)
    pais = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)
    direccion = models.TextField()
    moneda = models.CharField(
        max_length=10, choices=Moneda.choices, default=Moneda.COP)
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
    """Categorías GLOBALES — gestionadas solo por admin_central."""
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


class Ingrediente(models.Model):
    """
    Ingrediente con FK opcional a Restaurante.

    restaurante = null  → ingrediente global (admin_central, visible en toda la cadena)
    restaurante = X     → ingrediente local de ese restaurante (gestionado por su gerente)

    Estrategia de query:
      Gerente ve: restaurante=su_id OR restaurante=null
      Admin ve: todos
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FK opcional — null = global
    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ingredientes",
        help_text="null = global (toda la cadena). Asignado = exclusivo de ese restaurante."
    )

    nombre = models.CharField(max_length=255)
    unidad_medida = models.CharField(
        max_length=10, choices=UnidadMedida.choices, default=UnidadMedida.UNIDAD)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Ingrediente"
        verbose_name_plural = "Ingredientes"
        ordering = ["nombre"]
        # El mismo nombre puede existir en diferentes restaurantes
        # pero no puede repetirse dentro del mismo contexto (global o mismo restaurante)
        constraints = [
            models.UniqueConstraint(
                fields=["nombre", "restaurante"],
                name="unique_ingrediente_nombre_restaurante"
            )
        ]

    def __str__(self):
        scope = self.restaurante.nombre if self.restaurante else "Global"
        return f"{self.nombre} ({self.unidad_medida}) [{scope}]"


class Plato(models.Model):
    """
    Plato con FK opcional a Restaurante.

    restaurante = null  → plato global (admin_central)
    restaurante = X     → plato local de ese restaurante (gerente)

    El gerente crea platos propios de su restaurante y les asigna precio
    mediante PrecioPlato. Los platos globales también pueden tener PrecioPlato
    específico por restaurante.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FK opcional — null = global
    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="platos",
        help_text="null = global. Asignado = exclusivo de ese restaurante."
    )

    nombre = models.CharField(max_length=255)
    descripcion = models.TextField()
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="platos"
    )
    imagen = models.URLField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plato"
        verbose_name_plural = "Platos"
        ordering = ["nombre"]

    def __str__(self):
        scope = self.restaurante.nombre if self.restaurante else "Global"
        return f"{self.nombre} [{scope}]"


class PlatoIngrediente(models.Model):
    """Receta del plato — ingredientes con cantidad."""
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
    Precio de un plato en un restaurante específico.
    Funciona para platos globales Y locales.
    Es el 'activador' del plato en el menú de cada restaurante.
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
            errores["fecha_fin"] = "La fecha de fin debe ser posterior a la de inicio."
        if not self.pk and self.fecha_inicio and self.fecha_inicio < timezone.now():
            errores["fecha_inicio"] = "La fecha de inicio no puede ser en el pasado."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def esta_vigente(self):
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

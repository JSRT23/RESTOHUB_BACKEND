# loyalty_service/app/loyalty/models.py
# FIX: Cupon ahora tiene restaurante_id para filtrar por restaurante
# Después de reemplazar este archivo ejecutar:
#   python manage.py makemigrations loyalty
#   python manage.py migrate
import uuid
from django.db import models


class NivelCliente(models.TextChoices):
    BRONCE = "bronce",   "Bronce"
    PLATA = "plata",    "Plata"
    ORO = "oro",      "Oro"
    DIAMANTE = "diamante", "Diamante"


class TipoTransaccion(models.TextChoices):
    ACUMULACION = "acumulacion", "Acumulación"
    CANJE = "canje",       "Canje"
    VENCIMIENTO = "vencimiento", "Vencimiento"
    AJUSTE = "ajuste",      "Ajuste manual"
    BONO = "bono",        "Bono promocional"


class AlcancePromocion(models.TextChoices):
    GLOBAL = "global", "Global (toda la cadena)"
    MARCA = "marca",  "Por marca"
    LOCAL = "local",  "Por restaurante"


class TipoBeneficio(models.TextChoices):
    DESCUENTO_PORCENTAJE = "descuento_pct",   "Descuento porcentual"
    DESCUENTO_MONTO = "descuento_monto", "Descuento en monto fijo"
    PUNTOS_EXTRA = "puntos_extra",    "Puntos extra"
    REGALO = "regalo",          "Producto de regalo"
    DOS_POR_UNO = "2x1",             "2x1"


class TipoCondicion(models.TextChoices):
    MONTO_MINIMO = "monto_minimo",  "Monto mínimo de compra"
    PLATO = "plato",         "Plato específico"
    CATEGORIA = "categoria",     "Categoría de plato"
    HORA = "hora",          "Franja horaria"
    PRIMER_PEDIDO = "primer_pedido", "Primer pedido del cliente"


class TipoDescuentoCupon(models.TextChoices):
    PORCENTAJE = "porcentaje", "Porcentaje"
    MONTO_FIJO = "monto_fijo", "Monto fijo"


class Moneda(models.TextChoices):
    COP = "COP", "Peso colombiano"
    USD = "USD", "Dólar estadounidense"
    EUR = "EUR", "Euro"
    MXN = "MXN", "Peso mexicano"
    ARS = "ARS", "Peso argentino"
    BRL = "BRL", "Real brasileño"
    CLP = "CLP", "Peso chileno"


class CuentaPuntos(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente_id = models.UUIDField(unique=True, db_index=True)
    saldo = models.PositiveIntegerField(default=0)
    puntos_totales_historicos = models.PositiveIntegerField(default=0)
    nivel = models.CharField(
        max_length=10, choices=NivelCliente.choices, default=NivelCliente.BRONCE)
    created_at = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cuenta de puntos"
        verbose_name_plural = "Cuentas de puntos"

    def __str__(self):
        return f"Cuenta {self.cliente_id} | {self.saldo} pts [{self.get_nivel_display()}]"

    def actualizar_nivel(self) -> None:
        total = self.puntos_totales_historicos
        if total >= 10000:
            self.nivel = NivelCliente.DIAMANTE
        elif total >= 5000:
            self.nivel = NivelCliente.ORO
        elif total >= 1000:
            self.nivel = NivelCliente.PLATA
        else:
            self.nivel = NivelCliente.BRONCE


class TransaccionPuntos(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cuenta = models.ForeignKey(
        CuentaPuntos, on_delete=models.PROTECT, related_name="transacciones")
    tipo = models.CharField(max_length=15, choices=TipoTransaccion.choices)
    puntos = models.IntegerField()
    saldo_anterior = models.PositiveIntegerField()
    saldo_posterior = models.PositiveIntegerField()
    pedido_id = models.UUIDField(null=True, blank=True, db_index=True)
    restaurante_id = models.UUIDField(null=True, blank=True)
    promocion_id = models.UUIDField(null=True, blank=True)
    descripcion = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Transacción de puntos"
        verbose_name_plural = "Transacciones de puntos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cuenta", "tipo"]),
            models.Index(fields=["pedido_id"]),
        ]

    def __str__(self):
        signo = "+" if self.puntos >= 0 else ""
        return f"{self.get_tipo_display()} {signo}{self.puntos} pts → saldo: {self.saldo_posterior}"


class CatalogoPlato(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plato_id = models.UUIDField(unique=True, db_index=True)
    categoria_id = models.UUIDField(null=True, blank=True, db_index=True)
    nombre = models.CharField(max_length=200)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Catálogo de plato"
        verbose_name_plural = "Catálogo de platos"

    def __str__(self):
        return f"{self.nombre} ({'activo' if self.activo else 'inactivo'})"


class CatalogoCategoria(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    categoria_id = models.UUIDField(unique=True, db_index=True)
    nombre = models.CharField(max_length=200)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Catálogo de categoría"
        verbose_name_plural = "Catálogo de categorías"

    def __str__(self):
        return f"{self.nombre} ({'activa' if self.activo else 'inactiva'})"


class Promocion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    alcance = models.CharField(max_length=10, choices=AlcancePromocion.choices)
    marca = models.CharField(max_length=100, blank=True)
    restaurante_id = models.UUIDField(null=True, blank=True, db_index=True)
    tipo_beneficio = models.CharField(
        max_length=20, choices=TipoBeneficio.choices)
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    puntos_bonus = models.PositiveIntegerField(default=0)
    multiplicador_puntos = models.DecimalField(
        max_digits=4, decimal_places=2, default=1.0)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Promoción"
        verbose_name_plural = "Promociones"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["activa", "fecha_inicio", "fecha_fin"]),
            models.Index(fields=["alcance", "activa"]),
        ]

    def __str__(self):
        return f"{self.nombre} [{self.get_alcance_display()}] — {self.get_tipo_beneficio_display()}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.alcance == AlcancePromocion.MARCA and not self.marca:
            raise ValidationError(
                "Campo 'marca' requerido cuando alcance es MARCA.")
        if self.alcance == AlcancePromocion.LOCAL and not self.restaurante_id:
            raise ValidationError(
                "Campo 'restaurante_id' requerido cuando alcance es LOCAL.")


class ReglaPromocion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promocion = models.ForeignKey(
        Promocion, on_delete=models.CASCADE, related_name="reglas")
    tipo_condicion = models.CharField(
        max_length=20, choices=TipoCondicion.choices)
    monto_minimo = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True)
    moneda = models.CharField(max_length=3, choices=Moneda.choices, blank=True)
    plato_id = models.UUIDField(null=True, blank=True, db_index=True)
    categoria_id = models.UUIDField(null=True, blank=True, db_index=True)
    hora_inicio = models.PositiveSmallIntegerField(null=True, blank=True)
    hora_fin = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Regla de promoción"
        verbose_name_plural = "Reglas de promoción"

    def __str__(self):
        return f"Regla [{self.get_tipo_condicion_display()}] → {self.promocion.nombre}"


class AplicacionPromocion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promocion = models.ForeignKey(
        Promocion, on_delete=models.PROTECT, related_name="aplicaciones")
    pedido_id = models.UUIDField(unique=True, db_index=True)
    cliente_id = models.UUIDField(db_index=True)
    descuento_aplicado = models.DecimalField(
        max_digits=12, decimal_places=2, default=0)
    puntos_bonus_otorgados = models.PositiveIntegerField(default=0)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Aplicación de promoción"
        verbose_name_plural = "Aplicaciones de promoción"
        ordering = ["-applied_at"]

    def __str__(self):
        return f"Promo '{self.promocion.nombre}' → pedido {self.pedido_id}"


class Cupon(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promocion = models.ForeignKey(
        Promocion, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="cupones")
    cliente_id = models.UUIDField(null=True, blank=True, db_index=True)
    # FIX: campo nuevo para asociar cupón a un restaurante específico
    # Permite filtrar cupones por restaurante en el gerente.
    # null = cupón global (admin), valor = cupón del restaurante (gerente)
    restaurante_id = models.UUIDField(null=True, blank=True, db_index=True)
    codigo = models.CharField(max_length=20, unique=True, db_index=True)
    tipo_descuento = models.CharField(
        max_length=10, choices=TipoDescuentoCupon.choices)
    valor_descuento = models.DecimalField(max_digits=10, decimal_places=2)
    limite_uso = models.PositiveSmallIntegerField(default=1)
    usos_actuales = models.PositiveSmallIntegerField(default=0)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cupón"
        verbose_name_plural = "Cupones"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cliente_id", "activo"]),
            # FIX: índice nuevo
            models.Index(fields=["restaurante_id", "activo"]),
        ]

    def __str__(self):
        cliente = str(self.cliente_id) if self.cliente_id else "genérico"
        return f"Cupón {self.codigo} ({cliente}) — {self.get_tipo_descuento_display()} {self.valor_descuento}"

    @property
    def disponible(self) -> bool:
        from django.utils import timezone
        hoy = timezone.now().date()
        return (
            self.activo
            and self.usos_actuales < self.limite_uso
            and self.fecha_inicio <= hoy <= self.fecha_fin
        )

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self._generar_codigo()
        super().save(*args, **kwargs)

    @staticmethod
    def _generar_codigo() -> str:
        import random
        import string
        chars = string.ascii_uppercase + string.digits
        while True:
            codigo = "".join(random.choices(chars, k=8))
            if not Cupon.objects.filter(codigo=codigo).exists():
                return codigo

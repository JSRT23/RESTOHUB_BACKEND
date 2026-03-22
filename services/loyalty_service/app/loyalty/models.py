import uuid
from django.db import models


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class NivelCliente(models.TextChoices):
    BRONCE = "bronce", "Bronce"
    PLATA = "plata",  "Plata"
    ORO = "oro",    "Oro"
    DIAMANTE = "diamante", "Diamante"


class TipoTransaccion(models.TextChoices):
    ACUMULACION = "acumulacion", "Acumulación"
    CANJE = "canje",       "Canje"
    VENCIMIENTO = "vencimiento", "Vencimiento"
    AJUSTE = "ajuste",      "Ajuste manual"
    BONO = "bono",        "Bono promocional"


class AlcancePromocion(models.TextChoices):
    GLOBAL = "global",      "Global (toda la cadena)"
    MARCA = "marca",       "Por marca"
    LOCAL = "local",       "Por restaurante"


class TipoBeneficio(models.TextChoices):
    DESCUENTO_PORCENTAJE = "descuento_pct",    "Descuento porcentual"
    DESCUENTO_MONTO = "descuento_monto",  "Descuento en monto fijo"
    PUNTOS_EXTRA = "puntos_extra",     "Puntos extra"
    REGALO = "regalo",           "Producto de regalo"
    DOS_POR_UNO = "2x1",              "2x1"


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


# ---------------------------------------------------------------------------
# CuentaPuntos
#
# Una cuenta por cliente. Se crea automáticamente la primera vez que el
# consumer recibe un evento de pedido entregado para ese cliente_id.
# El saldo se cachea en Redis con key "loyalty:puntos:{cliente_id}".
# cliente_id es UUID externo — no hay modelo Cliente en este servicio.
# ---------------------------------------------------------------------------

class CuentaPuntos(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente_id = models.UUIDField(unique=True, db_index=True)

    saldo = models.PositiveIntegerField(
        default=0,
        help_text="Puntos disponibles actualmente"
    )
    puntos_totales_historicos = models.PositiveIntegerField(
        default=0,
        help_text="Total de puntos acumulados en toda la historia (nunca decrece)"
    )
    nivel = models.CharField(
        max_length=10,
        choices=NivelCliente.choices,
        default=NivelCliente.BRONCE,
        help_text="Nivel determinado por puntos_totales_historicos"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cuenta de puntos"
        verbose_name_plural = "Cuentas de puntos"

    def __str__(self):
        return f"Cuenta {self.cliente_id} | {self.saldo} pts [{self.get_nivel_display()}]"

    def actualizar_nivel(self) -> None:
        """
        Recalcula el nivel según puntos_totales_historicos.
        Llamar después de cada acumulación y guardar con update_fields.
        """
        total = self.puntos_totales_historicos
        if total >= 10000:
            self.nivel = NivelCliente.DIAMANTE
        elif total >= 5000:
            self.nivel = NivelCliente.ORO
        elif total >= 1000:
            self.nivel = NivelCliente.PLATA
        else:
            self.nivel = NivelCliente.BRONCE


# ---------------------------------------------------------------------------
# TransaccionPuntos
#
# Historial inmutable de movimientos de puntos.
# Un solo campo `puntos` + `tipo` en lugar de dos campos donde uno
# siempre sería 0 (patrón de staff.RegistroAsistencia).
# saldo_anterior y saldo_posterior permiten auditoría completa.
# pedido_id y restaurante_id son UUIDs externos sin FK.
# ---------------------------------------------------------------------------

class TransaccionPuntos(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cuenta = models.ForeignKey(
        CuentaPuntos,
        on_delete=models.PROTECT,
        related_name="transacciones"
    )

    tipo = models.CharField(max_length=15, choices=TipoTransaccion.choices)
    puntos = models.IntegerField(
        help_text="Positivo = acumulación/bono. Negativo = canje/vencimiento."
    )
    saldo_anterior = models.PositiveIntegerField()
    saldo_posterior = models.PositiveIntegerField()

    # Referencias externas — sin FK
    pedido_id = models.UUIDField(null=True, blank=True, db_index=True)
    restaurante_id = models.UUIDField(null=True, blank=True)
    promocion_id = models.UUIDField(
        null=True, blank=True,
        help_text="Si la transacción es resultado de una promoción"
    )

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
        return (
            f"{self.get_tipo_display()} {signo}{self.puntos} pts "
            f"→ saldo: {self.saldo_posterior}"
        )


# ---------------------------------------------------------------------------
# CatalogoPlato
#
# Copia local sincronizada vía RabbitMQ (eventos app.menu.plato.*).
# Permite filtrar y evaluar promociones por plato sin depender de
# menu_service en tiempo real. plato_id es UUID externo sin FK.
# ---------------------------------------------------------------------------

class CatalogoPlato(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plato_id = models.UUIDField(unique=True, db_index=True)
    categoria_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="UUID de la categoría en menu_service"
    )
    nombre = models.CharField(max_length=200)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Catálogo de plato"
        verbose_name_plural = "Catálogo de platos"

    def __str__(self):
        return f"{self.nombre} ({'activo' if self.activo else 'inactivo'})"


# ---------------------------------------------------------------------------
# CatalogoCategoria
#
# Copia local sincronizada vía RabbitMQ (eventos app.menu.categoria.*).
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Promocion
#
# Define una campaña de fidelización. El alcance determina a quién aplica:
#   - GLOBAL: todos los restaurantes de la cadena
#   - MARCA:  todos los restaurantes de una marca específica
#   - LOCAL:  un restaurante puntual (restaurante_id requerido)
#
# Las condiciones de activación están en ReglaPromocion (relación 1:N)
# para soportar múltiples condiciones por promoción sin columnas nulas.
# ---------------------------------------------------------------------------

class Promocion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    alcance = models.CharField(max_length=10, choices=AlcancePromocion.choices)
    marca = models.CharField(
        max_length=100, blank=True,
        help_text="Nombre de la marca — requerido si alcance=MARCA"
    )
    restaurante_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="UUID del restaurante — requerido si alcance=LOCAL"
    )

    tipo_beneficio = models.CharField(
        max_length=20, choices=TipoBeneficio.choices)
    valor = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Valor del descuento (monto o porcentaje según tipo_beneficio)"
    )
    puntos_bonus = models.PositiveIntegerField(
        default=0,
        help_text="Puntos extra a otorgar — aplica cuando tipo_beneficio=PUNTOS_EXTRA"
    )
    multiplicador_puntos = models.DecimalField(
        max_digits=4, decimal_places=2, default=1.0,
        help_text="Multiplicador sobre los puntos base del pedido (ej: 2.0 = doble puntos)"
    )

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


# ---------------------------------------------------------------------------
# ReglaPromocion
#
# Condiciones que debe cumplir un pedido para que la promoción aplique.
# Una promoción puede tener varias reglas — todas deben cumplirse (AND).
# Separado de Promocion para no tener columnas nulas en la tabla principal.
# ---------------------------------------------------------------------------

class ReglaPromocion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promocion = models.ForeignKey(
        Promocion,
        on_delete=models.CASCADE,
        related_name="reglas"
    )

    tipo_condicion = models.CharField(
        max_length=20, choices=TipoCondicion.choices)

    # Monto mínimo — aplica cuando tipo_condicion=MONTO_MINIMO
    monto_minimo = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    moneda = models.CharField(
        max_length=3, choices=Moneda.choices,
        blank=True,
        help_text="Moneda del monto mínimo"
    )

    # Plato específico — aplica cuando tipo_condicion=PLATO
    plato_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="UUID del plato en menu_service"
    )

    # Categoría — aplica cuando tipo_condicion=CATEGORIA
    categoria_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="UUID de la categoría en menu_service"
    )

    # Franja horaria — aplica cuando tipo_condicion=HORA
    hora_inicio = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Hora de inicio en formato 0-23 (ej: 11 = 11:00)"
    )
    hora_fin = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Hora de fin en formato 0-23 (ej: 14 = 14:00)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Regla de promoción"
        verbose_name_plural = "Reglas de promoción"

    def __str__(self):
        return f"Regla [{self.get_tipo_condicion_display()}] → {self.promocion.nombre}"


# ---------------------------------------------------------------------------
# AplicacionPromocion
#
# Registro de cuándo y cómo se aplicó una promoción a un pedido.
# pedido_id es unique → garantiza idempotencia en el consumer:
# si el mismo evento llega dos veces, get_or_create no duplica.
# cliente_id y pedido_id son UUIDs externos sin FK.
# ---------------------------------------------------------------------------

class AplicacionPromocion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promocion = models.ForeignKey(
        Promocion,
        on_delete=models.PROTECT,
        related_name="aplicaciones"
    )

    pedido_id = models.UUIDField(unique=True, db_index=True)
    cliente_id = models.UUIDField(db_index=True)

    descuento_aplicado = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Monto de descuento aplicado al pedido"
    )
    puntos_bonus_otorgados = models.PositiveIntegerField(
        default=0,
        help_text="Puntos bonus otorgados por esta promoción"
    )

    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Aplicación de promoción"
        verbose_name_plural = "Aplicaciones de promoción"
        ordering = ["-applied_at"]

    def __str__(self):
        return (
            f"Promo '{self.promocion.nombre}' → pedido {self.pedido_id} "
            f"(descuento: {self.descuento_aplicado})"
        )


# ---------------------------------------------------------------------------
# Cupon
#
# Cupones generados para clientes. Pueden originarse de una promoción
# o crearse manualmente. cliente_id=None significa cupón genérico
# (cualquier cliente puede usarlo hasta agotar limite_uso).
# codigo es único globalmente — se genera automáticamente si no se provee.
# ---------------------------------------------------------------------------

class Cupon(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promocion = models.ForeignKey(
        Promocion,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="cupones",
        help_text="Promoción que originó este cupón — puede ser nulo si es manual"
    )

    cliente_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="UUID del cliente — nulo si el cupón es genérico"
    )

    codigo = models.CharField(max_length=20, unique=True, db_index=True)
    tipo_descuento = models.CharField(
        max_length=10, choices=TipoDescuentoCupon.choices)
    valor_descuento = models.DecimalField(max_digits=10, decimal_places=2)

    limite_uso = models.PositiveSmallIntegerField(
        default=1,
        help_text="Cantidad máxima de veces que puede usarse"
    )
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
        ]

    def __str__(self):
        cliente = str(self.cliente_id) if self.cliente_id else "genérico"
        return f"Cupón {self.codigo} ({cliente}) — {self.get_tipo_descuento_display()} {self.valor_descuento}"

    @property
    def disponible(self) -> bool:
        """True si el cupón puede usarse ahora mismo."""
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
        """Genera un código alfanumérico único de 8 caracteres."""
        import random
        import string
        chars = string.ascii_uppercase + string.digits
        while True:
            codigo = "".join(random.choices(chars, k=8))
            if not Cupon.objects.filter(codigo=codigo).exists():
                return codigo

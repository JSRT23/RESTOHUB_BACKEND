# inventory_service/app/inventory/models.py
# CAMBIO: Proveedor ahora tiene los campos de alcance (Opción B).
# El resto del archivo es idéntico al original.

import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP


# ─────────────────────────────────────────
# CHOICES
# ─────────────────────────────────────────

class UnidadMedida(models.TextChoices):
    KILOGRAMO = "kg",  "Kilogramo"
    GRAMO = "g",   "Gramo"
    LITRO = "l",   "Litro"
    MILILITRO = "ml",  "Mililitro"
    UNIDAD = "und", "Unidad"
    PORCION = "por", "Porción"


class EstadoLote(models.TextChoices):
    ACTIVO = "ACTIVO",   "Activo"
    AGOTADO = "AGOTADO",  "Agotado"
    VENCIDO = "VENCIDO",  "Vencido"
    RETIRADO = "RETIRADO", "Retirado"


class EstadoOrdenCompra(models.TextChoices):
    BORRADOR = "BORRADOR",  "Borrador"
    PENDIENTE = "PENDIENTE", "Pendiente"
    ENVIADA = "ENVIADA",   "Enviada"
    RECIBIDA = "RECIBIDA",  "Recibida"
    CANCELADA = "CANCELADA", "Cancelada"


class TipoMovimiento(models.TextChoices):
    ENTRADA = "ENTRADA",    "Entrada — lote recibido"
    SALIDA = "SALIDA",     "Salida — pedido confirmado"
    DEVOLUCION = "DEVOLUCION", "Devolución — pedido cancelado"
    AJUSTE = "AJUSTE",     "Ajuste manual"
    VENCIMIENTO = "VENCIMIENTO", "Vencimiento de lote"


class TipoAlerta(models.TextChoices):
    STOCK_BAJO = "STOCK_BAJO",  "Stock bajo mínimo"
    VENCIMIENTO = "VENCIMIENTO", "Lote próximo a vencer"
    AGOTADO = "AGOTADO",     "Ingrediente agotado"


class EstadoAlerta(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    RESUELTA = "RESUELTA",  "Resuelta"
    IGNORADA = "IGNORADA",  "Ignorada"


class Moneda(models.TextChoices):
    COP = "COP", "Peso colombiano"
    USD = "USD", "Dólar estadounidense"
    EUR = "EUR", "Euro"
    MXN = "MXN", "Peso mexicano"
    ARS = "ARS", "Peso argentino"
    BRL = "BRL", "Real brasileño"
    CLP = "CLP", "Peso chileno"


class AlcanceProveedor(models.TextChoices):
    GLOBAL = "GLOBAL", "Global — visible para todos los restaurantes"
    PAIS = "PAIS",   "País — visible para restaurantes del país indicado"
    CIUDAD = "CIUDAD", "Ciudad — visible para restaurantes de esa ciudad"
    LOCAL = "LOCAL",  "Local — solo el restaurante que lo creó"


# ─────────────────────────────────────────
# PROVEEDOR
# ─────────────────────────────────────────

class Proveedor(models.Model):
    """
    Proveedor de ingredientes de la cadena.

    Opción B — alcance por scope:
      GLOBAL  → visible para todos los restaurantes
      PAIS    → visible para restaurantes del país indicado (pais_destino)
      CIUDAD  → visible para restaurantes de esa ciudad (ciudad_destino)
      LOCAL   → solo el restaurante que lo creó (creado_por_restaurante_id)

    El gateway aplica el filtro de visibilidad en resolve_proveedores
    según el rol del JWT — el inventory_service implementa el filtro
    cuando recibe scope=gerente + restaurante_id + pais_destino + ciudad_destino.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=255)
    pais = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    moneda_preferida = models.CharField(
        max_length=10, choices=Moneda.choices, default=Moneda.USD)
    activo = models.BooleanField(default=True)

    # ── Opción B — campos de alcance ──────────────────────────────────────
    alcance = models.CharField(
        max_length=10,
        choices=AlcanceProveedor.choices,
        default=AlcanceProveedor.GLOBAL,
        help_text="Opción B: controla qué restaurantes pueden ver este proveedor.",
    )
    pais_destino = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Requerido si alcance=PAIS o alcance=CIUDAD.",
    )
    ciudad_destino = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Requerido si alcance=CIUDAD.",
    )
    creado_por_restaurante_id = models.UUIDField(
        null=True, blank=True,
        help_text="UUID del restaurante que creó este proveedor. Solo para alcance=LOCAL.",
    )
    # ──────────────────────────────────────────────────────────────────────

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["nombre"]

    def clean(self):
        if self.alcance == "PAIS" and not self.pais_destino:
            raise ValidationError(
                {"pais_destino": "Requerido para alcance=PAIS."})
        if self.alcance == "CIUDAD" and not self.ciudad_destino:
            raise ValidationError(
                {"ciudad_destino": "Requerido para alcance=CIUDAD."})
        if self.alcance == "LOCAL" and not self.creado_por_restaurante_id:
            raise ValidationError(
                {"creado_por_restaurante_id": "Requerido para alcance=LOCAL."})

    def __str__(self):
        return f"{self.nombre} ({self.pais}) [{self.alcance}]"


# ─────────────────────────────────────────
# ALMACÉN
# ─────────────────────────────────────────

class Almacen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurante_id = models.UUIDField()
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Almacén"
        verbose_name_plural = "Almacenes"
        ordering = ["restaurante_id", "nombre"]

    def __str__(self):
        return f"{self.nombre} (restaurante: {self.restaurante_id})"


# ─────────────────────────────────────────
# RECETA PLATO
# ─────────────────────────────────────────

class RecetaPlato(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plato_id = models.UUIDField()
    ingrediente_id = models.UUIDField()
    nombre_ingrediente = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    unidad_medida = models.CharField(
        max_length=10, choices=UnidadMedida.choices)
    costo_unitario = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        help_text="Precio pagado al proveedor por unidad.")
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_costo_actualizado = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Receta de Plato"
        verbose_name_plural = "Recetas de Plato"
        constraints = [
            models.UniqueConstraint(
                fields=["plato_id", "ingrediente_id"],
                name="unique_receta_plato_ingrediente"
            )
        ]

    @property
    def costo_ingrediente(self) -> float:
        return float(self.cantidad * self.costo_unitario)

    def __str__(self):
        return f"Plato {self.plato_id} — {self.nombre_ingrediente}"


# ─────────────────────────────────────────
# INGREDIENTE INVENTARIO
# ─────────────────────────────────────────

class IngredienteInventario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ingrediente_id = models.UUIDField()
    almacen = models.ForeignKey(
        Almacen, on_delete=models.CASCADE, related_name="ingredientes")
    nombre_ingrediente = models.CharField(max_length=255)
    unidad_medida = models.CharField(
        max_length=10, choices=UnidadMedida.choices)
    cantidad_actual = models.DecimalField(
        max_digits=10, decimal_places=3, default=0)
    nivel_minimo = models.DecimalField(
        max_digits=10, decimal_places=3, default=0)
    nivel_maximo = models.DecimalField(
        max_digits=10, decimal_places=3, default=0)
    lote_actual = models.ForeignKey(
        "LoteIngrediente", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="en_uso")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ingrediente en Inventario"
        verbose_name_plural = "Ingredientes en Inventario"
        constraints = [
            models.UniqueConstraint(
                fields=["ingrediente_id", "almacen"],
                name="unique_ingrediente_almacen"
            )
        ]

    def clean(self):
        errores = {}
        if self.nivel_minimo < 0:
            errores["nivel_minimo"] = "El nivel mínimo no puede ser negativo."
        if self.nivel_maximo < self.nivel_minimo:
            errores["nivel_maximo"] = "El nivel máximo debe ser mayor al mínimo."
        if self.cantidad_actual < 0:
            errores["cantidad_actual"] = "La cantidad actual no puede ser negativa."
        if errores:
            raise ValidationError(errores)

    @property
    def necesita_reposicion(
        self): return self.cantidad_actual <= self.nivel_minimo

    @property
    def esta_agotado(self): return self.cantidad_actual == 0

    @property
    def porcentaje_stock(self):
        if self.nivel_maximo == 0:
            return 0
        return float(self.cantidad_actual / self.nivel_maximo * 100)

    def __str__(self):
        return f"{self.nombre_ingrediente} — {self.almacen.nombre} ({self.cantidad_actual} {self.unidad_medida})"


# ─────────────────────────────────────────
# LOTE INGREDIENTE
# ─────────────────────────────────────────

class LoteIngrediente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ingrediente_id = models.UUIDField()
    almacen = models.ForeignKey(
        Almacen, on_delete=models.CASCADE, related_name="lotes")
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, related_name="lotes")
    numero_lote = models.CharField(max_length=100)
    fecha_produccion = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField()
    cantidad_recibida = models.DecimalField(max_digits=10, decimal_places=3)
    cantidad_actual = models.DecimalField(max_digits=10, decimal_places=3)
    unidad_medida = models.CharField(
        max_length=10, choices=UnidadMedida.choices)
    estado = models.CharField(
        max_length=20, choices=EstadoLote.choices, default=EstadoLote.ACTIVO)
    fecha_recepcion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lote de Ingrediente"
        verbose_name_plural = "Lotes de Ingrediente"
        ordering = ["fecha_vencimiento"]

    def clean(self):
        if self.cantidad_actual > self.cantidad_recibida:
            raise ValidationError(
                {"cantidad_actual": "La cantidad actual no puede superar la recibida."})
        if self.fecha_produccion and self.fecha_vencimiento <= self.fecha_produccion:
            raise ValidationError(
                {"fecha_vencimiento": "Debe ser posterior a la fecha de producción."})

    @property
    def esta_vencido(self):
        if self.fecha_vencimiento is None:
            return None
        return self.fecha_vencimiento < timezone.now().date()

    @property
    def dias_para_vencer(self):
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - timezone.now().date()).days

    def __str__(self):
        return f"Lote {self.numero_lote} — {self.almacen.nombre} ({self.estado})"


# ─────────────────────────────────────────
# INGREDIENTE (caché local de menu_service)
# ─────────────────────────────────────────

class Ingrediente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ingrediente_id = models.UUIDField(unique=True, db_index=True,
                                      help_text="UUID del ingrediente en menu_service")
    nombre = models.CharField(max_length=255)
    unidad_medida = models.CharField(max_length=10, choices=UnidadMedida.choices,
                                     default=UnidadMedida.UNIDAD)
    activo = models.BooleanField(default=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ingrediente (caché)"
        verbose_name_plural = "Ingredientes (caché)"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.unidad_medida})"


# ─────────────────────────────────────────
# MOVIMIENTO INVENTARIO
# ─────────────────────────────────────────

class MovimientoInventario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ingrediente_inventario = models.ForeignKey(
        IngredienteInventario, on_delete=models.CASCADE, related_name="movimientos")
    lote = models.ForeignKey(LoteIngrediente, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="movimientos")
    tipo_movimiento = models.CharField(
        max_length=20, choices=TipoMovimiento.choices)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    cantidad_antes = models.DecimalField(max_digits=10, decimal_places=3)
    cantidad_despues = models.DecimalField(max_digits=10, decimal_places=3)
    pedido_id = models.UUIDField(null=True, blank=True)
    orden_compra_id = models.UUIDField(null=True, blank=True)
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"
        ordering = ["-fecha"]

    def clean(self):
        if self.cantidad <= 0:
            raise ValidationError(
                {"cantidad": "La cantidad del movimiento debe ser mayor a 0."})

    def __str__(self):
        return f"{self.tipo_movimiento} — {self.cantidad} ({self.fecha})"


# ─────────────────────────────────────────
# ORDEN DE COMPRA
# ─────────────────────────────────────────

class OrdenCompra(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, related_name="ordenes")
    restaurante_id = models.UUIDField()
    estado = models.CharField(max_length=20, choices=EstadoOrdenCompra.choices,
                              default=EstadoOrdenCompra.BORRADOR)
    moneda = models.CharField(
        max_length=10, choices=Moneda.choices, default=Moneda.USD)
    total_estimado = models.DecimalField(
        max_digits=12, decimal_places=2, default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_entrega_estimada = models.DateTimeField(null=True, blank=True)
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Orden de Compra"
        verbose_name_plural = "Órdenes de Compra"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"OC-{str(self.id)[:8]} — {self.proveedor.nombre} ({self.estado})"

    def calcular_total(self):
        total = sum(d.subtotal for d in self.detalles.all())
        self.total_estimado = total
        self.save(update_fields=["total_estimado"])


# ─────────────────────────────────────────
# DETALLE ORDEN COMPRA
# ─────────────────────────────────────────

class DetalleOrdenCompra(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    orden = models.ForeignKey(
        OrdenCompra, on_delete=models.CASCADE, related_name="detalles")
    ingrediente_id = models.UUIDField()
    nombre_ingrediente = models.CharField(max_length=255)
    unidad_medida = models.CharField(
        max_length=10, choices=UnidadMedida.choices)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    cantidad_recibida = models.DecimalField(max_digits=10, decimal_places=3, default=0,
                                            help_text="Se actualiza al recibir la orden — puede ser menor a la pedida.")
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Detalle de Orden de Compra"
        verbose_name_plural = "Detalles de Orden de Compra"

    def clean(self):
        if self.cantidad <= 0:
            raise ValidationError(
                {"cantidad": "La cantidad debe ser mayor a 0."})
        if self.precio_unitario <= 0:
            raise ValidationError(
                {"precio_unitario": "El precio debe ser mayor a 0."})
        if self.cantidad_recibida > self.cantidad:
            raise ValidationError(
                {"cantidad_recibida": "No se puede recibir más de lo pedido."})

    def save(self, *args, **kwargs):
        subtotal = Decimal(self.precio_unitario) * Decimal(self.cantidad)
        self.subtotal = subtotal.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_ingrediente} — {self.cantidad} {self.unidad_medida}"


# ─────────────────────────────────────────
# ALERTA STOCK
# ─────────────────────────────────────────

class AlertaStock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ingrediente_inventario = models.ForeignKey(
        IngredienteInventario, on_delete=models.CASCADE, related_name="alertas")
    almacen = models.ForeignKey(
        Almacen, on_delete=models.CASCADE, related_name="alertas")
    restaurante_id = models.UUIDField()
    ingrediente_id = models.UUIDField()
    tipo_alerta = models.CharField(max_length=20, choices=TipoAlerta.choices)
    estado = models.CharField(max_length=20, choices=EstadoAlerta.choices,
                              default=EstadoAlerta.PENDIENTE)
    nivel_actual = models.DecimalField(max_digits=10, decimal_places=3)
    nivel_minimo = models.DecimalField(max_digits=10, decimal_places=3)
    lote = models.ForeignKey(LoteIngrediente, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="alertas")
    fecha_alerta = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Alerta de Stock"
        verbose_name_plural = "Alertas de Stock"
        ordering = ["-fecha_alerta"]

    def resolver(self):
        self.estado = EstadoAlerta.RESUELTA
        self.fecha_resolucion = timezone.now()
        self.save(update_fields=["estado", "fecha_resolucion"])

    def __str__(self):
        return f"{self.tipo_alerta} — restaurante {self.restaurante_id} ({self.estado})"

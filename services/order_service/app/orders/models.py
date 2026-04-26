import uuid
from django.db import models


class CanalPedido(models.TextChoices):
    TPV = "TPV",       "TPV Presencial"
    APP = "APP",       "App Cliente"
    UBER_EATS = "UBER_EATS", "Uber Eats"
    RAPPI = "RAPPI",     "Rappi"


class EstadoPedido(models.TextChoices):
    RECIBIDO = "RECIBIDO",       "Recibido"
    EN_PREPARACION = "EN_PREPARACION", "En Preparación"
    LISTO = "LISTO",          "Listo"
    EN_CAMINO = "EN_CAMINO",      "En Camino"
    ENTREGADO = "ENTREGADO",      "Entregado"
    CANCELADO = "CANCELADO",      "Cancelado"


class PrioridadPedido(models.IntegerChoices):
    BAJA = 1, "Baja"
    NORMAL = 2, "Normal"
    ALTA = 3, "Alta"
    URGENTE = 4, "Urgente"


class MetodoPago(models.TextChoices):
    EFECTIVO = "efectivo",      "Efectivo"
    TARJETA = "tarjeta",       "Tarjeta"
    NEQUI = "nequi",         "Nequi"
    DAVIPLATA = "daviplata",     "Daviplata"
    TRANSFERENCIA = "transferencia", "Transferencia"


class EstacionCocina(models.TextChoices):
    PARRILLA = "PARRILLA", "Parrilla"
    BEBIDAS = "BEBIDAS",  "Bebidas"
    POSTRES = "POSTRES",  "Postres"
    FRIOS = "FRIOS",    "Fríos"
    GENERAL = "GENERAL",  "General"


class EstadoComanda(models.TextChoices):
    PENDIENTE = "PENDIENTE",  "Pendiente"
    PREPARANDO = "PREPARANDO", "Preparando"
    LISTO = "LISTO",      "Listo"


class TipoEntrega(models.TextChoices):
    LOCAL = "LOCAL",    "En Local"
    PICKUP = "PICKUP",   "Pickup"
    DELIVERY = "DELIVERY", "Delivery"


class EstadoEntrega(models.TextChoices):
    PENDIENTE = "PENDIENTE",  "Pendiente"
    EN_CAMINO = "EN_CAMINO",  "En Camino"
    ENTREGADO = "ENTREGADO",  "Entregado"
    FALLIDO = "FALLIDO",    "Fallido"


class Pedido(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurante_id = models.UUIDField()
    cliente_id = models.UUIDField(null=True, blank=True)
    canal = models.CharField(
        max_length=20, choices=CanalPedido.choices, default=CanalPedido.TPV)
    estado = models.CharField(
        max_length=20, choices=EstadoPedido.choices, default=EstadoPedido.RECIBIDO)
    prioridad = models.IntegerField(
        choices=PrioridadPedido.choices, default=PrioridadPedido.NORMAL)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=10)
    mesa_id = models.UUIDField(null=True, blank=True)

    # ── NUEVO: método de pago registrado al cobrar ────────────────────────
    metodo_pago = models.CharField(
        max_length=20,
        choices=MetodoPago.choices,
        null=True,
        blank=True,
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_entrega_estimada = models.DateTimeField(null=True, blank=True)

    # Número correlativo del día por restaurante (Pedido #1, #2... del día)
    numero_dia = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-prioridad", "fecha_creacion"]
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self):
        return f"Pedido {self.id} - {self.canal} - {self.estado}"


class DetallePedido(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="detalles")
    plato_id = models.UUIDField()
    nombre_plato = models.CharField(max_length=255)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Detalle de Pedido"
        verbose_name_plural = "Detalles de Pedido"

    def __str__(self):
        return f"{self.cantidad}x {self.nombre_plato} (Pedido {self.pedido_id})"

    def save(self, *args, **kwargs):
        self.subtotal = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)


class ComandaCocina(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="comandas")
    estacion = models.CharField(
        max_length=20, choices=EstacionCocina.choices, default=EstacionCocina.GENERAL)
    estado = models.CharField(
        max_length=20, choices=EstadoComanda.choices, default=EstadoComanda.PENDIENTE)
    hora_envio = models.DateTimeField(auto_now_add=True)
    hora_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Comanda de Cocina"
        verbose_name_plural = "Comandas de Cocina"

    def __str__(self):
        return f"Comanda {self.id} - {self.estacion} - {self.estado}"

    @property
    def tiempo_preparacion_segundos(self):
        if self.hora_fin and self.hora_envio:
            return (self.hora_fin - self.hora_envio).total_seconds()
        return None


class SeguimientoPedido(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="seguimientos")
    estado = models.CharField(max_length=20, choices=EstadoPedido.choices)
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["fecha"]
        verbose_name = "Seguimiento de Pedido"
        verbose_name_plural = "Seguimientos de Pedido"

    def __str__(self):
        return f"Pedido {self.pedido_id} → {self.estado} ({self.fecha})"


class EntregaPedido(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.OneToOneField(
        Pedido, on_delete=models.CASCADE, related_name="entrega")
    tipo_entrega = models.CharField(
        max_length=20, choices=TipoEntrega.choices, default=TipoEntrega.LOCAL)
    direccion = models.TextField(blank=True, null=True)
    repartidor_id = models.UUIDField(null=True, blank=True)
    repartidor_nombre = models.CharField(max_length=255, blank=True, null=True)
    estado_entrega = models.CharField(
        max_length=20, choices=EstadoEntrega.choices, default=EstadoEntrega.PENDIENTE)
    fecha_salida = models.DateTimeField(null=True, blank=True)
    fecha_entrega_real = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Entrega de Pedido"
        verbose_name_plural = "Entregas de Pedido"

    def __str__(self):
        return f"Entrega {self.tipo_entrega} - Pedido {self.pedido_id} - {self.estado_entrega}"

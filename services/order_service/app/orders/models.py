import uuid
from django.db import models


# ─────────────────────────────────────────
# CHOICES
# ─────────────────────────────────────────

class CanalPedido(models.TextChoices):
    TPV = "TPV", "TPV Presencial"
    APP = "APP", "App Cliente"
    UBER_EATS = "UBER_EATS", "Uber Eats"
    RAPPI = "RAPPI", "Rappi"


class EstadoPedido(models.TextChoices):
    RECIBIDO = "RECIBIDO", "Recibido"
    EN_PREPARACION = "EN_PREPARACION", "En Preparación"
    LISTO = "LISTO", "Listo"
    EN_CAMINO = "EN_CAMINO", "En Camino"
    ENTREGADO = "ENTREGADO", "Entregado"
    CANCELADO = "CANCELADO", "Cancelado"


class PrioridadPedido(models.IntegerChoices):
    BAJA = 1, "Baja"
    NORMAL = 2, "Normal"
    ALTA = 3, "Alta"
    URGENTE = 4, "Urgente"


class EstacionCocina(models.TextChoices):
    PARRILLA = "PARRILLA", "Parrilla"
    BEBIDAS = "BEBIDAS", "Bebidas"
    POSTRES = "POSTRES", "Postres"
    FRIOS = "FRIOS", "Fríos"
    GENERAL = "GENERAL", "General"


class EstadoComanda(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    PREPARANDO = "PREPARANDO", "Preparando"
    LISTO = "LISTO", "Listo"


class TipoEntrega(models.TextChoices):
    LOCAL = "LOCAL", "En Local"
    PICKUP = "PICKUP", "Pickup"
    DELIVERY = "DELIVERY", "Delivery"


class EstadoEntrega(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    EN_CAMINO = "EN_CAMINO", "En Camino"
    ENTREGADO = "ENTREGADO", "Entregado"
    FALLIDO = "FALLIDO", "Fallido"


# ─────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────

class Pedido(models.Model):
    """
    Orden completa realizada por un cliente.
    restaurante_id y cliente_id son referencias externas (sin FK real)
    hacia menu_service y el futuro user_service respectivamente.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Referencias externas a otros microservicios
    restaurante_id = models.UUIDField()
    # null para pedidos anónimos / TPV
    cliente_id = models.UUIDField(null=True, blank=True)

    canal = models.CharField(
        max_length=20,
        choices=CanalPedido.choices,
        default=CanalPedido.TPV
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoPedido.choices,
        default=EstadoPedido.RECIBIDO
    )
    prioridad = models.IntegerField(
        choices=PrioridadPedido.choices,
        default=PrioridadPedido.NORMAL
    )

    # Información económica
    total = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=10)  # ISO 4217: COP, USD, EUR...

    # Para canal TPV — referencia a mesa (futuro table_service o campo simple)
    mesa_id = models.UUIDField(null=True, blank=True)

    # Tiempos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_entrega_estimada = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-prioridad", "fecha_creacion"]
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self):
        return f"Pedido {self.id} - {self.canal} - {self.estado}"


class DetallePedido(models.Model):
    """
    Ítems individuales dentro de un pedido.
    Se guarda snapshot de nombre y precio para desacoplar de menu_service.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles"
    )

    # Referencia externa + snapshot de menu_service
    plato_id = models.UUIDField()
    # snapshot al momento del pedido
    nombre_plato = models.CharField(max_length=255)
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2)  # snapshot del precio

    cantidad = models.PositiveIntegerField()
    # precio_unitario * cantidad
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    # Notas especiales del cliente (sin cebolla, extra queso, etc.)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Detalle de Pedido"
        verbose_name_plural = "Detalles de Pedido"

    def __str__(self):
        return f"{self.cantidad}x {self.nombre_plato} (Pedido {self.pedido_id})"

    def save(self, *args, **kwargs):
        # Calcular subtotal automáticamente antes de guardar
        self.subtotal = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)


class ComandaCocina(models.Model):
    """
    Orden enviada a una estación de cocina específica.
    Un pedido puede generar múltiples comandas (una por estación).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="comandas"
    )
    estacion = models.CharField(
        max_length=20,
        choices=EstacionCocina.choices,
        default=EstacionCocina.GENERAL
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoComanda.choices,
        default=EstadoComanda.PENDIENTE
    )

    hora_envio = models.DateTimeField(auto_now_add=True)
    # para medir SLA de preparación
    hora_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Comanda de Cocina"
        verbose_name_plural = "Comandas de Cocina"

    def __str__(self):
        return f"Comanda {self.id} - {self.estacion} - {self.estado}"

    @property
    def tiempo_preparacion_segundos(self):
        """Calcula el tiempo de preparación si la comanda ya finalizó."""
        if self.hora_fin and self.hora_envio:
            return (self.hora_fin - self.hora_envio).total_seconds()
        return None


class SeguimientoPedido(models.Model):
    """
    Log de eventos de estado del pedido.
    Permite hacer tracking del progreso al cliente y auditoría interna.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="seguimientos"
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoPedido.choices
    )
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["fecha"]
        verbose_name = "Seguimiento de Pedido"
        verbose_name_plural = "Seguimientos de Pedido"

    def __str__(self):
        return f"Pedido {self.pedido_id} → {self.estado} ({self.fecha})"


class EntregaPedido(models.Model):
    """
    Información de entrega del pedido.
    Relación 1:1 con Pedido.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.CASCADE,
        related_name="entrega"
    )
    tipo_entrega = models.CharField(
        max_length=20,
        choices=TipoEntrega.choices,
        default=TipoEntrega.LOCAL
    )
    direccion = models.TextField(blank=True, null=True)  # solo para DELIVERY

    # Repartidor: string ahora, UUID cuando staff_service esté disponible
    # referencia futura a staff_service
    repartidor_id = models.UUIDField(null=True, blank=True)
    repartidor_nombre = models.CharField(
        max_length=255, blank=True, null=True)  # fallback

    estado_entrega = models.CharField(
        max_length=20,
        choices=EstadoEntrega.choices,
        default=EstadoEntrega.PENDIENTE
    )

    fecha_salida = models.DateTimeField(null=True, blank=True)
    fecha_entrega_real = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Entrega de Pedido"
        verbose_name_plural = "Entregas de Pedido"

    def __str__(self):
        return f"Entrega {self.tipo_entrega} - Pedido {self.pedido_id} - {self.estado_entrega}"

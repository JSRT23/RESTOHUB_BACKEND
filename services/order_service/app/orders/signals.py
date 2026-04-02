# order_service/app/orders/signals.py
"""
Signals de order_service.

order_service es el dueño de los eventos más importantes del sistema.
Los publica cuando el estado del pedido cambia.

Regla: usar get_publisher() (singleton), nunca publisher.close().
"""
from django.db.models.signals import pre_save
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from app.orders.events.builders import OrderEventBuilder
from app.orders.events.event_types import OrderEvents
from app.orders.infrastructure.messaging.publisher import get_publisher
from app.orders.models import Pedido

logger = logging.getLogger(__name__)

# Rastreamos estado anterior para saber si cambió
# Django no guarda estado previo automáticamente
# Usamos una técnica simple: pre_save + post_save


_estado_anterior: dict[str, str] = {}


@receiver(pre_save, sender=Pedido)
def capturar_estado_anterior(sender, instance: Pedido, **kwargs):
    """Guarda el estado antes de guardar para detectar transiciones."""
    if instance.pk:
        try:
            _estado_anterior[str(instance.pk)] = (
                Pedido.objects.filter(pk=instance.pk)
                .values_list("estado", flat=True)
                .first()
            )
        except Exception:
            pass


@receiver(post_save, sender=Pedido)
def publish_pedido_event(sender, instance: Pedido, created: bool, **kwargs):
    try:
        publisher = get_publisher()

        if created:
            # Pedido recién creado → ya está en RECIBIDO
            # No publicamos aquí: esperamos a que el TPV/API confirme el pago
            # La confirmación la hace la vista/serializer → cambia estado a CONFIRMADO
            return

        estado_prev = _estado_anterior.pop(str(instance.pk), None)
        estado_now = instance.estado

        # Sin cambio de estado → sin evento
        if estado_prev == estado_now:
            return

        # ── CONFIRMADO ────────────────────────────────────────
        # → inventory descuenta stock
        # → staff asigna cocina
        # → loyalty evalúa promociones
        if estado_now == "EN_PREPARACION" and estado_prev == "RECIBIDO":
            publisher.publish(
                OrderEvents.PEDIDO_CONFIRMADO,
                OrderEventBuilder.pedido_confirmado(instance),
            )
            logger.info(f"📤 pedido.confirmado → {instance.id}")

        # ── CANCELADO ─────────────────────────────────────────
        # → inventory devuelve stock
        # → loyalty anula puntos si ya se habían otorgado
        elif estado_now == "CANCELADO":
            publisher.publish(
                OrderEvents.PEDIDO_CANCELADO,
                OrderEventBuilder.pedido_cancelado(instance),
            )
            logger.info(f"📤 pedido.cancelado → {instance.id}")

        # ── ENTREGADO ─────────────────────────────────────────
        # → loyalty acumula puntos del cliente
        elif estado_now == "ENTREGADO":
            publisher.publish(
                OrderEvents.PEDIDO_ENTREGADO,
                OrderEventBuilder.pedido_entregado(instance),
            )
            logger.info(f"📤 pedido.entregado → {instance.id}")

    except Exception:
        logger.exception(
            f"💥 Error publicando evento de pedido → {instance.id}")

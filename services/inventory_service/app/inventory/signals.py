# inventory_service/app/inventory/signals.py
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from app.inventory.events.builders import InventoryEventBuilder
from app.inventory.events.event_types import InventoryEvents
from app.inventory.infrastructure.messaging.publisher import get_publisher  # ✅ singleton
from app.inventory.models import (
    AlertaStock,
    LoteIngrediente,
    OrdenCompra,
)

logger = logging.getLogger(__name__)


# =========================================================
# 🚨 ALERTAS — solo las creadas fuera de order_handlers
# (ej: alertas de vencimiento generadas por un cron)
# Las alertas de stock bajo las publica order_handlers
# directamente para tener el contexto completo.
# =========================================================

@receiver(post_save, sender=AlertaStock)
def alerta_creada(sender, instance, created, **kwargs):
    if not created:
        return

    # Las alertas STOCK_BAJO y AGOTADO las publica order_handlers
    # para evitar double-publish. Aquí solo cubrimos VENCIMIENTO
    # que viene de un proceso distinto (cron de verificación).
    if instance.tipo_alerta != "VENCIMIENTO":
        return

    try:
        publisher = get_publisher()  # ✅ singleton, sin close()
        publisher.publish(
            InventoryEvents.ALERTA_VENCIMIENTO_PROXIMO,
            InventoryEventBuilder.alerta_vencimiento_proximo(
                instance),  # ✅ nombre correcto
        )
        logger.info(f"🚨 Alerta vencimiento publicada → {instance.id}")

    except Exception:
        logger.exception("💥 Error publicando alerta.vencimiento_proximo")


# =========================================================
# 🧪 LOTES
# =========================================================

@receiver(post_save, sender=LoteIngrediente)
def lote_recibido(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        publisher = get_publisher()  # ✅ singleton
        publisher.publish(
            InventoryEvents.LOTE_RECIBIDO,
            InventoryEventBuilder.lote_recibido(instance),
        )
        logger.info(f"🧪 Lote recibido publicado → {instance.id}")

    except Exception:
        logger.exception("💥 Error publicando lote.recibido")


# =========================================================
# 🛒 ÓRDENES DE COMPRA
# =========================================================

_ESTADO_A_EVENTO = {
    "ENVIADA":   InventoryEvents.ORDEN_COMPRA_ENVIADA,
    "RECIBIDA":  InventoryEvents.ORDEN_COMPRA_RECIBIDA,
    "CANCELADA": InventoryEvents.ORDEN_COMPRA_CANCELADA,
}

_ESTADO_A_BUILDER = {
    "ENVIADA":   InventoryEventBuilder.orden_compra_enviada,    # ✅ métodos que existen
    "RECIBIDA":  InventoryEventBuilder.orden_compra_recibida,
    "CANCELADA": InventoryEventBuilder.orden_compra_cancelada,
}


@receiver(post_save, sender=OrdenCompra)
def orden_compra_eventos(sender, instance, created, **kwargs):
    try:
        publisher = get_publisher()  # ✅ singleton

        if created:
            publisher.publish(
                InventoryEvents.ORDEN_COMPRA_CREADA,
                InventoryEventBuilder.orden_compra_creada(instance),
            )
        else:
            event_type = _ESTADO_A_EVENTO.get(instance.estado)
            builder = _ESTADO_A_BUILDER.get(instance.estado)

            if not event_type:
                return  # BORRADOR, PENDIENTE → sin evento

            publisher.publish(event_type, builder(instance))

        logger.info(
            f"🛒 OrdenCompra evento publicado → {instance.estado} ({instance.id})")

    except Exception:
        logger.exception("💥 Error publicando evento de orden_compra")

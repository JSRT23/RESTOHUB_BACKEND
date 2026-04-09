# inventory_service/app/inventory/signals.py
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from app.inventory.events.builders import InventoryEventBuilder
from app.inventory.events.event_types import InventoryEvents
from app.inventory.infrastructure.messaging.publisher import get_publisher
from app.inventory.models import (
    AlertaStock,
    LoteIngrediente,
    OrdenCompra,
)

logger = logging.getLogger(__name__)


# =========================================================
# 🚨 ALERTAS DE VENCIMIENTO
#
# Las alertas STOCK_BAJO y AGOTADO las publica order_handlers
# directamente para tener el contexto completo y evitar
# double-publish. Aquí solo cubrimos VENCIMIENTO, que viene
# de un proceso distinto (cron de verificación de lotes).
# =========================================================

@receiver(post_save, sender=AlertaStock)
def alerta_creada(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.tipo_alerta != "VENCIMIENTO":
        return

    # Las alertas de vencimiento están asociadas a un lote.
    # El builder necesita: lote_id, fecha_vencimiento, dias_para_vencer.
    # Estos datos viven en LoteIngrediente, no en AlertaStock.
    # Si no hay lote asociado, no podemos construir el payload completo.
    if not instance.lote_id:
        logger.warning(
            f"⚠️ Alerta VENCIMIENTO sin lote asociado → {instance.id} — evento no publicado"
        )
        return

    try:
        lote = instance.lote

        payload = {
            "alerta_id":          str(instance.id),
            "lote_id":            str(lote.id),
            "ingrediente_id":     str(instance.ingrediente_id),
            "restaurante_id":     str(instance.restaurante_id),
            "almacen_id":         str(instance.almacen_id),
            "nombre_ingrediente": instance.ingrediente_inventario.nombre_ingrediente,
            "fecha_vencimiento":  lote.fecha_vencimiento.isoformat() if lote.fecha_vencimiento else None,
            "dias_para_vencer":   lote.dias_para_vencer,
        }

        get_publisher().publish(
            InventoryEvents.ALERTA_VENCIMIENTO_PROXIMO,
            payload,
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
        get_publisher().publish(
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
    "ENVIADA":   InventoryEventBuilder.orden_compra_enviada,
    "RECIBIDA":  InventoryEventBuilder.orden_compra_recibida,
    "CANCELADA": InventoryEventBuilder.orden_compra_cancelada,
}


@receiver(post_save, sender=OrdenCompra)
def orden_compra_eventos(sender, instance, created, **kwargs):
    try:
        publisher = get_publisher()

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
            f"🛒 OrdenCompra evento publicado → {instance.estado} ({instance.id})"
        )

    except Exception:
        logger.exception("💥 Error publicando evento de orden_compra")

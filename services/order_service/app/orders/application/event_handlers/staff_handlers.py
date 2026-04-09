# order_service/app/orders/signals.py
"""
Signals de order_service.

CORRECCIONES:
1. _estado_anterior en dict de memoria NO es seguro en multi-worker.
   Fix: consultamos el estado previo directamente desde DB en pre_save.
   Usamos instance.__estado_previo como atributo de instancia (vive en el
   mismo request cycle — pre_save y post_save son síncronos en el mismo worker).

2. Doble pedido.confirmado:
   El signal publica pedido.confirmado cuando RECIBIDO→EN_PREPARACION.
   Pero staff_handlers.handle_cocina_asignacion_creada también llama
   pedido.save(estado=EN_PREPARACION) desde el consumer, lo que dispararía
   OTRO pedido.confirmado → inventory descontaría stock dos veces.

   Fix: pedido.confirmado SOLO se publica cuando el cambio lo hace la API
   (acción confirmar() de la vista). El consumer de staff solo llama
   _avanzar_estado_sin_evento() para no disparar el signal.

   Implementación: el consumer usa update() en lugar de save() para no
   disparar el signal de Django en esas transiciones controladas.
   Ver staff_handlers.py corregido.
"""
import logging

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from app.orders.events.builders import OrderEventBuilder
from app.orders.events.event_types import OrderEvents
from app.orders.infrastructure.messaging.publisher import get_publisher
from app.orders.models import Pedido

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Pedido)
def capturar_estado_anterior(sender, instance: Pedido, **kwargs):
    """
    Guarda el estado previo como atributo de la instancia.
    Pre_save y post_save ocurren síncronamente en el mismo worker/thread,
    así que el atributo sobrevive entre ambos signals.
    Para instancias nuevas (sin pk) el estado previo es None.
    """
    if instance.pk:
        try:
            estado_db = (
                Pedido.objects
                .filter(pk=instance.pk)
                .values_list("estado", flat=True)
                .first()
            )
            instance.__estado_previo = estado_db
        except Exception:
            instance.__estado_previo = None
    else:
        instance.__estado_previo = None


@receiver(post_save, sender=Pedido)
def publish_pedido_event(sender, instance: Pedido, created: bool, **kwargs):
    try:
        publisher = get_publisher()

        if created:
            # Pedido recién creado en RECIBIDO — no publicar aún.
            # Se publica pedido.confirmado cuando pasa a EN_PREPARACION
            # desde la vista confirmar() o desde el TPV.
            return

        estado_prev = getattr(instance, "__estado_previo", None)
        estado_now = instance.estado

        if estado_prev == estado_now:
            return

        # ── CONFIRMADO ────────────────────────────────────────────────────
        # RECIBIDO → EN_PREPARACION (disparado desde la vista confirmar())
        # inventory descuenta stock / staff asigna cocina / loyalty evalúa
        #
        # ⚠️ El consumer de staff_handlers usa QuerySet.update() para avanzar
        # estado sin pasar por save() → no dispara este signal → no hay doble evento.
        if estado_now == "EN_PREPARACION" and estado_prev == "RECIBIDO":
            publisher.publish(
                OrderEvents.PEDIDO_CONFIRMADO,
                OrderEventBuilder.pedido_confirmado(instance),
            )
            logger.info(f"📤 pedido.confirmado → {instance.id}")

        # ── CANCELADO ─────────────────────────────────────────────────────
        elif estado_now == "CANCELADO":
            publisher.publish(
                OrderEvents.PEDIDO_CANCELADO,
                OrderEventBuilder.pedido_cancelado(instance),
            )
            logger.info(f"📤 pedido.cancelado → {instance.id}")

        # ── ENTREGADO ─────────────────────────────────────────────────────
        elif estado_now == "ENTREGADO":
            publisher.publish(
                OrderEvents.PEDIDO_ENTREGADO,
                OrderEventBuilder.pedido_entregado(instance),
            )
            logger.info(f"📤 pedido.entregado → {instance.id}")

    except Exception:
        logger.exception(
            f"💥 Error publicando evento de pedido → {instance.id}")

# order_service/app/orders/application/event_handlers/staff_handlers.py
"""
Handlers de eventos del staff_service para order_service.

CORRECCIONES:
1. handle_entrega_asignada: staff_builders envía 'repartidor_id', no 'empleado_id'.
   Fix: data.get("repartidor_id") en lugar de data.get("empleado_id").

2. handle_cocina_asignacion_creada y handle_cocina_asignacion_completada:
   Usaban pedido.save(update_fields=["estado"]) que DISPARA el signal de Django
   → publish_pedido_event publica pedido.confirmado otra vez → inventory
   descontaría stock dos veces.

   Fix: usar QuerySet.update() que NO dispara signals de Django.
   El seguimiento se crea manualmente (como antes), pero el save() del pedido
   se reemplaza por Pedido.objects.filter(pk=...).update(estado=...).
   La publicación de pedido.confirmado SOLO la hace la vista confirmar() de la API.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)


def _registrar_seguimiento(pedido, estado: str, descripcion: str = "") -> None:
    from app.orders.models import SeguimientoPedido
    SeguimientoPedido.objects.create(
        pedido=pedido,
        estado=estado,
        descripcion=descripcion,
    )


# ─────────────────────────────────────────
# 🍳 COCINA — ASIGNACION CREADA
# ─────────────────────────────────────────

def handle_cocina_asignacion_creada(data: dict) -> None:
    """
    staff asignó un cocinero → Pedido pasa a EN_PREPARACION.
    ✅ Usa QuerySet.update() — NO dispara signal → NO publica pedido.confirmado doble.
    pedido.confirmado ya fue publicado cuando la vista confirmar() cambió RECIBIDO→EN_PREPARACION.
    """
    try:
        from app.orders.models import ComandaCocina, Pedido

        pedido_id = data.get("pedido_id")
        if not pedido_id:
            logger.warning("❌ cocina.asignacion.creada sin pedido_id")
            return

        try:
            pedido = Pedido.objects.get(id=UUID(pedido_id))
        except Pedido.DoesNotExist:
            logger.warning(f"⚠️ Pedido no encontrado → {pedido_id}")
            return

        if pedido.estado != "RECIBIDO":
            logger.info(
                f"⏭️ Pedido ya en estado '{pedido.estado}' — sin cambio")
            return

        # ✅ update() NO dispara signals — evita doble pedido.confirmado
        Pedido.objects.filter(pk=pedido.pk).update(estado="EN_PREPARACION")

        _registrar_seguimiento(
            pedido,
            estado="EN_PREPARACION",
            descripcion="Cocinero asignado por staff_service",
        )

        # Actualizar ComandaCocina si existe
        ComandaCocina.objects.filter(
            pedido=pedido, estado="PENDIENTE",
        ).update(estado="PREPARANDO")

        logger.info(f"👨‍🍳 Pedido → EN_PREPARACION (via staff) | {pedido_id}")

    except Exception:
        logger.exception("💥 Error en cocina.asignacion.creada (order)")
        raise


# ─────────────────────────────────────────
# 🍳 COCINA — ASIGNACION COMPLETADA
# ─────────────────────────────────────────

def handle_cocina_asignacion_completada(data: dict) -> None:
    """
    Cocina terminó → Pedido pasa a LISTO.
    ✅ Usa QuerySet.update() — NO dispara signals.
    """
    try:
        from app.orders.models import ComandaCocina, Pedido
        from django.utils import timezone as dj_timezone

        pedido_id = data.get("pedido_id")
        if not pedido_id:
            logger.warning("❌ cocina.asignacion.completada sin pedido_id")
            return

        try:
            pedido = Pedido.objects.get(id=UUID(pedido_id))
        except Pedido.DoesNotExist:
            logger.warning(f"⚠️ Pedido no encontrado → {pedido_id}")
            return

        if pedido.estado != "EN_PREPARACION":
            logger.info(
                f"⏭️ Pedido ya en estado '{pedido.estado}' — sin cambio")
            return

        # ✅ update() NO dispara signals
        Pedido.objects.filter(pk=pedido.pk).update(estado="LISTO")

        _registrar_seguimiento(
            pedido,
            estado="LISTO",
            descripcion="Preparación completada por cocina",
        )

        ComandaCocina.objects.filter(
            pedido=pedido, estado="PREPARANDO",
        ).update(estado="LISTO", hora_fin=dj_timezone.now())

        logger.info(f"✅ Pedido → LISTO | {pedido_id}")

    except Exception:
        logger.exception("💥 Error en cocina.asignacion.completada (order)")
        raise


# ─────────────────────────────────────────
# 🚚 ENTREGA — ASIGNADA
# ─────────────────────────────────────────

def handle_entrega_asignada(data: dict) -> None:
    """
    staff asignó repartidor → Pedido pasa a EN_CAMINO.
    ✅ Fix: usa data.get("repartidor_id") — staff builders envía repartidor_id, no empleado_id.
    ✅ Usa QuerySet.update() para el pedido — NO dispara signals innecesarios.
    Publica app.order.entrega.asignada para loyalty/analytics.
    """
    try:
        from app.orders.models import EntregaPedido, Pedido

        pedido_id = data.get("pedido_id")
        # ✅ CORREGIDO: staff_builders envía "repartidor_id", no "empleado_id"
        repartidor_id = data.get("repartidor_id")

        if not pedido_id:
            logger.warning("❌ entrega.asignada sin pedido_id")
            return

        try:
            pedido = Pedido.objects.get(id=UUID(pedido_id))
        except Pedido.DoesNotExist:
            logger.warning(f"⚠️ Pedido no encontrado → {pedido_id}")
            return

        if pedido.estado not in ("LISTO", "EN_PREPARACION"):
            logger.info(f"⏭️ Pedido en estado '{pedido.estado}' — sin cambio")
            return

        # ✅ update() NO dispara signals
        Pedido.objects.filter(pk=pedido.pk).update(estado="EN_CAMINO")

        _registrar_seguimiento(
            pedido,
            estado="EN_CAMINO",
            descripcion=f"Repartidor asignado: {repartidor_id}",
        )

        # Actualizar o crear EntregaPedido
        entrega, _ = EntregaPedido.objects.get_or_create(pedido=pedido)
        update_fields = ["estado_entrega", "fecha_salida"]

        entrega.estado_entrega = "EN_CAMINO"
        entrega.fecha_salida = datetime.now(tz=timezone.utc)

        if repartidor_id:
            entrega.repartidor_id = UUID(repartidor_id)
            update_fields.append("repartidor_id")

        entrega.save(update_fields=update_fields)

        # Publicar app.order.entrega.asignada
        from app.orders.events.builders import OrderEventBuilder
        from app.orders.events.event_types import OrderEvents
        from app.orders.infrastructure.messaging.publisher import get_publisher

        get_publisher().publish(
            OrderEvents.ENTREGA_ASIGNADA,
            OrderEventBuilder.entrega_asignada(
                pedido=pedido,
                repartidor_id=str(repartidor_id) if repartidor_id else "",
                direccion=getattr(entrega, "direccion", "") or "",
            ),
        )

        logger.info(f"🚚 Pedido → EN_CAMINO | {pedido_id}")

    except Exception:
        logger.exception("💥 Error en entrega.asignada (order)")
        raise

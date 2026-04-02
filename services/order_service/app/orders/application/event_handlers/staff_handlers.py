# order_service/app/orders/application/event_handlers/staff_handlers.py
"""
Handlers de eventos del staff_service para order_service.

Flujo de estados del pedido controlado por staff:

  staff.cocina.asignacion.creada     → Pedido: RECIBIDO → EN_PREPARACION
                                       ComandaCocina: PENDIENTE → PREPARANDO

  staff.cocina.asignacion.completada → Pedido: EN_PREPARACION → LISTO
                                       ComandaCocina: PREPARANDO → LISTO

  staff.entrega.asignada             → Pedido: LISTO → EN_CAMINO
                                       EntregaPedido: crear/actualizar repartidor
                                       Publica: app.order.entrega.asignada → loyalty/analytics
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# HELPER: registrar seguimiento
# ─────────────────────────────────────────

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

        # Idempotencia: solo avanzar si está en RECIBIDO
        if pedido.estado != "RECIBIDO":
            logger.info(
                f"⏭️ Pedido ya en estado '{pedido.estado}' — sin cambio")
            return

        pedido.estado = "EN_PREPARACION"
        pedido.save(update_fields=["estado"])

        _registrar_seguimiento(
            pedido,
            estado="EN_PREPARACION",
            descripcion=f"Cocinero asignado por staff_service",
        )

        # Actualizar ComandaCocina si existe
        ComandaCocina.objects.filter(
            pedido=pedido,
            estado="PENDIENTE",
        ).update(estado="PREPARANDO")

        logger.info(f"👨‍🍳 Pedido → EN_PREPARACION | {pedido_id}")

    except Exception:
        logger.exception("💥 Error en cocina.asignacion.creada (order)")
        raise


# ─────────────────────────────────────────
# 🍳 COCINA — ASIGNACION COMPLETADA
# ─────────────────────────────────────────

def handle_cocina_asignacion_completada(data: dict) -> None:
    """
    Cocina terminó → Pedido pasa a LISTO.
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

        pedido.estado = "LISTO"
        pedido.save(update_fields=["estado"])

        _registrar_seguimiento(
            pedido,
            estado="LISTO",
            descripcion="Preparación completada por cocina",
        )

        # Cerrar ComandaCocina
        ComandaCocina.objects.filter(
            pedido=pedido,
            estado="PREPARANDO",
        ).update(
            estado="LISTO",
            hora_fin=dj_timezone.now(),
        )

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
    Publica app.order.entrega.asignada para que loyalty/analytics lo sepan.
    """
    try:
        from app.orders.models import EntregaPedido, Pedido

        pedido_id = data.get("pedido_id")
        repartidor_id = data.get("empleado_id")  # staff envía empleado_id

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

        pedido.estado = "EN_CAMINO"
        pedido.save(update_fields=["estado"])

        _registrar_seguimiento(
            pedido,
            estado="EN_CAMINO",
            descripcion=f"Repartidor asignado: {repartidor_id}",
        )

        # Actualizar o crear EntregaPedido
        entrega, _ = EntregaPedido.objects.get_or_create(pedido=pedido)
        if repartidor_id:
            entrega.repartidor_id = UUID(repartidor_id)
            entrega.estado_entrega = "EN_CAMINO"
            entrega.fecha_salida = datetime.now(tz=timezone.utc)
            entrega.save(update_fields=[
                         "repartidor_id", "estado_entrega", "fecha_salida"])

        # Publicar app.order.entrega.asignada
        from app.orders.events.builders import OrderEventBuilder
        from app.orders.events.event_types import OrderEvents
        from app.orders.infrastructure.messaging.publisher import get_publisher

        get_publisher().publish(
            OrderEvents.ENTREGA_ASIGNADA,
            OrderEventBuilder.entrega_asignada(
                pedido=pedido,
                repartidor_id=repartidor_id or "",
                direccion=getattr(entrega, "direccion", "") or "",
            ),
        )

        logger.info(f"🚚 Pedido → EN_CAMINO | {pedido_id}")

    except Exception:
        logger.exception("💥 Error en entrega.asignada (order)")
        raise

# staff_service/app/staff/application/event_handlers/order_handlers.py
"""
Handlers de eventos del order_service para staff_service.

staff_service no es dueño del pedido, pero necesita:
- pedido.confirmado → crear AsignacionCocina (asignar cocinero disponible)
- entrega.asignada  → crear ServicioEntrega  (registrar repartidor)
"""
import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def handle_pedido_confirmado(data: dict) -> None:
    """
    Crea una AsignacionCocina para el pedido.

    Busca un cocinero activo con turno activo en ese restaurante.
    Si no hay cocinero disponible, deja el registro sin cocinero
    y emite una alerta operacional.
    """
    try:
        from app.staff.models import (
            AsignacionCocina,
            AlertaOperacional,
            Empleado,
            EstacionCocina,
            RolEmpleado,
            EstadoTurno,
        )

        pedido_id = data.get("pedido_id")
        restaurante_id = data.get("restaurante_id")

        if not pedido_id or not restaurante_id:
            logger.warning(
                "❌ pedido.confirmado sin pedido_id o restaurante_id")
            return

        # Idempotencia: no crear dos asignaciones para el mismo pedido
        if AsignacionCocina.objects.filter(pedido_id=UUID(pedido_id)).exists():
            logger.info(f"⏭️ AsignacionCocina ya existe → {pedido_id}")
            return

        # Buscar estación general del restaurante
        estacion = EstacionCocina.objects.filter(
            restaurante_id=UUID(restaurante_id),
            activa=True,
        ).first()

        # Buscar cocinero disponible con turno activo
        cocinero = (
            Empleado.objects
            .filter(
                restaurante__restaurante_id=UUID(restaurante_id),
                rol__in=[RolEmpleado.COCINERO, RolEmpleado.AUXILIAR],
                activo=True,
                turnos__estado=EstadoTurno.ACTIVO,
            )
            .first()
        )

        if not cocinero:
            logger.warning(
                f"⚠️ Sin cocinero disponible → restaurante {restaurante_id}")
            AlertaOperacional.objects.create(
                restaurante_id=UUID(restaurante_id),
                tipo="stock_bajo",     # reusar tipo más cercano o agregar PERSONAL_BAJO
                nivel="urgente",
                mensaje=f"Sin cocinero disponible para pedido {pedido_id}",
            )
            return

        if not estacion:
            logger.warning(
                f"⚠️ Sin estación activa → restaurante {restaurante_id}")
            return

        AsignacionCocina.objects.create(
            pedido_id=UUID(pedido_id),
            # 1:1 hasta que order_service mande comanda_id separado
            comanda_id=UUID(pedido_id),
            cocinero=cocinero,
            estacion=estacion,
        )

        logger.info(
            f"👨‍🍳 AsignacionCocina creada → pedido {pedido_id} / cocinero {cocinero}")

    except Exception:
        logger.exception("💥 Error en pedido.confirmado (staff)")
        raise


def handle_entrega_asignada(data: dict) -> None:
    """
    Crea un ServicioEntrega cuando order_service asigna un repartidor.
    """
    try:
        from app.staff.models import ServicioEntrega, Empleado, RolEmpleado

        pedido_id = data.get("pedido_id")
        repartidor_id = data.get("repartidor_id")

        if not pedido_id or not repartidor_id:
            logger.warning("❌ entrega.asignada sin pedido_id o repartidor_id")
            return

        # Idempotencia
        if ServicioEntrega.objects.filter(pedido_id=UUID(pedido_id)).exists():
            logger.info(f"⏭️ ServicioEntrega ya existe → {pedido_id}")
            return

        try:
            repartidor = Empleado.objects.get(
                id=UUID(repartidor_id),
                rol=RolEmpleado.REPARTIDOR,
                activo=True,
            )
        except Empleado.DoesNotExist:
            logger.warning(f"⚠️ Repartidor no encontrado → {repartidor_id}")
            return

        ServicioEntrega.objects.create(
            pedido_id=UUID(pedido_id),
            repartidor=repartidor,
        )

        logger.info(
            f"🚚 ServicioEntrega creado → pedido {pedido_id} / repartidor {repartidor}")

    except Exception:
        logger.exception("💥 Error en entrega.asignada (staff)")
        raise

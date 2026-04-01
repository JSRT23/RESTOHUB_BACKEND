# inventory_service/app/inventory/application/event_handlers/order_handlers.py
"""
Handlers de eventos del order_service.

Cambios respecto a la versión anterior:
✅ Nombres de modelos correctos (IngredienteInventario, RecetaPlato)
✅ F() expressions — updates atómicos, sin race condition
✅ Idempotencia — registra event_id para no procesar dos veces
✅ Genera AlertaStock cuando el stock baja del mínimo
✅ Publica stock.actualizado y alerta.* al final
✅ Validación de payload con schemas antes de tocar la BD
"""
import logging

from django.db import transaction
from django.db.models import F

from app.inventory.events.builders import InventoryEventBuilder
from app.inventory.events.event_types import InventoryEvents
from app.inventory.infrastructure.messaging.publisher import get_publisher

from .schemas import PedidoCanceladoSchema, PedidoConfirmadoSchema, SchemaError

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# IDEMPOTENCIA
# ─────────────────────────────────────────

def _ya_procesado(event_id: str | None) -> bool:
    """
    Revisa si este event_id ya fue procesado.

    Requiere un modelo ProcessedEvent en tu app:

        class ProcessedEvent(models.Model):
            event_id   = models.CharField(max_length=36, unique=True, db_index=True)
            processed_at = models.DateTimeField(auto_now_add=True)

    Si no existe ese modelo aún, créalo con una migración simple.
    Mientras tanto puedes comentar este check y añadirlo después.
    """
    if not event_id:
        return False

    try:
        from app.inventory.models import ProcessedEvent
        _, created = ProcessedEvent.objects.get_or_create(event_id=event_id)
        return not created   # True → ya existía → ya procesado
    except ImportError:
        # Modelo no creado aún → saltar idempotencia por ahora
        logger.warning(
            "⚠️ ProcessedEvent no existe — idempotencia desactivada")
        return False


# ─────────────────────────────────────────
# HELPER: descontar / devolver stock
# ─────────────────────────────────────────

def _ajustar_stock(
    restaurante_id,
    detalles: list,
    signo: int,          # -1 para confirmado, +1 para cancelado
    pedido_id: str,
    tipo_movimiento: str,
) -> None:
    """
    Ajusta el stock de todos los ingredientes involucrados en un pedido.

    signo = -1 → descuento (pedido confirmado)
    signo = +1 → devolución (pedido cancelado)

    Usa F() para que el UPDATE sea atómico en la BD —
    sin leer el valor primero, imposible race condition.
    """
    from app.inventory.models import (
        AlertaStock,
        IngredienteInventario,
        MovimientoInventario,
        RecetaPlato,
    )

    publisher = get_publisher()

    for item in detalles:
        plato_id = item.plato_id
        cantidad_pedido = item.cantidad

        recetas = RecetaPlato.objects.filter(plato_id=plato_id)

        if not recetas.exists():
            logger.warning(f"⚠️ Sin receta para plato {plato_id}")
            continue

        for receta in recetas:
            cantidad_total = receta.cantidad * cantidad_pedido

            try:
                stock = IngredienteInventario.objects.select_for_update().get(
                    ingrediente_id=receta.ingrediente_id,
                    almacen__restaurante_id=restaurante_id,
                )
            except IngredienteInventario.DoesNotExist:
                logger.warning(
                    f"⚠️ Sin stock registrado para ingrediente {receta.ingrediente_id}")
                continue

            cantidad_antes = float(stock.cantidad_actual)

            # ✅ Update atómico — sin race condition
            IngredienteInventario.objects.filter(pk=stock.pk).update(
                cantidad_actual=F("cantidad_actual") + (signo * cantidad_total)
            )
            stock.refresh_from_db()

            cantidad_despues = float(stock.cantidad_actual)

            logger.info(
                f"{'📉' if signo < 0 else '📈'} Stock ajustado → "
                f"{receta.nombre_ingrediente}: {cantidad_antes} → {cantidad_despues}"
            )

            # ── Movimiento de inventario (audit log) ──────────────
            MovimientoInventario.objects.create(
                ingrediente_inventario=stock,
                tipo_movimiento=tipo_movimiento,
                cantidad=float(cantidad_total),
                cantidad_antes=cantidad_antes,
                cantidad_despues=cantidad_despues,
                pedido_id=pedido_id,
            )

            # ── Publicar stock.actualizado ────────────────────────
            publisher.publish(
                InventoryEvents.STOCK_ACTUALIZADO,
                InventoryEventBuilder.stock_actualizado(
                    ingrediente_id=receta.ingrediente_id,
                    almacen_id=stock.almacen_id,
                    restaurante_id=restaurante_id,
                    cantidad_anterior=cantidad_antes,
                    cantidad_nueva=cantidad_despues,
                    unidad_medida=stock.unidad_medida,
                    tipo_movimiento=tipo_movimiento,
                ),
            )

            # ── Alertas de stock ──────────────────────────────────
            # Solo al descontar (no al devolver)
            if signo < 0:
                _generar_alertas_si_aplica(stock, restaurante_id, publisher)


def _generar_alertas_si_aplica(stock, restaurante_id, publisher) -> None:
    """
    Crea AlertaStock y publica evento si el nivel bajó del mínimo.
    Evita duplicar alertas PENDIENTE para el mismo ingrediente.
    """
    from app.inventory.models import AlertaStock, TipoAlerta, EstadoAlerta

    if stock.esta_agotado:
        tipo = TipoAlerta.AGOTADO
        evento = InventoryEvents.ALERTA_AGOTADO
    elif stock.necesita_reposicion:
        tipo = TipoAlerta.STOCK_BAJO
        evento = InventoryEvents.ALERTA_STOCK_BAJO
    else:
        return  # Stock OK

    # Evitar duplicar alertas PENDIENTE
    ya_existe = AlertaStock.objects.filter(
        ingrediente_id=stock.ingrediente_id,
        restaurante_id=restaurante_id,
        tipo_alerta=tipo,
        estado=EstadoAlerta.PENDIENTE,
    ).exists()

    if ya_existe:
        return

    alerta = AlertaStock.objects.create(
        ingrediente_inventario=stock,
        almacen=stock.almacen,
        restaurante_id=restaurante_id,
        ingrediente_id=stock.ingrediente_id,
        tipo_alerta=tipo,
        nivel_actual=stock.cantidad_actual,
        nivel_minimo=stock.nivel_minimo,
    )

    builder_fn = (
        InventoryEventBuilder.alerta_agotado
        if tipo == TipoAlerta.AGOTADO
        else InventoryEventBuilder.alerta_stock_bajo
    )

    publisher.publish(evento, builder_fn(alerta))

    logger.warning(
        f"🚨 Alerta {tipo} generada → {stock.nombre_ingrediente} "
        f"(actual: {stock.cantidad_actual}, mínimo: {stock.nivel_minimo})"
    )


# ─────────────────────────────────────────
# HANDLERS PÚBLICOS
# ─────────────────────────────────────────

def handle_pedido_confirmado(data: dict) -> None:
    """
    Descuenta stock por cada ingrediente de los platos pedidos.
    """
    # 1. Idempotencia
    event_id = data.get("event_id")
    if _ya_procesado(event_id):
        logger.info(f"⏭️ Evento ya procesado → {event_id}")
        return

    # 2. Validar payload
    try:
        payload = PedidoConfirmadoSchema.from_dict(data)
    except SchemaError as e:
        logger.error(f"❌ Payload inválido en pedido.confirmado: {e}")
        raise  # re-lanzar para que consumer_base aplique NACK + retry

    # 3. Ajustar stock dentro de una transacción
    logger.info(f"📦 Procesando pedido confirmado → {payload.pedido_id}")

    with transaction.atomic():
        _ajustar_stock(
            restaurante_id=payload.restaurante_id,
            detalles=payload.detalles,
            signo=-1,
            pedido_id=str(payload.pedido_id),
            tipo_movimiento="SALIDA",
        )


def handle_pedido_cancelado(data: dict) -> None:
    """
    Devuelve stock cuando un pedido se cancela.
    """
    event_id = data.get("event_id")
    if _ya_procesado(event_id):
        logger.info(f"⏭️ Evento ya procesado → {event_id}")
        return

    try:
        payload = PedidoCanceladoSchema.from_dict(data)
    except SchemaError as e:
        logger.error(f"❌ Payload inválido en pedido.cancelado: {e}")
        raise

    logger.info(f"🔄 Revirtiendo pedido cancelado → {payload.pedido_id}")

    with transaction.atomic():
        _ajustar_stock(
            restaurante_id=payload.restaurante_id,
            detalles=payload.detalles,
            signo=+1,
            pedido_id=str(payload.pedido_id),
            tipo_movimiento="DEVOLUCION",
        )

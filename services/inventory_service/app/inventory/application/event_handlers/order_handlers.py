# inventory_service/app/inventory/application/event_handlers/order_handlers.py
# CAMBIOS vs original:
#   1. import requests (ya está en requirements.txt)
#   2. función _get_nombre_plato() — consulta menu_service con timeout 2s
#   3. En _ajustar_stock: llama _get_nombre_plato() y pasa descripcion
#      al MovimientoInventario.objects.create()
# TODO lo demás es BYTE-FOR-BYTE idéntico al original.

import logging
import requests

from django.db import transaction
from django.db.models import F

from app.inventory.events.builders import InventoryEventBuilder
from app.inventory.events.event_types import InventoryEvents
from app.inventory.infrastructure.messaging.publisher import get_publisher

from .schemas import PedidoCanceladoSchema, PedidoConfirmadoSchema, SchemaError

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# NUEVO: nombre del plato desde menu_service
# ─────────────────────────────────────────

def _get_nombre_plato(plato_id: str) -> str:
    """
    Consulta menu_service para obtener el nombre del plato.
    Timeout 2 s — nunca bloquea el consumer de RabbitMQ.
    Si falla por cualquier razón devuelve el ID corto.
    """
    try:
        from django.conf import settings
        menu_url = getattr(settings, "MENU_SERVICE_URL",
                           "http://menu_service:8000/api/menu")
        resp = requests.get(f"{menu_url}/platos/{plato_id}/", timeout=2)
        if resp.status_code == 200:
            return resp.json().get("nombre") or f"Plato {str(plato_id)[:8].upper()}"
    except Exception:
        pass
    return f"Plato {str(plato_id)[:8].upper()}"


# ─────────────────────────────────────────
# IDEMPOTENCIA  (sin cambios)
# ─────────────────────────────────────────

def _ya_procesado(event_id: str | None) -> bool:
    if not event_id:
        return False
    try:
        from app.inventory.models import ProcessedEvent
        _, created = ProcessedEvent.objects.get_or_create(event_id=event_id)
        return not created
    except ImportError:
        logger.warning(
            "⚠️ ProcessedEvent no existe — idempotencia desactivada")
        return False


# ─────────────────────────────────────────
# HELPER: descontar / devolver stock  (MODIFICADO — agrega descripcion)
# ─────────────────────────────────────────

def _ajustar_stock(
    restaurante_id,
    detalles: list,
    signo: int,
    pedido_id: str,
    tipo_movimiento: str,
) -> None:
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

        # Obtener nombre del plato una sola vez por plato (no por ingrediente)
        nombre_plato = _get_nombre_plato(str(plato_id))

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

            IngredienteInventario.objects.filter(pk=stock.pk).update(
                cantidad_actual=F("cantidad_actual") + (signo * cantidad_total)
            )
            stock.refresh_from_db()

            cantidad_despues = float(stock.cantidad_actual)

            logger.info(
                f"{'📉' if signo < 0 else '📈'} Stock ajustado → "
                f"{receta.nombre_ingrediente}: {cantidad_antes} → {cantidad_despues}"
            )

            # ── Descripción legible para el gerente ───────────────
            if tipo_movimiento == "SALIDA":
                descripcion = (
                    f"{nombre_plato} × {int(cantidad_pedido)} "
                    f"— {float(receta.cantidad):.3g} {receta.unidad_medida} "
                    f"de {receta.nombre_ingrediente}"
                )
            elif tipo_movimiento == "DEVOLUCION":
                descripcion = (
                    f"Devolución: {nombre_plato} × {int(cantidad_pedido)} "
                    f"(pedido #{str(pedido_id)[:8].upper()} cancelado)"
                )
            else:
                descripcion = None

            # ── Movimiento de inventario (audit log) ──────────────
            MovimientoInventario.objects.create(
                ingrediente_inventario=stock,
                tipo_movimiento=tipo_movimiento,
                cantidad=float(cantidad_total),
                cantidad_antes=cantidad_antes,
                cantidad_despues=cantidad_despues,
                pedido_id=pedido_id,
                descripcion=descripcion,          # ← ÚNICO CAMPO NUEVO
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
            if signo < 0:
                _generar_alertas_si_aplica(stock, restaurante_id, publisher)


# ─────────────────────────────────────────
# _generar_alertas_si_aplica  (sin cambios)
# ─────────────────────────────────────────

def _generar_alertas_si_aplica(stock, restaurante_id, publisher) -> None:
    from app.inventory.models import AlertaStock, TipoAlerta, EstadoAlerta

    if stock.esta_agotado:
        tipo = TipoAlerta.AGOTADO
        evento = InventoryEvents.ALERTA_AGOTADO
    elif stock.necesita_reposicion:
        tipo = TipoAlerta.STOCK_BAJO
        evento = InventoryEvents.ALERTA_STOCK_BAJO
    else:
        return

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
# HANDLERS PÚBLICOS  (sin cambios)
# ─────────────────────────────────────────

def handle_pedido_confirmado(data: dict) -> None:
    """Descuenta stock por cada ingrediente de los platos pedidos."""
    event_id = data.get("event_id")
    if _ya_procesado(event_id):
        logger.info(f"⏭️ Evento ya procesado → {event_id}")
        return

    try:
        payload = PedidoConfirmadoSchema.from_dict(data)
    except SchemaError as e:
        logger.error(f"❌ Payload inválido en pedido.confirmado: {e}")
        raise

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
    """Devuelve stock cuando un pedido se cancela."""
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

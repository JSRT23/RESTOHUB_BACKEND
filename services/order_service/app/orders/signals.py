import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from app.orders.events.event_types import OrderEvents
from app.orders.services.rabbitmq import publish_event

logger = logging.getLogger(__name__)


def _sid(value):
    return str(value) if value is not None else None


# ---------------------------------------------------------------------------
# Pedido
# Los imports del modelo van dentro del receiver para evitar
# ImportError si el modelo no existe o cambia de nombre.
# ---------------------------------------------------------------------------

def connect_pedido_signal():
    try:
        from app.orders.models import Pedido

        @receiver(post_save, sender=Pedido)
        def pedido_saved(sender, instance, created, update_fields, **kwargs):

            if created:
                try:
                    detalles = [
                        {
                            "detalle_id":      _sid(d.id),
                            "plato_id":        _sid(d.plato_id),
                            "nombre_plato":    getattr(d, "nombre_plato", ""),
                            "cantidad":        d.cantidad,
                            "precio_unitario": str(d.precio_unitario),
                            "subtotal":        str(d.subtotal),
                        }
                        for d in instance.detalles.all()
                    ]
                except Exception:
                    detalles = []

                publish_event(OrderEvents.PEDIDO_CREADO, {
                    "pedido_id":      _sid(instance.id),
                    "restaurante_id": _sid(instance.restaurante_id),
                    "cliente_id":     _sid(getattr(instance, "cliente_id", None)),
                    "canal":          getattr(instance, "canal", ""),
                    "estado":         instance.estado,
                    "total":          str(instance.total),
                    "moneda":         getattr(instance, "moneda", ""),
                    "detalles":       detalles,
                })
                return

            if not update_fields or "estado" not in update_fields:
                return

            estado = instance.estado

            if estado in ("EN_PREPARACION", "CONFIRMADO"):
                try:
                    detalles = [
                        {
                            "detalle_id":   _sid(d.id),
                            "plato_id":     _sid(d.plato_id),
                            "nombre_plato": getattr(d, "nombre_plato", ""),
                            "cantidad":     d.cantidad,
                            "precio_unitario": str(d.precio_unitario),
                            "subtotal":     str(d.subtotal),
                        }
                        for d in instance.detalles.all()
                    ]
                except Exception:
                    detalles = []

                publish_event(OrderEvents.PEDIDO_CONFIRMADO, {
                    "pedido_id":      _sid(instance.id),
                    "restaurante_id": _sid(instance.restaurante_id),
                    "cliente_id":     _sid(getattr(instance, "cliente_id", None)),
                    "total":          str(instance.total),
                    "moneda":         getattr(instance, "moneda", ""),
                    "detalles":       detalles,
                })

            elif estado == "CANCELADO":
                publish_event(OrderEvents.PEDIDO_CANCELADO, {
                    "pedido_id":      _sid(instance.id),
                    "restaurante_id": _sid(instance.restaurante_id),
                    "cliente_id":     _sid(getattr(instance, "cliente_id", None)),
                    "motivo":         getattr(instance, "motivo_cancelacion", ""),
                    "total":          str(instance.total),
                    "moneda":         getattr(instance, "moneda", ""),
                })

            elif estado == "ENTREGADO":
                publish_event(OrderEvents.PEDIDO_ENTREGADO, {
                    "pedido_id":         _sid(instance.id),
                    "restaurante_id":    _sid(instance.restaurante_id),
                    "cliente_id":        _sid(getattr(instance, "cliente_id", None)),
                    "total":             str(instance.total),
                    "moneda":            getattr(instance, "moneda", ""),
                    "fecha_entrega_real": (
                        instance.fecha_entrega_real.isoformat()
                        if getattr(instance, "fecha_entrega_real", None) else None
                    ),
                })

            else:
                publish_event(OrderEvents.PEDIDO_ESTADO_ACTUALIZADO, {
                    "pedido_id":    _sid(instance.id),
                    "estado_nuevo": estado,
                    "timestamp":    (
                        instance.updated_at.isoformat()
                        if hasattr(instance, "updated_at") else None
                    ),
                })

    except ImportError:
        logger.warning(
            "[order_signals] Modelo Pedido no encontrado — signal no conectado.")


# ---------------------------------------------------------------------------
# Comanda — solo se conecta si el modelo existe
# ---------------------------------------------------------------------------

def connect_comanda_signal():
    try:
        from app.orders.models import Comanda

        @receiver(post_save, sender=Comanda)
        def comanda_saved(sender, instance, created, update_fields, **kwargs):
            if created:
                publish_event(OrderEvents.COMANDA_CREADA, {
                    "comanda_id":     _sid(instance.id),
                    "pedido_id":      _sid(instance.pedido_id),
                    "restaurante_id": _sid(instance.pedido.restaurante_id),
                    "estacion":       getattr(instance, "estacion", ""),
                    "estado":         getattr(instance, "estado", ""),
                    "hora_envio":     (
                        instance.hora_envio.isoformat()
                        if getattr(instance, "hora_envio", None) else None
                    ),
                })
                return

            if update_fields and "estado" in update_fields:
                estado = getattr(instance, "estado", "")
                if estado == "LISTA":
                    tiempo = None
                    if getattr(instance, "hora_envio", None) and getattr(instance, "hora_fin", None):
                        tiempo = int(
                            (instance.hora_fin - instance.hora_envio).total_seconds())
                    publish_event(OrderEvents.COMANDA_LISTA, {
                        "comanda_id":                  _sid(instance.id),
                        "pedido_id":                   _sid(instance.pedido_id),
                        "restaurante_id":              _sid(instance.pedido.restaurante_id),
                        "estacion":                    getattr(instance, "estacion", ""),
                        "hora_envio":                  (
                            instance.hora_envio.isoformat()
                            if getattr(instance, "hora_envio", None) else None
                        ),
                        "hora_fin":                    (
                            instance.hora_fin.isoformat()
                            if getattr(instance, "hora_fin", None) else None
                        ),
                        "tiempo_preparacion_segundos": tiempo,
                    })

    except ImportError:
        logger.warning(
            "[order_signals] Modelo Comanda no encontrado — signal no conectado.")


# ---------------------------------------------------------------------------
# Entrega — solo se conecta si el modelo existe
# ---------------------------------------------------------------------------

def connect_entrega_signal():
    try:
        from app.orders.models import Entrega

        @receiver(post_save, sender=Entrega)
        def entrega_saved(sender, instance, created, update_fields, **kwargs):
            if created:
                publish_event(OrderEvents.ENTREGA_ASIGNADA, {
                    "entrega_id":        _sid(instance.id),
                    "pedido_id":         _sid(instance.pedido_id),
                    "tipo_entrega":      getattr(instance, "tipo_entrega", ""),
                    "repartidor_id":     _sid(getattr(instance, "repartidor_id", None)),
                    "repartidor_nombre": getattr(instance, "repartidor_nombre", ""),
                    "direccion":         getattr(instance, "direccion", ""),
                })
                return

            if update_fields and "estado" in update_fields:
                estado = getattr(instance, "estado", "")
                if estado == "COMPLETADA":
                    publish_event(OrderEvents.ENTREGA_COMPLETADA, {
                        "entrega_id":         _sid(instance.id),
                        "pedido_id":          _sid(instance.pedido_id),
                        "restaurante_id":     _sid(instance.pedido.restaurante_id),
                        "cliente_id":         _sid(instance.pedido.cliente_id),
                        "tipo_entrega":       getattr(instance, "tipo_entrega", ""),
                        "fecha_entrega_real": (
                            instance.fecha_entrega_real.isoformat()
                            if getattr(instance, "fecha_entrega_real", None) else None
                        ),
                    })
                elif estado == "FALLIDA":
                    publish_event(OrderEvents.ENTREGA_FALLIDA, {
                        "entrega_id": _sid(instance.id),
                        "pedido_id":  _sid(instance.pedido_id),
                        "motivo":     getattr(instance, "motivo_falla", ""),
                    })

    except ImportError:
        logger.warning(
            "[order_signals] Modelo Entrega no encontrado — signal no conectado.")


# ---------------------------------------------------------------------------
# Conectar todos los signals disponibles
# El try/except por modelo permite que el servicio arranque aunque
# algunos modelos no existan todavía.
# ---------------------------------------------------------------------------

connect_pedido_signal()
connect_comanda_signal()
connect_entrega_signal()

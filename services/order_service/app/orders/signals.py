import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Pedido, DetallePedido, ComandaCocina, SeguimientoPedido, EntregaPedido
from .events.event_types import OrderEvents
from .services.rabbitmq import publish_event

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# Helper
# ─────────────────────────────────────────

def _sid(value):
    """UUID / Decimal / cualquier valor a string seguro. None → None."""
    return str(value) if value is not None else None


def _detalles(pedido):
    """
    Serializa los detalles del pedido para incluirlos en el payload.
    Snapshot completo: plato_id, nombre, precio, cantidad, subtotal.
    inventory_service usa esto para descontar stock por ingrediente.
    """
    return [
        {
            "detalle_id":     _sid(d.id),
            "plato_id":       _sid(d.plato_id),
            "nombre_plato":   d.nombre_plato,
            "precio_unitario": str(d.precio_unitario),
            "cantidad":       d.cantidad,
            "subtotal":       str(d.subtotal),
            "notas":          d.notas,
        }
        for d in pedido.detalles.all()
    ]


# ─────────────────────────────────────────
# PEDIDO
# El signal detecta el estado para disparar el evento correcto:
#   RECIBIDO    → PEDIDO_CREADO
#   CONFIRMADO  → PEDIDO_CONFIRMADO  (si tu flujo lo tiene)
#   CANCELADO   → PEDIDO_CANCELADO
#   ENTREGADO   → PEDIDO_ENTREGADO
#   cualquier   → PEDIDO_ESTADO_ACTUALIZADO (siempre, para tracking)
# ─────────────────────────────────────────

@receiver(post_save, sender=Pedido)
def pedido_saved(sender, instance, created, update_fields, **kwargs):

    if created:
        # Al crear el pedido los detalles aún no existen (se crean después).
        # Publicamos el pedido sin detalles — DetallePedido tiene su propio signal.
        publish_event(OrderEvents.PEDIDO_CREADO, {
            "pedido_id":              _sid(instance.id),
            "restaurante_id":         _sid(instance.restaurante_id),
            "cliente_id":             _sid(instance.cliente_id),
            "canal":                  instance.canal,
            "estado":                 instance.estado,
            "prioridad":              instance.prioridad,
            "total":                  str(instance.total),
            "moneda":                 instance.moneda,
            "mesa_id":                _sid(instance.mesa_id),
            "fecha_creacion":         instance.fecha_creacion.isoformat() if instance.fecha_creacion else None,
            "fecha_entrega_estimada": instance.fecha_entrega_estimada.isoformat() if instance.fecha_entrega_estimada else None,
        })
        return

    # Cambio de estado — siempre publicar estado_actualizado para tracking
    if update_fields and "estado" in update_fields:
        publish_event(OrderEvents.PEDIDO_ESTADO_ACTUALIZADO, {
            "pedido_id":    _sid(instance.id),
            "estado_nuevo": instance.estado,
            "timestamp":    instance.fecha_creacion.isoformat() if instance.fecha_creacion else None,
        })

        # Eventos semánticos por estado final
        if instance.estado == "CANCELADO":
            publish_event(OrderEvents.PEDIDO_CANCELADO, {
                "pedido_id":      _sid(instance.id),
                "restaurante_id": _sid(instance.restaurante_id),
                "cliente_id":     _sid(instance.cliente_id),
                "total":          str(instance.total),
                "moneda":         instance.moneda,
            })

        elif instance.estado == "ENTREGADO":
            publish_event(OrderEvents.PEDIDO_ENTREGADO, {
                "pedido_id":      _sid(instance.id),
                "restaurante_id": _sid(instance.restaurante_id),
                "cliente_id":     _sid(instance.cliente_id),
                "total":          str(instance.total),
                "moneda":         instance.moneda,
            })

        elif instance.estado == "EN_PREPARACION":
            # EN_PREPARACION equivale a confirmado — inventory descuenta stock
            publish_event(OrderEvents.PEDIDO_CONFIRMADO, {
                "pedido_id":      _sid(instance.id),
                "restaurante_id": _sid(instance.restaurante_id),
                "cliente_id":     _sid(instance.cliente_id),
                "total":          str(instance.total),
                "moneda":         instance.moneda,
                "detalles":       _detalles(instance),
            })


# ─────────────────────────────────────────
# DETALLE PEDIDO
# Se publica cuando se agregan ítems al pedido.
# loyalty_service evalúa promociones por plato/categoría.
# ─────────────────────────────────────────

@receiver(post_save, sender=DetallePedido)
def detalle_saved(sender, instance, created, **kwargs):
    if not created:
        return  # los detalles no se editan, solo se crean

    # Notificar que se agregó un ítem al pedido
    # loyalty_service puede evaluar promo por plato en tiempo real
    publish_event("app.order.detalle.agregado", {
        "pedido_id":       _sid(instance.pedido_id),
        "detalle_id":      _sid(instance.id),
        "plato_id":        _sid(instance.plato_id),
        "nombre_plato":    instance.nombre_plato,
        "precio_unitario": str(instance.precio_unitario),
        "cantidad":        instance.cantidad,
        "subtotal":        str(instance.subtotal),
    })


# ─────────────────────────────────────────
# COMANDA COCINA
# ─────────────────────────────────────────

@receiver(post_save, sender=ComandaCocina)
def comanda_saved(sender, instance, created, update_fields, **kwargs):
    if created:
        publish_event(OrderEvents.COMANDA_CREADA, {
            "comanda_id":     _sid(instance.id),
            "pedido_id":      _sid(instance.pedido_id),
            "restaurante_id": _sid(instance.pedido.restaurante_id),
            "estacion":       instance.estacion,
            "estado":         instance.estado,
            "hora_envio":     instance.hora_envio.isoformat() if instance.hora_envio else None,
        })
        return

    # Detectar cuando la comanda pasa a LISTO — save(update_fields=["estado", "hora_fin"])
    if update_fields and "estado" in update_fields and instance.estado == "LISTO":
        publish_event(OrderEvents.COMANDA_LISTA, {
            "comanda_id":                _sid(instance.id),
            "pedido_id":                 _sid(instance.pedido_id),
            "restaurante_id":            _sid(instance.pedido.restaurante_id),
            "estacion":                  instance.estacion,
            "hora_envio":                instance.hora_envio.isoformat() if instance.hora_envio else None,
            "hora_fin":                  instance.hora_fin.isoformat() if instance.hora_fin else None,
            "tiempo_preparacion_segundos": instance.tiempo_preparacion_segundos,
        })


# ─────────────────────────────────────────
# ENTREGA PEDIDO
# ─────────────────────────────────────────

@receiver(post_save, sender=EntregaPedido)
def entrega_saved(sender, instance, created, update_fields, **kwargs):
    if created:
        # Solo publicar si tiene repartidor asignado (delivery)
        if instance.tipo_entrega == "DELIVERY" and instance.repartidor_id:
            publish_event(OrderEvents.ENTREGA_ASIGNADA, {
                "entrega_id":       _sid(instance.id),
                "pedido_id":        _sid(instance.pedido_id),
                "tipo_entrega":     instance.tipo_entrega,
                "repartidor_id":    _sid(instance.repartidor_id),
                "repartidor_nombre": instance.repartidor_nombre,
                "direccion":        instance.direccion,
            })
        return

    # Detectar cambio de estado — save(update_fields=["estado_entrega", ...])
    if not update_fields or "estado_entrega" not in update_fields:
        return

    if instance.estado_entrega == "ENTREGADO":
        publish_event(OrderEvents.ENTREGA_COMPLETADA, {
            "entrega_id":        _sid(instance.id),
            "pedido_id":         _sid(instance.pedido_id),
            "restaurante_id":    _sid(instance.pedido.restaurante_id),
            "cliente_id":        _sid(instance.pedido.cliente_id),
            "tipo_entrega":      instance.tipo_entrega,
            "fecha_entrega_real": instance.fecha_entrega_real.isoformat() if instance.fecha_entrega_real else None,
        })

    elif instance.estado_entrega == "FALLIDO":
        publish_event(OrderEvents.ENTREGA_FALLIDA, {
            "entrega_id": _sid(instance.id),
            "pedido_id":  _sid(instance.pedido_id),
            "motivo":     "Entrega fallida",
        })

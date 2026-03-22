import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from app.inventory.events.event_types import InventoryEvents
from app.inventory.models import (
    AlertaStock,
    IngredienteInventario,
    LoteIngrediente,
    OrdenCompra,
)
from app.inventory.services.rabbitmq import publish_event

logger = logging.getLogger(__name__)


def _sid(value):
    """UUID / Decimal a string seguro. None → None."""
    return str(value) if value is not None else None


# ---------------------------------------------------------------------------
# LoteIngrediente
# Se publica LOTE_RECIBIDO cuando se crea un lote nuevo.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=LoteIngrediente)
def lote_saved(sender, instance, created, update_fields, **kwargs):
    if not created:
        return

    publish_event(InventoryEvents.LOTE_RECIBIDO, {
        "lote_id":           _sid(instance.id),
        "ingrediente_id":    _sid(instance.ingrediente_id),
        "almacen_id":        _sid(instance.almacen_id),
        "restaurante_id":    _sid(instance.almacen.restaurante_id),
        "proveedor_id":      _sid(instance.proveedor_id),
        "numero_lote":       instance.numero_lote,
        "cantidad_recibida": str(instance.cantidad_recibida),
        "unidad_medida":     instance.unidad_medida,
        "fecha_vencimiento": str(instance.fecha_vencimiento),
    })


# ---------------------------------------------------------------------------
# IngredienteInventario
# Solo reacciona cuando cambia cantidad_actual.
# Detecta lotes vencidos y publica LOTE_VENCIDO.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=IngredienteInventario)
def inventario_saved(sender, instance, created, update_fields, **kwargs):
    if created:
        return

    if update_fields and "cantidad_actual" not in update_fields:
        return

    # Detectar lote vencido
    lote = getattr(instance, "lote_actual", None)
    if lote and getattr(lote, "esta_vencido", False):
        if getattr(lote, "estado", "") != "VENCIDO":
            lote.estado = "VENCIDO"
            lote.save(update_fields=["estado"])
            publish_event(InventoryEvents.LOTE_VENCIDO, {
                "lote_id":           _sid(lote.id),
                "ingrediente_id":    _sid(instance.ingrediente_id),
                "almacen_id":        _sid(instance.almacen_id),
                "restaurante_id":    _sid(instance.almacen.restaurante_id),
                "numero_lote":       lote.numero_lote,
                "cantidad_actual":   str(getattr(lote, "cantidad_actual", 0)),
                "fecha_vencimiento": str(lote.fecha_vencimiento),
            })


# ---------------------------------------------------------------------------
# AlertaStock
# Publica el evento correcto según tipo_alerta al crear la alerta.
# Solo en created=True — las alertas no se editan, se resuelven.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=AlertaStock)
def alerta_saved(sender, instance, created, update_fields, **kwargs):
    if not created:
        return

    base = {
        "alerta_id":      _sid(instance.id),
        "ingrediente_id": _sid(instance.ingrediente_id),
        "restaurante_id": _sid(instance.restaurante_id),
        "almacen_id":     _sid(instance.almacen_id),
        "nivel_actual":   str(instance.nivel_actual),
        "nivel_minimo":   str(instance.nivel_minimo),
    }

    nombre = getattr(
        getattr(instance, "ingrediente_inventario", None),
        "nombre_ingrediente", ""
    )
    unidad = getattr(
        getattr(instance, "ingrediente_inventario", None),
        "unidad_medida", ""
    )

    if instance.tipo_alerta == "STOCK_BAJO":
        publish_event(InventoryEvents.ALERTA_STOCK_BAJO, {
            **base,
            "nombre_ingrediente": nombre,
            "unidad_medida":      unidad,
        })

    elif instance.tipo_alerta == "AGOTADO":
        publish_event(InventoryEvents.ALERTA_AGOTADO, {
            **base,
            "nombre_ingrediente": nombre,
        })

    elif instance.tipo_alerta == "VENCIMIENTO":
        lote = getattr(instance, "lote", None)
        publish_event(InventoryEvents.ALERTA_VENCIMIENTO_PROXIMO, {
            **base,
            "lote_id":            _sid(getattr(instance, "lote_id", None)),
            "nombre_ingrediente": nombre,
            "fecha_vencimiento":  str(lote.fecha_vencimiento) if lote else None,
            "dias_para_vencer":   getattr(lote, "dias_para_vencer", None),
        })


# ---------------------------------------------------------------------------
# OrdenCompra
# CREADA → al crear
# ENVIADA / RECIBIDA / CANCELADA → por transición de estado
#
# FIX: _on_orden_compra_recibida_costo existía en el consumer pero no
# estaba conectado. Ahora la lógica de actualizar costos está en el
# consumer (consume_inventory_events._on_pedido_confirmado) que es
# donde pertenece — el signal solo publica el evento ORDEN_COMPRA_RECIBIDA
# con los detalles para que quien la consuma (consume_inventory_events
# vía ORDEN_COMPRA_RECIBIDA si se agrega el handler) actualice los costos.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=OrdenCompra)
def orden_compra_saved(sender, instance, created, update_fields, **kwargs):

    if created:
        publish_event(InventoryEvents.ORDEN_COMPRA_CREADA, {
            "orden_id":               _sid(instance.id),
            "proveedor_id":           _sid(instance.proveedor_id),
            "restaurante_id":         _sid(instance.restaurante_id),
            "total_estimado":         str(instance.total_estimado),
            "moneda":                 instance.moneda,
            "fecha_entrega_estimada": (
                str(instance.fecha_entrega_estimada)
                if instance.fecha_entrega_estimada else None
            ),
        })
        return

    if not update_fields or "estado" not in update_fields:
        return

    estado = instance.estado

    if estado == "ENVIADA":
        publish_event(InventoryEvents.ORDEN_COMPRA_ENVIADA, {
            "orden_id":       _sid(instance.id),
            "proveedor_id":   _sid(instance.proveedor_id),
            "restaurante_id": _sid(instance.restaurante_id),
        })

    elif estado == "RECIBIDA":
        detalles = [
            {
                "ingrediente_id":    _sid(d.ingrediente_id),
                "nombre_ingrediente": getattr(d, "nombre_ingrediente", ""),
                "cantidad_pedida":   str(d.cantidad),
                "cantidad_recibida": str(getattr(d, "cantidad_recibida", d.cantidad)),
                "precio_unitario":   str(getattr(d, "precio_unitario", 0)),
                "unidad_medida":     getattr(d, "unidad_medida", ""),
            }
            for d in instance.detalles.all()
        ]
        publish_event(InventoryEvents.ORDEN_COMPRA_RECIBIDA, {
            "orden_id":       _sid(instance.id),
            "proveedor_id":   _sid(instance.proveedor_id),
            "restaurante_id": _sid(instance.restaurante_id),
            "detalles":       detalles,
        })

    elif estado == "CANCELADA":
        publish_event(InventoryEvents.ORDEN_COMPRA_CANCELADA, {
            "orden_id":       _sid(instance.id),
            "proveedor_id":   _sid(instance.proveedor_id),
            "restaurante_id": _sid(instance.restaurante_id),
        })

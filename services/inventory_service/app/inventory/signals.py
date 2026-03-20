import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    LoteIngrediente, IngredienteInventario,
    OrdenCompra, DetalleOrdenCompra, AlertaStock,
)
from .events.event_types import InventoryEvents
from .services.rabbitmq import publish_event

logger = logging.getLogger(__name__)


def _sid(value):
    """UUID / Decimal a string seguro. None → None."""
    return str(value) if value is not None else None


# ─────────────────────────────────────────
# LOTE INGREDIENTE
# ─────────────────────────────────────────

@receiver(post_save, sender=LoteIngrediente)
def lote_saved(sender, instance, created, update_fields, **kwargs):
    if not created:
        return

    # Nuevo lote recibido — publicar evento
    publish_event(InventoryEvents.LOTE_RECIBIDO, {
        "lote_id":          _sid(instance.id),
        "ingrediente_id":   _sid(instance.ingrediente_id),
        "almacen_id":       _sid(instance.almacen_id),
        "restaurante_id":   _sid(instance.almacen.restaurante_id),
        "proveedor_id":     _sid(instance.proveedor_id),
        "numero_lote":      instance.numero_lote,
        "cantidad_recibida": str(instance.cantidad_recibida),
        "unidad_medida":    instance.unidad_medida,
        "fecha_vencimiento": str(instance.fecha_vencimiento),
    })


# ─────────────────────────────────────────
# INGREDIENTE INVENTARIO
# Detecta cambios de stock para publicar
# STOCK_ACTUALIZADO y generar alertas
# ─────────────────────────────────────────

@receiver(post_save, sender=IngredienteInventario)
def inventario_saved(sender, instance, created, update_fields, **kwargs):
    # Solo reaccionar cuando cambia cantidad_actual
    if not created and update_fields and "cantidad_actual" not in update_fields:
        return

    if created:
        return  # El movimiento lo registra quien crea el inventario

    # Verificar si está vencido algún lote activo
    if instance.lote_actual and instance.lote_actual.esta_vencido:
        if instance.lote_actual.estado != "VENCIDO":
            instance.lote_actual.estado = "VENCIDO"
            instance.lote_actual.save(update_fields=["estado"])
            publish_event(InventoryEvents.LOTE_VENCIDO, {
                "lote_id":          _sid(instance.lote_actual.id),
                "ingrediente_id":   _sid(instance.ingrediente_id),
                "almacen_id":       _sid(instance.almacen_id),
                "restaurante_id":   _sid(instance.almacen.restaurante_id),
                "numero_lote":      instance.lote_actual.numero_lote,
                "cantidad_actual":  str(instance.lote_actual.cantidad_actual),
                "fecha_vencimiento": str(instance.lote_actual.fecha_vencimiento),
            })


# ─────────────────────────────────────────
# ALERTA STOCK
# Publica el evento correcto según tipo_alerta
# ─────────────────────────────────────────

@receiver(post_save, sender=AlertaStock)
def alerta_saved(sender, instance, created, update_fields, **kwargs):
    if not created:
        return

    base_data = {
        "alerta_id":      _sid(instance.id),
        "ingrediente_id": _sid(instance.ingrediente_id),
        "restaurante_id": _sid(instance.restaurante_id),
        "almacen_id":     _sid(instance.almacen_id),
        "nivel_actual":   str(instance.nivel_actual),
        "nivel_minimo":   str(instance.nivel_minimo),
    }

    if instance.tipo_alerta == "STOCK_BAJO":
        publish_event(InventoryEvents.ALERTA_STOCK_BAJO, {
            **base_data,
            "nombre_ingrediente": instance.ingrediente_inventario.nombre_ingrediente,
            "unidad_medida":      instance.ingrediente_inventario.unidad_medida,
        })

    elif instance.tipo_alerta == "AGOTADO":
        publish_event(InventoryEvents.ALERTA_AGOTADO, {
            **base_data,
            "nombre_ingrediente": instance.ingrediente_inventario.nombre_ingrediente,
        })

    elif instance.tipo_alerta == "VENCIMIENTO":
        publish_event(InventoryEvents.ALERTA_VENCIMIENTO_PROXIMO, {
            **base_data,
            "lote_id":            _sid(instance.lote_id),
            "nombre_ingrediente": instance.ingrediente_inventario.nombre_ingrediente,
            "fecha_vencimiento":  str(instance.lote.fecha_vencimiento) if instance.lote else None,
            "dias_para_vencer":   instance.lote.dias_para_vencer if instance.lote else None,
        })


# ─────────────────────────────────────────
# ORDEN COMPRA
# ─────────────────────────────────────────

@receiver(post_save, sender=OrdenCompra)
def orden_compra_saved(sender, instance, created, update_fields, **kwargs):
    if created:
        publish_event(InventoryEvents.ORDEN_COMPRA_CREADA, {
            "orden_id":              _sid(instance.id),
            "proveedor_id":          _sid(instance.proveedor_id),
            "restaurante_id":        _sid(instance.restaurante_id),
            "total_estimado":        str(instance.total_estimado),
            "moneda":                instance.moneda,
            "fecha_entrega_estimada": str(instance.fecha_entrega_estimada) if instance.fecha_entrega_estimada else None,
        })
        return

    if not update_fields or "estado" not in update_fields:
        return

    if instance.estado == "ENVIADA":
        publish_event(InventoryEvents.ORDEN_COMPRA_ENVIADA, {
            "orden_id":       _sid(instance.id),
            "proveedor_id":   _sid(instance.proveedor_id),
            "restaurante_id": _sid(instance.restaurante_id),
        })

    elif instance.estado == "RECIBIDA":
        # Construir detalles de lo recibido para el evento
        detalles = [
            {
                "ingrediente_id":    _sid(d.ingrediente_id),
                "nombre_ingrediente": d.nombre_ingrediente,
                "cantidad_pedida":   str(d.cantidad),
                "cantidad_recibida": str(d.cantidad_recibida),
                "unidad_medida":     d.unidad_medida,
            }
            for d in instance.detalles.all()
        ]
        publish_event(InventoryEvents.ORDEN_COMPRA_RECIBIDA, {
            "orden_id":       _sid(instance.id),
            "proveedor_id":   _sid(instance.proveedor_id),
            "restaurante_id": _sid(instance.restaurante_id),
            "detalles":       detalles,
        })

    elif instance.estado == "CANCELADA":
        publish_event(InventoryEvents.ORDEN_COMPRA_CANCELADA, {
            "orden_id":       _sid(instance.id),
            "proveedor_id":   _sid(instance.proveedor_id),
            "restaurante_id": _sid(instance.restaurante_id),
        })

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from app.menu.events.event_types import MenuEvents
from app.menu.models import (
    Categoria,
    Ingrediente,
    Plato,
    PlatoIngrediente,
    PrecioPlato,
    Restaurante,
)
from app.menu.services.rabbitmq import publish_event

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _sid(value):
    """UUID / cualquier valor a string seguro. None → None."""
    return str(value) if value is not None else None


# ---------------------------------------------------------------------------
# Plato
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Plato)
def plato_saved(sender, instance, created, update_fields, **kwargs):
    # Activated / Deactivated — save(update_fields=["activo"])
    if not created and update_fields and set(update_fields) == {"activo"}:
        event = (
            MenuEvents.PLATO_ACTIVATED
            if instance.activo
            else MenuEvents.PLATO_DEACTIVATED
        )
        publish_event(event, {"plato_id": _sid(instance.id)})
        return

    event = MenuEvents.PLATO_CREATED if created else MenuEvents.PLATO_UPDATED

    publish_event(event, {
        "plato_id":    _sid(instance.id),
        "nombre":      instance.nombre,
        "descripcion": instance.descripcion,
        "categoria_id": _sid(instance.categoria_id),
        "imagen":      instance.imagen,
        "activo":      instance.activo,
    })


@receiver(post_delete, sender=Plato)
def plato_deleted(sender, instance, **kwargs):
    publish_event(MenuEvents.PLATO_DELETED, {
        "plato_id": _sid(instance.id),
    })


# ---------------------------------------------------------------------------
# PrecioPlato
# ---------------------------------------------------------------------------

@receiver(post_save, sender=PrecioPlato)
def precio_saved(sender, instance, created, update_fields, **kwargs):
    # Activated / Deactivated — save(update_fields=["activo"])
    if not created and update_fields and set(update_fields) == {"activo"}:
        event = (
            MenuEvents.PRECIO_ACTIVATED
            if instance.activo
            else MenuEvents.PRECIO_DEACTIVATED
        )
        publish_event(event, {
            "precio_id":      _sid(instance.id),
            "plato_id":       _sid(instance.plato_id),
            "restaurante_id": _sid(instance.restaurante_id),
            # Incluir precio y moneda para que order/loyalty no necesiten
            # hacer un GET adicional al recibir el evento
            "precio":         str(instance.precio),
            "moneda":         instance.moneda,
        })
        return

    event = MenuEvents.PRECIO_CREATED if created else MenuEvents.PRECIO_UPDATED

    publish_event(event, {
        "precio_id":      _sid(instance.id),
        "plato_id":       _sid(instance.plato_id),
        "restaurante_id": _sid(instance.restaurante_id),
        "precio":         str(instance.precio),
        "moneda":         instance.moneda,
        "fecha_inicio":   instance.fecha_inicio.isoformat(),
        "fecha_fin":      instance.fecha_fin.isoformat() if instance.fecha_fin else None,
        "activo":         instance.activo,
    })


# ---------------------------------------------------------------------------
# Restaurante
# FIX: el original solo cubría deactivated en el bloque update_fields.
# Un restaurante puede reactivarse (activo=True) — ese caso también
# debe publicar RESTAURANTE_UPDATED para que los consumidores se sincronicen.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Restaurante)
def restaurante_saved(sender, instance, created, update_fields, **kwargs):
    # Deactivated — save(update_fields=["activo"]) con activo=False
    if not created and update_fields and set(update_fields) == {"activo"}:
        if not instance.activo:
            publish_event(MenuEvents.RESTAURANTE_DEACTIVATED, {
                "restaurante_id": _sid(instance.id),
            })
        else:
            # Reactivación — notificar como updated para que los servicios
            # que lo marcaron inactivo (ej: staff) lo vuelvan a activar
            publish_event(MenuEvents.RESTAURANTE_UPDATED, {
                "restaurante_id": _sid(instance.id),
                "nombre":         instance.nombre,
                "pais":           instance.pais,
                "ciudad":         instance.ciudad,
                "moneda":         instance.moneda,
                "activo":         instance.activo,
            })
        return

    event = MenuEvents.RESTAURANTE_CREATED if created else MenuEvents.RESTAURANTE_UPDATED

    publish_event(event, {
        "restaurante_id": _sid(instance.id),
        "nombre":         instance.nombre,
        "pais":           instance.pais,
        "ciudad":         instance.ciudad,
        "direccion":      instance.direccion,
        "moneda":         instance.moneda,
        "activo":         instance.activo,
    })


# ---------------------------------------------------------------------------
# Categoria
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Categoria)
def categoria_saved(sender, instance, created, update_fields, **kwargs):
    if not created and update_fields and set(update_fields) == {"activo"}:
        if not instance.activo:
            publish_event(MenuEvents.CATEGORIA_DEACTIVATED, {
                "categoria_id": _sid(instance.id),
            })
            return
        # Si se reactiva la categoría → publicar como updated
        # loyalty_service puede reactivar promos asociadas

    event = MenuEvents.CATEGORIA_CREATED if created else MenuEvents.CATEGORIA_UPDATED

    publish_event(event, {
        "categoria_id": _sid(instance.id),
        "nombre":       instance.nombre,
        "orden":        instance.orden,
        "activo":       instance.activo,
    })


# ---------------------------------------------------------------------------
# Ingrediente
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Ingrediente)
def ingrediente_saved(sender, instance, created, update_fields, **kwargs):
    if not created and update_fields and set(update_fields) == {"activo"}:
        if not instance.activo:
            publish_event(MenuEvents.INGREDIENTE_DEACTIVATED, {
                "ingrediente_id": _sid(instance.id),
            })
            return

    event = MenuEvents.INGREDIENTE_CREATED if created else MenuEvents.INGREDIENTE_UPDATED

    publish_event(event, {
        "ingrediente_id": _sid(instance.id),
        "nombre":         instance.nombre,
        "unidad_medida":  instance.unidad_medida,
        "activo":         instance.activo,
    })


# ---------------------------------------------------------------------------
# PlatoIngrediente
# ---------------------------------------------------------------------------

@receiver(post_save, sender=PlatoIngrediente)
def plato_ingrediente_saved(sender, instance, created, **kwargs):
    if created:
        publish_event(MenuEvents.PLATO_INGREDIENTE_ADDED, {
            "plato_id":       _sid(instance.plato_id),
            "ingrediente_id": _sid(instance.ingrediente_id),
            "cantidad":       str(instance.cantidad),
            "unidad_medida":  instance.ingrediente.unidad_medida,
        })
    else:
        # unique_together garantiza que plato e ingrediente no cambian —
        # el único campo editable es cantidad
        publish_event(MenuEvents.PLATO_INGREDIENTE_CANTIDAD_UPDATED, {
            "plato_id":       _sid(instance.plato_id),
            "ingrediente_id": _sid(instance.ingrediente_id),
            "cantidad_nueva": str(instance.cantidad),
            "unidad_medida":  instance.ingrediente.unidad_medida,
        })


@receiver(post_delete, sender=PlatoIngrediente)
def plato_ingrediente_deleted(sender, instance, **kwargs):
    publish_event(MenuEvents.PLATO_INGREDIENTE_REMOVED, {
        "plato_id":       _sid(instance.plato_id),
        "ingrediente_id": _sid(instance.ingrediente_id),
    })

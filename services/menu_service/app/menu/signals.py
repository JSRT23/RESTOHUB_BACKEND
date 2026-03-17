from .models import Restaurante
from .models import PrecioPlato, Plato
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .services.rabbitmq import publish_event
from .events.event_types import MenuEvents


# Disparar eventos para Plato
@receiver(post_save, sender=Plato)
def plato_saved(sender, instance, created, **kwargs):
    event = MenuEvents.PLATO_CREATED if created else MenuEvents.PLATO_UPDATED

    data = {
        "id": str(instance.id),
        "nombre": instance.nombre,
        "categoria": str(instance.categoria.id),
        "activo": instance.activo,
    }

    publish_event(event, data)


@receiver(post_delete, sender=Plato)
def plato_deleted(sender, instance, **kwargs):
    data = {"id": str(instance.id)}
    publish_event(MenuEvents.PLATO_DELETED, data)


# Disparar eventos para PrecioPlato


@receiver(post_save, sender=PrecioPlato)
def precio_saved(sender, instance, created, **kwargs):
    event = MenuEvents.PRECIO_CREATED if created else MenuEvents.PRECIO_UPDATED

    data = {
        "id": str(instance.id),
        "plato_id": str(instance.plato.id),
        "restaurante_id": str(instance.restaurante.id),
        "precio": float(instance.precio),
        "activo": instance.activo,
    }

    publish_event(event, data)


# Disparar eventos para Restaurante


@receiver(post_save, sender=Restaurante)
def restaurante_saved(sender, instance, created, **kwargs):
    event = (
        MenuEvents.RESTAURANTE_CREATED
        if created else MenuEvents.RESTAURANTE_UPDATED
    )

    data = {
        "id": str(instance.id),
        "nombre": instance.nombre,
        "pais": instance.pais,
        "ciudad": instance.ciudad,
        "activo": instance.activo,
    }

    publish_event(event, data)

# staff_service/app/staff/signals.py
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from app.staff.events.event_types import StaffEvents
from app.staff.infrastructure.messaging.publisher import publish_event
from app.staff.models import Turno

logger = logging.getLogger(__name__)


def _sid(value):
    """Convierte cualquier valor (UUID, int, None) a str o None."""
    return str(value) if value is not None else None


# ---------------------------------------------------------------------------
# TURNO
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Turno)
def turno_saved(sender, instance, created, update_fields=None, **kwargs):

    # ── CREACIÓN ────────────────────────────────────────────────────────────
    if created:
        publish_event(StaffEvents.TURNO_CREATED, {
            "turno_id":       _sid(instance.id),
            "empleado_id":    _sid(getattr(instance, "empleado_id", None)),
            "restaurante_id": _sid(getattr(instance, "restaurante_id", None)),
            "fecha_inicio":   str(instance.fecha_inicio) if instance.fecha_inicio else None,
            "fecha_fin":      str(instance.fecha_fin) if instance.fecha_fin else None,
        })
        return

    # ── ACTUALIZACIÓN ───────────────────────────────────────────────────────
    # Si solo cambió el estado → publicamos el evento de estado específico.
    # Si cambió cualquier otra cosa → publicamos TURNO_UPDATED.
    # Nunca publicamos ambos en el mismo save.

    estado = getattr(instance, "estado", None)
    fields = set(update_fields) if update_fields else set()

    if fields == {"estado"} or (not fields and estado):
        # Transición de estado pura
        if estado == "activo":
            publish_event(StaffEvents.TURNO_ACTIVATED, {
                "turno_id": _sid(instance.id),
            })

        elif estado == "completado":
            publish_event(StaffEvents.TURNO_COMPLETED, {
                "turno_id":      _sid(instance.id),
                "fecha_fin_real": str(instance.fecha_fin) if instance.fecha_fin else None,
            })

        elif estado == "cancelado":
            publish_event(StaffEvents.TURNO_CANCELLED, {
                "turno_id": _sid(instance.id),
                "motivo":   getattr(instance, "motivo_cancelacion", None),
            })

        else:
            logger.warning("[signals] Estado de turno desconocido: %s", estado)

    else:
        # Actualización general de campos
        publish_event(StaffEvents.TURNO_UPDATED, {
            "turno_id":          _sid(instance.id),
            "campos_modificados": list(fields) if fields else "all",
        })

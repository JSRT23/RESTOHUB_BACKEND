# staff_service/app/staff/signals.py
"""
Signals de staff_service.

Regla: solo publicar eventos de recursos que staff_service POSEE.
Usar get_publisher() (singleton), nunca publisher.close() desde un signal.

CORRECCIONES:
- cocina_asignacion_creada: necesita estacion.restaurante_id → se carga con select_related
  pero en el signal post_save la instancia ya viene de la DB, así que se hace .estacion
  sin query adicional si Django ya tiene el objeto en memoria (caso create normal).
  Para seguridad se usa try/except y se omite restaurante_id si no está disponible.
- entrega_asignada: repartidor.restaurante_id requiere select_related.
  Se envuelve en try/except para no bloquear el signal.
- alerta_resuelta: se publica al resolver (not created, resuelta=True).
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from app.staff.events.builders import StaffEventBuilder
from app.staff.events.event_types import StaffEvents
from app.staff.infrastructure.messaging.publisher import get_publisher
from app.staff.models import (
    AlertaOperacional,
    AsignacionCocina,
    RegistroAsistencia,
    ResumenNomina,
    ServicioEntrega,
    Turno,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# 👷 TURNOS
# ─────────────────────────────────────────

@receiver(post_save, sender=Turno)
def publish_turno_event(sender, instance: Turno, created: bool, **kwargs):
    try:
        publisher = get_publisher()

        if created:
            publisher.publish(
                StaffEvents.TURNO_CREADO,
                StaffEventBuilder.turno_creado(instance),
            )
        else:
            estado = instance.estado

            if estado == "completado":
                publisher.publish(
                    StaffEvents.TURNO_COMPLETADO,
                    StaffEventBuilder.turno_completado(instance),
                )
            elif estado == "cancelado":
                publisher.publish(
                    StaffEvents.TURNO_CANCELADO,
                    StaffEventBuilder.turno_cancelado(instance, motivo=""),
                )
            elif estado == "activo":
                publisher.publish(
                    StaffEvents.TURNO_ACTIVADO,
                    StaffEventBuilder.turno_estado(instance),
                )
            else:
                publisher.publish(
                    StaffEvents.TURNO_ACTUALIZADO,
                    StaffEventBuilder.turno_actualizado(instance, cambios={}),
                )

        logger.info(
            f"📤 Evento turno → {instance.id} ({'creado' if created else instance.estado})")

    except Exception:
        logger.exception("💥 Error publicando evento de turno")


# ─────────────────────────────────────────
# ⏱️ ASISTENCIA
# ─────────────────────────────────────────

@receiver(post_save, sender=RegistroAsistencia)
def publish_asistencia_event(sender, instance: RegistroAsistencia, created: bool, **kwargs):
    try:
        publisher = get_publisher()

        if created and instance.hora_entrada:
            publisher.publish(
                StaffEvents.ASISTENCIA_REGISTRADA,
                StaffEventBuilder.asistencia_registrada(
                    instance, tipo="entrada"),
            )
        elif not created and instance.hora_salida:
            publisher.publish(
                StaffEvents.ASISTENCIA_REGISTRADA,
                StaffEventBuilder.asistencia_registrada(
                    instance, tipo="salida"),
            )

        logger.info(f"📤 Asistencia → {instance.id}")

    except Exception:
        logger.exception("💥 Error publicando evento de asistencia")


# ─────────────────────────────────────────
# 🍳 COCINA
# ─────────────────────────────────────────

@receiver(post_save, sender=AsignacionCocina)
def publish_asignacion_cocina_event(sender, instance: AsignacionCocina, created: bool, **kwargs):
    try:
        publisher = get_publisher()

        if created:
            # ✅ Cargar estacion si no está en caché para obtener restaurante_id
            try:
                # Django carga la FK en el mismo objeto si ya está en memoria
                # En caso de create directo desde el handler, la estacion viene del parámetro
                # Si no, hacemos el select
                if not hasattr(instance, '_estacion_cache'):
                    from app.staff.models import EstacionCocina
                    instance.__dict__['_estacion_cache'] = EstacionCocina.objects.get(
                        pk=instance.estacion_id)
            except Exception:
                pass  # si falla, el builder omite restaurante_id

            publisher.publish(
                StaffEvents.COCINA_ASIGNACION_CREADA,
                StaffEventBuilder.cocina_asignacion_creada(instance),
            )

        elif instance.completado_en:
            sla = instance.calcular_sla()
            publisher.publish(
                StaffEvents.COCINA_ASIGNACION_COMPLETADA,
                StaffEventBuilder.cocina_asignacion_completada(
                    instance, tiempo_preparacion=sla or 0),
            )

        logger.info(f"📤 AsignacionCocina → {instance.id}")

    except Exception:
        logger.exception("💥 Error publicando evento de asignacion_cocina")


# ─────────────────────────────────────────
# 🚚 ENTREGAS
# ─────────────────────────────────────────

@receiver(post_save, sender=ServicioEntrega)
def publish_entrega_event(sender, instance: ServicioEntrega, created: bool, **kwargs):
    try:
        if not created:
            return

        publisher = get_publisher()

        # ✅ Cargar repartidor con restaurante si no está en caché
        try:
            if not hasattr(instance, '_repartidor_cache'):
                from app.staff.models import Empleado
                repartidor = Empleado.objects.select_related(
                    "restaurante").get(pk=instance.repartidor_id)
                instance.__dict__['_repartidor_cache'] = repartidor
        except Exception:
            pass

        publisher.publish(
            StaffEvents.ENTREGA_ASIGNADA,
            StaffEventBuilder.entrega_asignada(instance),
        )

        logger.info(f"📤 ServicioEntrega → {instance.id}")

    except Exception:
        logger.exception("💥 Error publicando evento de entrega")


# ─────────────────────────────────────────
# 🚨 ALERTAS OPERACIONALES
# ─────────────────────────────────────────

@receiver(post_save, sender=AlertaOperacional)
def publish_alerta_event(sender, instance: AlertaOperacional, created: bool, **kwargs):
    try:
        publisher = get_publisher()

        if created:
            publisher.publish(
                StaffEvents.ALERTA_CREADA,
                StaffEventBuilder.alerta_creada(instance),
            )
            logger.info(f"📤 AlertaOperacional creada → {instance.id}")

        elif instance.resuelta:
            # ✅ Publicar también cuando se resuelve
            publisher.publish(
                StaffEvents.ALERTA_RESUELTA,
                StaffEventBuilder.alerta_resuelta(instance),
            )
            logger.info(f"📤 AlertaOperacional resuelta → {instance.id}")

    except Exception:
        logger.exception("💥 Error publicando evento de alerta")


# ─────────────────────────────────────────
# 💰 NÓMINA
# ─────────────────────────────────────────

@receiver(post_save, sender=ResumenNomina)
def publish_nomina_event(sender, instance: ResumenNomina, created: bool, **kwargs):
    try:
        if not instance.cerrado:
            return

        publisher = get_publisher()
        publisher.publish(
            StaffEvents.NOMINA_CERRADA,
            StaffEventBuilder.nomina_cerrada(instance),
        )

        logger.info(f"📤 NóminaCerrada → {instance.id}")

    except Exception:
        logger.exception("💥 Error publicando evento de nómina")

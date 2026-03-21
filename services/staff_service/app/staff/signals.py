"""
signals.py — staff_service

Detecta cambios en los modelos y publica eventos a RabbitMQ.

Reglas del patrón:
  - save(update_fields=["estado"]) → detectar transiciones de estado
  - save(update_fields=["activo"]) → detectar activated / deactivated
  - Nunca se publica en __init__ ni en migraciones
  - _sid() convierte cualquier valor a str para JSON seguro

Custom managers definidos aquí (cerca de donde se usan en signals y consumer):
  - EmpleadoQuerySet.annotate_open_assignments()

NOTA sobre senders:
  Los @receiver usan la clase del modelo directamente (no strings) para evitar
  el error signals.E001. El string "app_label.ModelName" usa el app_label que
  Django deriva del último segmento del AppConfig.name — como name="app.staff"
  el label es "staff", no "app_staff". Importar la clase es siempre más seguro.
"""

from django.db import models as _models
from django.db.models.signals import post_save
from django.dispatch import receiver

from app.staff.events.event_types import StaffEvents
from app.staff.models import (
    AlertaOperacional,
    AsignacionCocina,
    RegistroAsistencia,
    ResumenNomina,
    ServicioEntrega,
    Turno,
)
from app.staff.services.rabbitmq import publish_event


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _sid(value) -> str | None:
    return str(value) if value is not None else None


# ---------------------------------------------------------------------------
# Custom QuerySet — necesario en el consumer (_on_comanda_creada)
# Se define aquí y se aplica al modelo vía models.py o monkey-patch en ready()
# ---------------------------------------------------------------------------


class EmpleadoQuerySet(_models.QuerySet):
    def annotate_open_assignments(self):
        """
        Anota cada empleado con el número de AsignacionCocina sin completar.
        Ordena ascendente → el cocinero con menos carga queda primero.
        """
        from django.db.models import Count, Q
        return self.annotate(
            open_assignments=Count(
                "asignaciones_cocina",
                filter=Q(asignaciones_cocina__completado_en__isnull=True),
            )
        )


# ---------------------------------------------------------------------------
# Turno
# Transiciones de estado: programado → activo → completado / cancelado
# update_fields obligatorio en las acciones del ViewSet para que el signal
# distinga una transición de estado de una edición normal.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Turno)
def turno_saved(sender, instance, created, update_fields, **kwargs):
    from app.staff.models import EstadoTurno  # noqa — re-import local para claridad

    # — Transición de estado (update_fields=["estado"]) —
    if not created and update_fields and "estado" in update_fields:
        estado_map = {
            EstadoTurno.ACTIVO:     StaffEvents.TURNO_ACTIVADO,
            EstadoTurno.COMPLETADO: StaffEvents.TURNO_COMPLETADO,
            EstadoTurno.CANCELADO:  StaffEvents.TURNO_CANCELADO,
        }
        event = estado_map.get(instance.estado)
        if event:
            publish_event(event, {
                "turno_id":       _sid(instance.id),
                "empleado_id":    _sid(instance.empleado_id),
                "restaurante_id": _sid(instance.restaurante_id),
                "estado":         instance.estado,
                "fecha_inicio":   instance.fecha_inicio.isoformat(),
                "fecha_fin":      instance.fecha_fin.isoformat(),
            })
        return

    # — Creación —
    if created:
        publish_event(StaffEvents.TURNO_CREADO, {
            "turno_id":                _sid(instance.id),
            "empleado_id":             _sid(instance.empleado_id),
            "restaurante_id":          _sid(instance.restaurante_id),
            "fecha_inicio":            instance.fecha_inicio.isoformat(),
            "fecha_fin":               instance.fecha_fin.isoformat(),
            "estado":                  instance.estado,
            "duracion_programada_h":   instance.duracion_programada_horas,
        })
        return

    # — Edición general —
    publish_event(StaffEvents.TURNO_ACTUALIZADO, {
        "turno_id":       _sid(instance.id),
        "empleado_id":    _sid(instance.empleado_id),
        "restaurante_id": _sid(instance.restaurante_id),
        "estado":         instance.estado,
        "fecha_inicio":   instance.fecha_inicio.isoformat(),
        "fecha_fin":      instance.fecha_fin.isoformat(),
    })


# ---------------------------------------------------------------------------
# RegistroAsistencia
# Dos momentos: entrada (hora_salida is None) y salida (hora_salida set).
# Se detectan por update_fields para no publicar el mismo evento dos veces.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=RegistroAsistencia)
def registro_asistencia_saved(sender, instance, created, update_fields, **kwargs):

    # — Entrada: se crea el registro con hora_entrada —
    if created:
        publish_event(StaffEvents.ASISTENCIA_ENTRADA_REGISTRADA, {
            "registro_id":      _sid(instance.id),
            "turno_id":         _sid(instance.turno_id),
            "empleado_id":      _sid(instance.turno.empleado_id),
            "hora_entrada":     instance.hora_entrada.isoformat(),
            "metodo_registro":  instance.metodo_registro,
        })
        return

    # — Salida: update_fields=["hora_salida", "horas_normales", "horas_extra"] —
    if update_fields and "hora_salida" in update_fields and instance.hora_salida:
        publish_event(StaffEvents.ASISTENCIA_SALIDA_REGISTRADA, {
            "registro_id":     _sid(instance.id),
            "turno_id":        _sid(instance.turno_id),
            "empleado_id":     _sid(instance.turno.empleado_id),
            "hora_entrada":    instance.hora_entrada.isoformat(),
            "hora_salida":     instance.hora_salida.isoformat(),
            "horas_normales":  str(instance.horas_normales),
            "horas_extra":     str(instance.horas_extra),
            "horas_totales":   str(instance.horas_totales),
            "metodo_registro": instance.metodo_registro,
        })


# ---------------------------------------------------------------------------
# AsignacionCocina
# Dos momentos: creación (asignado_en) y completado (completado_en set).
# Si el SLA supera el umbral del restaurante se publica además COCINA_SLA_EXCEDIDO.
# ---------------------------------------------------------------------------

# Umbral de SLA en segundos (15 minutos por defecto — ajustable por config)
SLA_UMBRAL_SEGUNDOS = 15 * 60


@receiver(post_save, sender=AsignacionCocina)
def asignacion_cocina_saved(sender, instance, created, update_fields, **kwargs):

    # — Creación —
    if created:
        publish_event(StaffEvents.COCINA_ASIGNACION_CREADA, {
            "asignacion_id": _sid(instance.id),
            "pedido_id":     _sid(instance.pedido_id),
            "comanda_id":    _sid(instance.comanda_id),
            "cocinero_id":   _sid(instance.cocinero_id),
            "estacion_id":   _sid(instance.estacion_id),
            "estacion":      instance.estacion.nombre,
            "asignado_en":   instance.asignado_en.isoformat(),
        })
        return

    # — Completado: update_fields=["completado_en", "sla_segundos"] —
    if update_fields and "completado_en" in update_fields and instance.completado_en:
        publish_event(StaffEvents.COCINA_ASIGNACION_COMPLETADA, {
            "asignacion_id": _sid(instance.id),
            "pedido_id":     _sid(instance.pedido_id),
            "comanda_id":    _sid(instance.comanda_id),
            "cocinero_id":   _sid(instance.cocinero_id),
            "estacion_id":   _sid(instance.estacion_id),
            "sla_segundos":  instance.sla_segundos,
            "completado_en": instance.completado_en.isoformat(),
        })

        # SLA excedido → evento adicional para analytics / notificaciones
        if instance.sla_segundos and instance.sla_segundos > SLA_UMBRAL_SEGUNDOS:
            publish_event(StaffEvents.COCINA_SLA_EXCEDIDO, {
                "asignacion_id":    _sid(instance.id),
                "comanda_id":       _sid(instance.comanda_id),
                "cocinero_id":      _sid(instance.cocinero_id),
                "estacion_id":      _sid(instance.estacion_id),
                "sla_segundos":     instance.sla_segundos,
                "sla_umbral":       SLA_UMBRAL_SEGUNDOS,
                "exceso_segundos":  instance.sla_segundos - SLA_UMBRAL_SEGUNDOS,
            })


# ---------------------------------------------------------------------------
# ServicioEntrega
# Dos momentos: asignación (created) y liberación (completada / fallida).
# ---------------------------------------------------------------------------

@receiver(post_save, sender=ServicioEntrega)
def servicio_entrega_saved(sender, instance, created, update_fields, **kwargs):
    from app.staff.models import EstadoEntrega

    # — Asignación inicial —
    if created:
        publish_event(StaffEvents.ENTREGA_REPARTIDOR_ASIGNADO, {
            "servicio_id":   _sid(instance.id),
            "pedido_id":     _sid(instance.pedido_id),
            "repartidor_id": _sid(instance.repartidor_id),
            "estado":        instance.estado,
            "asignado_en":   instance.asignado_en.isoformat(),
        })
        return

    # — Liberación: estado → completada o fallida —
    if update_fields and "estado" in update_fields:
        if instance.estado in [EstadoEntrega.COMPLETADA, EstadoEntrega.FALLIDA]:
            publish_event(StaffEvents.ENTREGA_REPARTIDOR_LIBERADO, {
                "servicio_id":    _sid(instance.id),
                "pedido_id":      _sid(instance.pedido_id),
                "repartidor_id":  _sid(instance.repartidor_id),
                "estado_final":   instance.estado,
                "completado_en":  (
                    instance.completado_en.isoformat()
                    if instance.completado_en else None
                ),
            })


# ---------------------------------------------------------------------------
# AlertaOperacional
# Se publica al crear y al resolver.
# Nunca se edita el contenido de una alerta — solo se marca resuelta.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=AlertaOperacional)
def alerta_operacional_saved(sender, instance, created, update_fields, **kwargs):

    # — Creación —
    if created:
        publish_event(StaffEvents.ALERTA_CREADA, {
            "alerta_id":      _sid(instance.id),
            "restaurante_id": _sid(instance.restaurante_id),
            "tipo":           instance.tipo,
            "nivel":          instance.nivel,
            "mensaje":        instance.mensaje,
            "referencia_id":  _sid(instance.referencia_id),
        })
        return

    # — Resolución: update_fields=["resuelta"] —
    if update_fields and set(update_fields) == {"resuelta"} and instance.resuelta:
        publish_event(StaffEvents.ALERTA_RESUELTA, {
            "alerta_id":      _sid(instance.id),
            "restaurante_id": _sid(instance.restaurante_id),
            "tipo":           instance.tipo,
            "nivel":          instance.nivel,
        })


# ---------------------------------------------------------------------------
# ResumenNomina
# Solo se publica cuando el período se cierra (cerrado=True).
# update_fields=["cerrado"] es obligatorio en el ViewSet.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=ResumenNomina)
def resumen_nomina_saved(sender, instance, created, update_fields, **kwargs):

    if not created and update_fields and set(update_fields) == {"cerrado"} and instance.cerrado:
        publish_event(StaffEvents.NOMINA_PERIODO_CERRADO, {
            "resumen_id":            _sid(instance.id),
            "empleado_id":           _sid(instance.empleado_id),
            "periodo_inicio":        instance.periodo_inicio.isoformat(),
            "periodo_fin":           instance.periodo_fin.isoformat(),
            "total_horas_normales":  str(instance.total_horas_normales),
            "total_horas_extra":     str(instance.total_horas_extra),
            "total_horas":           str(instance.total_horas),
            "dias_trabajados":       instance.dias_trabajados,
            "moneda":                instance.moneda,
        })

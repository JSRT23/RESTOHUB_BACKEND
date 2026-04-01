# staff_service/app/staff/events/event_types.py
class StaffEvents:
    """
    Eventos publicados por staff_service.

    Convención: app.{servicio}.{entidad}.{accion}

    staff_service NO es dueño del pedido.
    Solo emite eventos de operación interna.

    Consumidores:
    ┌──────────────────────────────────────┬────────────────────────────┐
    │ Evento                               │ Consumidores               │
    ├──────────────────────────────────────┼────────────────────────────┤
    │ turno.*                              │ analytics_service          │
    │ asistencia.*                         │ analytics_service          │
    │ cocina.asignacion.creada             │ order_service              │
    │ cocina.asignacion.completada         │ order_service              │
    │ cocina.sla.excedido                  │ order_service              │
    │ entrega.asignada                     │ order_service              │
    │ alerta.*                             │ gateway (dashboard)        │
    │ nomina.cerrada                       │ analytics_service          │
    └──────────────────────────────────────┴────────────────────────────┘
    """

    # ─────────────────────────────────────────
    # 👷 TURNOS
    # ─────────────────────────────────────────

    TURNO_CREADO = "app.staff.turno.creado"
    TURNO_ACTUALIZADO = "app.staff.turno.actualizado"
    TURNO_ACTIVADO = "app.staff.turno.activado"
    TURNO_COMPLETADO = "app.staff.turno.completado"
    TURNO_CANCELADO = "app.staff.turno.cancelado"

    # ─────────────────────────────────────────
    # ⏱️ ASISTENCIA
    # ─────────────────────────────────────────

    ASISTENCIA_REGISTRADA = "app.staff.asistencia.registrada"
    # data: { asistencia_id, empleado_id, turno_id, tipo: "entrada|salida", timestamp }

    # ─────────────────────────────────────────
    # 🍳 COCINA
    # ─────────────────────────────────────────

    COCINA_ASIGNACION_CREADA = "app.staff.cocina.asignacion.creada"
    COCINA_ASIGNACION_COMPLETADA = "app.staff.cocina.asignacion.completada"
    COCINA_SLA_EXCEDIDO = "app.staff.cocina.sla.excedido"

    # ─────────────────────────────────────────
    # 🚚 ENTREGAS
    # ─────────────────────────────────────────

    ENTREGA_ASIGNADA = "app.staff.entrega.asignada"
    # ⚠️ entrega.finalizada lo controla order_service

    # ─────────────────────────────────────────
    # 🚨 ALERTAS
    # ─────────────────────────────────────────

    ALERTA_CREADA = "app.staff.alerta.creada"
    ALERTA_RESUELTA = "app.staff.alerta.resuelta"

    # ─────────────────────────────────────────
    # 💰 NÓMINA
    # ─────────────────────────────────────────

    NOMINA_CERRADA = "app.staff.nomina.cerrada"

# staff_service/app/staff/events/event_types.py
class StaffEvents:

    # ─────────────────────────────────────────
    # TURNOS
    # Consumidores: payroll_service, analytics_service
    # ─────────────────────────────────────────

    TURNO_CREATED = "app.staff.turno.created"
    # data: { turno_id, empleado_id, restaurante_id, fecha_inicio, fecha_fin }

    TURNO_UPDATED = "app.staff.turno.updated"
    # data: { turno_id, campos_modificados: {...} }

    TURNO_ACTIVATED = "app.staff.turno.activated"
    # data: { turno_id }
    # El turno pasa a estado activo (listo para trabajar).

    TURNO_COMPLETED = "app.staff.turno.completed"
    # data: { turno_id, fecha_fin_real }
    # payroll_service calcula horas trabajadas.

    TURNO_CANCELLED = "app.staff.turno.cancelled"
    # data: { turno_id, motivo }
    # payroll_service evita cálculos de pago para este turno.

    # ─────────────────────────────────────────
    # ASISTENCIA
    # Consumidores: payroll_service, analytics_service
    # ─────────────────────────────────────────

    ASISTENCIA_CHECKIN = "app.staff.asistencia.checkin"
    # data: { asistencia_id, empleado_id, turno_id, timestamp }
    # Marca inicio de jornada real.

    ASISTENCIA_CHECKOUT = "app.staff.asistencia.checkout"
    # data: { asistencia_id, empleado_id, turno_id, timestamp }
    # Marca fin de jornada real.

    # ─────────────────────────────────────────
    # COCINA
    # Consumidores: order_service, analytics_service
    # ─────────────────────────────────────────

    COCINA_ASIGNACION_CREATED = "app.staff.cocina.asignacion.created"
    # data: { asignacion_id, pedido_id, empleado_id, restaurante_id }
    # order_service actualiza estado del pedido a "en preparación".

    COCINA_ASIGNACION_COMPLETED = "app.staff.cocina.asignacion.completed"
    # data: { asignacion_id, pedido_id, empleado_id, tiempo_preparacion }
    # order_service marca pedido como "listo para entrega".

    COCINA_SLA_EXCEDIDO = "app.staff.cocina.sla.excedido"
    # data: { pedido_id, tiempo_estimado, tiempo_real }
    # alert_service genera alerta operativa.

    # ─────────────────────────────────────────
    # ENTREGAS
    # Consumidores: order_service, analytics_service
    # ─────────────────────────────────────────

    ENTREGA_ASIGNADA = "app.staff.entrega.asignada"
    # data: { entrega_id, pedido_id, empleado_id, restaurante_id }
    # order_service cambia estado a "en camino".

    ENTREGA_FINALIZADA = "app.staff.entrega.finalizada"
    # data: { entrega_id, pedido_id, empleado_id, timestamp }
    # order_service marca pedido como "entregado".

    # ─────────────────────────────────────────
    # ALERTAS
    # Consumidores: alert_service
    # ─────────────────────────────────────────

    ALERTA_CREATED = "app.staff.alerta.created"
    # data: { alerta_id, tipo, descripcion, prioridad, restaurante_id }

    ALERTA_RESOLVED = "app.staff.alerta.resolved"
    # data: { alerta_id, timestamp_resolucion }

    # ─────────────────────────────────────────
    # NÓMINA
    # Consumidores: payroll_service, finance_service
    # ─────────────────────────────────────────

    NOMINA_CLOSED = "app.staff.nomina.closed"
    # data: { nomina_id, periodo_inicio, periodo_fin, total_pagado }
    # finance_service registra egreso global.

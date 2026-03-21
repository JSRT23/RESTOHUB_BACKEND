class StaffEvents:
    """
    Eventos que publica staff_service al exchange 'restohub'.
    Convención: app.{servicio}.{entidad}.{accion}
    """

    # Turnos
    TURNO_CREADO = "app.staff.turno.creado"
    TURNO_ACTUALIZADO = "app.staff.turno.actualizado"
    TURNO_ACTIVADO = "app.staff.turno.activado"       # empleado inicia turno
    TURNO_COMPLETADO = "app.staff.turno.completado"     # empleado cierra turno
    TURNO_CANCELADO = "app.staff.turno.cancelado"

    # Asistencia
    ASISTENCIA_ENTRADA_REGISTRADA = "app.staff.asistencia.entrada_registrada"
    ASISTENCIA_SALIDA_REGISTRADA = "app.staff.asistencia.salida_registrada"

    # Asignación de cocina
    COCINA_ASIGNACION_CREADA = "app.staff.cocina.asignacion_creada"
    COCINA_ASIGNACION_COMPLETADA = "app.staff.cocina.asignacion_completada"
    COCINA_SLA_EXCEDIDO = "app.staff.cocina.sla_excedido"

    # Servicio de entrega
    ENTREGA_REPARTIDOR_ASIGNADO = "app.staff.entrega.repartidor_asignado"
    ENTREGA_REPARTIDOR_LIBERADO = "app.staff.entrega.repartidor_liberado"

    # Alertas operacionales
    ALERTA_CREADA = "app.staff.alerta.creada"
    ALERTA_RESUELTA = "app.staff.alerta.resuelta"

    # Nómina
    NOMINA_PERIODO_CERRADO = "app.staff.nomina.periodo_cerrado"

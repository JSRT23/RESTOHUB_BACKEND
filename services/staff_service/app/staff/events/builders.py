# staff_service/app/staff/events/builders.py
class StaffEventBuilder:
    """
    Construye los payloads (data) de los eventos de staff_service.
    Mantiene consistencia con menu_service.
    """

    # ─────────────────────────────────────────
    # 👷 TURNOS
    # ─────────────────────────────────────────

    @staticmethod
    def turno_creado(turno):
        return {
            "turno_id": str(turno.id),
            "empleado_id": str(turno.empleado_id),
            "restaurante_id": str(turno.restaurante_id),
            "fecha_inicio": turno.fecha_inicio.isoformat(),
            "fecha_fin": turno.fecha_fin.isoformat() if turno.fecha_fin else None,
        }

    @staticmethod
    def turno_actualizado(turno, cambios: dict):
        return {
            "turno_id": str(turno.id),
            "cambios": cambios
        }

    @staticmethod
    def turno_estado(turno):
        return {
            "turno_id": str(turno.id)
        }

    @staticmethod
    def turno_completado(turno):
        return {
            "turno_id": str(turno.id),
            "fecha_fin_real": turno.fecha_fin_real.isoformat() if hasattr(turno, "fecha_fin_real") and turno.fecha_fin_real else None
        }

    @staticmethod
    def turno_cancelado(turno, motivo: str):
        return {
            "turno_id": str(turno.id),
            "motivo": motivo
        }

    # ─────────────────────────────────────────
    # ⏱️ ASISTENCIA
    # ─────────────────────────────────────────

    @staticmethod
    def asistencia_registrada(asistencia, tipo: str):
        """
        tipo: 'entrada' | 'salida'
        """
        return {
            "asistencia_id": str(asistencia.id),
            "empleado_id": str(asistencia.empleado_id),
            "turno_id": str(asistencia.turno_id),
            "tipo": tipo,
            "timestamp": asistencia.timestamp.isoformat()
        }

    # ─────────────────────────────────────────
    # 🍳 COCINA
    # ─────────────────────────────────────────

    @staticmethod
    def cocina_asignacion_creada(asignacion):
        return {
            "asignacion_id": str(asignacion.id),
            "pedido_id": str(asignacion.pedido_id),
            "empleado_id": str(asignacion.empleado_id),
            "restaurante_id": str(asignacion.restaurante_id),
            "estacion": asignacion.estacion
        }

    @staticmethod
    def cocina_asignacion_completada(asignacion, tiempo_preparacion: float):
        return {
            "asignacion_id": str(asignacion.id),
            "pedido_id": str(asignacion.pedido_id),
            "empleado_id": str(asignacion.empleado_id),
            "tiempo_preparacion": tiempo_preparacion
        }

    @staticmethod
    def cocina_sla_excedido(pedido_id, tiempo_estimado, tiempo_real):
        return {
            "pedido_id": str(pedido_id),
            "tiempo_estimado": tiempo_estimado,
            "tiempo_real": tiempo_real
        }

    # ─────────────────────────────────────────
    # 🚚 ENTREGA
    # ─────────────────────────────────────────

    @staticmethod
    def entrega_asignada(entrega):
        return {
            "entrega_id": str(entrega.id),
            "pedido_id": str(entrega.pedido_id),
            "empleado_id": str(entrega.empleado_id),
            "restaurante_id": str(entrega.restaurante_id)
        }

    # ─────────────────────────────────────────
    # 🚨 ALERTAS
    # ─────────────────────────────────────────

    @staticmethod
    def alerta_creada(alerta):
        return {
            "alerta_id": str(alerta.id),
            "tipo": alerta.tipo,
            "descripcion": alerta.descripcion,
            "prioridad": alerta.prioridad,
            "restaurante_id": str(alerta.restaurante_id)
        }

    @staticmethod
    def alerta_resuelta(alerta):
        return {
            "alerta_id": str(alerta.id),
            "fecha_resolucion": alerta.fecha_resolucion.isoformat() if alerta.fecha_resolucion else None
        }

    # ─────────────────────────────────────────
    # 💰 NÓMINA
    # ─────────────────────────────────────────

    @staticmethod
    def nomina_cerrada(nomina):
        return {
            "nomina_id": str(nomina.id),
            "periodo_inicio": nomina.periodo_inicio.isoformat(),
            "periodo_fin": nomina.periodo_fin.isoformat(),
            "total_pagado": float(nomina.total_pagado)
        }

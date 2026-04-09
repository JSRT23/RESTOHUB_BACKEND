# staff_service/app/staff/events/builders.py
class StaffEventBuilder:
    """
    Construye los payloads de los eventos de staff_service.

    Regla: solo acceder a campos que EXISTEN en el modelo.
    AsignacionCocina: id, pedido_id, comanda_id, cocinero_id, estacion_id, asignado_en, completado_en, sla_segundos
    ServicioEntrega:  id, pedido_id, repartidor_id, estado, asignado_en, completado_en
    Turno:            id, empleado_id, restaurante_id, fecha_inicio, fecha_fin, estado
    """

    # ─────────────────────────────────────────
    # 👷 TURNOS
    # ─────────────────────────────────────────

    @staticmethod
    def turno_creado(turno):
        return {
            "turno_id":      str(turno.id),
            "empleado_id":   str(turno.empleado_id),
            "restaurante_id": str(turno.restaurante_id),
            "fecha_inicio":  turno.fecha_inicio.isoformat(),
            "fecha_fin":     turno.fecha_fin.isoformat() if turno.fecha_fin else None,
        }

    @staticmethod
    def turno_actualizado(turno, cambios: dict):
        return {
            "turno_id": str(turno.id),
            "cambios":  cambios,
        }

    @staticmethod
    def turno_estado(turno):
        return {
            "turno_id": str(turno.id),
            "estado":   turno.estado,
        }

    @staticmethod
    def turno_completado(turno):
        return {
            "turno_id": str(turno.id),
        }

    @staticmethod
    def turno_cancelado(turno, motivo: str):
        return {
            "turno_id": str(turno.id),
            "motivo":   motivo,
        }

    # ─────────────────────────────────────────
    # ⏱️ ASISTENCIA
    # ─────────────────────────────────────────

    @staticmethod
    def asistencia_registrada(asistencia, tipo: str):
        """tipo: 'entrada' | 'salida'"""
        return {
            "asistencia_id": str(asistencia.id),
            "empleado_id":   str(asistencia.turno.empleado_id),
            "turno_id":      str(asistencia.turno_id),
            "tipo":          tipo,
            "timestamp":     asistencia.hora_entrada.isoformat() if tipo == "entrada" else asistencia.hora_salida.isoformat(),
        }

    # ─────────────────────────────────────────
    # 🍳 COCINA
    # ─────────────────────────────────────────

    @staticmethod
    def cocina_asignacion_creada(asignacion):
        # ✅ Accede solo a campos reales de AsignacionCocina
        # cocinero_id y estacion_id existen como FK _id fields
        return {
            "asignacion_id": str(asignacion.id),
            "pedido_id":     str(asignacion.pedido_id),
            "comanda_id":    str(asignacion.comanda_id),
            "cocinero_id":   str(asignacion.cocinero_id),
            "estacion_id":   str(asignacion.estacion_id),
            # restaurante_id se obtiene desde la estación (sin query extra si no está cargada)
            "restaurante_id": str(asignacion.estacion.restaurante_id) if hasattr(asignacion, "_estacion_cache") or asignacion.estacion_id else None,
        }

    @staticmethod
    def cocina_asignacion_completada(asignacion, tiempo_preparacion: float):
        return {
            "asignacion_id":      str(asignacion.id),
            "pedido_id":          str(asignacion.pedido_id),
            "cocinero_id":        str(asignacion.cocinero_id),
            "tiempo_preparacion": tiempo_preparacion,
            "sla_segundos":       asignacion.sla_segundos,
        }

    @staticmethod
    def cocina_sla_excedido(pedido_id, tiempo_estimado, tiempo_real):
        return {
            "pedido_id":       str(pedido_id),
            "tiempo_estimado": tiempo_estimado,
            "tiempo_real":     tiempo_real,
        }

    # ─────────────────────────────────────────
    # 🚚 ENTREGA
    # ─────────────────────────────────────────

    @staticmethod
    def entrega_asignada(entrega):
        # ✅ ServicioEntrega tiene: id, pedido_id, repartidor_id, estado
        # NO tiene empleado_id ni restaurante_id directamente
        return {
            "entrega_id":    str(entrega.id),
            "pedido_id":     str(entrega.pedido_id),
            "repartidor_id": str(entrega.repartidor_id),
            # restaurante del repartidor — acceso lazy, solo si ya está en caché
            "restaurante_id": str(entrega.repartidor.restaurante_id) if hasattr(entrega, "_repartidor_cache") else None,
        }

    # ─────────────────────────────────────────
    # 🚨 ALERTAS
    # ─────────────────────────────────────────

    @staticmethod
    def alerta_creada(alerta):
        return {
            "alerta_id":      str(alerta.id),
            "tipo":           alerta.tipo,
            "nivel":          alerta.nivel,
            "mensaje":        alerta.mensaje,
            "restaurante_id": str(alerta.restaurante_id),
            "referencia_id":  str(alerta.referencia_id) if alerta.referencia_id else None,
        }

    @staticmethod
    def alerta_resuelta(alerta):
        return {
            "alerta_id":        str(alerta.id),
            "fecha_resolucion": alerta.updated_at.isoformat() if alerta.updated_at else None,
        }

    # ─────────────────────────────────────────
    # 💰 NÓMINA
    # ─────────────────────────────────────────

    @staticmethod
    def nomina_cerrada(nomina):
        return {
            "nomina_id":       str(nomina.id),
            "empleado_id":     str(nomina.empleado_id),
            "periodo_inicio":  nomina.periodo_inicio.isoformat(),
            "periodo_fin":     nomina.periodo_fin.isoformat(),
            "total_horas_normales": float(nomina.total_horas_normales),
            "total_horas_extra":    float(nomina.total_horas_extra),
            "dias_trabajados":      nomina.dias_trabajados,
            "moneda":               nomina.moneda,
        }

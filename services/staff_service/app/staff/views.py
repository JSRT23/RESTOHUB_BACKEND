# staff_service/app/staff/views.py
# CAMBIOS vs original:
#   1. TurnoViewSet.iniciar():  TTL del QR = tiempo_hasta_fin + 45 min (era 15 min fijo)
#   2. AsistenciaViewSet.salida(): acepta sin RegistroAsistencia de entrada
#      (permite que supervisor complete turno manualmente aunque no haya entrada QR)
#   3. TurnoViewSet: agrega @action completar() — supervisor puede completar sin QR
#   4. TurnoViewSet.cancelar(): acepta estado ACTIVO además de PROGRAMADO
#      (para auto-cancelar turnos activos que pasaron +30min del fin)
# Todo lo demás es IDÉNTICO al original.

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from app.staff.models import (
    AlertaOperacional,
    AsignacionCocina,
    ConfiguracionLaboralPais,
    Empleado,
    EstacionCocina,
    EstadoTurno,
    PrediccionPersonal,
    RegistroAsistencia,
    ResumenNomina,
    RestauranteLocal,
    RolEmpleado,
    ServicioEntrega,
    Turno,
)
from app.staff.serializers import (
    AlertaOperacionalSerializer,
    AsignacionCocinaListSerializer,
    AsignacionCocinaSerializer,
    ConfiguracionLaboralPaisSerializer,
    EmpleadoListSerializer,
    EmpleadoSerializer,
    EmpleadoWriteSerializer,
    EntradaSerializer,
    EstacionCocinaSerializer,
    GenerarNominaSerializer,
    PrediccionPersonalSerializer,
    RepartidorDisponibleSerializer,
    RegistroAsistenciaSerializer,
    ResumenNominaSerializer,
    RestauranteLocalSerializer,
    SalidaSerializer,
    TurnoListSerializer,
    TurnoSerializer,
    TurnoWriteSerializer,
    ServicioEntregaSerializer,
)


# ---------------------------------------------------------------------------
# RestauranteLocal
# ---------------------------------------------------------------------------

class RestauranteLocalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RestauranteLocal.objects.all()
    serializer_class = RestauranteLocalSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = RestauranteLocal.objects.all()
        pais = self.request.query_params.get("pais")
        activo = self.request.query_params.get("activo")
        if pais:
            qs = qs.filter(pais=pais)
        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")
        return qs.order_by("nombre")

    @action(detail=True, methods=["get"], url_path="config-laboral")
    def config_laboral(self, request, pk=None):
        restaurante = self.get_object()
        config = ConfiguracionLaboralPais.objects.filter(
            pais=restaurante.pais
        ).first()
        if not config:
            return Response(
                {"detail": f"No hay configuración laboral para '{restaurante.get_pais_display()}'."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ConfiguracionLaboralPaisSerializer(config).data)


# ---------------------------------------------------------------------------
# Empleado
# ---------------------------------------------------------------------------

class EmpleadoViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Empleado.objects.select_related("restaurante").all()
        restaurante_id = self.request.query_params.get("restaurante_id")
        rol = self.request.query_params.get("rol")
        activo = self.request.query_params.get("activo")
        pais = self.request.query_params.get("pais")
        if restaurante_id:
            qs = qs.filter(restaurante__restaurante_id=restaurante_id)
        if rol:
            qs = qs.filter(rol=rol)
        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")
        if pais:
            qs = qs.filter(pais=pais)
        return qs.order_by("apellido", "nombre")

    def get_serializer_class(self):
        if self.action == "list":
            return EmpleadoListSerializer
        if self.action in ["create", "partial_update"]:
            return EmpleadoWriteSerializer
        return EmpleadoSerializer

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        empleado = self.get_object()
        if not empleado.activo:
            return Response(
                {"detail": "El empleado ya está inactivo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        empleado.activo = False
        empleado.save(update_fields=["activo", "updated_at"])
        return Response(EmpleadoSerializer(empleado).data)


# ---------------------------------------------------------------------------
# Turno
# ---------------------------------------------------------------------------

class TurnoViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Turno.objects.select_related("empleado__restaurante").all()
        empleado_id = self.request.query_params.get("empleado_id")
        restaurante_id = self.request.query_params.get("restaurante_id")
        estado = self.request.query_params.get("estado")
        fecha_desde = self.request.query_params.get("fecha_desde")
        fecha_hasta = self.request.query_params.get("fecha_hasta")
        if empleado_id:
            qs = qs.filter(empleado_id=empleado_id)
        if restaurante_id:
            qs = qs.filter(restaurante_id=restaurante_id)
        if estado:
            qs = qs.filter(estado=estado)
        if fecha_desde:
            qs = qs.filter(fecha_inicio__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_inicio__date__lte=fecha_hasta)
        return qs.order_by("-fecha_inicio")

    def get_serializer_class(self):
        if self.action == "list":
            return TurnoListSerializer
        if self.action == "create":
            return TurnoWriteSerializer
        return TurnoSerializer

    @action(detail=True, methods=["post"])
    def iniciar(self, request, pk=None):
        """
        POST /turnos/{id}/iniciar/
        PROGRAMADO → ACTIVO.

        FIX: TTL del QR = tiempo restante hasta fechaFin + 45 min de gracia.
        Antes era 15 min fijo → el QR expiraba mucho antes de que el empleado
        llegara a escanearlo al final del turno.
        """
        import uuid
        turno = self.get_object()

        if turno.estado != EstadoTurno.PROGRAMADO:
            return Response(
                {"detail": f"Solo se puede iniciar un turno en estado 'programado'. Estado actual: '{turno.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # TTL dinámico: tiempo hasta el fin del turno + 45 min de gracia
        ahora = timezone.now()
        tiempo_hasta_fin = max((turno.fecha_fin - ahora).total_seconds(), 0)
        ttl_segundos = tiempo_hasta_fin + (45 * 60)   # + 45 min post-fin

        turno.estado = EstadoTurno.ACTIVO
        turno.qr_token = uuid.uuid4()
        turno.qr_expira_en = ahora + timedelta(seconds=ttl_segundos)
        turno.save(update_fields=["estado", "qr_token", "qr_expira_en"])

        return Response(TurnoSerializer(turno).data)

    @action(detail=True, methods=["post"])
    def completar(self, request, pk=None):
        """
        POST /turnos/{id}/completar/
        ACTIVO → COMPLETADO sin necesidad de QR escaneado.

        Permite al supervisor registrar la salida manualmente cuando
        el empleado no ha escaneado el QR de salida.
        Si existe un RegistroAsistencia abierto, lo cierra calculando horas.
        """
        turno = self.get_object()

        if turno.estado != EstadoTurno.ACTIVO:
            return Response(
                {"detail": f"Solo se pueden completar turnos activos. Estado actual: '{turno.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ahora = timezone.now()

        # Cerrar RegistroAsistencia si existe uno abierto
        try:
            registro = turno.registro_asistencia
            if registro.hora_salida is None:
                from decimal import Decimal
                horas_normales, horas_extra = AsistenciaViewSet._calcular_horas_static(
                    registro.hora_entrada, ahora, turno.empleado
                )
                registro.hora_salida = ahora
                registro.horas_normales = horas_normales
                registro.horas_extra = horas_extra
                registro.save(
                    update_fields=["hora_salida", "horas_normales", "horas_extra"])
        except RegistroAsistencia.DoesNotExist:
            pass  # Sin registro QR — no pasa nada, el turno igual se completa

        turno.estado = EstadoTurno.COMPLETADO
        turno.save(update_fields=["estado"])

        return Response(TurnoSerializer(turno).data)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        """
        POST /turnos/{id}/cancelar/

        FIX: acepta PROGRAMADO y ACTIVO.
        El auto-cancelador del frontend cancela turnos ACTIVOS que llevan
        +30 min después de su fechaFin sin registrar salida.
        """
        turno = self.get_object()

        if turno.estado not in [EstadoTurno.PROGRAMADO, EstadoTurno.ACTIVO]:
            return Response(
                {"detail": f"Solo se pueden cancelar turnos en estado 'programado' o 'activo'. Estado actual: '{turno.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        turno.estado = EstadoTurno.CANCELADO
        turno.save(update_fields=["estado"])

        return Response(TurnoSerializer(turno).data)


# ---------------------------------------------------------------------------
# Asistencia
# ---------------------------------------------------------------------------

class AsistenciaViewSet(viewsets.ViewSet):

    def list(self, request):
        empleado_id = request.query_params.get("empleado_id")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        restaurante_id = request.query_params.get("restaurante_id")

        if not empleado_id and not fecha_desde:
            return Response(
                {"detail": "Se requiere al menos 'empleado_id' o 'fecha_desde'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = RegistroAsistencia.objects.select_related(
            "turno__empleado__restaurante"
        ).all()

        if empleado_id:
            qs = qs.filter(turno__empleado_id=empleado_id)
        if restaurante_id:
            qs = qs.filter(turno__restaurante_id=restaurante_id)
        if fecha_desde:
            qs = qs.filter(hora_entrada__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(hora_entrada__date__lte=fecha_hasta)

        return Response(
            RegistroAsistenciaSerializer(
                qs.order_by("-hora_entrada"), many=True).data
        )

    @action(detail=False, methods=["post"])
    def entrada(self, request):
        serializer = EntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        metodo = serializer.validated_data["metodo_registro"]
        qr_token = serializer.validated_data.get("qr_token")
        turno_id = serializer.validated_data.get("turno_id")

        if metodo == "qr":
            turno = self._resolver_turno_por_qr(qr_token)
            if turno is None:
                return Response(
                    {"detail": "QR inválido o expirado."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            turno = self._resolver_turno_manual(turno_id)
            if turno is None:
                return Response(
                    {"detail": "Turno no encontrado o no está activo."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if hasattr(turno, "registro_asistencia"):
            return Response(
                {"detail": "Ya existe un registro de entrada para este turno."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        registro = RegistroAsistencia.objects.create(
            turno=turno,
            hora_entrada=timezone.now(),
            metodo_registro=metodo,
        )
        return Response(
            RegistroAsistenciaSerializer(registro).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def salida(self, request):
        """
        POST /asistencia/salida/

        FIX: ya no requiere RegistroAsistencia de entrada.
        Si el empleado no escaneó entrada (turno iniciado manualmente),
        se completa el turno de todas formas calculando horas desde fechaInicio.
        """
        serializer = SalidaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        turno_id = serializer.validated_data["turno_id"]

        try:
            turno = Turno.objects.get(pk=turno_id, estado=EstadoTurno.ACTIVO)
        except Turno.DoesNotExist:
            return Response(
                {"detail": "Turno no encontrado o no está activo."},
                status=status.HTTP_404_NOT_FOUND,
            )

        ahora = timezone.now()

        try:
            registro = turno.registro_asistencia

            if registro.hora_salida:
                return Response(
                    {"detail": "Ya se registró la salida de este turno."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            horas_normales, horas_extra = self._calcular_horas(
                registro.hora_entrada, ahora, turno.empleado
            )
            registro.hora_salida = ahora
            registro.horas_normales = horas_normales
            registro.horas_extra = horas_extra
            registro.save(
                update_fields=["hora_salida", "horas_normales", "horas_extra"])

        except RegistroAsistencia.DoesNotExist:
            # Sin registro de entrada (turno iniciado manualmente por supervisor)
            # Calcular horas desde el inicio del turno
            horas_normales, horas_extra = self._calcular_horas(
                turno.fecha_inicio, ahora, turno.empleado
            )
            registro = RegistroAsistencia.objects.create(
                turno=turno,
                hora_entrada=turno.fecha_inicio,
                hora_salida=ahora,
                horas_normales=horas_normales,
                horas_extra=horas_extra,
                metodo_registro="manual",
            )

        # Completar el turno
        turno.estado = EstadoTurno.COMPLETADO
        turno.save(update_fields=["estado"])

        return Response(RegistroAsistenciaSerializer(registro).data)

    # ── helpers ─────────────────────────────────────────────────────────────

    def _resolver_turno_por_qr(self, qr_token):
        return Turno.objects.filter(
            qr_token=qr_token,
            estado=EstadoTurno.ACTIVO,
            qr_expira_en__gte=timezone.now(),
        ).first()

    def _resolver_turno_manual(self, turno_id):
        return Turno.objects.filter(
            pk=turno_id,
            estado=EstadoTurno.ACTIVO,
        ).first()

    def _calcular_horas(self, hora_entrada, hora_salida, empleado):
        from decimal import Decimal
        total_horas = Decimal(
            str(round((hora_salida - hora_entrada).total_seconds() / 3600, 2))
        )
        config = ConfiguracionLaboralPais.objects.filter(
            pais=empleado.pais).first()
        if not config:
            return total_horas, Decimal("0.00")
        limite = Decimal(str(config.horas_max_diarias))
        if total_horas <= limite:
            return total_horas, Decimal("0.00")
        return limite, total_horas - limite

    @staticmethod
    def _calcular_horas_static(hora_entrada, hora_salida, empleado):
        """Static version para uso desde TurnoViewSet.completar()"""
        from decimal import Decimal
        total_horas = Decimal(
            str(round((hora_salida - hora_entrada).total_seconds() / 3600, 2))
        )
        config = ConfiguracionLaboralPais.objects.filter(
            pais=empleado.pais).first()
        if not config:
            return total_horas, Decimal("0.00")
        limite = Decimal(str(config.horas_max_diarias))
        if total_horas <= limite:
            return total_horas, Decimal("0.00")
        return limite, total_horas - limite


# ---------------------------------------------------------------------------
# EstacionCocina
# ---------------------------------------------------------------------------

class EstacionCocinaViewSet(viewsets.ModelViewSet):
    serializer_class = EstacionCocinaSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = EstacionCocina.objects.all()
        restaurante_id = self.request.query_params.get("restaurante_id")
        activa = self.request.query_params.get("activa")
        if restaurante_id:
            qs = qs.filter(restaurante_id=restaurante_id)
        if activa is not None:
            qs = qs.filter(activa=activa.lower() == "true")
        return qs.order_by("nombre")


# ---------------------------------------------------------------------------
# AsignacionCocina
# ---------------------------------------------------------------------------

class AsignacionCocinaViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = AsignacionCocina.objects.select_related(
            "cocinero", "estacion").all()
        restaurante_id = self.request.query_params.get("restaurante_id")
        cocinero_id = self.request.query_params.get("cocinero_id")
        fecha_desde = self.request.query_params.get("fecha_desde")
        fecha_hasta = self.request.query_params.get("fecha_hasta")
        sin_completar = self.request.query_params.get("sin_completar")
        if restaurante_id:
            qs = qs.filter(estacion__restaurante_id=restaurante_id)
        if cocinero_id:
            qs = qs.filter(cocinero_id=cocinero_id)
        if fecha_desde:
            qs = qs.filter(asignado_en__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(asignado_en__date__lte=fecha_hasta)
        if sin_completar and sin_completar.lower() == "true":
            qs = qs.filter(completado_en__isnull=True)
        return qs.order_by("-asignado_en")

    def get_serializer_class(self):
        if self.action == "list":
            return AsignacionCocinaListSerializer
        return AsignacionCocinaSerializer

    @action(detail=True, methods=["post"])
    def completar(self, request, pk=None):
        asignacion = self.get_object()
        if asignacion.completado_en:
            return Response(
                {"detail": "Esta asignación ya fue completada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        asignacion.completado_en = timezone.now()
        asignacion.sla_segundos = asignacion.calcular_sla()
        asignacion.save(update_fields=["completado_en", "sla_segundos"])
        return Response(AsignacionCocinaSerializer(asignacion).data)


# ---------------------------------------------------------------------------
# ServicioEntrega
# ---------------------------------------------------------------------------

class ServicioEntregaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServicioEntregaSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = ServicioEntrega.objects.select_related("repartidor").all()
        repartidor_id = self.request.query_params.get("repartidor_id")
        estado = self.request.query_params.get("estado")
        fecha_desde = self.request.query_params.get("fecha_desde")
        fecha_hasta = self.request.query_params.get("fecha_hasta")
        if repartidor_id:
            qs = qs.filter(repartidor_id=repartidor_id)
        if estado:
            qs = qs.filter(estado=estado)
        if fecha_desde:
            qs = qs.filter(asignado_en__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(asignado_en__date__lte=fecha_hasta)
        return qs.order_by("-asignado_en")

    @action(detail=False, methods=["get"])
    def disponibles(self, request):
        restaurante_id = request.query_params.get("restaurante_id")
        qs = Empleado.objects.filter(
            rol=RolEmpleado.REPARTIDOR,
            activo=True,
            turnos__estado=EstadoTurno.ACTIVO,
        ).exclude(
            servicios_entrega__estado__in=["asignada", "en_camino"]
        ).distinct()
        if restaurante_id:
            qs = qs.filter(restaurante__restaurante_id=restaurante_id)
        return Response(RepartidorDisponibleSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# AlertaOperacional
# ---------------------------------------------------------------------------

class AlertaOperacionalViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AlertaOperacionalSerializer

    def get_queryset(self):
        qs = AlertaOperacional.objects.all()
        restaurante_id = self.request.query_params.get("restaurante_id")
        nivel = self.request.query_params.get("nivel")
        tipo = self.request.query_params.get("tipo")
        resuelta = self.request.query_params.get("resuelta")
        if restaurante_id:
            qs = qs.filter(restaurante_id=restaurante_id)
        if nivel:
            qs = qs.filter(nivel=nivel)
        if tipo:
            qs = qs.filter(tipo=tipo)
        if resuelta is not None:
            qs = qs.filter(resuelta=resuelta.lower() == "true")
        return qs.order_by("-created_at")

    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        alerta = self.get_object()
        if alerta.resuelta:
            return Response(
                {"detail": "La alerta ya está resuelta."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        alerta.resuelta = True
        alerta.save(update_fields=["resuelta", "updated_at"])
        return Response(AlertaOperacionalSerializer(alerta).data)


# ---------------------------------------------------------------------------
# ResumenNomina
# ---------------------------------------------------------------------------

class ResumenNominaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ResumenNominaSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = ResumenNomina.objects.select_related("empleado").all()
        empleado_id = self.request.query_params.get("empleado_id")
        restaurante_id = self.request.query_params.get("restaurante_id")
        cerrado = self.request.query_params.get("cerrado")
        periodo_inicio = self.request.query_params.get("periodo_inicio")
        periodo_fin = self.request.query_params.get("periodo_fin")
        if empleado_id:
            qs = qs.filter(empleado_id=empleado_id)
        if restaurante_id:
            qs = qs.filter(
                empleado__restaurante__restaurante_id=restaurante_id)
        if cerrado is not None:
            qs = qs.filter(cerrado=cerrado.lower() == "true")
        if periodo_inicio:
            qs = qs.filter(periodo_inicio__gte=periodo_inicio)
        if periodo_fin:
            qs = qs.filter(periodo_fin__lte=periodo_fin)
        return qs.order_by("-periodo_inicio")

    @action(detail=False, methods=["post"])
    def generar(self, request):
        serializer = GenerarNominaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        periodo_inicio = serializer.validated_data["periodo_inicio"]
        periodo_fin = serializer.validated_data["periodo_fin"]
        empleado_id = serializer.validated_data.get("empleado_id")
        restaurante_id = serializer.validated_data.get("restaurante_id")
        if empleado_id:
            empleados = Empleado.objects.filter(pk=empleado_id)
        else:
            empleados = Empleado.objects.filter(
                restaurante__restaurante_id=restaurante_id, activo=True,
            )
        if not empleados.exists():
            return Response(
                {"detail": "No se encontraron empleados para los parámetros dados."},
                status=status.HTTP_404_NOT_FOUND,
            )
        generados = []
        for empleado in empleados:
            resumen = self._generar_resumen(
                empleado, periodo_inicio, periodo_fin)
            if resumen:
                generados.append(resumen)
        return Response(
            ResumenNominaSerializer(generados, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def cerrar(self, request, pk=None):
        resumen = self.get_object()
        if resumen.cerrado:
            return Response(
                {"detail": "Este período ya está cerrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        resumen.cerrado = True
        resumen.save(update_fields=["cerrado"])
        return Response(ResumenNominaSerializer(resumen).data)

    def _generar_resumen(self, empleado, periodo_inicio, periodo_fin):
        from decimal import Decimal
        existente = ResumenNomina.objects.filter(
            empleado=empleado,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
        ).first()
        if existente and existente.cerrado:
            return existente
        registros = RegistroAsistencia.objects.filter(
            turno__empleado=empleado,
            hora_entrada__date__gte=periodo_inicio,
            hora_entrada__date__lte=periodo_fin,
            hora_salida__isnull=False,
        )
        total_normales = sum(
            (r.horas_normales for r in registros), Decimal("0.00"))
        total_extra = sum((r.horas_extra for r in registros), Decimal("0.00"))
        dias = registros.values("hora_entrada__date").distinct().count()
        moneda_por_pais = {
            "CO": "COP", "MX": "MXN", "AR": "ARS",
            "CL": "CLP", "BR": "BRL", "PE": "PEN", "PA": "USD",
        }
        moneda = moneda_por_pais.get(empleado.pais, "USD")
        resumen, _ = ResumenNomina.objects.update_or_create(
            empleado=empleado,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            defaults={
                "total_horas_normales": total_normales,
                "total_horas_extra":    total_extra,
                "dias_trabajados":      dias,
                "moneda":               moneda,
            },
        )
        return resumen


# ---------------------------------------------------------------------------
# PrediccionPersonal
# ---------------------------------------------------------------------------

class PrediccionPersonalViewSet(viewsets.ModelViewSet):
    serializer_class = PrediccionPersonalSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = PrediccionPersonal.objects.all()
        restaurante_id = self.request.query_params.get("restaurante_id")
        fecha_desde = self.request.query_params.get("fecha_desde")
        fecha_hasta = self.request.query_params.get("fecha_hasta")
        fuente = self.request.query_params.get("fuente")
        if restaurante_id:
            qs = qs.filter(restaurante_id=restaurante_id)
        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__lte=fecha_hasta)
        if fuente:
            qs = qs.filter(fuente=fuente)
        return qs.order_by("fecha")

    @action(detail=False, methods=["get"], url_path=r"(?P<restaurante_id>[^/.]+)/semana")
    def semana(self, request, restaurante_id=None):
        from django.utils import timezone
        hoy = timezone.now().date()
        fin = hoy + timedelta(days=7)
        predicciones = PrediccionPersonal.objects.filter(
            restaurante_id=restaurante_id,
            fecha__gte=hoy,
            fecha__lte=fin,
        ).order_by("fecha")
        return Response(PrediccionPersonalSerializer(predicciones, many=True).data)

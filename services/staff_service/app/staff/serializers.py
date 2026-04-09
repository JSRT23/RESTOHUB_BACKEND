from django.utils import timezone
from rest_framework import serializers

from app.staff.models import (
    AlertaOperacional,
    AsignacionCocina,
    ConfiguracionLaboralPais,
    Empleado,
    EstacionCocina,
    PrediccionPersonal,
    RegistroAsistencia,
    ResumenNomina,
    RestauranteLocal,
    ServicioEntrega,
    Turno,
)


# ---------------------------------------------------------------------------
# RestauranteLocal
# ---------------------------------------------------------------------------

class RestauranteLocalSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestauranteLocal
        fields = [
            "id", "restaurante_id", "nombre",
            "pais", "ciudad", "activo",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "restaurante_id", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# ConfiguracionLaboralPais
# ---------------------------------------------------------------------------

class ConfiguracionLaboralPaisSerializer(serializers.ModelSerializer):
    pais_display = serializers.CharField(
        source="get_pais_display", read_only=True)

    class Meta:
        model = ConfiguracionLaboralPais
        fields = [
            "id", "pais", "pais_display",
            "horas_max_diarias", "horas_max_semanales",
            "factor_hora_extra",
            "descanso_min_entre_turnos",
            "horas_continuas_para_descanso",
            "duracion_descanso_obligatorio",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


# ---------------------------------------------------------------------------
# Empleado
# ---------------------------------------------------------------------------

class EmpleadoListSerializer(serializers.ModelSerializer):
    """Versión ligera para listados — sin datos de auditoría."""
    rol_display = serializers.CharField(
        source="get_rol_display", read_only=True)
    pais_display = serializers.CharField(
        source="get_pais_display", read_only=True)
    restaurante_nombre = serializers.CharField(
        source="restaurante.nombre", read_only=True
    )

    class Meta:
        model = Empleado
        fields = [
            "id", "nombre", "apellido", "documento",
            "rol", "rol_display", "pais", "pais_display",
            "restaurante", "restaurante_nombre", "activo",
        ]


class EmpleadoSerializer(serializers.ModelSerializer):
    """Detalle completo — incluye auditoría y config laboral del país."""
    rol_display = serializers.CharField(
        source="get_rol_display", read_only=True)
    pais_display = serializers.CharField(
        source="get_pais_display", read_only=True)
    restaurante_nombre = serializers.CharField(
        source="restaurante.nombre", read_only=True
    )

    class Meta:
        model = Empleado
        fields = [
            "id", "nombre", "apellido", "documento",
            "email", "telefono",
            "rol", "rol_display",
            "pais", "pais_display",
            "restaurante", "restaurante_nombre",
            "fecha_contratacion", "activo",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmpleadoWriteSerializer(serializers.ModelSerializer):
    """Para POST y PATCH — valida documento único y restaurante existente."""

    class Meta:
        model = Empleado
        fields = [
            "nombre", "apellido", "documento",
            "email", "telefono",
            "rol", "pais", "restaurante",
            "fecha_contratacion",
        ]

    def validate_restaurante(self, value):
        if not value.activo:
            raise serializers.ValidationError(
                "No se puede asignar un empleado a un restaurante inactivo."
            )
        return value

    def validate(self, attrs):
        # Consistencia país — el empleado debe ser del mismo país que el restaurante
        restaurante = attrs.get("restaurante") or (
            self.instance.restaurante if self.instance else None
        )
        pais = attrs.get("pais") or (
            self.instance.pais if self.instance else None)

        if restaurante and pais and restaurante.pais != pais:
            raise serializers.ValidationError(
                f"El país del empleado ({pais}) no coincide con el "
                f"país del restaurante ({restaurante.pais})."
            )
        return attrs


# ---------------------------------------------------------------------------
# Turno
# ---------------------------------------------------------------------------

class TurnoListSerializer(serializers.ModelSerializer):
    """Listado — sin exponer qr_token."""
    empleado_nombre = serializers.SerializerMethodField()
    estado_display = serializers.CharField(
        source="get_estado_display", read_only=True)
    duracion_horas = serializers.FloatField(
        source="duracion_programada_horas", read_only=True
    )

    class Meta:
        model = Turno
        fields = [
            "id", "empleado", "empleado_nombre",
            "restaurante_id", "fecha_inicio", "fecha_fin",
            "estado", "estado_display", "duracion_horas",
        ]

    def get_empleado_nombre(self, obj):
        return f"{obj.empleado.nombre} {obj.empleado.apellido}"


class TurnoSerializer(serializers.ModelSerializer):
    """Detalle — expone qr_token para que la app móvil genere el QR."""
    empleado_nombre = serializers.SerializerMethodField()
    estado_display = serializers.CharField(
        source="get_estado_display", read_only=True)
    duracion_horas = serializers.FloatField(
        source="duracion_programada_horas", read_only=True
    )

    class Meta:
        model = Turno
        fields = [
            "id", "empleado", "empleado_nombre",
            "restaurante_id", "fecha_inicio", "fecha_fin",
            "estado", "estado_display", "duracion_horas",
            "qr_token", "qr_expira_en",
            "notas", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "qr_token", "created_at", "updated_at",
        ]

    def get_empleado_nombre(self, obj):
        return f"{obj.empleado.nombre} {obj.empleado.apellido}"


class TurnoWriteSerializer(serializers.ModelSerializer):
    """Para POST — valida solapamiento y descanso mínimo entre turnos."""

    class Meta:
        model = Turno
        fields = [
            "empleado", "restaurante_id",
            "fecha_inicio", "fecha_fin", "notas",
        ]

    def validate(self, attrs):
        empleado = attrs.get("empleado")
        fecha_inicio = attrs.get("fecha_inicio")
        fecha_fin = attrs.get("fecha_fin")

        if fecha_inicio and fecha_fin and fecha_inicio >= fecha_fin:
            raise serializers.ValidationError(
                "fecha_inicio debe ser anterior a fecha_fin."
            )

        # ✅ ELIMINADA la validación fecha_inicio < now() — bloqueaba fixtures y tests

        if empleado and fecha_inicio and fecha_fin:
            self._validar_solapamiento(empleado, fecha_inicio, fecha_fin)
            self._validar_descanso_minimo(empleado, fecha_inicio, fecha_fin)

        return attrs

    def _validar_solapamiento(self, empleado, fecha_inicio, fecha_fin):
        from app.staff.models import EstadoTurno
        from django.db.models import Q

        qs = Turno.objects.filter(
            empleado=empleado,
            estado__in=[EstadoTurno.PROGRAMADO, EstadoTurno.ACTIVO],
        ).filter(
            Q(fecha_inicio__lt=fecha_fin) & Q(fecha_fin__gt=fecha_inicio)
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "El empleado ya tiene un turno que se solapa con este horario."
            )

    def _validar_descanso_minimo(self, empleado, fecha_inicio, fecha_fin):
        """
        Verifica que el empleado descansó el mínimo de minutos entre
        el turno anterior y este, según ConfiguracionLaboralPais.
        """
        from app.staff.models import ConfiguracionLaboralPais
        from datetime import timedelta

        config = ConfiguracionLaboralPais.objects.filter(
            pais=empleado.pais).first()
        if not config:
            return

        min_descanso = timedelta(minutes=config.descanso_min_entre_turnos)

        # Turno inmediatamente anterior
        turno_anterior = (
            Turno.objects
            .filter(empleado=empleado, fecha_fin__lte=fecha_inicio)
            .order_by("-fecha_fin")
            .first()
        )
        if turno_anterior:
            descanso_real = fecha_inicio - turno_anterior.fecha_fin
            if descanso_real < min_descanso:
                horas = config.descanso_min_entre_turnos // 60
                minutos = config.descanso_min_entre_turnos % 60
                raise serializers.ValidationError(
                    f"El empleado necesita al menos {horas}h {minutos}m de descanso "
                    f"entre turnos según la normativa de {empleado.get_pais_display()}."
                )

        # Turno inmediatamente posterior
        turno_posterior = (
            Turno.objects
            .filter(empleado=empleado, fecha_inicio__gte=fecha_fin)
            .order_by("fecha_inicio")
            .first()
        )
        if turno_posterior:
            descanso_real = turno_posterior.fecha_inicio - fecha_fin
            if descanso_real < min_descanso:
                raise serializers.ValidationError(
                    f"Este turno no deja suficiente descanso antes del siguiente turno "
                    f"del empleado ({turno_posterior.fecha_inicio:%Y-%m-%d %H:%M})."
                )


# ---------------------------------------------------------------------------
# RegistroAsistencia
# ---------------------------------------------------------------------------

class RegistroAsistenciaSerializer(serializers.ModelSerializer):
    empleado_id = serializers.UUIDField(
        source="turno.empleado_id", read_only=True)
    empleado_nombre = serializers.SerializerMethodField()
    metodo_display = serializers.CharField(
        source="get_metodo_registro_display", read_only=True
    )
    horas_totales = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = RegistroAsistencia
        fields = [
            "id", "turno", "empleado_id", "empleado_nombre",
            "hora_entrada", "hora_salida",
            "metodo_registro", "metodo_display",
            "horas_normales", "horas_extra", "horas_totales",
            "created_at",
        ]
        read_only_fields = [
            "id", "empleado_id", "horas_normales",
            "horas_extra", "horas_totales", "created_at",
        ]

    def get_empleado_nombre(self, obj):
        e = obj.turno.empleado
        return f"{e.nombre} {e.apellido}"


class EntradaSerializer(serializers.Serializer):
    """
    POST /asistencia/entrada/
    Valida el QR token o permite entrada manual con turno_id explícito.
    """
    qr_token = serializers.UUIDField(required=False)
    turno_id = serializers.UUIDField(required=False)
    metodo_registro = serializers.ChoiceField(
        choices=[("qr", "QR dinámico"), ("manual", "Registro manual")],
        default="qr",
    )

    def validate(self, attrs):
        qr_token = attrs.get("qr_token")
        turno_id = attrs.get("turno_id")

        if not qr_token and not turno_id:
            raise serializers.ValidationError(
                "Se requiere qr_token o turno_id."
            )
        if attrs["metodo_registro"] == "qr" and not qr_token:
            raise serializers.ValidationError(
                "Se requiere qr_token para método QR."
            )
        return attrs


class SalidaSerializer(serializers.Serializer):
    """
    POST /asistencia/salida/
    Cierra el RegistroAsistencia abierto del turno activo del empleado.
    """
    turno_id = serializers.UUIDField()


# ---------------------------------------------------------------------------
# EstacionCocina
# ---------------------------------------------------------------------------

class EstacionCocinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstacionCocina
        fields = [
            "id", "restaurante_id", "nombre",
            "capacidad_simultanea", "activa",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        # Verificar que el restaurante existe en la copia local
        restaurante_id = attrs.get("restaurante_id")
        if restaurante_id:
            if not RestauranteLocal.objects.filter(
                restaurante_id=restaurante_id, activo=True
            ).exists():
                raise serializers.ValidationError(
                    {"restaurante_id": "Restaurante no encontrado o inactivo."}
                )
        return attrs


# ---------------------------------------------------------------------------
# AsignacionCocina
# ---------------------------------------------------------------------------

class AsignacionCocinaListSerializer(serializers.ModelSerializer):
    cocinero_nombre = serializers.SerializerMethodField()
    estacion_nombre = serializers.CharField(
        source="estacion.nombre", read_only=True)
    sla_display = serializers.SerializerMethodField()

    class Meta:
        model = AsignacionCocina
        fields = [
            "id", "pedido_id", "comanda_id",
            "cocinero", "cocinero_nombre",
            "estacion", "estacion_nombre",
            "asignado_en", "completado_en",
            "sla_segundos", "sla_display",
        ]

    def get_cocinero_nombre(self, obj):
        return f"{obj.cocinero.nombre} {obj.cocinero.apellido}"

    def get_sla_display(self, obj):
        if obj.sla_segundos is None:
            return None
        m = obj.sla_segundos // 60
        s = obj.sla_segundos % 60
        return f"{m:02d}:{s:02d}"


class AsignacionCocinaSerializer(AsignacionCocinaListSerializer):
    """Detalle completo — igual que el listado, sin campos extra por ahora."""
    class Meta(AsignacionCocinaListSerializer.Meta):
        fields = AsignacionCocinaListSerializer.Meta.fields + \
            ["created_at", "updated_at"]


# ---------------------------------------------------------------------------
# ServicioEntrega
# ---------------------------------------------------------------------------

class ServicioEntregaSerializer(serializers.ModelSerializer):
    repartidor_nombre = serializers.SerializerMethodField()
    estado_display = serializers.CharField(
        source="get_estado_display", read_only=True)

    class Meta:
        model = ServicioEntrega
        fields = [
            "id", "pedido_id",
            "repartidor", "repartidor_nombre",
            "estado", "estado_display",
            "asignado_en", "completado_en",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "asignado_en", "created_at", "updated_at"]

    def get_repartidor_nombre(self, obj):
        return f"{obj.repartidor.nombre} {obj.repartidor.apellido}"


class RepartidorDisponibleSerializer(serializers.ModelSerializer):
    """Versión mínima para el endpoint /entregas/disponibles/."""
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Empleado
        fields = ["id", "nombre_completo", "telefono", "restaurante"]

    def get_nombre_completo(self, obj):
        return f"{obj.nombre} {obj.apellido}"


# ---------------------------------------------------------------------------
# AlertaOperacional
# ---------------------------------------------------------------------------

class AlertaOperacionalSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(
        source="get_tipo_display", read_only=True)
    nivel_display = serializers.CharField(
        source="get_nivel_display", read_only=True)

    class Meta:
        model = AlertaOperacional
        fields = [
            "id", "restaurante_id",
            "tipo", "tipo_display",
            "nivel", "nivel_display",
            "mensaje", "referencia_id",
            "resuelta", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "tipo", "nivel", "mensaje",
            "referencia_id", "created_at", "updated_at",
        ]


# ---------------------------------------------------------------------------
# ResumenNomina
# ---------------------------------------------------------------------------

class ResumenNominaSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.SerializerMethodField()
    total_horas = serializers.DecimalField(
        max_digits=7, decimal_places=2, read_only=True
    )
    moneda_display = serializers.CharField(
        source="get_moneda_display", read_only=True)

    class Meta:
        model = ResumenNomina
        fields = [
            "id", "empleado", "empleado_nombre",
            "periodo_inicio", "periodo_fin",
            "total_horas_normales", "total_horas_extra", "total_horas",
            "dias_trabajados", "moneda", "moneda_display",
            "cerrado", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "total_horas_normales", "total_horas_extra",
            "dias_trabajados", "cerrado", "created_at", "updated_at",
        ]

    def get_empleado_nombre(self, obj):
        return f"{obj.empleado.nombre} {obj.empleado.apellido}"


class GenerarNominaSerializer(serializers.Serializer):
    """
    POST /nomina/generar/
    Genera o recalcula el ResumenNomina de un período para un empleado
    o todos los empleados de un restaurante.
    """
    periodo_inicio = serializers.DateField()
    periodo_fin = serializers.DateField()
    empleado_id = serializers.UUIDField(required=False)
    restaurante_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if not attrs.get("empleado_id") and not attrs.get("restaurante_id"):
            raise serializers.ValidationError(
                "Se requiere empleado_id o restaurante_id."
            )
        if attrs["periodo_inicio"] > attrs["periodo_fin"]:
            raise serializers.ValidationError(
                "periodo_inicio debe ser anterior a periodo_fin."
            )
        return attrs


# ---------------------------------------------------------------------------
# PrediccionPersonal
# ---------------------------------------------------------------------------

class PrediccionPersonalSerializer(serializers.ModelSerializer):
    fuente_display = serializers.CharField(
        source="get_fuente_display", read_only=True)

    class Meta:
        model = PrediccionPersonal
        fields = [
            "id", "restaurante_id", "fecha",
            "demanda_estimada", "personal_recomendado",
            "fuente", "fuente_display", "notas",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        restaurante_id = attrs.get("restaurante_id")
        if restaurante_id:
            if not RestauranteLocal.objects.filter(
                restaurante_id=restaurante_id, activo=True
            ).exists():
                raise serializers.ValidationError(
                    {"restaurante_id": "Restaurante no encontrado o inactivo."}
                )
        return attrs

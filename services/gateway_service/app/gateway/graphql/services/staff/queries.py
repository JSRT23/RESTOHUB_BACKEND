import graphene

from ....client import staff_client
from .types import (
    AlertaOperacionalType,
    AsignacionCocinaType,
    ConfigLaboralType,
    EmpleadoType,
    EstacionCocinaType,
    PrediccionPersonalType,
    RegistroAsistenciaType,
    RepartidorDisponibleType,
    ResumenNominaType,
    RestauranteStaffType,
    ServicioEntregaType,
    TurnoType,
)


def _build(tipo, data):
    """Instancia un ObjectType desde un dict. Retorna None si data es None."""
    if not data:
        return None
    return tipo(**{k: v for k, v in data.items() if hasattr(tipo, k)})


def _build_list(tipo, data):
    if not data:
        return []
    items = data.get("results", data) if isinstance(data, dict) else data
    return [_build(tipo, item) for item in items if item]


class StaffQuery(graphene.ObjectType):

    # ── Restaurantes ─────────────────────────────────────────────────────────

    restaurantes_staff = graphene.List(
        RestauranteStaffType,
        pais=graphene.String(),
        activo=graphene.Boolean(),
    )
    restaurante_staff = graphene.Field(
        RestauranteStaffType,
        restaurante_id=graphene.ID(required=True),
    )
    config_laboral = graphene.Field(
        ConfigLaboralType,
        restaurante_id=graphene.ID(required=True),
    )

    # ── Empleados ────────────────────────────────────────────────────────────

    empleados = graphene.List(
        EmpleadoType,
        restaurante_id=graphene.ID(),
        rol=graphene.String(),
        activo=graphene.Boolean(),
    )
    empleado = graphene.Field(
        EmpleadoType,
        empleado_id=graphene.ID(required=True),
    )

    # ── Turnos ───────────────────────────────────────────────────────────────

    turnos = graphene.List(
        TurnoType,
        empleado_id=graphene.ID(),
        restaurante_id=graphene.ID(),
        estado=graphene.String(),
        fecha_desde=graphene.String(),
        fecha_hasta=graphene.String(),
    )
    turno = graphene.Field(
        TurnoType,
        turno_id=graphene.ID(required=True),
    )

    # ── Asistencia ───────────────────────────────────────────────────────────

    asistencia = graphene.List(
        RegistroAsistenciaType,
        empleado_id=graphene.ID(),
        restaurante_id=graphene.ID(),
        fecha_desde=graphene.String(),
        fecha_hasta=graphene.String(),
    )

    # ── Cocina ───────────────────────────────────────────────────────────────

    estaciones = graphene.List(
        EstacionCocinaType,
        restaurante_id=graphene.ID(),
        activa=graphene.Boolean(),
    )
    asignaciones_cocina = graphene.List(
        AsignacionCocinaType,
        restaurante_id=graphene.ID(),
        cocinero_id=graphene.ID(),
        fecha_desde=graphene.String(),
        sin_completar=graphene.Boolean(),
    )

    # ── Entregas ─────────────────────────────────────────────────────────────

    entregas = graphene.List(
        ServicioEntregaType,
        repartidor_id=graphene.ID(),
        estado=graphene.String(),
    )
    repartidores_disponibles = graphene.List(
        RepartidorDisponibleType,
        restaurante_id=graphene.ID(),
    )

    # ── Alertas ──────────────────────────────────────────────────────────────

    alertas = graphene.List(
        AlertaOperacionalType,
        restaurante_id=graphene.ID(),
        nivel=graphene.String(),
        tipo=graphene.String(),
        resuelta=graphene.Boolean(),
    )

    # ── Nómina ───────────────────────────────────────────────────────────────

    nomina = graphene.List(
        ResumenNominaType,
        empleado_id=graphene.ID(),
        restaurante_id=graphene.ID(),
        cerrado=graphene.Boolean(),
    )

    # ── Predicción ───────────────────────────────────────────────────────────

    predicciones = graphene.List(
        PrediccionPersonalType,
        restaurante_id=graphene.ID(),
        fecha_desde=graphene.String(),
        fecha_hasta=graphene.String(),
    )
    prediccion_semana = graphene.List(
        PrediccionPersonalType,
        restaurante_id=graphene.ID(required=True),
    )

    # =========================================================================
    # Resolvers
    # =========================================================================

    def resolve_restaurantes_staff(self, info, pais=None, activo=None):
        data = staff_client.get_restaurantes(pais=pais, activo=activo)
        return _build_list(RestauranteStaffType, data)

    def resolve_restaurante_staff(self, info, restaurante_id):
        data = staff_client.get_restaurante(restaurante_id)
        return _build(RestauranteStaffType, data)

    def resolve_config_laboral(self, info, restaurante_id):
        data = staff_client.get_config_laboral(restaurante_id)
        return _build(ConfigLaboralType, data)

    def resolve_empleados(self, info, restaurante_id=None, rol=None, activo=None):
        data = staff_client.get_empleados(
            restaurante_id=restaurante_id, rol=rol, activo=activo
        )
        return _build_list(EmpleadoType, data)

    def resolve_empleado(self, info, empleado_id):
        data = staff_client.get_empleado(empleado_id)
        return _build(EmpleadoType, data)

    def resolve_turnos(self, info, empleado_id=None, restaurante_id=None,
                       estado=None, fecha_desde=None, fecha_hasta=None):
        data = staff_client.get_turnos(
            empleado_id=empleado_id,
            restaurante_id=restaurante_id,
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
        return _build_list(TurnoType, data)

    def resolve_turno(self, info, turno_id):
        data = staff_client.get_turno(turno_id)
        return _build(TurnoType, data)

    def resolve_asistencia(self, info, empleado_id=None, restaurante_id=None,
                           fecha_desde=None, fecha_hasta=None):
        data = staff_client.get_asistencia(
            empleado_id=empleado_id,
            restaurante_id=restaurante_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
        return _build_list(RegistroAsistenciaType, data)

    def resolve_estaciones(self, info, restaurante_id=None, activa=None):
        data = staff_client.get_estaciones(
            restaurante_id=restaurante_id, activa=activa)
        return _build_list(EstacionCocinaType, data)

    def resolve_asignaciones_cocina(self, info, restaurante_id=None, cocinero_id=None,
                                    fecha_desde=None, sin_completar=None):
        data = staff_client.get_asignaciones_cocina(
            restaurante_id=restaurante_id,
            cocinero_id=cocinero_id,
            fecha_desde=fecha_desde,
            sin_completar=sin_completar,
        )
        return _build_list(AsignacionCocinaType, data)

    def resolve_entregas(self, info, repartidor_id=None, estado=None):
        data = staff_client.get_entregas(
            repartidor_id=repartidor_id, estado=estado)
        return _build_list(ServicioEntregaType, data)

    def resolve_repartidores_disponibles(self, info, restaurante_id=None):
        data = staff_client.get_repartidores_disponibles(
            restaurante_id=restaurante_id)
        return _build_list(RepartidorDisponibleType, data)

    def resolve_alertas(self, info, restaurante_id=None, nivel=None,
                        tipo=None, resuelta=None):
        data = staff_client.get_alertas(
            restaurante_id=restaurante_id,
            nivel=nivel,
            tipo=tipo,
            resuelta=resuelta,
        )
        return _build_list(AlertaOperacionalType, data)

    def resolve_nomina(self, info, empleado_id=None, restaurante_id=None, cerrado=None):
        data = staff_client.get_nomina(
            empleado_id=empleado_id,
            restaurante_id=restaurante_id,
            cerrado=cerrado,
        )
        return _build_list(ResumenNominaType, data)

    def resolve_predicciones(self, info, restaurante_id=None,
                             fecha_desde=None, fecha_hasta=None):
        data = staff_client.get_predicciones(
            restaurante_id=restaurante_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
        return _build_list(PrediccionPersonalType, data)

    def resolve_prediccion_semana(self, info, restaurante_id):
        data = staff_client.get_prediccion_semana(restaurante_id)
        return _build_list(PrediccionPersonalType, data)

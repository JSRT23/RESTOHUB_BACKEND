# gateway_service/app/gateway/graphql/services/staff/queries.py
import graphene
from .types import (
    AlertaOperacionalType, AsignacionCocinaType,
    ConfigLaboralType, EmpleadoType, EstacionCocinaType,
    PrediccionPersonalType, RegistroAsistenciaType,
    RepartidorDisponibleType, ResumenNominaType,
    RestauranteStaffType, ServicioEntregaType, TurnoType,
)
from ....client import staff_client


# ─────────────────────────────────────────
# NOTA
# ─────────────────────────────────────────
# Retornamos dicts crudos directamente.
# graphene resuelve cada campo buscando root.get(field_name).
# No se necesita _build() ni instanciar ObjectType manualmente.
#
# La API retorna listas directas (no paginadas con "results").
# Si en algún momento se agrega paginación, solo hay que cambiar
# el resolver correspondiente.
# ─────────────────────────────────────────


class StaffQuery(graphene.ObjectType):

    # Restaurantes
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

    # Empleados
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

    # Turnos
    turnos = graphene.List(
        TurnoType,
        empleado_id=graphene.ID(),
        restaurante_id=graphene.ID(),
        estado=graphene.String(),
        fecha_desde=graphene.String(),
        fecha_hasta=graphene.String(),
    )
    turno = graphene.Field(TurnoType, turno_id=graphene.ID(required=True))

    # Asistencia
    asistencia = graphene.List(
        RegistroAsistenciaType,
        empleado_id=graphene.ID(),
        restaurante_id=graphene.ID(),
        fecha_desde=graphene.String(),
        fecha_hasta=graphene.String(),
    )

    # Cocina
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

    # Entregas
    entregas = graphene.List(
        ServicioEntregaType,
        repartidor_id=graphene.ID(),
        estado=graphene.String(),
    )
    repartidores_disponibles = graphene.List(
        RepartidorDisponibleType,
        restaurante_id=graphene.ID(),
    )

    # Alertas
    alertas_operacionales = graphene.List(
        AlertaOperacionalType,
        restaurante_id=graphene.ID(),
        nivel=graphene.String(),
        tipo=graphene.String(),
        resuelta=graphene.Boolean(),
    )

    # Nómina
    nomina = graphene.List(
        ResumenNominaType,
        empleado_id=graphene.ID(),
        restaurante_id=graphene.ID(),
        cerrado=graphene.Boolean(),
    )

    # Predicción
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

    # ── Resolvers ─────────────────────────────────────────────────────────

    def resolve_restaurantes_staff(self, info, pais=None, activo=None):
        return staff_client.get_restaurantes(pais=pais, activo=activo) or []

    def resolve_restaurante_staff(self, info, restaurante_id):
        return staff_client.get_restaurante(restaurante_id)

    def resolve_config_laboral(self, info, restaurante_id):
        return staff_client.get_config_laboral(restaurante_id)

    def resolve_empleados(self, info, restaurante_id=None, rol=None, activo=None):
        return staff_client.get_empleados(
            restaurante_id=restaurante_id, rol=rol, activo=activo
        ) or []

    def resolve_empleado(self, info, empleado_id):
        return staff_client.get_empleado(empleado_id)

    def resolve_turnos(self, info, empleado_id=None, restaurante_id=None,
                       estado=None, fecha_desde=None, fecha_hasta=None):
        return staff_client.get_turnos(
            empleado_id=empleado_id,
            restaurante_id=restaurante_id,
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        ) or []

    def resolve_turno(self, info, turno_id):
        return staff_client.get_turno(turno_id)

    def resolve_asistencia(self, info, empleado_id=None, restaurante_id=None,
                           fecha_desde=None, fecha_hasta=None):
        return staff_client.get_asistencia(
            empleado_id=empleado_id,
            restaurante_id=restaurante_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        ) or []

    def resolve_estaciones(self, info, restaurante_id=None, activa=None):
        return staff_client.get_estaciones(
            restaurante_id=restaurante_id, activa=activa
        ) or []

    def resolve_asignaciones_cocina(self, info, restaurante_id=None,
                                    cocinero_id=None, fecha_desde=None,
                                    sin_completar=None):
        return staff_client.get_asignaciones_cocina(
            restaurante_id=restaurante_id,
            cocinero_id=cocinero_id,
            fecha_desde=fecha_desde,
            sin_completar=sin_completar,
        ) or []

    def resolve_entregas(self, info, repartidor_id=None, estado=None):
        return staff_client.get_entregas(
            repartidor_id=repartidor_id, estado=estado
        ) or []

    def resolve_repartidores_disponibles(self, info, restaurante_id=None):
        return staff_client.get_repartidores_disponibles(
            restaurante_id=restaurante_id
        ) or []

    def resolve_alertas_operacionales(self, info, restaurante_id=None,
                                      nivel=None, tipo=None, resuelta=None):
        return staff_client.get_alertas(
            restaurante_id=restaurante_id,
            nivel=nivel,
            tipo=tipo,
            resuelta=resuelta,
        ) or []

    def resolve_nomina(self, info, empleado_id=None, restaurante_id=None, cerrado=None):
        return staff_client.get_nomina(
            empleado_id=empleado_id,
            restaurante_id=restaurante_id,
            cerrado=cerrado,
        ) or []

    def resolve_predicciones(self, info, restaurante_id=None,
                             fecha_desde=None, fecha_hasta=None):
        return staff_client.get_predicciones(
            restaurante_id=restaurante_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        ) or []

    def resolve_prediccion_semana(self, info, restaurante_id):
        return staff_client.get_prediccion_semana(restaurante_id) or []

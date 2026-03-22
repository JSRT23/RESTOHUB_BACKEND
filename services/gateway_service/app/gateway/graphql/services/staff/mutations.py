import graphene

from ....client import staff_client
from .types import (
    AlertaOperacionalType,
    EmpleadoType,
    EstacionCocinaType,
    PrediccionPersonalType,
    RegistroAsistenciaType,
    ResumenNominaType,
    TurnoType,
)


def _build(tipo, data):
    if not data:
        return None
    return tipo(**{k: v for k, v in data.items() if hasattr(tipo, k)})


# ---------------------------------------------------------------------------
# Empleados
# ---------------------------------------------------------------------------

class CrearEmpleado(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        apellido = graphene.String(required=True)
        documento = graphene.String(required=True)
        email = graphene.String(required=True)
        telefono = graphene.String()
        rol = graphene.String(required=True)
        pais = graphene.String(required=True)
        restaurante = graphene.ID(required=True)
        fecha_contratacion = graphene.String()

    empleado = graphene.Field(EmpleadoType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, **kwargs):
        data = staff_client.crear_empleado(kwargs)
        if not data:
            return CrearEmpleado(ok=False, errores="Error al crear el empleado.")
        return CrearEmpleado(empleado=_build(EmpleadoType, data), ok=True)


class EditarEmpleado(graphene.Mutation):
    class Arguments:
        empleado_id = graphene.ID(required=True)
        nombre = graphene.String()
        apellido = graphene.String()
        telefono = graphene.String()
        rol = graphene.String()
        restaurante = graphene.ID()

    empleado = graphene.Field(EmpleadoType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, empleado_id, **kwargs):
        data = staff_client.editar_empleado(empleado_id, kwargs)
        if not data:
            return EditarEmpleado(ok=False, errores="Error al editar el empleado.")
        return EditarEmpleado(empleado=_build(EmpleadoType, data), ok=True)


class DesactivarEmpleado(graphene.Mutation):
    class Arguments:
        empleado_id = graphene.ID(required=True)

    empleado = graphene.Field(EmpleadoType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, empleado_id):
        data = staff_client.desactivar_empleado(empleado_id)
        if not data:
            return DesactivarEmpleado(ok=False, errores="Error al desactivar el empleado.")
        return DesactivarEmpleado(empleado=_build(EmpleadoType, data), ok=True)


# ---------------------------------------------------------------------------
# Turnos
# ---------------------------------------------------------------------------

class CrearTurno(graphene.Mutation):
    class Arguments:
        empleado = graphene.ID(required=True)
        restaurante_id = graphene.ID(required=True)
        fecha_inicio = graphene.String(required=True)
        fecha_fin = graphene.String(required=True)
        notas = graphene.String()

    turno = graphene.Field(TurnoType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, **kwargs):
        data = staff_client.crear_turno(kwargs)
        if not data:
            return CrearTurno(ok=False, errores="Error al crear el turno.")
        return CrearTurno(turno=_build(TurnoType, data), ok=True)


class IniciarTurno(graphene.Mutation):
    class Arguments:
        turno_id = graphene.ID(required=True)

    turno = graphene.Field(TurnoType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, turno_id):
        data = staff_client.iniciar_turno(turno_id)
        if not data:
            return IniciarTurno(ok=False, errores="Error al iniciar el turno.")
        return IniciarTurno(turno=_build(TurnoType, data), ok=True)


class CancelarTurno(graphene.Mutation):
    class Arguments:
        turno_id = graphene.ID(required=True)

    turno = graphene.Field(TurnoType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, turno_id):
        data = staff_client.cancelar_turno(turno_id)
        if not data:
            return CancelarTurno(ok=False, errores="Error al cancelar el turno.")
        return CancelarTurno(turno=_build(TurnoType, data), ok=True)


# ---------------------------------------------------------------------------
# Asistencia
# ---------------------------------------------------------------------------

class RegistrarEntrada(graphene.Mutation):
    class Arguments:
        qr_token = graphene.String()
        turno_id = graphene.ID()
        metodo = graphene.String()

    registro = graphene.Field(RegistroAsistenciaType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, qr_token=None, turno_id=None, metodo="qr"):
        if not qr_token and not turno_id:
            return RegistrarEntrada(ok=False, errores="Se requiere qr_token o turno_id.")
        data = staff_client.registrar_entrada(
            qr_token=qr_token, turno_id=turno_id, metodo=metodo
        )
        if not data:
            return RegistrarEntrada(ok=False, errores="QR inválido o error al registrar entrada.")
        return RegistrarEntrada(registro=_build(RegistroAsistenciaType, data), ok=True)


class RegistrarSalida(graphene.Mutation):
    class Arguments:
        turno_id = graphene.ID(required=True)

    registro = graphene.Field(RegistroAsistenciaType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, turno_id):
        data = staff_client.registrar_salida(turno_id)
        if not data:
            return RegistrarSalida(ok=False, errores="Error al registrar salida.")
        return RegistrarSalida(registro=_build(RegistroAsistenciaType, data), ok=True)


# ---------------------------------------------------------------------------
# Estaciones de cocina
# ---------------------------------------------------------------------------

class CrearEstacion(graphene.Mutation):
    class Arguments:
        restaurante_id = graphene.ID(required=True)
        nombre = graphene.String(required=True)
        capacidad_simultanea = graphene.Int()

    estacion = graphene.Field(EstacionCocinaType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, **kwargs):
        data = staff_client.crear_estacion(kwargs)
        if not data:
            return CrearEstacion(ok=False, errores="Error al crear la estación.")
        return CrearEstacion(estacion=_build(EstacionCocinaType, data), ok=True)


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------

class ResolverAlerta(graphene.Mutation):
    class Arguments:
        alerta_id = graphene.ID(required=True)

    alerta = graphene.Field(AlertaOperacionalType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, alerta_id):
        data = staff_client.resolver_alerta(alerta_id)
        if not data:
            return ResolverAlerta(ok=False, errores="Error al resolver la alerta.")
        return ResolverAlerta(alerta=_build(AlertaOperacionalType, data), ok=True)


# ---------------------------------------------------------------------------
# Nómina
# ---------------------------------------------------------------------------

class GenerarNomina(graphene.Mutation):
    class Arguments:
        periodo_inicio = graphene.String(required=True)
        periodo_fin = graphene.String(required=True)
        empleado_id = graphene.ID()
        restaurante_id = graphene.ID()

    resumenes = graphene.List(ResumenNominaType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, periodo_inicio, periodo_fin,
               empleado_id=None, restaurante_id=None):
        if not empleado_id and not restaurante_id:
            return GenerarNomina(ok=False, errores="Se requiere empleado_id o restaurante_id.")

        payload = {"periodo_inicio": periodo_inicio,
                   "periodo_fin": periodo_fin}
        if empleado_id:
            payload["empleado_id"] = empleado_id
        if restaurante_id:
            payload["restaurante_id"] = restaurante_id

        data = staff_client.generar_nomina(payload)
        if data is None:
            return GenerarNomina(ok=False, errores="Error al generar nómina.")

        items = data if isinstance(data, list) else data.get("results", [])
        resumenes = [_build(ResumenNominaType, r) for r in items if r]
        return GenerarNomina(resumenes=resumenes, ok=True)


class CerrarNomina(graphene.Mutation):
    class Arguments:
        resumen_id = graphene.ID(required=True)

    resumen = graphene.Field(ResumenNominaType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, resumen_id):
        data = staff_client.cerrar_nomina(resumen_id)
        if not data:
            return CerrarNomina(ok=False, errores="Error al cerrar el período.")
        return CerrarNomina(resumen=_build(ResumenNominaType, data), ok=True)


# ---------------------------------------------------------------------------
# Predicción de personal
# ---------------------------------------------------------------------------

class CrearPrediccion(graphene.Mutation):
    class Arguments:
        restaurante_id = graphene.ID(required=True)
        fecha = graphene.String(required=True)
        demanda_estimada = graphene.Int(required=True)
        personal_recomendado = graphene.Int(required=True)
        fuente = graphene.String()
        notas = graphene.String()

    prediccion = graphene.Field(PrediccionPersonalType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, **kwargs):
        data = staff_client.crear_prediccion(kwargs)
        if not data:
            return CrearPrediccion(ok=False, errores="Error al crear la predicción.")
        return CrearPrediccion(prediccion=_build(PrediccionPersonalType, data), ok=True)


# ---------------------------------------------------------------------------
# Mutation raíz del servicio
# ---------------------------------------------------------------------------

class StaffMutation(graphene.ObjectType):
    # Empleados
    crear_empleado = CrearEmpleado.Field()
    editar_empleado = EditarEmpleado.Field()
    desactivar_empleado = DesactivarEmpleado.Field()

    # Turnos
    crear_turno = CrearTurno.Field()
    iniciar_turno = IniciarTurno.Field()
    cancelar_turno = CancelarTurno.Field()

    # Asistencia
    registrar_entrada = RegistrarEntrada.Field()
    registrar_salida = RegistrarSalida.Field()

    # Cocina
    crear_estacion = CrearEstacion.Field()

    # Alertas
    resolver_alerta = ResolverAlerta.Field()

    # Nómina
    generar_nomina = GenerarNomina.Field()
    cerrar_nomina = CerrarNomina.Field()

    # Predicción
    crear_prediccion = CrearPrediccion.Field()

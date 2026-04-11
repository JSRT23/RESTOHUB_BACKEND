# gateway_service/app/gateway/graphql/services/staff/mutations.py
import graphene
from ....client import staff_client
from .types import (
    AlertaOperacionalType, EmpleadoType, EstacionCocinaType,
    PrediccionPersonalType, RegistroAsistenciaType,
    ResumenNominaType, TurnoType,
)


# ─────────────────────────────────────────
# EMPLEADOS
# ─────────────────────────────────────────

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
        print("DATA ENVIADA:", kwargs)
        data = staff_client.crear_empleado(kwargs)
        print("RESPUESTA:", data)

        if not data:
            return CrearEmpleado(ok=False, errores="Error al crear el empleado.")
        return CrearEmpleado(ok=True, empleado=data)


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
        payload = {k: v for k, v in kwargs.items() if v is not None}
        data = staff_client.editar_empleado(empleado_id, payload)
        if not data:
            return EditarEmpleado(ok=False, errores="Error al editar el empleado.")
        return EditarEmpleado(ok=True, empleado=data)


class ActivarEmpleado(graphene.Mutation):
    """
    Reactiva un empleado desactivado.
    Solo admin_central puede activar empleados.
    Usa editar_empleado con activo=True ya que staff_service
    no tiene endpoint dedicado de activación.
    """
    class Arguments:
        empleado_id = graphene.ID(required=True)

    empleado = graphene.Field(EmpleadoType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, empleado_id):
        from ....middleware.permissions import get_jwt_user
        jwt_user = get_jwt_user(info)
        if not jwt_user or jwt_user.get("rol") != "admin_central":
            return ActivarEmpleado(ok=False, errores="Solo el admin central puede activar empleados.")
        data = staff_client.editar_empleado(str(empleado_id), {"activo": True})
        if not data:
            return ActivarEmpleado(ok=False, errores="Error al activar el empleado.")
        return ActivarEmpleado(ok=True, empleado=data)


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
        return DesactivarEmpleado(ok=True, empleado=data)


# ─────────────────────────────────────────
# TURNOS
# ─────────────────────────────────────────

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
        return CrearTurno(ok=True, turno=data)


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
        return IniciarTurno(ok=True, turno=data)


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
        return CancelarTurno(ok=True, turno=data)


# ─────────────────────────────────────────
# ASISTENCIA
# ─────────────────────────────────────────

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
            qr_token=qr_token, turno_id=turno_id, metodo=metodo)
        if not data:
            return RegistrarEntrada(ok=False, errores="QR inválido o error al registrar entrada.")
        return RegistrarEntrada(ok=True, registro=data)


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
        return RegistrarSalida(ok=True, registro=data)


# ─────────────────────────────────────────
# ESTACIONES DE COCINA
# ─────────────────────────────────────────

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
        return CrearEstacion(ok=True, estacion=data)


class CompletarAsignacionCocina(graphene.Mutation):
    class Arguments:
        asignacion_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, asignacion_id):
        from ....client.staff_client import _post
        data = _post(f"/asignaciones-cocina/{asignacion_id}/completar/")
        if not data:
            return CompletarAsignacionCocina(ok=False, errores="Error al completar asignación.")
        return CompletarAsignacionCocina(ok=True)


# ─────────────────────────────────────────
# ALERTAS
# ─────────────────────────────────────────

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
        return ResolverAlerta(ok=True, alerta=data)


# ─────────────────────────────────────────
# NÓMINA
# ─────────────────────────────────────────

class GenerarNomina(graphene.Mutation):
    class Arguments:
        periodo_inicio = graphene.String(required=True)
        periodo_fin = graphene.String(required=True)
        empleado_id = graphene.ID()
        restaurante_id = graphene.ID()

    resumenes = graphene.List(ResumenNominaType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, periodo_inicio, periodo_fin, empleado_id=None, restaurante_id=None):
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
        items = data if isinstance(data, list) else []
        return GenerarNomina(ok=True, resumenes=items)


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
        return CerrarNomina(ok=True, resumen=data)


# ─────────────────────────────────────────
# PREDICCIÓN DE PERSONAL
# ─────────────────────────────────────────

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
        return CrearPrediccion(ok=True, prediccion=data)


# ─────────────────────────────────────────
# REGISTRO
# ─────────────────────────────────────────

class StaffMutation(graphene.ObjectType):
    # Empleados
    crear_empleado = CrearEmpleado.Field()
    editar_empleado = EditarEmpleado.Field()
    activar_empleado = ActivarEmpleado.Field()   # ← NUEVO
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
    completar_asignacion_cocina = CompletarAsignacionCocina.Field()

    # Alertas
    resolver_alerta = ResolverAlerta.Field()

    # Nómina
    generar_nomina = GenerarNomina.Field()
    cerrar_nomina = CerrarNomina.Field()

    # Predicción
    crear_prediccion = CrearPrediccion.Field()

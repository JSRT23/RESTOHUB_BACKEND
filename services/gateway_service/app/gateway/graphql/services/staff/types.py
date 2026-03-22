import graphene


class RestauranteStaffType(graphene.ObjectType):
    id = graphene.ID()
    restaurante_id = graphene.ID()
    nombre = graphene.String()
    pais = graphene.String()
    ciudad = graphene.String()
    activo = graphene.Boolean()


class ConfigLaboralType(graphene.ObjectType):
    id = graphene.ID()
    pais = graphene.String()
    pais_display = graphene.String()
    horas_max_diarias = graphene.Int()
    horas_max_semanales = graphene.Int()
    factor_hora_extra = graphene.String()
    descanso_min_entre_turnos = graphene.Int()
    horas_continuas_para_descanso = graphene.Int()
    duracion_descanso_obligatorio = graphene.Int()


class EmpleadoType(graphene.ObjectType):
    id = graphene.ID()
    nombre = graphene.String()
    apellido = graphene.String()
    documento = graphene.String()
    email = graphene.String()
    telefono = graphene.String()
    rol = graphene.String()
    rol_display = graphene.String()
    pais = graphene.String()
    pais_display = graphene.String()
    restaurante = graphene.ID()
    restaurante_nombre = graphene.String()
    fecha_contratacion = graphene.String()
    activo = graphene.Boolean()


class TurnoType(graphene.ObjectType):
    id = graphene.ID()
    empleado = graphene.ID()
    empleado_nombre = graphene.String()
    restaurante_id = graphene.ID()
    fecha_inicio = graphene.String()
    fecha_fin = graphene.String()
    estado = graphene.String()
    estado_display = graphene.String()
    duracion_horas = graphene.Float()
    qr_token = graphene.String()
    qr_expira_en = graphene.String()
    notas = graphene.String()


class RegistroAsistenciaType(graphene.ObjectType):
    id = graphene.ID()
    turno = graphene.ID()
    empleado_id = graphene.ID()
    empleado_nombre = graphene.String()
    hora_entrada = graphene.String()
    hora_salida = graphene.String()
    metodo_registro = graphene.String()
    metodo_display = graphene.String()
    horas_normales = graphene.String()
    horas_extra = graphene.String()
    horas_totales = graphene.String()


class EstacionCocinaType(graphene.ObjectType):
    id = graphene.ID()
    restaurante_id = graphene.ID()
    nombre = graphene.String()
    capacidad_simultanea = graphene.Int()
    activa = graphene.Boolean()


class AsignacionCocinaType(graphene.ObjectType):
    id = graphene.ID()
    pedido_id = graphene.ID()
    comanda_id = graphene.ID()
    cocinero = graphene.ID()
    cocinero_nombre = graphene.String()
    estacion = graphene.ID()
    estacion_nombre = graphene.String()
    asignado_en = graphene.String()
    completado_en = graphene.String()
    sla_segundos = graphene.Int()
    sla_display = graphene.String()


class ServicioEntregaType(graphene.ObjectType):
    id = graphene.ID()
    pedido_id = graphene.ID()
    repartidor = graphene.ID()
    repartidor_nombre = graphene.String()
    estado = graphene.String()
    estado_display = graphene.String()
    asignado_en = graphene.String()
    completado_en = graphene.String()


class RepartidorDisponibleType(graphene.ObjectType):
    id = graphene.ID()
    nombre_completo = graphene.String()
    telefono = graphene.String()
    restaurante = graphene.ID()


class AlertaOperacionalType(graphene.ObjectType):
    id = graphene.ID()
    restaurante_id = graphene.ID()
    tipo = graphene.String()
    tipo_display = graphene.String()
    nivel = graphene.String()
    nivel_display = graphene.String()
    mensaje = graphene.String()
    referencia_id = graphene.ID()
    resuelta = graphene.Boolean()
    created_at = graphene.String()


class ResumenNominaType(graphene.ObjectType):
    id = graphene.ID()
    empleado = graphene.ID()
    empleado_nombre = graphene.String()
    periodo_inicio = graphene.String()
    periodo_fin = graphene.String()
    total_horas_normales = graphene.String()
    total_horas_extra = graphene.String()
    total_horas = graphene.String()
    dias_trabajados = graphene.Int()
    moneda = graphene.String()
    moneda_display = graphene.String()
    cerrado = graphene.Boolean()


class PrediccionPersonalType(graphene.ObjectType):
    id = graphene.ID()
    restaurante_id = graphene.ID()
    fecha = graphene.String()
    demanda_estimada = graphene.Int()
    personal_recomendado = graphene.Int()
    fuente = graphene.String()
    fuente_display = graphene.String()
    notas = graphene.String()

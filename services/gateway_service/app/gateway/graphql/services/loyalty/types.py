import graphene


class CuentaPuntosType(graphene.ObjectType):
    id = graphene.ID()
    cliente_id = graphene.ID()
    saldo = graphene.Int()
    puntos_totales_historicos = graphene.Int()
    nivel = graphene.String()
    nivel_display = graphene.String()
    ultima_actualizacion = graphene.String()
    cache = graphene.Boolean()


class TransaccionPuntosType(graphene.ObjectType):
    id = graphene.ID()
    cuenta = graphene.ID()
    cliente_id = graphene.ID()
    tipo = graphene.String()
    tipo_display = graphene.String()
    puntos = graphene.Int()
    puntos_display = graphene.String()
    saldo_anterior = graphene.Int()
    saldo_posterior = graphene.Int()
    pedido_id = graphene.ID()
    restaurante_id = graphene.ID()
    promocion_id = graphene.ID()
    descripcion = graphene.String()
    created_at = graphene.String()


class ReglaPromocionType(graphene.ObjectType):
    id = graphene.ID()
    tipo_condicion = graphene.String()
    tipo_condicion_display = graphene.String()
    monto_minimo = graphene.String()
    moneda = graphene.String()
    plato_id = graphene.ID()
    categoria_id = graphene.ID()
    hora_inicio = graphene.Int()
    hora_fin = graphene.Int()


class PromocionType(graphene.ObjectType):
    id = graphene.ID()
    nombre = graphene.String()
    descripcion = graphene.String()
    alcance = graphene.String()
    alcance_display = graphene.String()
    marca = graphene.String()
    restaurante_id = graphene.ID()
    tipo_beneficio = graphene.String()
    tipo_beneficio_display = graphene.String()
    valor = graphene.String()
    puntos_bonus = graphene.Int()
    multiplicador_puntos = graphene.String()
    fecha_inicio = graphene.String()
    fecha_fin = graphene.String()
    activa = graphene.Boolean()
    reglas = graphene.List(ReglaPromocionType)
    total_aplicaciones = graphene.Int()
    created_at = graphene.String()
    updated_at = graphene.String()


class PromocionListType(graphene.ObjectType):
    id = graphene.ID()
    nombre = graphene.String()
    alcance = graphene.String()
    alcance_display = graphene.String()
    tipo_beneficio = graphene.String()
    tipo_beneficio_display = graphene.String()
    valor = graphene.String()
    puntos_bonus = graphene.Int()
    fecha_inicio = graphene.String()
    fecha_fin = graphene.String()
    activa = graphene.Boolean()


class AplicacionPromocionType(graphene.ObjectType):
    id = graphene.ID()
    promocion = graphene.ID()
    promocion_nombre = graphene.String()
    pedido_id = graphene.ID()
    cliente_id = graphene.ID()
    descuento_aplicado = graphene.String()
    puntos_bonus_otorgados = graphene.Int()
    applied_at = graphene.String()


class CuponType(graphene.ObjectType):
    id = graphene.ID()
    codigo = graphene.String()
    tipo_descuento = graphene.String()
    tipo_descuento_display = graphene.String()
    valor_descuento = graphene.String()
    cliente_id = graphene.ID()
    promocion = graphene.ID()
    promocion_nombre = graphene.String()
    usos_actuales = graphene.Int()
    limite_uso = graphene.Int()
    fecha_inicio = graphene.String()
    fecha_fin = graphene.String()
    activo = graphene.Boolean()
    disponible = graphene.Boolean()
    created_at = graphene.String()


class CatalogoPlatoType(graphene.ObjectType):
    id = graphene.ID()
    plato_id = graphene.ID()
    categoria_id = graphene.ID()
    nombre = graphene.String()
    activo = graphene.Boolean()
    updated_at = graphene.String()


class CatalogoCategoriaType(graphene.ObjectType):
    id = graphene.ID()
    categoria_id = graphene.ID()
    nombre = graphene.String()
    activo = graphene.Boolean()
    updated_at = graphene.String()

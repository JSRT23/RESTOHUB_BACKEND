import graphene


# ─────────────────────────────────────────
# MENU SERVICE TYPES
# ─────────────────────────────────────────

class RestauranteType(graphene.ObjectType):
    id = graphene.ID()
    nombre = graphene.String()
    pais = graphene.String()
    ciudad = graphene.String()
    direccion = graphene.String()
    moneda = graphene.String()
    activo = graphene.Boolean()
    fecha_creacion = graphene.String()
    fecha_actualizacion = graphene.String()


class CategoriaType(graphene.ObjectType):
    id = graphene.ID()
    nombre = graphene.String()
    orden = graphene.Int()
    activo = graphene.Boolean()


class IngredienteType(graphene.ObjectType):
    id = graphene.ID()
    nombre = graphene.String()
    unidad_medida = graphene.String()
    descripcion = graphene.String()
    activo = graphene.Boolean()


class PlatoIngredienteType(graphene.ObjectType):
    id = graphene.ID()
    ingrediente = graphene.Field(IngredienteType)
    ingrediente_nombre = graphene.String()
    unidad_medida = graphene.String()
    cantidad = graphene.Float()


class PrecioPlatoType(graphene.ObjectType):
    id = graphene.ID()
    plato_id = graphene.ID()
    restaurante_id = graphene.ID()
    restaurante_nombre = graphene.String()
    precio = graphene.String()
    moneda = graphene.String()
    fecha_inicio = graphene.String()
    fecha_fin = graphene.String()
    activo = graphene.Boolean()
    esta_vigente = graphene.Boolean()


class PlatoType(graphene.ObjectType):
    id = graphene.ID()
    nombre = graphene.String()
    descripcion = graphene.String()
    categoria = graphene.Field(CategoriaType)
    categoria_nombre = graphene.String()
    imagen = graphene.String()
    activo = graphene.Boolean()
    fecha_creacion = graphene.String()
    fecha_actualizacion = graphene.String()
    ingredientes = graphene.List(PlatoIngredienteType)
    precios = graphene.List(PrecioPlatoType)


# Tipos especiales para menú agrupado
class MenuPlatoType(graphene.ObjectType):
    plato_id = graphene.ID()
    nombre = graphene.String()
    descripcion = graphene.String()
    imagen = graphene.String()
    precio = graphene.String()
    moneda = graphene.String()


class MenuCategoriaType(graphene.ObjectType):
    categoria_id = graphene.ID()
    nombre = graphene.String()
    orden = graphene.Int()
    platos = graphene.List(MenuPlatoType)


class MenuRestauranteType(graphene.ObjectType):
    restaurante_id = graphene.ID()
    nombre = graphene.String()
    ciudad = graphene.String()
    pais = graphene.String()
    moneda = graphene.String()
    categorias = graphene.List(MenuCategoriaType)


# ─────────────────────────────────────────
# ORDER SERVICE TYPES
# ─────────────────────────────────────────

class DetallePedidoType(graphene.ObjectType):
    id = graphene.ID()
    plato_id = graphene.ID()
    nombre_plato = graphene.String()
    precio_unitario = graphene.String()
    cantidad = graphene.Int()
    subtotal = graphene.String()
    notas = graphene.String()


class ComandaCocinaType(graphene.ObjectType):
    id = graphene.ID()
    estacion = graphene.String()
    estado = graphene.String()
    hora_envio = graphene.String()
    hora_fin = graphene.String()
    tiempo_preparacion_segundos = graphene.Float()


class SeguimientoPedidoType(graphene.ObjectType):
    id = graphene.ID()
    estado = graphene.String()
    fecha = graphene.String()
    descripcion = graphene.String()


class EntregaPedidoType(graphene.ObjectType):
    id = graphene.ID()
    tipo_entrega = graphene.String()
    direccion = graphene.String()
    repartidor_id = graphene.ID()
    repartidor_nombre = graphene.String()
    estado_entrega = graphene.String()
    fecha_salida = graphene.String()
    fecha_entrega_real = graphene.String()


class PedidoType(graphene.ObjectType):
    id = graphene.ID()
    restaurante_id = graphene.ID()
    cliente_id = graphene.ID()
    canal = graphene.String()
    estado = graphene.String()
    prioridad = graphene.Int()
    total = graphene.String()
    moneda = graphene.String()
    mesa_id = graphene.ID()
    fecha_creacion = graphene.String()
    fecha_entrega_estimada = graphene.String()
    detalles = graphene.List(DetallePedidoType)
    comandas = graphene.List(ComandaCocinaType)
    seguimientos = graphene.List(SeguimientoPedidoType)
    entrega = graphene.Field(EntregaPedidoType)

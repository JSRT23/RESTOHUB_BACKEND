import graphene


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
    categoria_nombre = graphene.String()
    imagen = graphene.String()
    activo = graphene.Boolean()
    fecha_creacion = graphene.String()
    fecha_actualizacion = graphene.String()
    ingredientes = graphene.List(PlatoIngredienteType)
    precios = graphene.List(PrecioPlatoType)


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

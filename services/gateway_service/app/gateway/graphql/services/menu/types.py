# gateway_service/app/gateway/graphql/services/menu/types.py
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
    """
    restaurante_id = null → ingrediente global
    restaurante_id = UUID → ingrediente del restaurante
    """
    id = graphene.ID()
    restaurante_id = graphene.ID()   # null = global
    nombre = graphene.String()
    unidad_medida = graphene.String()
    descripcion = graphene.String()
    activo = graphene.Boolean()


class PlatoIngredienteType(graphene.ObjectType):
    id = graphene.ID()
    ingrediente_id = graphene.ID()
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
    """
    restaurante_id = null → plato global
    restaurante_id = UUID → plato del restaurante
    """
    id = graphene.ID()
    restaurante_id = graphene.ID()  # null = global
    nombre = graphene.String()
    descripcion = graphene.String()
    categoria_id = graphene.ID()
    categoria_nombre = graphene.String()
    imagen = graphene.String()
    activo = graphene.Boolean()
    fecha_creacion = graphene.String()
    fecha_actualizacion = graphene.String()
    ingredientes = graphene.List(PlatoIngredienteType)
    precios = graphene.List(PrecioPlatoType)

    def resolve_ingredientes(root, info):
        return root.get("ingredientes", []) if isinstance(root, dict) else []

    def resolve_precios(root, info):
        return root.get("precios", []) if isinstance(root, dict) else []


# ── Menú agrupado ──────────────────────────────────────────────────────────

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

# gateway_service/app/gateway/graphql/services/menu/types.py
import graphene


# ─────────────────────────────────────────
# NOTA DE ARQUITECTURA
# ─────────────────────────────────────────
# Los resolvers reciben el root como dict (la respuesta cruda de la API).
# graphene usa root.get(field_name) por defecto.
# Cuando el nombre del campo GraphQL difiere de la clave del dict
# (ej: GraphQL plato_id ← dict key "plato"), se agrega resolve_*.
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
    # Todos los campos coinciden con el dict → sin resolvers extra


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
    """
    Serializer retorna:
      id, ingrediente (UUID), ingrediente_nombre, unidad_medida, cantidad
    """
    id = graphene.ID()
    ingrediente_id = graphene.ID()
    ingrediente_nombre = graphene.String()
    unidad_medida = graphene.String()
    cantidad = graphene.Float()

    def resolve_ingrediente_id(root, info):
        return root.get("ingrediente") if isinstance(root, dict) else None


class PrecioPlatoType(graphene.ObjectType):
    """
    Serializer retorna:
      id, plato (UUID), restaurante (UUID), restaurante_nombre,
      precio, moneda (flat desde restaurante.moneda),
      fecha_inicio, fecha_fin, activo, esta_vigente
    """
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

    def resolve_plato_id(root, info):
        return root.get("plato") if isinstance(root, dict) else None

    def resolve_restaurante_id(root, info):
        return root.get("restaurante") if isinstance(root, dict) else None


class PlatoType(graphene.ObjectType):
    """
    List serializer retorna: id, nombre, descripcion, categoria (UUID),
      categoria_nombre, imagen, activo, fecha_creacion, fecha_actualizacion
    Detail serializer agrega: ingredientes[], precios[]
    """
    id = graphene.ID()
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

    def resolve_categoria_id(root, info):
        return root.get("categoria") if isinstance(root, dict) else None

    def resolve_ingredientes(root, info):
        if isinstance(root, dict):
            return root.get("ingredientes", [])
        return []

    def resolve_precios(root, info):
        if isinstance(root, dict):
            return root.get("precios", [])
        return []


# ─────────────────────────────────────────
# MENU AGRUPADO — construido en el gateway
# ─────────────────────────────────────────

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

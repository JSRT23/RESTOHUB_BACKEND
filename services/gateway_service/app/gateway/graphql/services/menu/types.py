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
    restaurante_id = graphene.ID()
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

    # FIX: el menu_service devuelve la FK como "ingrediente", no "ingrediente_id"
    def resolve_ingrediente_id(root, info):
        if isinstance(root, dict):
            return root.get("ingrediente_id") or root.get("ingrediente")
        return getattr(root, "ingrediente_id", None)

    def resolve_ingrediente_nombre(root, info):
        if isinstance(root, dict):
            return root.get("ingrediente_nombre")
        return getattr(root, "ingrediente_nombre", None)

    def resolve_unidad_medida(root, info):
        if isinstance(root, dict):
            return root.get("unidad_medida")
        return getattr(root, "unidad_medida", None)

    def resolve_cantidad(root, info):
        if isinstance(root, dict):
            return root.get("cantidad")
        return getattr(root, "cantidad", None)


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

    # FIX: normalizar claves snake_case del serializer
    def resolve_plato_id(root, info):
        if isinstance(root, dict):
            return root.get("plato_id") or root.get("plato")
        return getattr(root, "plato_id", None)

    def resolve_restaurante_id(root, info):
        if isinstance(root, dict):
            return root.get("restaurante_id") or root.get("restaurante")
        return getattr(root, "restaurante_id", None)

    def resolve_esta_vigente(root, info):
        if isinstance(root, dict):
            return root.get("esta_vigente")
        return getattr(root, "esta_vigente", None)


class PlatoType(graphene.ObjectType):
    """
    restaurante_id = null → plato global
    restaurante_id = UUID → plato del restaurante
    """
    id = graphene.ID()
    restaurante_id = graphene.ID()
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

    # FIX: el menu_service devuelve la FK de categoría como "categoria" (no "categoria_id")
    def resolve_categoria_id(root, info):
        if isinstance(root, dict):
            return root.get("categoria_id") or root.get("categoria")
        return getattr(root, "categoria_id", None)

    def resolve_categoria_nombre(root, info):
        if isinstance(root, dict):
            return root.get("categoria_nombre")
        return getattr(root, "categoria_nombre", None)

    def resolve_restaurante_id(root, info):
        if isinstance(root, dict):
            return root.get("restaurante_id") or root.get("restaurante")
        return getattr(root, "restaurante_id", None)

    def resolve_ingredientes(root, info):
        if isinstance(root, dict):
            return root.get("ingredientes", [])
        return []

    def resolve_precios(root, info):
        if isinstance(root, dict):
            return root.get("precios", [])
        return []


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

# gateway_service/app/gateway/graphql/services/menu/types.py
import graphene

# CORRECCIONES:
# 1. PrecioPlatoType: resolve_plato_id y resolve_restaurante_id usaban
#    root.get("plato") y root.get("restaurante") pero el serializer retorna
#    "plato_id" y "restaurante_id" → siempre None. Fix: leer las claves correctas.
#
# 2. PlatoIngredienteType: resolve_ingrediente_id usaba root.get("ingrediente")
#    pero el serializer retorna "ingrediente_id" → siempre None.
#    Fix: el campo ya se llama ingrediente_id, no necesita resolver custom.
#
# 3. PlatoType: resolve_categoria_id usaba root.get("categoria") pero el
#    serializer retorna "categoria_id". Fix: leer la clave correcta.


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
    """
    Serializer retorna: id, ingrediente_id, ingrediente_nombre, unidad_medida, cantidad
    ✅ Fix: el campo del dict es 'ingrediente_id', no 'ingrediente'
    """
    id = graphene.ID()
    # ✅ graphene lo resuelve directo: root.get("ingrediente_id")
    ingrediente_id = graphene.ID()
    ingrediente_nombre = graphene.String()
    unidad_medida = graphene.String()
    cantidad = graphene.Float()

    # ✅ Sin resolver custom — el nombre del campo GraphQL coincide con el key del dict


class PrecioPlatoType(graphene.ObjectType):
    """
    Serializer retorna: id, plato_id, restaurante_id, restaurante_nombre,
    precio, moneda, fecha_inicio, fecha_fin, activo, esta_vigente
    ✅ Fix: los campos del dict son 'plato_id' y 'restaurante_id', no 'plato'/'restaurante'
    """
    id = graphene.ID()
    plato_id = graphene.ID()              # ✅ sin resolver custom
    restaurante_id = graphene.ID()        # ✅ sin resolver custom
    restaurante_nombre = graphene.String()
    precio = graphene.String()
    moneda = graphene.String()
    fecha_inicio = graphene.String()
    fecha_fin = graphene.String()
    activo = graphene.Boolean()
    esta_vigente = graphene.Boolean()


class PlatoType(graphene.ObjectType):
    """
    List serializer retorna: id, nombre, descripcion, categoria_id,
    categoria_nombre, imagen, activo, fecha_creacion, fecha_actualizacion
    Detail serializer agrega: ingredientes[], precios[]
    ✅ Fix: el campo del dict es 'categoria_id', no 'categoria'
    """
    id = graphene.ID()
    nombre = graphene.String()
    descripcion = graphene.String()
    categoria_id = graphene.ID()          # ✅ sin resolver custom
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

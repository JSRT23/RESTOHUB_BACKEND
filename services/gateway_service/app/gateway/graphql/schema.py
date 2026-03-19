import graphene
from .types import (
    RestauranteType, CategoriaType, PlatoType, IngredienteType,
    PrecioPlatoType, MenuRestauranteType, MenuCategoriaType, MenuPlatoType,
    PedidoType,
)
from ..client import menu_client


# ═══════════════════════════════════════════
# QUERIES
# ═══════════════════════════════════════════

class Query(graphene.ObjectType):

    # ── Menu ──
    restaurantes = graphene.List(
        RestauranteType, activo=graphene.Boolean(), pais=graphene.String())
    restaurante = graphene.Field(
        RestauranteType, id=graphene.ID(required=True))
    menu_restaurante = graphene.Field(
        MenuRestauranteType, id=graphene.ID(required=True))
    categorias = graphene.List(CategoriaType, activo=graphene.Boolean())
    categoria = graphene.Field(CategoriaType, id=graphene.ID(required=True))
    platos = graphene.List(
        PlatoType, activo=graphene.Boolean(), categoria_id=graphene.ID())
    plato = graphene.Field(PlatoType, id=graphene.ID(required=True))
    ingredientes = graphene.List(IngredienteType, activo=graphene.Boolean())
    precios = graphene.List(
        PrecioPlatoType,
        plato_id=graphene.ID(),
        restaurante_id=graphene.ID(),
        activo=graphene.Boolean(),
    )

    # ─────────────────────────────────────────
    # Resolvers — llaman al REST client
    # El cliente retorna dict/list → lo mapeamos al ObjectType
    # ─────────────────────────────────────────

    def resolve_restaurantes(self, info, activo=None, pais=None):
        data = menu_client.get_restaurantes(activo=activo, pais=pais)
        return [RestauranteType(**r) for r in data]

    def resolve_restaurante(self, info, id):
        data = menu_client.get_restaurante(id)
        return RestauranteType(**data) if data else None

    def resolve_menu_restaurante(self, info, id):
        data = menu_client.get_menu_restaurante(id)
        if not data:
            return None

        categorias = [
            MenuCategoriaType(
                categoria_id=cat.get("categoria_id"),
                nombre=cat.get("nombre"),
                orden=cat.get("orden"),
                platos=[
                    MenuPlatoType(**p) for p in cat.get("platos", [])
                ],
            )
            for cat in data.get("categorias", [])
        ]

        return MenuRestauranteType(
            restaurante_id=data.get("restaurante_id"),
            nombre=data.get("nombre"),
            ciudad=data.get("ciudad"),
            pais=data.get("pais"),
            moneda=data.get("moneda"),
            categorias=categorias,
        )

    def resolve_categorias(self, info, activo=None):
        data = menu_client.get_categorias(activo=activo)
        return [CategoriaType(**c) for c in data]

    def resolve_categoria(self, info, id):
        data = menu_client.get_categoria(id)
        return CategoriaType(**data) if data else None

    def resolve_platos(self, info, activo=None, categoria_id=None):
        data = menu_client.get_platos(activo=activo, categoria_id=categoria_id)
        return [PlatoType(**p) for p in data]

    def resolve_plato(self, info, id):
        data = menu_client.get_plato(id)
        return PlatoType(**data) if data else None

    def resolve_ingredientes(self, info, activo=None):
        data = menu_client.get_ingredientes(activo=activo)
        return [IngredienteType(**i) for i in data]

    def resolve_precios(self, info, plato_id=None, restaurante_id=None, activo=None):
        data = menu_client.get_precios(
            plato_id=plato_id,
            restaurante_id=restaurante_id,
            activo=activo,
        )
        return [PrecioPlatoType(**p) for p in data]


# ═══════════════════════════════════════════
# MUTATIONS — Menu
# ═══════════════════════════════════════════

class CrearRestaurante(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        pais = graphene.String(required=True)
        ciudad = graphene.String(required=True)
        direccion = graphene.String(required=True)
        moneda = graphene.String(required=True)

    ok = graphene.Boolean()
    restaurante = graphene.Field(RestauranteType)
    error = graphene.String()

    def mutate(self, info, **kwargs):
        data = menu_client.crear_restaurante(kwargs)
        if not data:
            return CrearRestaurante(ok=False, error="Error al crear restaurante.")
        return CrearRestaurante(ok=True, restaurante=RestauranteType(**data))


class ActualizarRestaurante(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        nombre = graphene.String()
        pais = graphene.String()
        ciudad = graphene.String()
        direccion = graphene.String()
        moneda = graphene.String()

    ok = graphene.Boolean()
    restaurante = graphene.Field(RestauranteType)
    error = graphene.String()

    def mutate(self, info, id, **kwargs):
        data = menu_client.actualizar_restaurante(id, kwargs)
        if not data:
            return ActualizarRestaurante(ok=False, error="Error al actualizar.")
        return ActualizarRestaurante(ok=True, restaurante=RestauranteType(**data))


class ActivarRestaurante(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        result = menu_client.activar_restaurante(id)
        return ActivarRestaurante(ok=bool(result))


class DesactivarRestaurante(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        result = menu_client.desactivar_restaurante(id)
        return DesactivarRestaurante(ok=bool(result))


class CrearCategoria(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        orden = graphene.Int()

    ok = graphene.Boolean()
    categoria = graphene.Field(CategoriaType)
    error = graphene.String()

    def mutate(self, info, nombre, orden=0):
        data = menu_client.crear_categoria({"nombre": nombre, "orden": orden})
        if not data:
            return CrearCategoria(ok=False, error="Error al crear categoría.")
        return CrearCategoria(ok=True, categoria=CategoriaType(**data))


class CrearPlato(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        descripcion = graphene.String(required=True)
        categoria_id = graphene.ID()
        imagen = graphene.String()

    ok = graphene.Boolean()
    plato = graphene.Field(PlatoType)
    error = graphene.String()

    def mutate(self, info, nombre, descripcion, categoria_id=None, imagen=None):
        data = menu_client.crear_plato({
            "nombre":      nombre,
            "descripcion": descripcion,
            "categoria":   categoria_id,
            "imagen":      imagen,
        })
        if not data:
            return CrearPlato(ok=False, error="Error al crear plato.")
        return CrearPlato(ok=True, plato=PlatoType(**data))


class ActivarPlato(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        result = menu_client.activar_plato(id)
        return ActivarPlato(ok=bool(result))


class DesactivarPlato(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        result = menu_client.desactivar_plato(id)
        return DesactivarPlato(ok=bool(result))


class AgregarIngredientePlato(graphene.Mutation):
    class Arguments:
        plato_id = graphene.ID(required=True)
        ingrediente_id = graphene.ID(required=True)
        cantidad = graphene.Float(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, plato_id, ingrediente_id, cantidad):
        result = menu_client.agregar_ingrediente_plato(
            plato_id,
            {"ingrediente": ingrediente_id, "cantidad": cantidad}
        )
        return AgregarIngredientePlato(ok=bool(result))


class CrearIngrediente(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        unidad_medida = graphene.String(required=True)
        descripcion = graphene.String()

    ok = graphene.Boolean()
    ingrediente = graphene.Field(IngredienteType)
    error = graphene.String()

    def mutate(self, info, nombre, unidad_medida, descripcion=None):
        data = menu_client.crear_ingrediente({
            "nombre": nombre,
            "unidad_medida": unidad_medida,
            "descripcion": descripcion,
        })
        if not data:
            return CrearIngrediente(ok=False, error="Error al crear ingrediente.")
        return CrearIngrediente(ok=True, ingrediente=IngredienteType(**data))


class CrearPrecioPlato(graphene.Mutation):
    class Arguments:
        plato_id = graphene.ID(required=True)
        restaurante_id = graphene.ID(required=True)
        precio = graphene.Float(required=True)
        fecha_inicio = graphene.String(required=True)
        fecha_fin = graphene.String()

    ok = graphene.Boolean()
    precio_plato = graphene.Field(PrecioPlatoType)
    error = graphene.String()

    def mutate(self, info, plato_id, restaurante_id, precio, fecha_inicio, fecha_fin=None):
        data = menu_client.crear_precio({
            "plato":       plato_id,
            "restaurante": restaurante_id,
            "precio":      precio,
            "fecha_inicio": fecha_inicio,
            "fecha_fin":    fecha_fin,
        })
        if not data:
            return CrearPrecioPlato(ok=False, error="Error al crear precio.")
        return CrearPrecioPlato(ok=True, precio_plato=PrecioPlatoType(**data))


# ═══════════════════════════════════════════
# MUTATION ROOT
# ═══════════════════════════════════════════

class Mutation(graphene.ObjectType):
    # Restaurante
    crear_restaurante = CrearRestaurante.Field()
    actualizar_restaurante = ActualizarRestaurante.Field()
    activar_restaurante = ActivarRestaurante.Field()
    desactivar_restaurante = DesactivarRestaurante.Field()

    # Categoría
    crear_categoria = CrearCategoria.Field()

    # Plato
    crear_plato = CrearPlato.Field()
    activar_plato = ActivarPlato.Field()
    desactivar_plato = DesactivarPlato.Field()
    agregar_ingrediente_plato = AgregarIngredientePlato.Field()

    # Ingrediente
    crear_ingrediente = CrearIngrediente.Field()

    # Precio
    crear_precio_plato = CrearPrecioPlato.Field()


# ═══════════════════════════════════════════
# SCHEMA RAÍZ
# Aquí se irán agregando los schemas de los
# otros servicios a medida que estén listos:
# order, inventory, staff, loyalty
# ═══════════════════════════════════════════

schema = graphene.Schema(query=Query, mutation=Mutation)

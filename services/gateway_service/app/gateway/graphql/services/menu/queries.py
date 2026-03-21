import graphene
from .types import (
    RestauranteType, CategoriaType, PlatoType,
    IngredienteType, PrecioPlatoType,
    MenuRestauranteType, MenuCategoriaType, MenuPlatoType,
)
from ....client import menu_client


class MenuQuery(graphene.ObjectType):

    restaurantes = graphene.List(
        RestauranteType,
        activo=graphene.Boolean(),
        pais=graphene.String(),
    )
    restaurante = graphene.Field(
        RestauranteType,
        id=graphene.ID(required=True),
    )
    menu_restaurante = graphene.Field(
        MenuRestauranteType,
        id=graphene.ID(required=True),
        description="Menú activo agrupado por categoría",
    )
    categorias = graphene.List(CategoriaType, activo=graphene.Boolean())
    categoria = graphene.Field(CategoriaType, id=graphene.ID(required=True))
    platos = graphene.List(
        PlatoType,
        activo=graphene.Boolean(),
        categoria_id=graphene.ID(),
    )
    plato = graphene.Field(PlatoType, id=graphene.ID(required=True))
    ingredientes = graphene.List(IngredienteType, activo=graphene.Boolean())
    precios = graphene.List(
        PrecioPlatoType,
        plato_id=graphene.ID(),
        restaurante_id=graphene.ID(),
        activo=graphene.Boolean(),
    )

    # ── Resolvers ──

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
                platos=[MenuPlatoType(**p) for p in cat.get("platos", [])],
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
        return [CategoriaType(**c) for c in menu_client.get_categorias(activo=activo)]

    def resolve_categoria(self, info, id):
        data = menu_client.get_categoria(id)
        return CategoriaType(**data) if data else None

    def resolve_platos(self, info, activo=None, categoria_id=None):
        return [PlatoType(**p) for p in menu_client.get_platos(
            activo=activo, categoria_id=categoria_id
        )]

    def resolve_plato(self, info, id):
        data = menu_client.get_plato(id)
        return PlatoType(**data) if data else None

    def resolve_ingredientes(self, info, activo=None):
        return [IngredienteType(**i) for i in menu_client.get_ingredientes(activo=activo)]

    def resolve_precios(self, info, plato_id=None, restaurante_id=None, activo=None):
        return [PrecioPlatoType(**p) for p in menu_client.get_precios(
            plato_id=plato_id, restaurante_id=restaurante_id, activo=activo
        )]

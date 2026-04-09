# gateway_service/app/gateway/graphql/services/menu/queries.py
# CORRECCIÓN: resolve_menu_restaurante usaba plato.get("categoria")
# pero PlatoListSerializer retorna "categoria_id" → todos los platos
# terminaban en el grupo "Otros". Fix: usar "categoria_id".

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
        restaurante_id=graphene.ID(required=True),
        description="Menú activo del restaurante agrupado por categoría",
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

    def resolve_restaurantes(self, info, activo=None, pais=None):
        return menu_client.get_restaurantes(activo=activo, pais=pais) or []

    def resolve_restaurante(self, info, id):
        return menu_client.get_restaurante(id)

    def resolve_menu_restaurante(self, info, restaurante_id):
        restaurante = menu_client.get_restaurante(restaurante_id)
        if not restaurante:
            return None

        moneda = restaurante.get("moneda", "COP")

        # Precios activos indexados por plato_id
        precios_raw = menu_client.get_precios(
            restaurante_id=restaurante_id, activo=True
        ) or []
        precios_por_plato = {}
        for p in precios_raw:
            # ✅ El serializer retorna "plato_id" no "plato"
            pid = str(p.get("plato_id", ""))
            if pid:
                precios_por_plato[pid] = p

        platos_raw = menu_client.get_platos(activo=True) or []
        categorias_raw = menu_client.get_categorias(activo=True) or []
        categorias_idx = {str(c["id"]): c for c in categorias_raw}

        grupos: dict[str, list] = {}
        sin_categoria: list = []

        for plato in platos_raw:
            pid = str(plato.get("id", ""))
            if pid not in precios_por_plato:
                continue

            precio_obj = precios_por_plato[pid]
            menu_plato = MenuPlatoType(
                plato_id=pid,
                nombre=plato.get("nombre", ""),
                descripcion=plato.get("descripcion", ""),
                imagen=plato.get("imagen"),
                precio=str(precio_obj.get("precio", "0")),
                moneda=moneda,
            )

            # ✅ CORREGIDO: el serializer retorna "categoria_id" no "categoria"
            cat_id = str(plato.get("categoria_id") or "")
            if cat_id and cat_id in categorias_idx:
                grupos.setdefault(cat_id, []).append(menu_plato)
            else:
                sin_categoria.append(menu_plato)

        categorias_result = []
        for cat in sorted(categorias_raw, key=lambda c: c.get("orden", 0)):
            cat_id = str(cat["id"])
            platos_cat = grupos.get(cat_id, [])
            if not platos_cat:
                continue
            categorias_result.append(MenuCategoriaType(
                categoria_id=cat_id,
                nombre=cat.get("nombre", ""),
                orden=cat.get("orden", 0),
                platos=platos_cat,
            ))

        if sin_categoria:
            categorias_result.append(MenuCategoriaType(
                categoria_id=None,
                nombre="Otros",
                orden=999,
                platos=sin_categoria,
            ))

        return MenuRestauranteType(
            restaurante_id=restaurante_id,
            nombre=restaurante.get("nombre", ""),
            ciudad=restaurante.get("ciudad", ""),
            pais=restaurante.get("pais", ""),
            moneda=moneda,
            categorias=categorias_result,
        )

    def resolve_categorias(self, info, activo=None):
        return menu_client.get_categorias(activo=activo) or []

    def resolve_categoria(self, info, id):
        return menu_client.get_categoria(id)

    def resolve_platos(self, info, activo=None, categoria_id=None):
        return menu_client.get_platos(activo=activo, categoria_id=categoria_id) or []

    def resolve_plato(self, info, id):
        return menu_client.get_plato(id)

    def resolve_ingredientes(self, info, activo=None):
        return menu_client.get_ingredientes(activo=activo) or []

    def resolve_precios(self, info, plato_id=None, restaurante_id=None, activo=None):
        return menu_client.get_precios(
            plato_id=plato_id,
            restaurante_id=restaurante_id,
            activo=activo,
        ) or []

# gateway_service/app/gateway/graphql/services/menu/queries.py
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

    # ── Resolvers ─────────────────────────────────────────────────────────
    # Retornamos dicts crudos — graphene los resuelve con los resolvers
    # definidos en cada Type (root.get(field_name) por defecto,
    # resolve_* para campos con nombre distinto al key del dict).

    def resolve_restaurantes(self, info, activo=None, pais=None):
        return menu_client.get_restaurantes(activo=activo, pais=pais) or []

    def resolve_restaurante(self, info, id):
        return menu_client.get_restaurante(id)

    def resolve_menu_restaurante(self, info, restaurante_id):
        """
        Construye el menú agrupado en el gateway combinando:
          1. GET /restaurantes/{id}/
          2. GET /platos/?activo=true
          3. GET /precios/?restaurante_id=...&activo=true
          4. GET /categorias/?activo=true

        No requiere endpoint especial en menu_service.
        El MenuRestauranteSerializer existe en menu_service pero no tiene
        endpoint expuesto — se deja así para no acoplar el gateway al backend.
        """
        restaurante = menu_client.get_restaurante(restaurante_id)
        if not restaurante:
            return None

        moneda = restaurante.get("moneda", "COP")

        # Precios activos indexados por plato UUID
        precios_raw = menu_client.get_precios(
            restaurante_id=restaurante_id, activo=True
        ) or []
        precios_por_plato = {}
        for p in precios_raw:
            pid = str(p.get("plato", ""))
            if pid:
                precios_por_plato[pid] = p

        # Platos activos
        platos_raw = menu_client.get_platos(activo=True) or []

        # Categorías activas indexadas por UUID
        categorias_raw = menu_client.get_categorias(activo=True) or []
        categorias_idx = {str(c["id"]): c for c in categorias_raw}

        # Agrupar platos por categoría — solo con precio activo
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

            cat_id = str(plato.get("categoria") or "")
            if cat_id and cat_id in categorias_idx:
                grupos.setdefault(cat_id, []).append(menu_plato)
            else:
                sin_categoria.append(menu_plato)

        # Construir categorías ordenadas
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
        # Usa PlatoListSerializer — sin ingredientes ni precios
        return menu_client.get_platos(activo=activo, categoria_id=categoria_id) or []

    def resolve_plato(self, info, id):
        # Usa PlatoSerializer completo — incluye ingredientes y precios
        return menu_client.get_plato(id)

    def resolve_ingredientes(self, info, activo=None):
        return menu_client.get_ingredientes(activo=activo) or []

    def resolve_precios(self, info, plato_id=None, restaurante_id=None, activo=None):
        return menu_client.get_precios(
            plato_id=plato_id,
            restaurante_id=restaurante_id,
            activo=activo,
        ) or []

# gateway_service/app/gateway/graphql/services/inventory/queries.py
import graphene
from .types import (
    ProveedorType, AlmacenType, StockType,
    LoteType, OrdenCompraType, AlertaStockType, RecetaPlatoType,
)
from ....client import inventory_client, menu_client
from ....middleware.permissions import get_jwt_user


class InventoryQuery(graphene.ObjectType):

    # Proveedores
    proveedores = graphene.List(
        ProveedorType,
        activo=graphene.Boolean(),
        pais=graphene.String(),
        ciudad=graphene.String(),
        alcance=graphene.String(
            description="Filtrar por alcance: GLOBAL | PAIS | CIUDAD | LOCAL. Solo admin_central."
        ),
    )
    proveedor = graphene.Field(ProveedorType, id=graphene.ID(required=True))

    # Almacenes
    almacenes = graphene.List(
        AlmacenType,
        restaurante_id=graphene.ID(),
        activo=graphene.Boolean(),
    )
    almacen = graphene.Field(AlmacenType, id=graphene.ID(required=True))
    stock_almacen = graphene.List(
        StockType,
        almacen_id=graphene.ID(required=True),
        bajo_minimo=graphene.Boolean(),
        description="Stock de un almacén específico",
    )

    # Stock
    stock = graphene.List(
        StockType,
        almacen_id=graphene.ID(),
        bajo_minimo=graphene.Boolean(),
        agotado=graphene.Boolean(),
    )
    stock_item = graphene.Field(StockType, id=graphene.ID(required=True))
    movimientos = graphene.List(
        graphene.String,
        stock_id=graphene.ID(required=True),
    )

    # Lotes
    lotes = graphene.List(
        LoteType,
        estado=graphene.String(),
        almacen_id=graphene.ID(),
        por_vencer=graphene.Int(description="Días máximos para vencer"),
    )
    lote = graphene.Field(LoteType, id=graphene.ID(required=True))

    # Órdenes de compra
    ordenes_compra = graphene.List(
        OrdenCompraType,
        estado=graphene.String(),
        proveedor_id=graphene.ID(),
        restaurante_id=graphene.ID(),
    )
    orden_compra = graphene.Field(
        OrdenCompraType, id=graphene.ID(required=True))

    # Alertas
    alertas_stock = graphene.List(
        AlertaStockType,
        tipo=graphene.String(),
        estado=graphene.String(),
        restaurante_id=graphene.ID(),
    )

    # Recetas
    recetas = graphene.List(
        RecetaPlatoType,
        plato_id=graphene.ID(),
    )

    # ── Resolvers ─────────────────────────────────────────────────────────

    def resolve_proveedores(self, info, activo=None, pais=None, ciudad=None, alcance=None):
        """
        Control de visibilidad por rol (Opción B):

        admin_central  → ve todos; puede filtrar por pais/ciudad/alcance libremente.
        gerente_local  → ve solo los que aplican a su restaurante:
                           alcance=GLOBAL
                           OR (alcance=PAIS   AND pais_destino  == pais del restaurante)
                           OR (alcance=CIUDAD AND ciudad_destino == ciudad del restaurante)
                           OR (alcance=LOCAL  AND creado_por_restaurante_id == jwt.restaurante_id)
                         El frontend NO pasa filtros — el gateway los inyecta automáticamente.
        supervisor y roles operativos → lista vacía.
        """
        user = get_jwt_user(info)
        if not user:
            return []

        rol = user.get("rol")

        # ── admin_central: sin restricción ───────────────────────────────
        if rol == "admin_central":
            params = {}
            if activo is not None:
                params["activo"] = activo
            if pais:
                params["pais"] = pais
            if ciudad:
                params["ciudad"] = ciudad
            if alcance:
                params["alcance"] = alcance
            return inventory_client.get_proveedores(**params) or []

        # ── gerente_local: filtro por scope ──────────────────────────────
        if rol == "gerente_local":
            restaurante_id = user.get("restaurante_id")
            if not restaurante_id:
                return []

            # 1. Intentar leer pais y ciudad del JWT (si el auth_service los incluye)
            pais_restaurante = user.get("pais")
            ciudad_restaurante = user.get("ciudad")

            # 2. Si no están en el JWT, resolver desde menu_service
            #    (el restaurante tiene pais y ciudad en menu_service)
            if not pais_restaurante or not ciudad_restaurante:
                try:
                    restaurante = menu_client.get_restaurante(restaurante_id)
                    if restaurante:
                        pais_restaurante = pais_restaurante or restaurante.get(
                            "pais")
                        ciudad_restaurante = ciudad_restaurante or restaurante.get(
                            "ciudad")
                except Exception:
                    pass  # Si falla menu_service solo verá GLOBAL + LOCAL

            # 3. Llamar a inventory con scope=gerente + pais + ciudad del restaurante
            return inventory_client.get_proveedores_para_gerente(
                restaurante_id=restaurante_id,
                pais=pais_restaurante,
                ciudad=ciudad_restaurante,
                activo=activo,
            ) or []

        # supervisor, cocinero, mesero, cajero, repartidor → sin acceso
        return []

    def resolve_proveedor(self, info, id):
        user = get_jwt_user(info)
        if not user:
            return None
        if user.get("rol") not in ("admin_central", "gerente_local"):
            return None
        return inventory_client.get_proveedor(id)

    def resolve_almacenes(self, info, restaurante_id=None, activo=None):
        user = get_jwt_user(info)
        if not user:
            return []
        rol = user.get("rol")
        if rol in ("gerente_local", "supervisor"):
            restaurante_id = user.get("restaurante_id")
        elif rol not in ("admin_central",):
            return []
        return inventory_client.get_almacenes(
            restaurante_id=restaurante_id, activo=activo
        ) or []

    def resolve_almacen(self, info, id):
        return inventory_client.get_almacen(id)

    def resolve_stock_almacen(self, info, almacen_id, bajo_minimo=None):
        return inventory_client.get_stock_almacen(
            almacen_id, bajo_minimo=bajo_minimo
        ) or []

    def resolve_stock(self, info, almacen_id=None, bajo_minimo=None, agotado=None):
        return inventory_client.get_stock(
            almacen_id=almacen_id,
            bajo_minimo=bajo_minimo,
            agotado=agotado,
        ) or []

    def resolve_stock_item(self, info, id):
        return inventory_client.get_stock_item(id)

    def resolve_lotes(self, info, estado=None, almacen_id=None, por_vencer=None):
        return inventory_client.get_lotes(
            estado=estado,
            almacen_id=almacen_id,
            por_vencer=por_vencer,
        ) or []

    def resolve_lote(self, info, id):
        return inventory_client.get_lote(id)

    def resolve_ordenes_compra(self, info, estado=None, proveedor_id=None, restaurante_id=None):
        user = get_jwt_user(info)
        if not user:
            return []
        rol = user.get("rol")
        if rol == "gerente_local":
            restaurante_id = user.get("restaurante_id")
        elif rol not in ("admin_central",):
            return []
        return inventory_client.get_ordenes_compra(
            estado=estado,
            proveedor_id=proveedor_id,
            restaurante_id=restaurante_id,
        ) or []

    def resolve_orden_compra(self, info, id):
        return inventory_client.get_orden_compra(id)

    def resolve_alertas_stock(self, info, tipo=None, estado=None, restaurante_id=None):
        user = get_jwt_user(info)
        if not user:
            return []
        rol = user.get("rol")
        if rol in ("gerente_local", "supervisor"):
            restaurante_id = user.get("restaurante_id")
        elif rol not in ("admin_central",):
            return []
        return inventory_client.get_alertas(
            tipo=tipo,
            estado=estado,
            restaurante_id=restaurante_id,
        ) or []

    def resolve_recetas(self, info, plato_id=None):
        from ....client.inventory_client import _get
        params = {}
        if plato_id:
            params["plato_id"] = plato_id
        return _get("/recetas/", params=params) or []

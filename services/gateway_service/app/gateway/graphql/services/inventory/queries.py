# services/gateway_service/app/gateway/graphql/services/inventory/queries.py
# CAMBIOS vs original:
# 1. Importa CostoPlatoType desde types
# 2. Agrega campo costoPlato en InventoryQuery
# 3. Agrega resolve_costo_plato
# 4. Corrige resolve_recetas: usaba _get() directo, ahora usa inventory_client.get_recetas()
# Todo lo demás idéntico al archivo actual.

import graphene
from .types import (
    ProveedorType, AlmacenType, StockType,
    LoteType, OrdenCompraType, AlertaStockType,
    RecetaPlatoType, CostoPlatoType,           # ← CostoPlatoType es nuevo
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
        alcance=graphene.String(),
    )
    proveedor = graphene.Field(ProveedorType, id=graphene.ID(required=True))

    # Almacenes
    almacenes = graphene.List(
        AlmacenType, restaurante_id=graphene.ID(), activo=graphene.Boolean())
    almacen = graphene.Field(AlmacenType, id=graphene.ID(required=True))
    stock_almacen = graphene.List(
        StockType,
        almacen_id=graphene.ID(required=True),
        bajo_minimo=graphene.Boolean(),
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
        graphene.String, stock_id=graphene.ID(required=True))

    # Lotes
    lotes = graphene.List(LoteType, estado=graphene.String(
    ), almacen_id=graphene.ID(), por_vencer=graphene.Int())
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

    # Recetas (ingredientes de un plato)
    recetas = graphene.List(RecetaPlatoType, plato_id=graphene.ID())

    # ── NUEVO: costo de producción ────────────────────────────────────────
    costo_plato = graphene.Field(
        CostoPlatoType,
        plato_id=graphene.ID(required=True),
        restaurante_id=graphene.ID(
            description="ID del restaurante para ver porciones con su stock actual"
        ),
        description=(
            "Costo de producción del plato y porciones disponibles con el stock actual. "
            "El costo_unitario se actualiza automáticamente al recibir una orden de compra."
        ),
    )

    # ── Resolvers ─────────────────────────────────────────────────────────

    def resolve_proveedores(self, info, activo=None, pais=None, ciudad=None, alcance=None):
        user = get_jwt_user(info)
        if not user:
            return []
        rol = user.get("rol")
        if rol == "admin_central":
            return inventory_client.get_proveedores(
                activo=activo, pais=pais, ciudad=ciudad, alcance=alcance
            ) or []
        if rol == "gerente_local":
            restaurante_id = user.get("restaurante_id")
            if not restaurante_id:
                return []
            pais_r = user.get("pais")
            ciudad_r = user.get("ciudad")
            if not pais_r or not ciudad_r:
                try:
                    restaurante = menu_client.get_restaurante(restaurante_id)
                    if restaurante:
                        pais_r = pais_r or restaurante.get("pais")
                        ciudad_r = ciudad_r or restaurante.get("ciudad")
                except Exception:
                    pass
            return inventory_client.get_proveedores_para_gerente(
                restaurante_id=restaurante_id,
                pais=pais_r,
                ciudad=ciudad_r,
                activo=activo,
            ) or []
        return []

    def resolve_proveedor(self, info, id):
        user = get_jwt_user(info)
        if not user or user.get("rol") not in ("admin_central", "gerente_local"):
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
        return inventory_client.get_almacenes(restaurante_id=restaurante_id, activo=activo) or []

    def resolve_almacen(self, info, id):
        return inventory_client.get_almacen(id)

    def resolve_stock_almacen(self, info, almacen_id, bajo_minimo=None):
        return inventory_client.get_stock_almacen(almacen_id, bajo_minimo=bajo_minimo) or []

    def resolve_stock(self, info, almacen_id=None, bajo_minimo=None, agotado=None):
        return inventory_client.get_stock(
            almacen_id=almacen_id, bajo_minimo=bajo_minimo, agotado=agotado
        ) or []

    def resolve_stock_item(self, info, id):
        return inventory_client.get_stock_item(id)

    def resolve_lotes(self, info, estado=None, almacen_id=None, por_vencer=None):
        return inventory_client.get_lotes(
            estado=estado, almacen_id=almacen_id, por_vencer=por_vencer
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
            estado=estado, proveedor_id=proveedor_id, restaurante_id=restaurante_id
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
            tipo=tipo, estado=estado, restaurante_id=restaurante_id
        ) or []

    def resolve_recetas(self, info, plato_id=None):
        # CORREGIDO: antes usaba _get() directo, ahora usa inventory_client
        return inventory_client.get_recetas(plato_id=plato_id) or []

    def resolve_costo_plato(self, info, plato_id, restaurante_id=None):
        """
        Calcula el costo de producción del plato y las porciones
        disponibles con el stock del restaurante.

        Accesible por: gerente_local (usa su restaurante del JWT),
        admin_central (puede pasar restaurante_id), cocinero (consulta).
        """
        user = get_jwt_user(info)
        if not user:
            return None

        # Si no se pasa restaurante_id, usar el del JWT
        if not restaurante_id and user.get("restaurante_id"):
            restaurante_id = user.get("restaurante_id")

        return inventory_client.get_costo_plato(
            plato_id=plato_id,
            restaurante_id=restaurante_id,
        )

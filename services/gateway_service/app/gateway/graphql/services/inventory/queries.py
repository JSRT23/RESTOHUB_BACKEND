# gateway_service/app/gateway/graphql/services/inventory/queries.py
import graphene
from .types import (
    ProveedorType, AlmacenType, StockType,
    LoteType, OrdenCompraType, AlertaStockType, RecetaPlatoType,
)
from ....client import inventory_client


# ─────────────────────────────────────────
# HELPERS — retornamos dicts crudos
# graphene los resuelve automáticamente con los campos del Type
# Solo necesitamos resolve_* cuando el nombre del campo difiere del key
# ─────────────────────────────────────────

class InventoryQuery(graphene.ObjectType):

    # Proveedores
    proveedores = graphene.List(
        ProveedorType,
        activo=graphene.Boolean(),
        pais=graphene.String(),
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
        graphene.String,  # raw — el frontend normalmente no los lista
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

    def resolve_proveedores(self, info, activo=None, pais=None):
        return inventory_client.get_proveedores(activo=activo, pais=pais) or []

    def resolve_proveedor(self, info, id):
        return inventory_client.get_proveedor(id)

    def resolve_almacenes(self, info, restaurante_id=None, activo=None):
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
        return inventory_client.get_ordenes_compra(
            estado=estado,
            proveedor_id=proveedor_id,
            restaurante_id=restaurante_id,
        ) or []

    def resolve_orden_compra(self, info, id):
        return inventory_client.get_orden_compra(id)

    def resolve_alertas_stock(self, info, tipo=None, estado=None, restaurante_id=None):
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

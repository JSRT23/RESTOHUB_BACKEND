import graphene
from .types import (
    ProveedorType, AlmacenType, StockType, LoteType,
    OrdenCompraType, AlertaType, CostoPlatoType,
    MovimientoInventarioType, DetalleOrdenCompraType,
    RecetaIngredienteType,
)
from ....client import inventory_client


def _map_stock(data: dict) -> StockType:
    return StockType(
        id=data.get("id"),
        ingrediente_id=data.get("ingrediente_id"),
        nombre_ingrediente=data.get("nombre_ingrediente"),
        almacen=data.get("almacen"),
        almacen_nombre=data.get("almacen_nombre"),
        unidad_medida=data.get("unidad_medida"),
        cantidad_actual=data.get("cantidad_actual"),
        nivel_minimo=data.get("nivel_minimo"),
        nivel_maximo=data.get("nivel_maximo"),
        necesita_reposicion=data.get("necesita_reposicion"),
        esta_agotado=data.get("esta_agotado"),
        porcentaje_stock=data.get("porcentaje_stock"),
        fecha_actualizacion=data.get("fecha_actualizacion"),
        movimientos=[
            MovimientoInventarioType(**m)
            for m in data.get("movimientos", [])
        ],
    )


def _map_orden(data: dict) -> OrdenCompraType:
    return OrdenCompraType(
        id=data.get("id"),
        proveedor=data.get("proveedor"),
        proveedor_nombre=data.get("proveedor_nombre"),
        restaurante_id=data.get("restaurante_id"),
        estado=data.get("estado"),
        moneda=data.get("moneda"),
        total_estimado=data.get("total_estimado"),
        fecha_creacion=data.get("fecha_creacion"),
        fecha_entrega_estimada=data.get("fecha_entrega_estimada"),
        fecha_recepcion=data.get("fecha_recepcion"),
        notas=data.get("notas"),
        detalles=[
            DetalleOrdenCompraType(**d)
            for d in data.get("detalles", [])
        ],
    )


def _map_costo(data: dict) -> CostoPlatoType:
    return CostoPlatoType(
        plato_id=data.get("plato_id"),
        costo_total=data.get("costo_total"),
        tiene_costos_vacios=data.get("tiene_costos_vacios"),
        advertencia=data.get("advertencia"),
        ingredientes=[
            RecetaIngredienteType(**i)
            for i in data.get("ingredientes", [])
        ],
    )


class InventoryQuery(graphene.ObjectType):

    proveedores = graphene.List(
        ProveedorType, activo=graphene.Boolean(), pais=graphene.String())
    proveedor = graphene.Field(ProveedorType, id=graphene.ID(required=True))

    almacenes = graphene.List(
        AlmacenType, restaurante_id=graphene.ID(), activo=graphene.Boolean())
    almacen = graphene.Field(AlmacenType, id=graphene.ID(required=True))
    stock_almacen = graphene.List(StockType, id=graphene.ID(
        required=True), bajo_minimo=graphene.Boolean())

    stock = graphene.List(StockType, almacen_id=graphene.ID(
    ), bajo_minimo=graphene.Boolean(), agotado=graphene.Boolean())
    stock_item = graphene.Field(StockType, id=graphene.ID(required=True))
    movimientos = graphene.List(
        MovimientoInventarioType, stock_id=graphene.ID(required=True))
    costo_plato = graphene.Field(
        CostoPlatoType,
        plato_id=graphene.ID(required=True),
        description="Costo real del plato — margen = precio_venta - costo_total",
    )

    lotes = graphene.List(
        LoteType,
        estado=graphene.String(),
        almacen_id=graphene.ID(),
        por_vencer=graphene.Int(description="Lotes que vencen en N días"),
    )
    lote = graphene.Field(LoteType, id=graphene.ID(required=True))

    ordenes_compra = graphene.List(
        OrdenCompraType,
        estado=graphene.String(),
        proveedor_id=graphene.ID(),
        restaurante_id=graphene.ID(),
    )
    orden_compra = graphene.Field(
        OrdenCompraType, id=graphene.ID(required=True))

    alertas = graphene.List(
        AlertaType,
        tipo=graphene.String(),
        estado=graphene.String(),
        restaurante_id=graphene.ID(),
    )
    alerta = graphene.Field(AlertaType, id=graphene.ID(required=True))

    # ── Resolvers ──

    def resolve_proveedores(self, info, activo=None, pais=None):
        return [ProveedorType(**p) for p in inventory_client.get_proveedores(activo=activo, pais=pais)]

    def resolve_proveedor(self, info, id):
        data = inventory_client.get_proveedor(id)
        return ProveedorType(**data) if data else None

    def resolve_almacenes(self, info, restaurante_id=None, activo=None):
        return [AlmacenType(**a) for a in inventory_client.get_almacenes(
            restaurante_id=restaurante_id, activo=activo
        )]

    def resolve_almacen(self, info, id):
        data = inventory_client.get_almacen(id)
        return AlmacenType(**data) if data else None

    def resolve_stock_almacen(self, info, id, bajo_minimo=None):
        return [_map_stock(s) for s in inventory_client.get_stock_almacen(id, bajo_minimo=bajo_minimo)]

    def resolve_stock(self, info, almacen_id=None, bajo_minimo=None, agotado=None):
        return [_map_stock(s) for s in inventory_client.get_stock(
            almacen_id=almacen_id, bajo_minimo=bajo_minimo, agotado=agotado
        )]

    def resolve_stock_item(self, info, id):
        data = inventory_client.get_stock_item(id)
        return _map_stock(data) if data else None

    def resolve_movimientos(self, info, stock_id):
        return [MovimientoInventarioType(**m) for m in inventory_client.get_movimientos(stock_id)]

    def resolve_costo_plato(self, info, plato_id):
        data = inventory_client.get_costo_plato(plato_id)
        return _map_costo(data) if data else None

    def resolve_lotes(self, info, estado=None, almacen_id=None, por_vencer=None):
        return [LoteType(**l) for l in inventory_client.get_lotes(
            estado=estado, almacen_id=almacen_id, por_vencer=por_vencer
        )]

    def resolve_lote(self, info, id):
        data = inventory_client.get_lote(id)
        return LoteType(**data) if data else None

    def resolve_ordenes_compra(self, info, estado=None, proveedor_id=None, restaurante_id=None):
        return [_map_orden(o) for o in inventory_client.get_ordenes_compra(
            estado=estado, proveedor_id=proveedor_id, restaurante_id=restaurante_id
        )]

    def resolve_orden_compra(self, info, id):
        data = inventory_client.get_orden_compra(id)
        return _map_orden(data) if data else None

    def resolve_alertas(self, info, tipo=None, estado=None, restaurante_id=None):
        return [AlertaType(**a) for a in inventory_client.get_alertas(
            tipo=tipo, estado=estado, restaurante_id=restaurante_id
        )]

    def resolve_alerta(self, info, id):
        data = inventory_client.get_alerta(id)
        return AlertaType(**data) if data else None

# gateway_service/app/gateway/services/inventory/mutations.py
import graphene
from .types import ProveedorType, AlmacenType, StockType, LoteType, OrdenCompraType, AlertaType
from .queries import _map_stock, _map_orden
from ....client import inventory_client


class CrearProveedor(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        pais = graphene.String(required=True)
        ciudad = graphene.String()
        telefono = graphene.String()
        email = graphene.String()
        moneda_preferida = graphene.String()
    ok = graphene.Boolean()
    proveedor = graphene.Field(ProveedorType)
    error = graphene.String()

    def mutate(self, info, nombre, pais, **kwargs):
        data = inventory_client.crear_proveedor(
            {"nombre": nombre, "pais": pais, **kwargs})
        if not data:
            return CrearProveedor(ok=False, error="Error al crear proveedor.")
        return CrearProveedor(ok=True, proveedor=ProveedorType(**data))


class CrearAlmacen(graphene.Mutation):
    class Arguments:
        restaurante_id = graphene.ID(required=True)
        nombre = graphene.String(required=True)
        descripcion = graphene.String()
    ok = graphene.Boolean()
    almacen = graphene.Field(AlmacenType)
    error = graphene.String()

    def mutate(self, info, restaurante_id, nombre, descripcion=None):
        data = inventory_client.crear_almacen({
            "restaurante_id": restaurante_id, "nombre": nombre, "descripcion": descripcion,
        })
        if not data:
            return CrearAlmacen(ok=False, error="Error al crear almacén.")
        return CrearAlmacen(ok=True, almacen=AlmacenType(**data))


class AjustarStock(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        cantidad = graphene.Float(required=True)
        descripcion = graphene.String(required=True)
    ok = graphene.Boolean()
    stock = graphene.Field(StockType)
    error = graphene.String()

    def mutate(self, info, id, cantidad, descripcion):
        data = inventory_client.ajustar_stock(id, cantidad, descripcion)
        if not data:
            return AjustarStock(ok=False, error="Error al ajustar stock.")
        return AjustarStock(ok=True, stock=_map_stock(data))


class DetalleOrdenInput(graphene.InputObjectType):
    ingrediente_id = graphene.ID(required=True)
    nombre_ingrediente = graphene.String(required=True)
    unidad_medida = graphene.String(required=True)
    cantidad = graphene.Float(required=True)
    precio_unitario = graphene.Float(required=True)


class CrearOrdenCompra(graphene.Mutation):
    class Arguments:
        proveedor_id = graphene.ID(required=True)
        restaurante_id = graphene.ID(required=True)
        moneda = graphene.String(required=True)
        detalles = graphene.List(graphene.NonNull(
            DetalleOrdenInput), required=True)
        fecha_entrega_estimada = graphene.String()
        notas = graphene.String()
    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, proveedor_id, restaurante_id, moneda, detalles, **kwargs):
        data = inventory_client.crear_orden_compra({
            "proveedor": proveedor_id, "restaurante_id": restaurante_id,
            "moneda": moneda, "detalles": [dict(d) for d in detalles], **kwargs,
        })
        if not data:
            return CrearOrdenCompra(ok=False, error="Error al crear orden de compra.")
        return CrearOrdenCompra(ok=True, orden=_map_orden(data))


class EnviarOrdenCompra(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.enviar_orden_compra(id)
        if not data:
            return EnviarOrdenCompra(ok=False, error="Error al enviar orden.")
        return EnviarOrdenCompra(ok=True, orden=_map_orden(data))


class DetalleRecepcionInput(graphene.InputObjectType):
    detalle_id = graphene.ID(required=True)
    cantidad_recibida = graphene.Float(required=True)
    numero_lote = graphene.String(required=True)
    fecha_vencimiento = graphene.String(required=True)
    fecha_produccion = graphene.String()


class RecibirOrdenCompra(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        detalles = graphene.List(graphene.NonNull(
            DetalleRecepcionInput), required=True)
        notas = graphene.String()
    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, id, detalles, notas=""):
        data = inventory_client.recibir_orden_compra(id, {
            "detalles": [dict(d) for d in detalles], "notas": notas,
        })
        if not data:
            return RecibirOrdenCompra(ok=False, error="Error al recibir orden.")
        return RecibirOrdenCompra(ok=True, orden=_map_orden(data))


class CancelarOrdenCompra(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.cancelar_orden_compra(id)
        if not data:
            return CancelarOrdenCompra(ok=False, error="Error.")
        return CancelarOrdenCompra(ok=True, orden=_map_orden(data))


class RetirarLote(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    lote = graphene.Field(LoteType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.retirar_lote(id)
        if not data:
            return RetirarLote(ok=False, error="Error al retirar lote.")
        return RetirarLote(ok=True, lote=LoteType(**data))


class ResolverAlerta(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    alerta = graphene.Field(AlertaType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.resolver_alerta(id)
        if not data:
            return ResolverAlerta(ok=False, error="Error.")
        return ResolverAlerta(ok=True, alerta=AlertaType(**data))


class IgnorarAlerta(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    alerta = graphene.Field(AlertaType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.ignorar_alerta(id)
        if not data:
            return IgnorarAlerta(ok=False, error="Error.")
        return IgnorarAlerta(ok=True, alerta=AlertaType(**data))


class InventoryMutation(graphene.ObjectType):
    crear_proveedor = CrearProveedor.Field()
    crear_almacen = CrearAlmacen.Field()
    ajustar_stock = AjustarStock.Field()
    crear_orden_compra = CrearOrdenCompra.Field()
    enviar_orden_compra = EnviarOrdenCompra.Field()
    recibir_orden_compra = RecibirOrdenCompra.Field()
    cancelar_orden_compra = CancelarOrdenCompra.Field()
    retirar_lote = RetirarLote.Field()
    resolver_alerta = ResolverAlerta.Field()
    ignorar_alerta = IgnorarAlerta.Field()

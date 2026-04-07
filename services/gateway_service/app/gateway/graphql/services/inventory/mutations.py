# gateway_service/app/gateway/graphql/services/inventory/mutations.py
import graphene
from .types import (
    ProveedorType, AlmacenType, StockType,
    LoteType, OrdenCompraType, AlertaStockType,
)
from ....client import inventory_client


class DetalleOrdenInput(graphene.InputObjectType):
    ingrediente_id = graphene.ID(required=True)
    nombre_ingrediente = graphene.String(required=True)
    unidad_medida = graphene.String(required=True)
    cantidad = graphene.Float(required=True)
    precio_unitario = graphene.Float(required=True)


class DetalleRecepcionInput(graphene.InputObjectType):
    detalle_id = graphene.ID(required=True)
    cantidad_recibida = graphene.Float(required=True)
    numero_lote = graphene.String(required=True)
    fecha_vencimiento = graphene.String(required=True)
    fecha_produccion = graphene.String()


# ─────────────────────────────────────────
# PROVEEDOR
# ─────────────────────────────────────────

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
            {"nombre": nombre, "pais": pais, **kwargs}
        )
        if not data:
            return CrearProveedor(ok=False, error="Error al crear proveedor.")
        return CrearProveedor(ok=True, proveedor=data)


# ─────────────────────────────────────────
# ALMACÉN
# ─────────────────────────────────────────

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
            "restaurante_id": restaurante_id,
            "nombre":         nombre,
            "descripcion":    descripcion,
        })
        if not data:
            return CrearAlmacen(ok=False, error="Error al crear almacén.")
        return CrearAlmacen(ok=True, almacen=data)


# ─────────────────────────────────────────
# STOCK
# ─────────────────────────────────────────

class RegistrarStock(graphene.Mutation):
    """Registra un ingrediente en el inventario de un almacén."""
    class Arguments:
        ingrediente_id = graphene.ID(required=True)
        nombre_ingrediente = graphene.String(required=True)
        almacen_id = graphene.ID(required=True)
        unidad_medida = graphene.String(required=True)
        cantidad_actual = graphene.Float(required=True)
        nivel_minimo = graphene.Float(required=True)
        nivel_maximo = graphene.Float(required=True)

    ok = graphene.Boolean()
    stock = graphene.Field(StockType)
    error = graphene.String()

    def mutate(self, info, ingrediente_id, nombre_ingrediente, almacen_id,
               unidad_medida, cantidad_actual, nivel_minimo, nivel_maximo):
        data = inventory_client.crear_stock({
            "ingrediente_id":     ingrediente_id,
            "nombre_ingrediente": nombre_ingrediente,
            "almacen":            almacen_id,
            "unidad_medida":      unidad_medida,
            "cantidad_actual":    str(cantidad_actual),
            "nivel_minimo":       str(nivel_minimo),
            "nivel_maximo":       str(nivel_maximo),
        })
        if not data:
            return RegistrarStock(ok=False, error="Error al registrar stock.")
        return RegistrarStock(ok=True, stock=data)


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
        return AjustarStock(ok=True, stock=data)  # ✅ dict crudo


# ─────────────────────────────────────────
# LOTES
# ─────────────────────────────────────────

class RegistrarLote(graphene.Mutation):
    class Arguments:
        ingrediente_id = graphene.ID(required=True)
        almacen_id = graphene.ID(required=True)
        proveedor_id = graphene.ID(required=True)
        numero_lote = graphene.String(required=True)
        fecha_vencimiento = graphene.String(required=True)
        cantidad_recibida = graphene.Float(required=True)
        unidad_medida = graphene.String(required=True)
        fecha_produccion = graphene.String()

    ok = graphene.Boolean()
    lote = graphene.Field(LoteType)
    error = graphene.String()

    def mutate(self, info, ingrediente_id, almacen_id, proveedor_id,
               numero_lote, fecha_vencimiento, cantidad_recibida,
               unidad_medida, fecha_produccion=None):
        data = inventory_client.crear_lote({
            "ingrediente_id":    ingrediente_id,
            "almacen":           almacen_id,
            "proveedor":         proveedor_id,
            "numero_lote":       numero_lote,
            "fecha_vencimiento": fecha_vencimiento,
            "fecha_produccion":  fecha_produccion,
            "cantidad_recibida": str(cantidad_recibida),
            "unidad_medida":     unidad_medida,
        })
        if not data:
            return RegistrarLote(ok=False, error="Error al registrar lote.")
        return RegistrarLote(ok=True, lote=data)


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
        return RetirarLote(ok=True, lote=data)


# ─────────────────────────────────────────
# ÓRDENES DE COMPRA
# ─────────────────────────────────────────

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
            "proveedor":      proveedor_id,
            "restaurante_id": restaurante_id,
            "moneda":         moneda,
            "detalles":       [dict(d) for d in detalles],
            **kwargs,
        })
        if not data:
            return CrearOrdenCompra(ok=False, error="Error al crear orden de compra.")
        return CrearOrdenCompra(ok=True, orden=data)


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
        return EnviarOrdenCompra(ok=True, orden=data)


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
            "detalles": [dict(d) for d in detalles],
            "notas":    notas,
        })
        if not data:
            return RecibirOrdenCompra(ok=False, error="Error al recibir orden.")
        return RecibirOrdenCompra(ok=True, orden=data)


class CancelarOrdenCompra(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.cancelar_orden_compra(id)
        if not data:
            return CancelarOrdenCompra(ok=False, error="Error al cancelar orden.")
        return CancelarOrdenCompra(ok=True, orden=data)


# ─────────────────────────────────────────
# ALERTAS
# ─────────────────────────────────────────

class ResolverAlerta(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    # ✅ AlertaStockType, no AlertaType
    alerta = graphene.Field(AlertaStockType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.resolver_alerta(id)
        if not data:
            return ResolverAlerta(ok=False, error="Error al resolver alerta.")
        return ResolverAlerta(ok=True, alerta=data)


class IgnorarAlerta(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    alerta = graphene.Field(AlertaStockType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.ignorar_alerta(id)
        if not data:
            return IgnorarAlerta(ok=False, error="Error al ignorar alerta.")
        return IgnorarAlerta(ok=True, alerta=data)


# ─────────────────────────────────────────
# REGISTRO
# ─────────────────────────────────────────

class InventoryMutation(graphene.ObjectType):
    crear_proveedor = CrearProveedor.Field()
    crear_almacen = CrearAlmacen.Field()
    registrar_stock = RegistrarStock.Field()
    ajustar_stock = AjustarStock.Field()
    registrar_lote = RegistrarLote.Field()
    retirar_lote = RetirarLote.Field()
    crear_orden_compra = CrearOrdenCompra.Field()
    enviar_orden_compra = EnviarOrdenCompra.Field()
    recibir_orden_compra = RecibirOrdenCompra.Field()
    cancelar_orden_compra = CancelarOrdenCompra.Field()
    resolver_alerta = ResolverAlerta.Field()
    ignorar_alerta = IgnorarAlerta.Field()

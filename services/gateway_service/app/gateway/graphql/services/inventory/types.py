# services/gateway_service/app/gateway/graphql/services/inventory/types.py
# CAMBIOS vs original:
# 1. Agrega IngredienteCostoType
# 2. Agrega CostoPlatoType
# Todo lo demás idéntico al archivo actual.

import graphene


class ProveedorType(graphene.ObjectType):
    id = graphene.ID()
    nombre = graphene.String()
    pais = graphene.String()
    ciudad = graphene.String()
    telefono = graphene.String()
    email = graphene.String()
    moneda_preferida = graphene.String()
    alcance = graphene.String()
    pais_destino = graphene.String()
    ciudad_destino = graphene.String()
    creado_por_restaurante_id = graphene.ID()
    activo = graphene.Boolean()
    fecha_creacion = graphene.String()
    fecha_actualizacion = graphene.String()


class AlmacenType(graphene.ObjectType):
    id = graphene.ID()
    restaurante_id = graphene.ID()
    nombre = graphene.String()
    descripcion = graphene.String()
    activo = graphene.Boolean()
    total_ingredientes = graphene.Int()
    ingredientes_bajo_minimo = graphene.Int()
    fecha_creacion = graphene.String()
    fecha_actualizacion = graphene.String()


class MovimientoType(graphene.ObjectType):
    id = graphene.ID()
    tipo_movimiento = graphene.String()
    cantidad = graphene.String()
    cantidad_antes = graphene.String()
    cantidad_despues = graphene.String()
    pedido_id = graphene.ID()
    orden_compra_id = graphene.ID()
    descripcion = graphene.String()
    fecha = graphene.String()


class StockType(graphene.ObjectType):
    id = graphene.ID()
    ingrediente_id = graphene.ID()
    nombre_ingrediente = graphene.String()
    almacen = graphene.ID()
    almacen_nombre = graphene.String()
    unidad_medida = graphene.String()
    cantidad_actual = graphene.String()
    nivel_minimo = graphene.String()
    nivel_maximo = graphene.String()
    necesita_reposicion = graphene.Boolean()
    esta_agotado = graphene.Boolean()
    porcentaje_stock = graphene.Float()
    fecha_actualizacion = graphene.String()
    movimientos = graphene.List(MovimientoType)

    def resolve_movimientos(root, info):
        return root.get("movimientos", []) if isinstance(root, dict) else []


class LoteType(graphene.ObjectType):
    id = graphene.ID()
    ingrediente_id = graphene.ID()
    almacen = graphene.ID()
    almacen_nombre = graphene.String()
    proveedor = graphene.ID()
    proveedor_nombre = graphene.String()
    numero_lote = graphene.String()
    fecha_produccion = graphene.String()
    fecha_vencimiento = graphene.String()
    cantidad_recibida = graphene.String()
    cantidad_actual = graphene.String()
    unidad_medida = graphene.String()
    estado = graphene.String()
    esta_vencido = graphene.Boolean()
    dias_para_vencer = graphene.Int()
    fecha_recepcion = graphene.String()


class DetalleOrdenType(graphene.ObjectType):
    id = graphene.ID()
    ingrediente_id = graphene.ID()
    nombre_ingrediente = graphene.String()
    unidad_medida = graphene.String()
    cantidad = graphene.String()
    cantidad_recibida = graphene.String()
    precio_unitario = graphene.String()
    subtotal = graphene.String()


class OrdenCompraType(graphene.ObjectType):
    id = graphene.ID()
    proveedor = graphene.ID()
    proveedor_nombre = graphene.String()
    restaurante_id = graphene.ID()
    estado = graphene.String()
    moneda = graphene.String()
    total_estimado = graphene.String()
    fecha_creacion = graphene.String()
    fecha_entrega_estimada = graphene.String()
    fecha_recepcion = graphene.String()
    notas = graphene.String()
    detalles = graphene.List(DetalleOrdenType)

    def resolve_detalles(root, info):
        return root.get("detalles", []) if isinstance(root, dict) else []


class AlertaStockType(graphene.ObjectType):
    id = graphene.ID()
    tipo_alerta = graphene.String()
    estado = graphene.String()
    ingrediente_id = graphene.ID()
    nombre_ingrediente = graphene.String()
    restaurante_id = graphene.ID()
    almacen = graphene.ID()
    almacen_nombre = graphene.String()
    nivel_actual = graphene.String()
    nivel_minimo = graphene.String()
    lote = graphene.ID()
    fecha_alerta = graphene.String()
    fecha_resolucion = graphene.String()


class RecetaPlatoType(graphene.ObjectType):
    id = graphene.ID()
    plato_id = graphene.ID()
    ingrediente_id = graphene.ID()
    nombre_ingrediente = graphene.String()
    cantidad = graphene.String()
    unidad_medida = graphene.String()
    costo_unitario = graphene.String()
    costo_ingrediente = graphene.Float()
    fecha_actualizacion = graphene.String()
    # fecha_costo_actualizado no estaba en el original — lo agrego
    fecha_costo_actualizado = graphene.String()


# ── NUEVO: Costo de producción ────────────────────────────────────────────────

class IngredienteCostoType(graphene.ObjectType):
    """
    Desglose de un ingrediente en el cálculo de costo de producción.
    Incluye stock en tiempo real del restaurante.
    """
    ingrediente_id = graphene.ID()
    nombre_ingrediente = graphene.String()
    cantidad_receta = graphene.Float()          # cantidad que pide la receta
    unidad_medida = graphene.String()
    # precio/unidad (última orden de compra)
    costo_unitario = graphene.Float()
    costo_ingrediente = graphene.Float()        # costo_unitario × cantidad_receta
    # Stock en tiempo real
    stock_actual = graphene.Float()             # cantidad en almacén ahora
    esta_agotado = graphene.Boolean()           # stock = 0
    necesita_reposicion = graphene.Boolean()    # stock ≤ nivel_minimo
    # floor(stock_actual / cantidad_receta)
    porciones_posibles = graphene.Int()
    fecha_costo_actualizado = graphene.String()  # cuándo se actualizó el costo


class CostoPlatoType(graphene.ObjectType):
    """
    Costo total de producción de un plato.
    Incluye desglose por ingrediente y porciones que se pueden preparar
    con el stock actual del restaurante.
    """
    plato_id = graphene.ID()
    costo_total = graphene.Float()           # suma de todos los costo_ingrediente
    # True si algún ingrediente tiene costo=0
    tiene_costos_vacios = graphene.Boolean()
    # mínimo de porciones posibles (cuello de botella)
    porciones_disponibles = graphene.Int()
    ingredientes = graphene.List(IngredienteCostoType)
    advertencia = graphene.String()          # mensaje si costos incompletos

    def resolve_ingredientes(root, info):
        if isinstance(root, dict):
            return root.get("ingredientes", [])
        return []

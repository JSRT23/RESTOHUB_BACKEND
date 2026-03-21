import graphene


class ProveedorType(graphene.ObjectType):
    id = graphene.ID()
    nombre = graphene.String()
    pais = graphene.String()
    ciudad = graphene.String()
    telefono = graphene.String()
    email = graphene.String()
    moneda_preferida = graphene.String()
    activo = graphene.Boolean()
    fecha_creacion = graphene.String()
    fecha_actualizacion = graphene.String()


class AlmacenType(graphene.ObjectType):
    id = graphene.ID()
    restaurante_id = graphene.ID()
    nombre = graphene.String()
    descripcion = graphene.String()
    activo = graphene.Boolean()
    fecha_creacion = graphene.String()
    total_ingredientes = graphene.Int()
    ingredientes_bajo_minimo = graphene.Int()


class MovimientoInventarioType(graphene.ObjectType):
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
    movimientos = graphene.List(MovimientoInventarioType)


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


class DetalleOrdenCompraType(graphene.ObjectType):
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
    detalles = graphene.List(DetalleOrdenCompraType)


class AlertaType(graphene.ObjectType):
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
    fecha_alerta = graphene.String()
    fecha_resolucion = graphene.String()


class RecetaIngredienteType(graphene.ObjectType):
    ingrediente_id = graphene.ID()
    nombre_ingrediente = graphene.String()
    cantidad = graphene.String()
    unidad_medida = graphene.String()
    costo_unitario = graphene.String()
    costo_ingrediente = graphene.String()
    fecha_costo_actualizado = graphene.String()


class CostoPlatoType(graphene.ObjectType):
    plato_id = graphene.ID()
    costo_total = graphene.String()
    tiene_costos_vacios = graphene.Boolean()
    advertencia = graphene.String()
    ingredientes = graphene.List(RecetaIngredienteType)

# gateway_service/app/gateway/graphql/services/order/types.py
import graphene


class DetallePedidoType(graphene.ObjectType):
    id = graphene.ID()
    plato_id = graphene.ID()
    nombre_plato = graphene.String()
    precio_unitario = graphene.String()
    cantidad = graphene.Int()
    subtotal = graphene.String()
    notas = graphene.String()


class ComandaCocinaType(graphene.ObjectType):
    id = graphene.ID()
    pedido = graphene.ID()
    estacion = graphene.String()
    estado = graphene.String()
    hora_envio = graphene.String()
    hora_fin = graphene.String()
    tiempo_preparacion_segundos = graphene.Float()
    numero_dia = graphene.Int()


class SeguimientoPedidoType(graphene.ObjectType):
    id = graphene.ID()
    estado = graphene.String()
    fecha = graphene.String()
    descripcion = graphene.String()


class EntregaPedidoType(graphene.ObjectType):
    id = graphene.ID()
    pedido = graphene.ID()
    tipo_entrega = graphene.String()
    direccion = graphene.String()
    repartidor_id = graphene.ID()
    repartidor_nombre = graphene.String()
    estado_entrega = graphene.String()
    fecha_salida = graphene.String()
    fecha_entrega_real = graphene.String()


class PedidoType(graphene.ObjectType):
    id = graphene.ID()
    restaurante_id = graphene.ID()
    cliente_id = graphene.ID()
    canal = graphene.String()
    estado = graphene.String()
    prioridad = graphene.Int()
    total = graphene.String()
    moneda = graphene.String()
    mesa_id = graphene.ID()
    metodo_pago = graphene.String()
    numero_dia = graphene.Int()
    fecha_creacion = graphene.String()
    fecha_entrega_estimada = graphene.String()
    detalles = graphene.List(DetallePedidoType)
    comandas = graphene.List(ComandaCocinaType)
    seguimientos = graphene.List(SeguimientoPedidoType)
    entrega = graphene.Field(EntregaPedidoType)

    def resolve_detalles(root, info):
        return root.get("detalles", []) if isinstance(root, dict) else []

    def resolve_comandas(root, info):
        return root.get("comandas", []) if isinstance(root, dict) else []

    def resolve_seguimientos(root, info):
        return root.get("seguimientos", []) if isinstance(root, dict) else []

    def resolve_entrega(root, info):
        return root.get("entrega") if isinstance(root, dict) else None

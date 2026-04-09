# gateway_service/app/gateway/graphql/services/order/queries.py
# CORRECCIÓN: seguimiento_pedido retornaba List(String) pero la API
# retorna lista de objetos {id, estado, fecha, descripcion}
# Fix: cambiar a List(SeguimientoPedidoType)

import graphene
from .types import PedidoType, ComandaCocinaType, EntregaPedidoType, SeguimientoPedidoType
from ....client import order_client


class OrderQuery(graphene.ObjectType):

    pedidos = graphene.List(
        PedidoType,
        estado=graphene.String(),
        canal=graphene.String(),
        restaurante_id=graphene.ID(),
        cliente_id=graphene.ID(),
    )
    pedido = graphene.Field(PedidoType, id=graphene.ID(required=True))

    # ✅ CORREGIDO: SeguimientoPedidoType en lugar de graphene.String
    seguimiento_pedido = graphene.List(
        SeguimientoPedidoType,
        pedido_id=graphene.ID(required=True),
        description="Historial de estados del pedido en orden cronológico",
    )

    comandas = graphene.List(
        ComandaCocinaType,
        estado=graphene.String(),
        estacion=graphene.String(),
        pedido_id=graphene.ID(),
    )
    comanda = graphene.Field(ComandaCocinaType, id=graphene.ID(required=True))
    entrega = graphene.Field(EntregaPedidoType, id=graphene.ID(required=True))

    def resolve_pedidos(self, info, estado=None, canal=None,
                        restaurante_id=None, cliente_id=None):
        return order_client.get_pedidos(
            estado=estado, canal=canal,
            restaurante_id=restaurante_id,
            cliente_id=cliente_id,
        ) or []

    def resolve_pedido(self, info, id):
        return order_client.get_pedido(id)

    def resolve_seguimiento_pedido(self, info, pedido_id):
        # ✅ Retorna lista de dicts — SeguimientoPedidoType los resuelve
        return order_client.get_seguimiento(pedido_id) or []

    def resolve_comandas(self, info, estado=None, estacion=None, pedido_id=None):
        return order_client.get_comandas(
            estado=estado, estacion=estacion, pedido_id=pedido_id
        ) or []

    def resolve_comanda(self, info, id):
        return order_client.get_comanda(id)

    def resolve_entrega(self, info, id):
        return order_client.get_entrega(id)

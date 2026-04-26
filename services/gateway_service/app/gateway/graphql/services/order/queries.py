# gateway_service/app/gateway/graphql/services/order/queries.py
# FIX: order_service devuelve respuesta paginada {"count": N, "results": [...]}
# pero resolve_pedidos esperaba una lista directa.
# Solución: _unwrap() extrae "results" si es paginado, o devuelve la lista/dict tal cual.

import graphene
from .types import PedidoType, ComandaCocinaType, EntregaPedidoType, SeguimientoPedidoType
from ....client import order_client


def _unwrap(data):
    """Extrae la lista real de una respuesta paginada o directa."""
    if isinstance(data, dict):
        # Respuesta paginada: {"count": N, "results": [...]}
        if "results" in data:
            return data["results"]
        # Respuesta de error
        if data.get("_error"):
            return []
    if isinstance(data, list):
        return data
    return []


class OrderQuery(graphene.ObjectType):

    pedidos = graphene.List(
        PedidoType,
        estado=graphene.String(),
        canal=graphene.String(),
        restaurante_id=graphene.ID(),
        cliente_id=graphene.ID(),
    )
    pedido = graphene.Field(PedidoType, id=graphene.ID(required=True))

    seguimiento_pedido = graphene.List(
        SeguimientoPedidoType,
        pedido_id=graphene.ID(required=True),
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
        data = order_client.get_pedidos(
            estado=estado, canal=canal,
            restaurante_id=restaurante_id,
            cliente_id=cliente_id,
        )
        return _unwrap(data)

    def resolve_pedido(self, info, id):
        return order_client.get_pedido(id)

    def resolve_seguimiento_pedido(self, info, pedido_id):
        data = order_client.get_seguimiento(pedido_id)
        return _unwrap(data) if isinstance(data, dict) else (data or [])

    def resolve_comandas(self, info, estado=None, estacion=None, pedido_id=None):
        data = order_client.get_comandas(
            estado=estado, estacion=estacion, pedido_id=pedido_id
        )
        return _unwrap(data) if isinstance(data, dict) else (data or [])

    def resolve_comanda(self, info, id):
        return order_client.get_comanda(id)

    def resolve_entrega(self, info, id):
        return order_client.get_entrega(id)

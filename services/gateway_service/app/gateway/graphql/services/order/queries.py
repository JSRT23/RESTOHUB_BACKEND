# gateway_service/app/gateway/graphql/services/order/queries.py
import graphene
from .types import PedidoType, ComandaCocinaType, EntregaPedidoType
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

    seguimiento_pedido = graphene.List(
        graphene.String,
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

    # ── Resolvers ─────────────────────────────────────────────────────────
    # Retornamos dicts crudos — los resolvers de PedidoType
    # (resolve_detalles, resolve_comandas, etc.) manejan los campos anidados.

    def resolve_pedidos(self, info, estado=None, canal=None,
                        restaurante_id=None, cliente_id=None):
        # Usa PedidoListSerializer — sin detalles/comandas anidados
        return order_client.get_pedidos(
            estado=estado, canal=canal,
            restaurante_id=restaurante_id,
            cliente_id=cliente_id,
        ) or []

    def resolve_pedido(self, info, id):
        # Usa PedidoSerializer completo — incluye detalles, comandas, seguimientos, entrega
        return order_client.get_pedido(id)

    def resolve_seguimiento_pedido(self, info, pedido_id):
        # Retorna lista de strings JSON — el frontend los parsea si necesita
        return order_client.get_seguimiento(pedido_id) or []

    def resolve_comandas(self, info, estado=None, estacion=None, pedido_id=None):
        return order_client.get_comandas(
            estado=estado, estacion=estacion, pedido_id=pedido_id
        ) or []

    def resolve_comanda(self, info, id):
        return order_client.get_comanda(id)

    def resolve_entrega(self, info, id):
        return order_client.get_entrega(id)

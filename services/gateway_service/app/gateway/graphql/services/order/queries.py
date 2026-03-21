import graphene
from .types import PedidoType, ComandaCocinaType, EntregaPedidoType
from .types import DetallePedidoType, SeguimientoPedidoType
from ....client import order_client


def _map_pedido(data: dict) -> PedidoType:
    return PedidoType(
        id=data.get("id"),
        restaurante_id=data.get("restaurante_id"),
        cliente_id=data.get("cliente_id"),
        canal=data.get("canal"),
        estado=data.get("estado"),
        prioridad=data.get("prioridad"),
        total=data.get("total"),
        moneda=data.get("moneda"),
        mesa_id=data.get("mesa_id"),
        fecha_creacion=data.get("fecha_creacion"),
        fecha_entrega_estimada=data.get("fecha_entrega_estimada"),
        detalles=[DetallePedidoType(**d) for d in data.get("detalles", [])],
        comandas=[ComandaCocinaType(**c) for c in data.get("comandas", [])],
        seguimientos=[SeguimientoPedidoType(**s)
                      for s in data.get("seguimientos", [])],
        entrega=EntregaPedidoType(
            **data["entrega"]) if data.get("entrega") else None,
    )


class OrderQuery(graphene.ObjectType):

    pedidos = graphene.List(
        PedidoType,
        estado=graphene.String(),
        canal=graphene.String(),
        restaurante_id=graphene.ID(),
        cliente_id=graphene.ID(),
    )
    pedido = graphene.Field(PedidoType, id=graphene.ID(required=True))
    comandas = graphene.List(
        ComandaCocinaType,
        estado=graphene.String(),
        estacion=graphene.String(),
        pedido_id=graphene.ID(),
    )
    comanda = graphene.Field(ComandaCocinaType, id=graphene.ID(required=True))
    entrega = graphene.Field(EntregaPedidoType, id=graphene.ID(required=True))

    def resolve_pedidos(self, info, estado=None, canal=None, restaurante_id=None, cliente_id=None):
        data = order_client.get_pedidos(
            estado=estado, canal=canal,
            restaurante_id=restaurante_id, cliente_id=cliente_id,
        )
        return [_map_pedido(p) for p in data]

    def resolve_pedido(self, info, id):
        data = order_client.get_pedido(id)
        return _map_pedido(data) if data else None

    def resolve_comandas(self, info, estado=None, estacion=None, pedido_id=None):
        return [ComandaCocinaType(**c) for c in order_client.get_comandas(
            estado=estado, estacion=estacion, pedido_id=pedido_id
        )]

    def resolve_comanda(self, info, id):
        data = order_client.get_comanda(id)
        return ComandaCocinaType(**data) if data else None

    def resolve_entrega(self, info, id):
        data = order_client.get_entrega(id)
        return EntregaPedidoType(**data) if data else None

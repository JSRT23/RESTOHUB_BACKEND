import graphene
from .types import PedidoType, ComandaCocinaType, EntregaPedidoType
from .types import DetallePedidoType, SeguimientoPedidoType
from .queries import _map_pedido
from ....client import order_client


class DetalleInput(graphene.InputObjectType):
    plato_id = graphene.ID(required=True)
    nombre_plato = graphene.String(required=True)
    precio_unitario = graphene.Float(required=True)
    cantidad = graphene.Int(required=True)
    notas = graphene.String()


class CrearPedido(graphene.Mutation):
    class Arguments:
        restaurante_id = graphene.ID(required=True)
        canal = graphene.String(required=True)
        moneda = graphene.String(required=True)
        detalles = graphene.List(graphene.NonNull(DetalleInput), required=True)
        cliente_id = graphene.ID()
        prioridad = graphene.Int()
        mesa_id = graphene.ID()
        fecha_entrega_estimada = graphene.String()
    ok = graphene.Boolean()
    pedido = graphene.Field(PedidoType)
    error = graphene.String()

    def mutate(self, info, restaurante_id, canal, moneda, detalles, **kwargs):
        data = order_client.crear_pedido({
            "restaurante_id": restaurante_id, "canal": canal, "moneda": moneda,
            "detalles": [dict(d) for d in detalles],
            **{k: v for k, v in kwargs.items() if v is not None},
        })
        if not data:
            return CrearPedido(ok=False, error="Error al crear pedido.")
        return CrearPedido(ok=True, pedido=_map_pedido(data))


class ConfirmarPedido(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        descripcion = graphene.String()
    ok = graphene.Boolean()
    pedido = graphene.Field(PedidoType)
    error = graphene.String()

    def mutate(self, info, id, descripcion=""):
        data = order_client.confirmar_pedido(id, descripcion)
        if not data:
            return ConfirmarPedido(ok=False, error="Error al confirmar.")
        return ConfirmarPedido(ok=True, pedido=_map_pedido(data))


class CancelarPedido(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        descripcion = graphene.String()
    ok = graphene.Boolean()
    pedido = graphene.Field(PedidoType)
    error = graphene.String()

    def mutate(self, info, id, descripcion=""):
        data = order_client.cancelar_pedido(id, descripcion)
        if not data:
            return CancelarPedido(ok=False, error="Error al cancelar.")
        return CancelarPedido(ok=True, pedido=_map_pedido(data))


class MarcarPedidoListo(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        descripcion = graphene.String()
    ok = graphene.Boolean()
    pedido = graphene.Field(PedidoType)
    error = graphene.String()

    def mutate(self, info, id, descripcion=""):
        data = order_client.marcar_listo(id, descripcion)
        if not data:
            return MarcarPedidoListo(ok=False, error="Error.")
        return MarcarPedidoListo(ok=True, pedido=_map_pedido(data))


class EntregarPedido(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        descripcion = graphene.String()
    ok = graphene.Boolean()
    pedido = graphene.Field(PedidoType)
    error = graphene.String()

    def mutate(self, info, id, descripcion=""):
        data = order_client.entregar_pedido(id, descripcion)
        if not data:
            return EntregarPedido(ok=False, error="Error.")
        return EntregarPedido(ok=True, pedido=_map_pedido(data))


class CrearComanda(graphene.Mutation):
    class Arguments:
        pedido_id = graphene.ID(required=True)
        estacion = graphene.String(required=True)
    ok = graphene.Boolean()
    comanda = graphene.Field(ComandaCocinaType)
    error = graphene.String()

    def mutate(self, info, pedido_id, estacion):
        data = order_client.crear_comanda(
            {"pedido": pedido_id, "estacion": estacion})
        if not data:
            return CrearComanda(ok=False, error="Error al crear comanda.")
        return CrearComanda(ok=True, comanda=ComandaCocinaType(**data))


class IniciarComanda(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    comanda = graphene.Field(ComandaCocinaType)
    error = graphene.String()

    def mutate(self, info, id):
        data = order_client.iniciar_comanda(id)
        if not data:
            return IniciarComanda(ok=False, error="Error.")
        return IniciarComanda(ok=True, comanda=ComandaCocinaType(**data))


class ComandaLista(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    comanda = graphene.Field(ComandaCocinaType)
    error = graphene.String()

    def mutate(self, info, id):
        data = order_client.comanda_lista(id)
        if not data:
            return ComandaLista(ok=False, error="Error.")
        return ComandaLista(ok=True, comanda=ComandaCocinaType(**data))


class CrearEntrega(graphene.Mutation):
    class Arguments:
        pedido_id = graphene.ID(required=True)
        tipo_entrega = graphene.String(required=True)
        direccion = graphene.String()
        repartidor_id = graphene.ID()
        repartidor_nombre = graphene.String()
    ok = graphene.Boolean()
    entrega = graphene.Field(EntregaPedidoType)
    error = graphene.String()

    def mutate(self, info, pedido_id, tipo_entrega, **kwargs):
        data = order_client.crear_entrega({
            "pedido": pedido_id, "tipo_entrega": tipo_entrega,
            **{k: v for k, v in kwargs.items() if v is not None},
        })
        if not data:
            return CrearEntrega(ok=False, error="Error al crear entrega.")
        return CrearEntrega(ok=True, entrega=EntregaPedidoType(**data))


class EntregaEnCamino(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    entrega = graphene.Field(EntregaPedidoType)
    error = graphene.String()

    def mutate(self, info, id):
        data = order_client.entrega_en_camino(id)
        if not data:
            return EntregaEnCamino(ok=False, error="Error.")
        return EntregaEnCamino(ok=True, entrega=EntregaPedidoType(**data))


class CompletarEntrega(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    entrega = graphene.Field(EntregaPedidoType)
    error = graphene.String()

    def mutate(self, info, id):
        data = order_client.completar_entrega(id)
        if not data:
            return CompletarEntrega(ok=False, error="Error.")
        return CompletarEntrega(ok=True, entrega=EntregaPedidoType(**data))


class EntregaFallo(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    entrega = graphene.Field(EntregaPedidoType)
    error = graphene.String()

    def mutate(self, info, id):
        data = order_client.entrega_fallo(id)
        if not data:
            return EntregaFallo(ok=False, error="Error.")
        return EntregaFallo(ok=True, entrega=EntregaPedidoType(**data))


class OrderMutation(graphene.ObjectType):
    crear_pedido = CrearPedido.Field()
    confirmar_pedido = ConfirmarPedido.Field()
    cancelar_pedido = CancelarPedido.Field()
    marcar_listo = MarcarPedidoListo.Field()
    entregar_pedido = EntregarPedido.Field()
    crear_comanda = CrearComanda.Field()
    iniciar_comanda = IniciarComanda.Field()
    comanda_lista = ComandaLista.Field()
    crear_entrega = CrearEntrega.Field()
    entrega_en_camino = EntregaEnCamino.Field()
    completar_entrega = CompletarEntrega.Field()
    entrega_fallo = EntregaFallo.Field()

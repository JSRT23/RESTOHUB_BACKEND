# gateway_service/app/gateway/graphql/services/order/mutations.py
# CAMBIOS vs original:
# 1. get_jwt_user — agrega autenticación y permisos por rol
# 2. CrearPedido — permite mesero + inyecta restaurante_id del JWT si el rol lo requiere
# 3. ConfirmarPedido / EntregarPedido — permite cajero
# 4. IniciarComanda / ComandaLista — permite cocinero
# 5. Mejor propagación de errores del order_service

import graphene
from .types import PedidoType, ComandaCocinaType, EntregaPedidoType
from ....client import order_client
from ....middleware.permissions import get_jwt_user


def _is_error(data) -> bool:
    return isinstance(data, dict) and data.get("_error") is True


def _extract_error(data, fallback: str) -> str:
    if not data:
        return fallback
    if isinstance(data, dict):
        detail = data.get("detail") or data.get("error") or data.get("message")
        if detail:
            return str(detail)
    return fallback


class DetalleInput(graphene.InputObjectType):
    plato_id = graphene.ID(required=True)
    nombre_plato = graphene.String(required=True)
    precio_unitario = graphene.Float(required=True)
    cantidad = graphene.Int(required=True)
    notas = graphene.String()


# ─────────────────────────────────────────
# PEDIDOS
# ─────────────────────────────────────────

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
        user = get_jwt_user(info)
        if not user:
            return CrearPedido(ok=False, error="Debes iniciar sesión.")

        rol = user.get("rol")

        # Roles con permiso para crear pedidos
        if rol not in ("admin_central", "gerente_local", "mesero", "cajero"):
            return CrearPedido(ok=False, error="No tienes permiso para crear pedidos.")

        # Para mesero y cajero: el restaurante_id viene del JWT, no del argumento
        if rol in ("mesero", "cajero"):
            restaurante_id = user.get("restaurante_id") or restaurante_id

        payload = {
            "restaurante_id": restaurante_id,
            "canal":          canal,
            "moneda":         moneda,
            "detalles":       [dict(d) for d in detalles],
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        data = order_client.crear_pedido(payload)
        if not data or _is_error(data):
            msg = _extract_error(data, "Error al crear pedido.")
            return CrearPedido(ok=False, error=msg)
        # Crear comanda GENERAL automáticamente → cocinero la ve en PENDIENTE
        try:
            pedido_id = data.get("id") if isinstance(data, dict) else None
            if pedido_id:
                order_client.crear_comanda(
                    {"pedido": pedido_id, "estacion": "GENERAL"})
        except Exception:
            pass

        return CrearPedido(ok=True, pedido=data)


class ConfirmarPedido(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        descripcion = graphene.String()

    ok = graphene.Boolean()
    pedido = graphene.Field(PedidoType)
    error = graphene.String()

    def mutate(self, info, id, descripcion=""):
        user = get_jwt_user(info)
        if not user:
            return ConfirmarPedido(ok=False, error="Debes iniciar sesión.")
        if user.get("rol") not in ("admin_central", "gerente_local", "mesero", "cajero", "supervisor"):
            return ConfirmarPedido(ok=False, error="No tienes permiso.")
        data = order_client.confirmar_pedido(id, descripcion)
        if not data or _is_error(data):
            return ConfirmarPedido(ok=False, error=_extract_error(data, "Error al confirmar."))

        return ConfirmarPedido(ok=True, pedido=data)


class CancelarPedido(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        descripcion = graphene.String()

    ok = graphene.Boolean()
    pedido = graphene.Field(PedidoType)
    error = graphene.String()

    def mutate(self, info, id, descripcion=""):
        user = get_jwt_user(info)
        if not user:
            return CancelarPedido(ok=False, error="Debes iniciar sesión.")
        if user.get("rol") not in ("admin_central", "gerente_local", "mesero", "cajero", "supervisor"):
            return CancelarPedido(ok=False, error="No tienes permiso.")
        data = order_client.cancelar_pedido(id, descripcion)
        if not data or _is_error(data):
            return CancelarPedido(ok=False, error=_extract_error(data, "Error al cancelar."))
        return CancelarPedido(ok=True, pedido=data)


class MarcarPedidoListo(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        descripcion = graphene.String()

    ok = graphene.Boolean()
    pedido = graphene.Field(PedidoType)
    error = graphene.String()

    def mutate(self, info, id, descripcion=""):
        user = get_jwt_user(info)
        if not user:
            return MarcarPedidoListo(ok=False, error="Debes iniciar sesión.")
        if user.get("rol") not in ("admin_central", "gerente_local", "supervisor", "cocinero"):
            return MarcarPedidoListo(ok=False, error="No tienes permiso.")
        data = order_client.marcar_listo(id, descripcion)
        if not data or _is_error(data):
            return MarcarPedidoListo(ok=False, error=_extract_error(data, "Error al marcar listo."))
        return MarcarPedidoListo(ok=True, pedido=data)


class EntregarPedido(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        descripcion = graphene.String()
        metodo_pago = graphene.String()

    ok = graphene.Boolean()
    pedido = graphene.Field(PedidoType)
    error = graphene.String()

    def mutate(self, info, id, descripcion="", metodo_pago=None):
        user = get_jwt_user(info)
        if not user:
            return EntregarPedido(ok=False, error="Debes iniciar sesión.")
        if user.get("rol") not in ("admin_central", "gerente_local", "cajero", "supervisor"):
            return EntregarPedido(ok=False, error="No tienes permiso.")
        data = order_client.entregar_pedido(
            id, descripcion, metodo_pago=metodo_pago)
        if not data or _is_error(data):
            return EntregarPedido(ok=False, error=_extract_error(data, "Error al entregar."))
        return EntregarPedido(ok=True, pedido=data)


# ─────────────────────────────────────────
# COMANDAS
# ─────────────────────────────────────────

class CrearComanda(graphene.Mutation):
    class Arguments:
        pedido_id = graphene.ID(required=True)
        estacion = graphene.String(required=True)

    ok = graphene.Boolean()
    comanda = graphene.Field(ComandaCocinaType)
    error = graphene.String()

    def mutate(self, info, pedido_id, estacion):
        user = get_jwt_user(info)
        if not user:
            return CrearComanda(ok=False, error="Debes iniciar sesión.")
        if user.get("rol") not in ("admin_central", "gerente_local", "supervisor"):
            return CrearComanda(ok=False, error="No tienes permiso.")
        data = order_client.crear_comanda(
            {"pedido": pedido_id, "estacion": estacion})
        if not data or _is_error(data):
            return CrearComanda(ok=False, error=_extract_error(data, "Error al crear comanda."))
        return CrearComanda(ok=True, comanda=data)


class IniciarComanda(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    comanda = graphene.Field(ComandaCocinaType)
    error = graphene.String()

    def mutate(self, info, id):
        user = get_jwt_user(info)
        if not user:
            return IniciarComanda(ok=False, error="Debes iniciar sesión.")
        if user.get("rol") not in ("admin_central", "gerente_local", "supervisor", "cocinero"):
            return IniciarComanda(ok=False, error="No tienes permiso.")
        data = order_client.iniciar_comanda(id)
        if not data or _is_error(data):
            return IniciarComanda(ok=False, error=_extract_error(data, "Error al iniciar comanda."))

        # Mover pedido RECIBIDO → EN_PREPARACION
        try:
            pedido_id = data.get("pedido") if isinstance(data, dict) else None
            if pedido_id:
                order_client.confirmar_pedido(
                    str(pedido_id), "Comanda iniciada en cocina.")
        except Exception:
            pass

        return IniciarComanda(ok=True, comanda=data)


class ComandaLista(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    comanda = graphene.Field(ComandaCocinaType)
    error = graphene.String()

    def mutate(self, info, id):
        user = get_jwt_user(info)
        if not user:
            return ComandaLista(ok=False, error="Debes iniciar sesión.")
        if user.get("rol") not in ("admin_central", "gerente_local", "supervisor", "cocinero"):
            return ComandaLista(ok=False, error="No tienes permiso.")
        data = order_client.comanda_lista(id)
        if not data or _is_error(data):
            return ComandaLista(ok=False, error=_extract_error(data, "Error al marcar comanda como lista."))

        # Marcar el pedido como LISTO automáticamente
        # (todas las comandas listas → pedido listo para el cajero)
        try:
            pedido_id = data.get("pedido") if isinstance(data, dict) else None
            if pedido_id:
                order_client.marcar_listo(
                    str(pedido_id), "Comanda lista — pedido listo para cobro.")
        except Exception:
            pass

        return ComandaLista(ok=True, comanda=data)


# ─────────────────────────────────────────
# ENTREGAS
# ─────────────────────────────────────────

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
        user = get_jwt_user(info)
        if not user:
            return CrearEntrega(ok=False, error="Debes iniciar sesión.")
        if user.get("rol") not in ("admin_central", "gerente_local", "supervisor"):
            return CrearEntrega(ok=False, error="No tienes permiso.")
        payload = {
            "pedido":       pedido_id,
            "tipo_entrega": tipo_entrega,
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        data = order_client.crear_entrega(payload)
        if not data or _is_error(data):
            return CrearEntrega(ok=False, error=_extract_error(data, "Error al crear entrega."))
        return CrearEntrega(ok=True, entrega=data)


class EntregaEnCamino(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    entrega = graphene.Field(EntregaPedidoType)
    error = graphene.String()

    def mutate(self, info, id):
        user = get_jwt_user(info)
        if not user:
            return EntregaEnCamino(ok=False, error="Debes iniciar sesión.")
        if user.get("rol") not in ("admin_central", "gerente_local", "supervisor", "repartidor"):
            return EntregaEnCamino(ok=False, error="No tienes permiso.")
        data = order_client.entrega_en_camino(id)
        if not data or _is_error(data):
            return EntregaEnCamino(ok=False, error=_extract_error(data, "Error al marcar en camino."))
        return EntregaEnCamino(ok=True, entrega=data)


class CompletarEntrega(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    entrega = graphene.Field(EntregaPedidoType)
    error = graphene.String()

    def mutate(self, info, id):
        user = get_jwt_user(info)
        if not user:
            return CompletarEntrega(ok=False, error="Debes iniciar sesión.")
        if user.get("rol") not in ("admin_central", "gerente_local", "supervisor", "repartidor"):
            return CompletarEntrega(ok=False, error="No tienes permiso.")
        data = order_client.completar_entrega(id)
        if not data or _is_error(data):
            return CompletarEntrega(ok=False, error=_extract_error(data, "Error al completar entrega."))
        return CompletarEntrega(ok=True, entrega=data)


class EntregaFallo(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    entrega = graphene.Field(EntregaPedidoType)
    error = graphene.String()

    def mutate(self, info, id):
        user = get_jwt_user(info)
        if not user:
            return EntregaFallo(ok=False, error="Debes iniciar sesión.")
        if user.get("rol") not in ("admin_central", "gerente_local", "supervisor", "repartidor"):
            return EntregaFallo(ok=False, error="No tienes permiso.")
        data = order_client.entrega_fallo(id)
        if not data or _is_error(data):
            return EntregaFallo(ok=False, error=_extract_error(data, "Error al marcar entrega fallida."))
        return EntregaFallo(ok=True, entrega=data)


# ─────────────────────────────────────────
# REGISTRO
# ─────────────────────────────────────────

class OrderMutation(graphene.ObjectType):
    # Pedidos
    crear_pedido = CrearPedido.Field()
    confirmar_pedido = ConfirmarPedido.Field()
    cancelar_pedido = CancelarPedido.Field()
    marcar_listo = MarcarPedidoListo.Field()
    entregar_pedido = EntregarPedido.Field()

    # Comandas
    crear_comanda = CrearComanda.Field()
    iniciar_comanda = IniciarComanda.Field()
    comanda_lista = ComandaLista.Field()

    # Entregas
    crear_entrega = CrearEntrega.Field()
    entrega_en_camino = EntregaEnCamino.Field()
    completar_entrega = CompletarEntrega.Field()
    entrega_fallo = EntregaFallo.Field()

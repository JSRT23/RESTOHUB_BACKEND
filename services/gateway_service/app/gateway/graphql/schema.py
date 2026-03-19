import graphene
from .types import (
    RestauranteType, CategoriaType, PlatoType, IngredienteType,
    PrecioPlatoType, MenuRestauranteType, MenuCategoriaType, MenuPlatoType,
    PedidoType, DetallePedidoType, ComandaCocinaType, EntregaPedidoType,
    SeguimientoPedidoType,
)
from ..client import menu_client, order_client


# ═══════════════════════════════════════════
# QUERIES
# ═══════════════════════════════════════════

class Query(graphene.ObjectType):

    # ── Menu ──
    restaurantes = graphene.List(
        RestauranteType, activo=graphene.Boolean(), pais=graphene.String())
    restaurante = graphene.Field(
        RestauranteType, id=graphene.ID(required=True))
    menu_restaurante = graphene.Field(
        MenuRestauranteType, id=graphene.ID(required=True))
    categorias = graphene.List(CategoriaType, activo=graphene.Boolean())
    categoria = graphene.Field(CategoriaType, id=graphene.ID(required=True))
    platos = graphene.List(
        PlatoType, activo=graphene.Boolean(), categoria_id=graphene.ID())
    plato = graphene.Field(PlatoType, id=graphene.ID(required=True))
    ingredientes = graphene.List(IngredienteType, activo=graphene.Boolean())
    precios = graphene.List(
        PrecioPlatoType,
        plato_id=graphene.ID(),
        restaurante_id=graphene.ID(),
        activo=graphene.Boolean(),
    )

    # ── Orders ──
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

    # ─────────────────────────────────────────
    # Resolvers — Menu
    # ─────────────────────────────────────────

    def resolve_restaurantes(self, info, activo=None, pais=None):
        data = menu_client.get_restaurantes(activo=activo, pais=pais)
        return [RestauranteType(**r) for r in data]

    def resolve_restaurante(self, info, id):
        data = menu_client.get_restaurante(id)
        return RestauranteType(**data) if data else None

    def resolve_menu_restaurante(self, info, id):
        data = menu_client.get_menu_restaurante(id)
        if not data:
            return None
        categorias = [
            MenuCategoriaType(
                categoria_id=cat.get("categoria_id"),
                nombre=cat.get("nombre"),
                orden=cat.get("orden"),
                platos=[MenuPlatoType(**p) for p in cat.get("platos", [])],
            )
            for cat in data.get("categorias", [])
        ]
        return MenuRestauranteType(
            restaurante_id=data.get("restaurante_id"),
            nombre=data.get("nombre"),
            ciudad=data.get("ciudad"),
            pais=data.get("pais"),
            moneda=data.get("moneda"),
            categorias=categorias,
        )

    def resolve_categorias(self, info, activo=None):
        data = menu_client.get_categorias(activo=activo)
        return [CategoriaType(**c) for c in data]

    def resolve_categoria(self, info, id):
        data = menu_client.get_categoria(id)
        return CategoriaType(**data) if data else None

    def resolve_platos(self, info, activo=None, categoria_id=None):
        data = menu_client.get_platos(activo=activo, categoria_id=categoria_id)
        return [PlatoType(**p) for p in data]

    def resolve_plato(self, info, id):
        data = menu_client.get_plato(id)
        return PlatoType(**data) if data else None

    def resolve_ingredientes(self, info, activo=None):
        data = menu_client.get_ingredientes(activo=activo)
        return [IngredienteType(**i) for i in data]

    def resolve_precios(self, info, plato_id=None, restaurante_id=None, activo=None):
        data = menu_client.get_precios(
            plato_id=plato_id,
            restaurante_id=restaurante_id,
            activo=activo,
        )
        return [PrecioPlatoType(**p) for p in data]

    # ─────────────────────────────────────────
    # Resolvers — Orders
    # ─────────────────────────────────────────

    def resolve_pedidos(self, info, estado=None, canal=None, restaurante_id=None, cliente_id=None):
        data = order_client.get_pedidos(
            estado=estado,
            canal=canal,
            restaurante_id=restaurante_id,
            cliente_id=cliente_id,
        )
        return [_map_pedido(p) for p in data]

    def resolve_pedido(self, info, id):
        data = order_client.get_pedido(id)
        return _map_pedido(data) if data else None

    def resolve_comandas(self, info, estado=None, estacion=None, pedido_id=None):
        data = order_client.get_comandas(
            estado=estado, estacion=estacion, pedido_id=pedido_id)
        return [ComandaCocinaType(**c) for c in data]

    def resolve_comanda(self, info, id):
        data = order_client.get_comanda(id)
        return ComandaCocinaType(**data) if data else None

    def resolve_entrega(self, info, id):
        data = order_client.get_entrega(id)
        return EntregaPedidoType(**data) if data else None


# ─────────────────────────────────────────
# Helper mapper — Pedido
# ─────────────────────────────────────────

def _map_pedido(data: dict) -> PedidoType:
    """Mapea el dict del REST al ObjectType incluyendo relaciones anidadas."""
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
        detalles=[
            DetallePedidoType(**d)
            for d in data.get("detalles", [])
        ],
        comandas=[
            ComandaCocinaType(**c)
            for c in data.get("comandas", [])
        ],
        seguimientos=[
            SeguimientoPedidoType(**s)
            for s in data.get("seguimientos", [])
        ],
        entrega=EntregaPedidoType(
            **data["entrega"]) if data.get("entrega") else None,
    )


# ═══════════════════════════════════════════
# MUTATIONS — Menu
# ═══════════════════════════════════════════

class CrearRestaurante(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        pais = graphene.String(required=True)
        ciudad = graphene.String(required=True)
        direccion = graphene.String(required=True)
        moneda = graphene.String(required=True)

    ok = graphene.Boolean()
    restaurante = graphene.Field(RestauranteType)
    error = graphene.String()

    def mutate(self, info, **kwargs):
        data = menu_client.crear_restaurante(kwargs)
        if not data:
            return CrearRestaurante(ok=False, error="Error al crear restaurante.")
        return CrearRestaurante(ok=True, restaurante=RestauranteType(**data))


class ActualizarRestaurante(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        nombre = graphene.String()
        pais = graphene.String()
        ciudad = graphene.String()
        direccion = graphene.String()
        moneda = graphene.String()

    ok = graphene.Boolean()
    restaurante = graphene.Field(RestauranteType)
    error = graphene.String()

    def mutate(self, info, id, **kwargs):
        data = menu_client.actualizar_restaurante(id, kwargs)
        if not data:
            return ActualizarRestaurante(ok=False, error="Error al actualizar.")
        return ActualizarRestaurante(ok=True, restaurante=RestauranteType(**data))


class ActivarRestaurante(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        result = menu_client.activar_restaurante(id)
        return ActivarRestaurante(ok=bool(result))


class DesactivarRestaurante(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        result = menu_client.desactivar_restaurante(id)
        return DesactivarRestaurante(ok=bool(result))


class CrearCategoria(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        orden = graphene.Int()

    ok = graphene.Boolean()
    categoria = graphene.Field(CategoriaType)
    error = graphene.String()

    def mutate(self, info, nombre, orden=0):
        data = menu_client.crear_categoria({"nombre": nombre, "orden": orden})
        if not data:
            return CrearCategoria(ok=False, error="Error al crear categoría.")
        return CrearCategoria(ok=True, categoria=CategoriaType(**data))


class CrearPlato(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        descripcion = graphene.String(required=True)
        categoria_id = graphene.ID()
        imagen = graphene.String()

    ok = graphene.Boolean()
    plato = graphene.Field(PlatoType)
    error = graphene.String()

    def mutate(self, info, nombre, descripcion, categoria_id=None, imagen=None):
        data = menu_client.crear_plato({
            "nombre":      nombre,
            "descripcion": descripcion,
            "categoria":   categoria_id,
            "imagen":      imagen,
        })
        if not data:
            return CrearPlato(ok=False, error="Error al crear plato.")
        return CrearPlato(ok=True, plato=PlatoType(**data))


class ActivarPlato(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        result = menu_client.activar_plato(id)
        return ActivarPlato(ok=bool(result))


class DesactivarPlato(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        result = menu_client.desactivar_plato(id)
        return DesactivarPlato(ok=bool(result))


class AgregarIngredientePlato(graphene.Mutation):
    class Arguments:
        plato_id = graphene.ID(required=True)
        ingrediente_id = graphene.ID(required=True)
        cantidad = graphene.Float(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, plato_id, ingrediente_id, cantidad):
        result = menu_client.agregar_ingrediente_plato(
            plato_id,
            {"ingrediente": ingrediente_id, "cantidad": cantidad}
        )
        return AgregarIngredientePlato(ok=bool(result))


class CrearIngrediente(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        unidad_medida = graphene.String(required=True)
        descripcion = graphene.String()

    ok = graphene.Boolean()
    ingrediente = graphene.Field(IngredienteType)
    error = graphene.String()

    def mutate(self, info, nombre, unidad_medida, descripcion=None):
        data = menu_client.crear_ingrediente({
            "nombre":        nombre,
            "unidad_medida": unidad_medida,
            "descripcion":   descripcion,
        })
        if not data:
            return CrearIngrediente(ok=False, error="Error al crear ingrediente.")
        return CrearIngrediente(ok=True, ingrediente=IngredienteType(**data))


class CrearPrecioPlato(graphene.Mutation):
    class Arguments:
        plato_id = graphene.ID(required=True)
        restaurante_id = graphene.ID(required=True)
        precio = graphene.Float(required=True)
        fecha_inicio = graphene.String(required=True)
        fecha_fin = graphene.String()

    ok = graphene.Boolean()
    precio_plato = graphene.Field(PrecioPlatoType)
    error = graphene.String()

    def mutate(self, info, plato_id, restaurante_id, precio, fecha_inicio, fecha_fin=None):
        data = menu_client.crear_precio({
            "plato":        plato_id,
            "restaurante":  restaurante_id,
            "precio":       precio,
            "fecha_inicio": fecha_inicio,
            "fecha_fin":    fecha_fin,
        })
        if not data:
            return CrearPrecioPlato(ok=False, error="Error al crear precio.")
        return CrearPrecioPlato(ok=True, precio_plato=PrecioPlatoType(**data))


# ═══════════════════════════════════════════
# MUTATIONS — Orders
# ═══════════════════════════════════════════

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
            "restaurante_id":         restaurante_id,
            "canal":                  canal,
            "moneda":                 moneda,
            "detalles":               [dict(d) for d in detalles],
            "cliente_id":             kwargs.get("cliente_id"),
            "prioridad":              kwargs.get("prioridad", 2),
            "mesa_id":                kwargs.get("mesa_id"),
            "fecha_entrega_estimada": kwargs.get("fecha_entrega_estimada"),
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
            return ConfirmarPedido(ok=False, error="Error al confirmar pedido.")
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
            return CancelarPedido(ok=False, error="Error al cancelar pedido.")
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
            return MarcarPedidoListo(ok=False, error="Error al marcar pedido como listo.")
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
            return EntregarPedido(ok=False, error="Error al entregar pedido.")
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
            return IniciarComanda(ok=False, error="Error al iniciar comanda.")
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
            return ComandaLista(ok=False, error="Error al marcar comanda como lista.")
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
            "pedido":             pedido_id,
            "tipo_entrega":       tipo_entrega,
            "direccion":          kwargs.get("direccion"),
            "repartidor_id":      kwargs.get("repartidor_id"),
            "repartidor_nombre":  kwargs.get("repartidor_nombre"),
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
            return EntregaEnCamino(ok=False, error="Error al actualizar entrega.")
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
            return CompletarEntrega(ok=False, error="Error al completar entrega.")
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
            return EntregaFallo(ok=False, error="Error al registrar fallo de entrega.")
        return EntregaFallo(ok=True, entrega=EntregaPedidoType(**data))


# ═══════════════════════════════════════════
# MUTATION ROOT
# ═══════════════════════════════════════════

class Mutation(graphene.ObjectType):
    # Menu
    crear_restaurante = CrearRestaurante.Field()
    actualizar_restaurante = ActualizarRestaurante.Field()
    activar_restaurante = ActivarRestaurante.Field()
    desactivar_restaurante = DesactivarRestaurante.Field()
    crear_categoria = CrearCategoria.Field()
    crear_plato = CrearPlato.Field()
    activar_plato = ActivarPlato.Field()
    desactivar_plato = DesactivarPlato.Field()
    agregar_ingrediente_plato = AgregarIngredientePlato.Field()
    crear_ingrediente = CrearIngrediente.Field()
    crear_precio_plato = CrearPrecioPlato.Field()

    # Orders
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


# ═══════════════════════════════════════════
# SCHEMA RAÍZ
# ═══════════════════════════════════════════

schema = graphene.Schema(query=Query, mutation=Mutation)

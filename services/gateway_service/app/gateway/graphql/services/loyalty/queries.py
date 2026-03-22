import graphene

from ....client import loyalty_client
from .types import (
    AplicacionPromocionType,
    CatalogoCategoriaType,
    CatalogoPlatoType,
    CuentaPuntosType,
    CuponType,
    PromocionListType,
    PromocionType,
    TransaccionPuntosType,
)


def _build(tipo, data):
    """Instancia ObjectType desde dict ignorando campos desconocidos."""
    if not data:
        return None
    return tipo(**{k: v for k, v in data.items() if hasattr(tipo, k)})


def _build_list(tipo, data):
    if not data:
        return []
    items = data.get("results", data) if isinstance(data, dict) else data
    return [_build(tipo, item) for item in items if item]


class LoyaltyQuery(graphene.ObjectType):

    # ── Puntos ───────────────────────────────────────────────────────────────

    puntos_cliente = graphene.Field(
        CuentaPuntosType,
        cliente_id=graphene.ID(required=True),
        description="Saldo de puntos del cliente — resuelve desde Redis si hay caché.",
    )

    # ── Transacciones ─────────────────────────────────────────────────────────

    transacciones_puntos = graphene.List(
        TransaccionPuntosType,
        cliente_id=graphene.ID(),
        pedido_id=graphene.ID(),
        tipo=graphene.String(),
        fecha_desde=graphene.String(),
        fecha_hasta=graphene.String(),
    )
    transaccion_puntos = graphene.Field(
        TransaccionPuntosType,
        transaccion_id=graphene.ID(required=True),
    )

    # ── Promociones ───────────────────────────────────────────────────────────

    promociones = graphene.List(
        PromocionListType,
        activa=graphene.Boolean(),
        alcance=graphene.String(),
        restaurante_id=graphene.ID(),
        tipo_beneficio=graphene.String(),
    )
    promocion = graphene.Field(
        PromocionType,
        promocion_id=graphene.ID(required=True),
    )

    # ── Cupones ───────────────────────────────────────────────────────────────

    cupones = graphene.List(
        CuponType,
        cliente_id=graphene.ID(),
        activo=graphene.Boolean(),
        codigo=graphene.String(),
    )
    cupon = graphene.Field(
        CuponType,
        cupon_id=graphene.ID(required=True),
    )
    validar_cupon = graphene.Field(
        CuponType,
        codigo=graphene.String(required=True),
        description="Valida un cupón por código. Retorna null si no existe.",
    )

    # ── Catálogo ──────────────────────────────────────────────────────────────

    catalogo_platos = graphene.List(
        CatalogoPlatoType,
        activo=graphene.Boolean(),
        categoria_id=graphene.ID(),
    )
    catalogo_categorias = graphene.List(
        CatalogoCategoriaType,
        activo=graphene.Boolean(),
    )

    # =========================================================================
    # Resolvers
    # =========================================================================

    def resolve_puntos_cliente(self, info, cliente_id):
        data = loyalty_client.get_puntos(cliente_id)
        if not data:
            return None
        # Mapear _cache → cache para el tipo GraphQL
        if "_cache" in data:
            data["cache"] = data.pop("_cache")
        return _build(CuentaPuntosType, data)

    def resolve_transacciones_puntos(self, info, cliente_id=None, pedido_id=None,
                                     tipo=None, fecha_desde=None, fecha_hasta=None):
        data = loyalty_client.get_transacciones(
            cliente_id=cliente_id,
            tipo=tipo,
            pedido_id=pedido_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
        return _build_list(TransaccionPuntosType, data)

    def resolve_transaccion_puntos(self, info, transaccion_id):
        data = loyalty_client.get_transaccion(transaccion_id)
        return _build(TransaccionPuntosType, data)

    def resolve_promociones(self, info, activa=None, alcance=None,
                            restaurante_id=None, tipo_beneficio=None):
        data = loyalty_client.get_promociones(
            activa=activa,
            alcance=alcance,
            restaurante_id=restaurante_id,
            tipo_beneficio=tipo_beneficio,
        )
        return _build_list(PromocionListType, data)

    def resolve_promocion(self, info, promocion_id):
        data = loyalty_client.get_promocion(promocion_id)
        if not data:
            return None
        # Construir reglas anidadas
        from .types import ReglaPromocionType
        reglas_data = data.pop("reglas", [])
        promo = _build(PromocionType, data)
        if promo:
            promo.reglas = [_build(ReglaPromocionType, r) for r in reglas_data]
        return promo

    def resolve_cupones(self, info, cliente_id=None, activo=None, codigo=None):
        data = loyalty_client.get_cupones(
            cliente_id=cliente_id,
            activo=activo,
            codigo=codigo,
        )
        return _build_list(CuponType, data)

    def resolve_cupon(self, info, cupon_id):
        data = loyalty_client.get_cupon(cupon_id)
        return _build(CuponType, data)

    def resolve_validar_cupon(self, info, codigo):
        data = loyalty_client.validar_cupon(codigo)
        return _build(CuponType, data)

    def resolve_catalogo_platos(self, info, activo=None, categoria_id=None):
        data = loyalty_client.get_catalogo_platos(
            activo=activo, categoria_id=categoria_id
        )
        return _build_list(CatalogoPlatoType, data)

    def resolve_catalogo_categorias(self, info, activo=None):
        data = loyalty_client.get_catalogo_categorias(activo=activo)
        return _build_list(CatalogoCategoriaType, data)

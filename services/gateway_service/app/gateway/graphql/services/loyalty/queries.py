# gateway_service/app/gateway/graphql/services/loyalty/queries.py
# FIX: cupones ahora acepta restaurante_id para filtrar por restaurante
import graphene
from .types import (
    AplicacionPromocionType, CatalogoCategoriaType, CatalogoPlatoType,
    CuentaPuntosType, CuponType, PromocionListType, PromocionType,
    TransaccionPuntosType,
)
from ....client import loyalty_client


class LoyaltyQuery(graphene.ObjectType):

    puntos_cliente = graphene.Field(
        CuentaPuntosType,
        cliente_id=graphene.ID(required=True),
        description="Saldo de puntos — resuelve desde Redis si hay caché",
    )

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

    # FIX: agrega restaurante_id para filtrar cupones por restaurante
    cupones = graphene.List(
        CuponType,
        cliente_id=graphene.ID(),
        activo=graphene.Boolean(),
        codigo=graphene.String(),
        restaurante_id=graphene.ID(
            description="Filtra cupones de un restaurante específico. Omitir = todos (admin)."
        ),
    )
    cupon = graphene.Field(CuponType, cupon_id=graphene.ID(required=True))
    validar_cupon = graphene.Field(
        CuponType,
        codigo=graphene.String(required=True),
        description="Valida cupón por código. Retorna null si no existe o no está disponible.",
    )

    catalogo_platos = graphene.List(
        CatalogoPlatoType,
        activo=graphene.Boolean(),
        categoria_id=graphene.ID(),
    )
    catalogo_categorias = graphene.List(
        CatalogoCategoriaType,
        activo=graphene.Boolean(),
    )

    # ── Resolvers ─────────────────────────────────────────────────────────

    def resolve_puntos_cliente(self, info, cliente_id):
        data = loyalty_client.get_puntos(cliente_id)
        if not data:
            return None
        if "_cache" in data:
            data["cache"] = data.pop("_cache")
        return data

    def resolve_transacciones_puntos(self, info, cliente_id=None, pedido_id=None,
                                     tipo=None, fecha_desde=None, fecha_hasta=None):
        return loyalty_client.get_transacciones(
            cliente_id=cliente_id, tipo=tipo, pedido_id=pedido_id,
            fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        ) or []

    def resolve_transaccion_puntos(self, info, transaccion_id):
        return loyalty_client.get_transaccion(transaccion_id)

    def resolve_promociones(self, info, activa=None, alcance=None,
                            restaurante_id=None, tipo_beneficio=None):
        return loyalty_client.get_promociones(
            activa=activa, alcance=alcance,
            restaurante_id=restaurante_id,
            tipo_beneficio=tipo_beneficio,
        ) or []

    def resolve_promocion(self, info, promocion_id):
        return loyalty_client.get_promocion(promocion_id)

    def resolve_cupones(self, info, cliente_id=None, activo=None,
                        codigo=None, restaurante_id=None):
        # FIX: pasa restaurante_id al cliente para filtrar
        return loyalty_client.get_cupones(
            cliente_id=cliente_id, activo=activo,
            codigo=codigo, restaurante_id=restaurante_id,
        ) or []

    def resolve_cupon(self, info, cupon_id):
        return loyalty_client.get_cupon(cupon_id)

    def resolve_validar_cupon(self, info, codigo):
        data = loyalty_client.validar_cupon(codigo)
        if not data:
            return None
        if "cupon" in data:
            return data["cupon"]
        if "detail" in data and "codigo" not in data:
            return None
        return data

    def resolve_catalogo_platos(self, info, activo=None, categoria_id=None):
        return loyalty_client.get_catalogo_platos(
            activo=activo, categoria_id=categoria_id
        ) or []

    def resolve_catalogo_categorias(self, info, activo=None):
        return loyalty_client.get_catalogo_categorias(activo=activo) or []

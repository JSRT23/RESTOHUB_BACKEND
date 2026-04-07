# gateway_service/app/gateway/graphql/services/loyalty/queries.py
import graphene
from .types import (
    AplicacionPromocionType, CatalogoCategoriaType, CatalogoPlatoType,
    CuentaPuntosType, CuponType, PromocionListType, PromocionType,
    TransaccionPuntosType,
)
from ....client import loyalty_client


class LoyaltyQuery(graphene.ObjectType):

    # Puntos
    puntos_cliente = graphene.Field(
        CuentaPuntosType,
        cliente_id=graphene.ID(required=True),
        description="Saldo de puntos — resuelve desde Redis si hay caché",
    )

    # Transacciones
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

    # Promociones
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

    # Cupones
    cupones = graphene.List(
        CuponType,
        cliente_id=graphene.ID(),
        activo=graphene.Boolean(),
        codigo=graphene.String(),
    )
    cupon = graphene.Field(CuponType, cupon_id=graphene.ID(required=True))
    validar_cupon = graphene.Field(
        CuponType,
        codigo=graphene.String(required=True),
        description="Valida cupón por código. Retorna null si no existe o no está disponible.",
    )

    # Catálogo
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
        # El endpoint retorna _cache (con underscore) → renombrar a cache
        if "_cache" in data:
            data["cache"] = data.pop("_cache")
        return data  # ✅ dict crudo

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
        # PromocionType tiene resolve_reglas que extrae root.get("reglas", [])
        # No hay que hacer nada especial — retornamos el dict crudo completo
        # ✅ dict crudo con reglas incluidas
        return loyalty_client.get_promocion(promocion_id)

    def resolve_cupones(self, info, cliente_id=None, activo=None, codigo=None):
        return loyalty_client.get_cupones(
            cliente_id=cliente_id, activo=activo, codigo=codigo
        ) or []

    def resolve_cupon(self, info, cupon_id):
        return loyalty_client.get_cupon(cupon_id)

    def resolve_validar_cupon(self, info, codigo):
        data = loyalty_client.validar_cupon(codigo)
        if not data:
            return None
        # El endpoint retorna el cupon directamente cuando está disponible
        # o {"detail": "...", "cupon": {...}} cuando no lo está
        if "cupon" in data:
            return data["cupon"]  # no disponible pero existe
        if "detail" in data and "codigo" not in data:
            return None  # no encontrado
        return data  # disponible — es el cupon directamente

    def resolve_catalogo_platos(self, info, activo=None, categoria_id=None):
        return loyalty_client.get_catalogo_platos(
            activo=activo, categoria_id=categoria_id
        ) or []

    def resolve_catalogo_categorias(self, info, activo=None):
        return loyalty_client.get_catalogo_categorias(activo=activo) or []

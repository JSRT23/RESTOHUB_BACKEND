# gateway_service/app/gateway/graphql/services/loyalty/mutations.py
import graphene
from .types import (
    AplicacionPromocionType, CuentaPuntosType,
    CuponType, PromocionType, TransaccionPuntosType,
)
from ....client import loyalty_client


def _add_tz(value: str) -> str:
    if not value:
        return value
    if value.endswith("Z") or "+" in value[10:]:
        return value
    if "T" not in value:
        return value + "T00:00:00Z"
    return value + "Z"


# ─────────────────────────────────────────
# PUNTOS
# ─────────────────────────────────────────

class AcumularPuntos(graphene.Mutation):
    class Arguments:
        cliente_id = graphene.ID(required=True)
        puntos = graphene.Int(required=True)
        pedido_id = graphene.ID()
        restaurante_id = graphene.ID()
        descripcion = graphene.String()

    cuenta = graphene.Field(CuentaPuntosType)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, cliente_id, puntos, **kwargs):
        payload = {"cliente_id": str(cliente_id), "puntos": puntos}
        payload.update({k: v for k, v in kwargs.items() if v is not None})
        result = loyalty_client.acumular_puntos(payload)
        if not result:
            return AcumularPuntos(ok=False, error="Error al acumular puntos.")
        return AcumularPuntos(ok=True, cuenta=result)


class CanjearPuntos(graphene.Mutation):
    class Arguments:
        cliente_id = graphene.ID(required=True)
        puntos = graphene.Int(required=True)
        pedido_id = graphene.ID()
        descripcion = graphene.String()

    cuenta = graphene.Field(CuentaPuntosType)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, cliente_id, puntos, **kwargs):
        payload = {"cliente_id": str(cliente_id), "puntos": puntos}
        payload.update({k: v for k, v in kwargs.items() if v is not None})
        result = loyalty_client.canjear_puntos(payload)
        if not result:
            return CanjearPuntos(ok=False, error="Saldo insuficiente o error al canjear.")
        return CanjearPuntos(ok=True, cuenta=result)


# ─────────────────────────────────────────
# PROMOCIONES
# ─────────────────────────────────────────

class CrearPromocion(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        descripcion = graphene.String()
        alcance = graphene.String(required=True)
        marca = graphene.String()
        restaurante_id = graphene.ID()
        tipo_beneficio = graphene.String(required=True)
        valor = graphene.Float()
        puntos_bonus = graphene.Int()
        multiplicador_puntos = graphene.Float()
        fecha_inicio = graphene.String(required=True)
        fecha_fin = graphene.String(required=True)

    promocion = graphene.Field(PromocionType)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, **kwargs):
        if "restaurante_id" in kwargs and not kwargs["restaurante_id"]:
            kwargs.pop("restaurante_id")
        if "fecha_inicio" in kwargs:
            kwargs["fecha_inicio"] = _add_tz(kwargs["fecha_inicio"])
        if "fecha_fin" in kwargs:
            kwargs["fecha_fin"] = _add_tz(kwargs["fecha_fin"])
        payload = {k: v for k, v in kwargs.items() if v is not None}
        result = loyalty_client.crear_promocion(payload)
        if not result:
            return CrearPromocion(ok=False, error="Error al crear la promoción.")
        return CrearPromocion(ok=True, promocion=result)


class EditarPromocion(graphene.Mutation):
    class Arguments:
        promocion_id = graphene.ID(required=True)
        nombre = graphene.String()
        descripcion = graphene.String()
        valor = graphene.Float()
        puntos_bonus = graphene.Int()
        multiplicador_puntos = graphene.Float()
        fecha_inicio = graphene.String()
        fecha_fin = graphene.String()

    promocion = graphene.Field(PromocionType)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, promocion_id, **kwargs):
        if "fecha_inicio" in kwargs and kwargs["fecha_inicio"]:
            kwargs["fecha_inicio"] = _add_tz(kwargs["fecha_inicio"])
        if "fecha_fin" in kwargs and kwargs["fecha_fin"]:
            kwargs["fecha_fin"] = _add_tz(kwargs["fecha_fin"])
        payload = {k: v for k, v in kwargs.items() if v is not None}
        result = loyalty_client.editar_promocion(promocion_id, payload)
        if not result:
            return EditarPromocion(ok=False, error="Error al editar la promoción.")
        return EditarPromocion(ok=True, promocion=result)


class ActivarPromocion(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    promocion = graphene.Field(PromocionType)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        result = loyalty_client.activar_promocion(id)
        if not result:
            return ActivarPromocion(ok=False, error="Error al activar la promoción.")
        return ActivarPromocion(ok=True, promocion=result)


class DesactivarPromocion(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    promocion = graphene.Field(PromocionType)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        result = loyalty_client.desactivar_promocion(id)
        if not result:
            return DesactivarPromocion(ok=False, error="Error al desactivar la promoción.")
        return DesactivarPromocion(ok=True, promocion=result)


class EvaluarPromocion(graphene.Mutation):
    class Arguments:
        pedido_id = graphene.ID(required=True)
        cliente_id = graphene.ID(required=True)
        restaurante_id = graphene.ID(required=True)
        total = graphene.Float(required=True)
        detalles = graphene.List(graphene.JSONString)

    aplicacion = graphene.Field(AplicacionPromocionType)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, pedido_id, cliente_id, restaurante_id, total, detalles=None):
        payload = {
            "pedido_id":      str(pedido_id),
            "cliente_id":     str(cliente_id),
            "restaurante_id": str(restaurante_id),
            "total":          total,
            "detalles":       detalles or [],
        }
        result = loyalty_client.evaluar_promocion(payload)
        if not result:
            return EvaluarPromocion(ok=False, error="Error al evaluar promoción.")
        if "detail" in result and "id" not in result:
            return EvaluarPromocion(ok=True, aplicacion=None)
        return EvaluarPromocion(ok=True, aplicacion=result)


# ─────────────────────────────────────────
# CUPONES
# ─────────────────────────────────────────

class CrearCupon(graphene.Mutation):
    class Arguments:
        cliente_id = graphene.ID()
        promocion_id = graphene.ID()
        # FIX: restaurante_id agregado — sin esto el payload no llega al loyalty_service
        # null = cupón global (admin), valor = cupón del restaurante (gerente)
        restaurante_id = graphene.ID()
        tipo_descuento = graphene.String(required=True)
        valor_descuento = graphene.Float(required=True)
        limite_uso = graphene.Int()
        fecha_inicio = graphene.String(required=True)
        fecha_fin = graphene.String(required=True)
        codigo = graphene.String()

    cupon = graphene.Field(CuponType)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, **kwargs):
        # promocion_id → promocion (FK en el serializer de loyalty_service)
        if "promocion_id" in kwargs:
            kwargs["promocion"] = kwargs.pop("promocion_id")

        # restaurante_id: si viene None o vacío, no incluir (cupón global)
        if "restaurante_id" in kwargs and not kwargs["restaurante_id"]:
            kwargs.pop("restaurante_id")

        # Cupon.fecha_inicio / fecha_fin son DateField → solo YYYY-MM-DD
        # El frontend puede mandar datetime completo (ISO) → truncar a fecha
        if "fecha_inicio" in kwargs and kwargs["fecha_inicio"]:
            kwargs["fecha_inicio"] = kwargs["fecha_inicio"][:10]
        if "fecha_fin" in kwargs and kwargs["fecha_fin"]:
            kwargs["fecha_fin"] = kwargs["fecha_fin"][:10]

        payload = {k: v for k, v in kwargs.items() if v is not None}
        result = loyalty_client.crear_cupon(payload)
        if not result:
            return CrearCupon(ok=False, error="Error al generar el cupón.")
        return CrearCupon(ok=True, cupon=result)


class CanjearCupon(graphene.Mutation):
    class Arguments:
        # FIX: usar "id" (no cupon_id) para que GraphQL lo exponga como "id"
        # y coincida con lo que manda el frontend: canjearCupon(id: $id, ...)
        id = graphene.ID(required=True)
        pedido_id = graphene.ID()

    cupon = graphene.Field(CuponType)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id, pedido_id=None):
        result = loyalty_client.canjear_cupon(
            id,
            pedido_id=str(pedido_id) if pedido_id else None,
        )
        if not result:
            return CanjearCupon(ok=False, error="Cupón no disponible o error al canjear.")
        return CanjearCupon(ok=True, cupon=result)


# ─────────────────────────────────────────
# REGISTRO
# ─────────────────────────────────────────

class LoyaltyMutation(graphene.ObjectType):
    acumular_puntos = AcumularPuntos.Field()
    canjear_puntos = CanjearPuntos.Field()
    crear_promocion = CrearPromocion.Field()
    editar_promocion = EditarPromocion.Field()
    activar_promocion = ActivarPromocion.Field()
    desactivar_promocion = DesactivarPromocion.Field()
    evaluar_promocion = EvaluarPromocion.Field()
    crear_cupon = CrearCupon.Field()
    canjear_cupon = CanjearCupon.Field()

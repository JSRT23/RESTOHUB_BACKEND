# gateway_service/app/gateway/graphql/services/loyalty/mutations.py
import graphene
from .types import (
    AplicacionPromocionType, CuentaPuntosType,
    CuponType, PromocionType, TransaccionPuntosType,
)
from ....client import loyalty_client


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
    errores = graphene.String()

    def mutate(self, info, cliente_id, puntos, **kwargs):
        payload = {"cliente_id": str(cliente_id), "puntos": puntos}
        payload.update({k: v for k, v in kwargs.items() if v is not None})
        result = loyalty_client.acumular_puntos(payload)
        if not result:
            return AcumularPuntos(ok=False, errores="Error al acumular puntos.")
        return AcumularPuntos(ok=True, cuenta=result)


class CanjearPuntos(graphene.Mutation):
    class Arguments:
        cliente_id = graphene.ID(required=True)
        puntos = graphene.Int(required=True)
        pedido_id = graphene.ID()
        descripcion = graphene.String()

    cuenta = graphene.Field(CuentaPuntosType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, cliente_id, puntos, **kwargs):
        payload = {"cliente_id": str(cliente_id), "puntos": puntos}
        payload.update({k: v for k, v in kwargs.items() if v is not None})
        result = loyalty_client.canjear_puntos(payload)
        if not result:
            return CanjearPuntos(ok=False, errores="Saldo insuficiente o error al canjear.")
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
    errores = graphene.String()

    def mutate(self, info, **kwargs):
        result = loyalty_client.crear_promocion(kwargs)
        if not result:
            return CrearPromocion(ok=False, errores="Error al crear la promoción.")
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
    errores = graphene.String()

    def mutate(self, info, promocion_id, **kwargs):
        payload = {k: v for k, v in kwargs.items() if v is not None}
        result = loyalty_client.editar_promocion(promocion_id, payload)
        if not result:
            return EditarPromocion(ok=False, errores="Error al editar la promoción.")
        return EditarPromocion(ok=True, promocion=result)


class ActivarPromocion(graphene.Mutation):
    class Arguments:
        promocion_id = graphene.ID(required=True)

    promocion = graphene.Field(PromocionType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, promocion_id):
        result = loyalty_client.activar_promocion(promocion_id)
        if not result:
            return ActivarPromocion(ok=False, errores="Error al activar la promoción.")
        return ActivarPromocion(ok=True, promocion=result)


class DesactivarPromocion(graphene.Mutation):
    class Arguments:
        promocion_id = graphene.ID(required=True)

    promocion = graphene.Field(PromocionType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, promocion_id):
        result = loyalty_client.desactivar_promocion(promocion_id)
        if not result:
            return DesactivarPromocion(ok=False, errores="Error al desactivar la promoción.")
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
    errores = graphene.String()

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
            return EvaluarPromocion(ok=False, errores="Error al evaluar promoción.")
        # 200 = ninguna aplica (retorna {"detail": "..."})
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
        tipo_descuento = graphene.String(required=True)
        valor_descuento = graphene.Float(required=True)
        limite_uso = graphene.Int()
        fecha_inicio = graphene.String(required=True)
        fecha_fin = graphene.String(required=True)
        codigo = graphene.String()

    cupon = graphene.Field(CuponType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, **kwargs):
        # El serializer espera "promocion" (FK), no "promocion_id"
        if "promocion_id" in kwargs:
            kwargs["promocion"] = kwargs.pop("promocion_id")
        payload = {k: v for k, v in kwargs.items() if v is not None}
        result = loyalty_client.crear_cupon(payload)
        if not result:
            return CrearCupon(ok=False, errores="Error al generar el cupón.")
        return CrearCupon(ok=True, cupon=result)


class CanjearCupon(graphene.Mutation):
    class Arguments:
        cupon_id = graphene.ID(required=True)
        pedido_id = graphene.ID()

    cupon = graphene.Field(CuponType)
    ok = graphene.Boolean()
    errores = graphene.String()

    def mutate(self, info, cupon_id, pedido_id=None):
        result = loyalty_client.canjear_cupon(
            cupon_id,
            pedido_id=str(pedido_id) if pedido_id else None,
        )
        if not result:
            return CanjearCupon(ok=False, errores="Cupón no disponible o error al canjear.")
        return CanjearCupon(ok=True, cupon=result)


# ─────────────────────────────────────────
# REGISTRO
# ─────────────────────────────────────────

class LoyaltyMutation(graphene.ObjectType):
    # Puntos
    acumular_puntos = AcumularPuntos.Field()
    canjear_puntos = CanjearPuntos.Field()

    # Promociones
    crear_promocion = CrearPromocion.Field()
    editar_promocion = EditarPromocion.Field()
    activar_promocion = ActivarPromocion.Field()
    desactivar_promocion = DesactivarPromocion.Field()
    evaluar_promocion = EvaluarPromocion.Field()

    # Cupones
    crear_cupon = CrearCupon.Field()
    canjear_cupon = CanjearCupon.Field()

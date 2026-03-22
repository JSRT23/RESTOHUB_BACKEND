import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from app.loyalty.events.event_types import LoyaltyEvents
from app.loyalty.models import (
    AplicacionPromocion,
    CuentaPuntos,
    Cupon,
    TransaccionPuntos,
)
from app.loyalty.services.rabbitmq import publish_event

logger = logging.getLogger(__name__)


def _sid(value):
    return str(value) if value is not None else None


# ---------------------------------------------------------------------------
# CuentaPuntos
# Se publica cuando cambia el saldo — update_fields=["saldo", "nivel", ...]
# No se publica en created porque el saldo arranca en 0 sin movimiento real.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=CuentaPuntos)
def cuenta_puntos_saved(sender, instance, created, update_fields, **kwargs):
    if created:
        return  # Cuenta nueva sin puntos — no hay nada que publicar

    # Solo reaccionar cuando se actualiza el saldo explícitamente
    if not update_fields or "saldo" not in update_fields:
        return

    # El tipo de publicación lo determina la última transacción
    # (acumulacion → PUNTOS_ACUMULADOS, canje → PUNTOS_CANJEADOS)
    # Los signals de TransaccionPuntos son los que publican el evento
    # correcto con el contexto completo del movimiento.
    # Este signal solo actúa como respaldo si el saldo cambia sin transacción.
    logger.debug(
        "[loyalty_signals] Saldo actualizado — cliente %s: %d pts",
        instance.cliente_id, instance.saldo,
    )


# ---------------------------------------------------------------------------
# TransaccionPuntos
# Publica el evento correcto según el tipo de transacción.
# Solo en created=True — las transacciones son inmutables.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=TransaccionPuntos)
def transaccion_puntos_saved(sender, instance, created, update_fields, **kwargs):
    if not created:
        return

    cuenta = instance.cuenta

    if instance.tipo in ("acumulacion", "bono"):
        publish_event(LoyaltyEvents.PUNTOS_ACUMULADOS, {
            "cuenta_id":        _sid(cuenta.id),
            "cliente_id":       _sid(cuenta.cliente_id),
            "puntos_acumulados": instance.puntos,
            "saldo_nuevo":      instance.saldo_posterior,
            "nivel":            cuenta.nivel,
            "pedido_id":        _sid(instance.pedido_id),
            "restaurante_id":   _sid(instance.restaurante_id),
        })

    elif instance.tipo == "canje":
        publish_event(LoyaltyEvents.PUNTOS_CANJEADOS, {
            "cuenta_id":       _sid(cuenta.id),
            "cliente_id":      _sid(cuenta.cliente_id),
            "puntos_canjeados": abs(instance.puntos),
            "saldo_nuevo":     instance.saldo_posterior,
            "pedido_id":       _sid(instance.pedido_id),
        })


# ---------------------------------------------------------------------------
# AplicacionPromocion
# Se publica al crearse — order_service lo consume para aplicar
# el descuento al pedido antes de confirmarlo.
# Solo en created=True — idempotencia garantizada por pedido_id unique.
# ---------------------------------------------------------------------------

@receiver(post_save, sender=AplicacionPromocion)
def aplicacion_promocion_saved(sender, instance, created, update_fields, **kwargs):
    if not created:
        return

    promocion = instance.promocion

    publish_event(LoyaltyEvents.PROMOCION_APLICADA, {
        "promocion_id":        _sid(promocion.id),
        "nombre_promocion":    promocion.nombre,
        "tipo_beneficio":      promocion.tipo_beneficio,
        "pedido_id":           _sid(instance.pedido_id),
        "cliente_id":          _sid(instance.cliente_id),
        "descuento":           str(instance.descuento_aplicado),
        "tipo_descuento":      (
            "porcentaje"
            if promocion.tipo_beneficio == "descuento_pct"
            else "absoluto"
        ),
        "puntos_bonus":        instance.puntos_bonus_otorgados,
    })


# ---------------------------------------------------------------------------
# Cupon
# CUPON_GENERADO al crear.
# CUPON_CANJEADO cuando usos_actuales aumenta (update_fields=["usos_actuales"]).
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Cupon)
def cupon_saved(sender, instance, created, update_fields, **kwargs):

    # — Generado —
    if created:
        publish_event(LoyaltyEvents.CUPON_GENERADO, {
            "cupon_id":       _sid(instance.id),
            "codigo":         instance.codigo,
            "cliente_id":     _sid(instance.cliente_id),
            "tipo_descuento": instance.tipo_descuento,
            "valor_descuento": str(instance.valor_descuento),
            "fecha_inicio":   str(instance.fecha_inicio),
            "fecha_fin":      str(instance.fecha_fin),
        })
        return

    # — Canjeado: update_fields=["usos_actuales", "activo"] —
    if update_fields and "usos_actuales" in update_fields:
        publish_event(LoyaltyEvents.CUPON_CANJEADO, {
            "cupon_id":       _sid(instance.id),
            "codigo":         instance.codigo,
            "cliente_id":     _sid(instance.cliente_id),
            "tipo_descuento": instance.tipo_descuento,
            "valor_descuento": str(instance.valor_descuento),
        })

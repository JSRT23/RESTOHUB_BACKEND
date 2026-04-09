# loyalty_service/app/loyalty/signals.py
"""
Signals de loyalty_service.

CORRECCIONES:
1. publish_cupon_event: solo publicaba cuando usos_actuales >= limite_uso
   (cupón agotado). Si limite_uso=5 y se canjea el 3ro, nunca publicaba.
   Fix: publicar en CADA canje (usos_actuales > 0 y not created),
   usando el evento cupon.canjeado. El evento cupon.agotado es adicional.

2. Se agrega SERVICE_NAME a INSTALLED_APPS en settings:
   'app.loyalty' → 'app.loyalty.apps.LoyaltyConfig' para que ready() cargue signals.
   (ver nota en settings.py)
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from app.loyalty.infrastructure.messaging.publisher import get_publisher
from app.loyalty.events.builders import LoyaltyEventBuilder
from app.loyalty.models import Cupon, TransaccionPuntos, TipoTransaccion

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# 🎟️ CUPONES
# ─────────────────────────────────────────

@receiver(post_save, sender=Cupon)
def publish_cupon_event(sender, instance: Cupon, created: bool, **kwargs):
    """
    Publica cupon.canjeado en cada canje (usos_actuales aumentó).
    Publica cupon.agotado adicional cuando se agota el límite.
    ✅ Fix: antes solo publicaba al agotar (usos >= limite).
    """
    if created:
        return

    # Detectar si hubo un canje — usos_actuales > 0 indica al menos un canje
    # (no tenemos el valor anterior, pero el ViewSet solo llama save() en canje)
    if instance.usos_actuales <= 0:
        return

    try:
        publisher = get_publisher()

        # ✅ Siempre publicar cupon.canjeado en cada save post-creación
        publisher.publish(
            "app.loyalty.cupon.canjeado",
            LoyaltyEventBuilder.cupon_canjeado(instance),
        )
        logger.info(
            f"📤 Cupón canjeado → {instance.codigo} ({instance.usos_actuales}/{instance.limite_uso})")

        # Adicionalmente publicar cupon.agotado si se agotó
        if instance.usos_actuales >= instance.limite_uso:
            publisher.publish(
                "app.loyalty.cupon.agotado",
                LoyaltyEventBuilder.cupon_canjeado(instance),
            )
            logger.info(f"📤 Cupón agotado → {instance.codigo}")

    except Exception:
        logger.exception("💥 Error publicando evento de cupón")


# ─────────────────────────────────────────
# ⭐ TRANSACCIONES — solo vencimientos
# ─────────────────────────────────────────

@receiver(post_save, sender=TransaccionPuntos)
def publish_transaccion_event(sender, instance: TransaccionPuntos, created: bool, **kwargs):
    """
    La acumulación (ACUMULACION) la publica order_handlers directamente.
    Aquí solo cubrimos VENCIMIENTO — generado por proceso batch externo.
    """
    if not created:
        return

    if instance.tipo != TipoTransaccion.VENCIMIENTO:
        return

    try:
        get_publisher().publish(
            "app.loyalty.puntos.vencidos",
            LoyaltyEventBuilder.puntos_vencidos(
                cuenta=instance.cuenta,
                puntos_vencidos=abs(instance.puntos),
            ),
        )
        logger.info(
            f"📤 Puntos vencidos → cliente {instance.cuenta.cliente_id}")
    except Exception:
        logger.exception("💥 Error publicando puntos.vencidos")

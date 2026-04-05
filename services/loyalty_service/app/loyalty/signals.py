# loyalty_service/app/loyalty/signals.py
"""
Signals de loyalty_service.

loyalty_service solo publica eventos cuando:
- Se canjea un cupón manualmente (desde la API)
- Se vence una cuenta de puntos (proceso batch)

La acumulación de puntos y aplicación de promociones
se publica directamente desde los handlers (order_handlers.py)
porque necesitan el contexto completo del pedido.
No se duplica aquí.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from app.loyalty.infrastructure.messaging.publisher import get_publisher
from app.loyalty.events.event_types import LoyaltyEvents
from app.loyalty.models import Cupon, TransaccionPuntos, TipoTransaccion

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# 🎟️ CUPONES — solo notificar canje
# ─────────────────────────────────────────

@receiver(post_save, sender=Cupon)
def publish_cupon_event(sender, instance: Cupon, created: bool, **kwargs):
    """
    No publicamos creación de cupones — es operación interna.
    Solo notificamos cuando usos_actuales aumenta (canje real).
    """
    if created:
        return

    # Detectar canje: usos_actuales llegó al límite o aumentó
    # Django no trackea el valor anterior automáticamente,
    # así que publicamos solo si el cupón quedó agotado
    if instance.usos_actuales >= instance.limite_uso:
        try:
            get_publisher().publish(
                "app.loyalty.cupon.agotado",
                {
                    "cupon_id":    str(instance.id),
                    "codigo":      instance.codigo,
                    "cliente_id":  str(instance.cliente_id) if instance.cliente_id else None,
                    "usos":        instance.usos_actuales,
                    "limite":      instance.limite_uso,
                }
            )
            logger.info(f"📤 Cupón agotado → {instance.codigo}")
        except Exception:
            logger.exception("💥 Error publicando cupon.agotado")


# ─────────────────────────────────────────
# ⭐ TRANSACCIONES — solo vencimientos
# ─────────────────────────────────────────

@receiver(post_save, sender=TransaccionPuntos)
def publish_transaccion_event(sender, instance: TransaccionPuntos, created: bool, **kwargs):
    """
    La acumulación (ACUMULACION) la publica order_handlers directamente.
    Aquí solo cubrimos VENCIMIENTO — generado por un proceso batch externo.
    """
    if not created:
        return

    if instance.tipo != TipoTransaccion.VENCIMIENTO:
        return

    try:
        get_publisher().publish(
            "app.loyalty.puntos.vencidos",
            {
                "cliente_id":      str(instance.cuenta.cliente_id),
                "puntos_vencidos": abs(instance.puntos),
                "saldo_nuevo":     instance.saldo_posterior,
            }
        )
        logger.info(
            f"📤 Puntos vencidos → cliente {instance.cuenta.cliente_id}")
    except Exception:
        logger.exception("💥 Error publicando puntos.vencidos")

# loyalty_service/app/loyalty/application/event_handlers/order_handlers.py
"""
Handlers de eventos del order_service para loyalty_service.

CORRECCIONES:
1. nivel_anterior se capturaba DESPUÉS de actualizar_nivel() → siempre igual al nuevo.
   Fix: capturar nivel_anterior ANTES de llamar actualizar_nivel().

2. _evaluar_promociones: AplicacionPromocion.pedido_id es unique=True pero
   el loop intentaba crear una por cada promoción → IntegrityError en la 2da.
   Fix: el loop aplica solo la PRIMERA promoción que cumple reglas (break).
   Una promoción por pedido es el comportamiento correcto de negocio.

3. Comparación de restaurante_id como string vs UUID — estandarizado a str().
"""
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

PUNTOS_POR_UNIDAD = 1  # 1 punto por cada unidad de moneda


# ─────────────────────────────────────────
# HELPER: evaluar y aplicar UNA promoción
# ─────────────────────────────────────────

def _evaluar_promociones(pedido_id: str, cliente_id: UUID, restaurante_id: UUID, data: dict):
    """
    Revisa si alguna promoción activa aplica al pedido.
    Aplica solo la PRIMERA que cumple todas las reglas (prioridad: local > global).
    ✅ Fix: break después de aplicar — evita IntegrityError por unique pedido_id.
    """
    from django.utils import timezone
    from app.loyalty.models import (
        AplicacionPromocion,
        CuentaPuntos,
        Promocion,
        TransaccionPuntos,
        TipoTransaccion,
    )
    from app.loyalty.events.builders import LoyaltyEventBuilder
    from app.loyalty.events.event_types import LoyaltyEvents
    from app.loyalty.infrastructure.messaging.publisher import get_publisher

    ahora = timezone.now()
    total = data.get("total", 0)
    detalles = data.get("detalles", [])
    plato_ids = {str(d["plato_id"]) for d in detalles if d.get("plato_id")}

    from django.db.models import Q
    promociones = Promocion.objects.filter(
        activa=True,
        fecha_inicio__lte=ahora,
        fecha_fin__gte=ahora,
    ).filter(
        Q(alcance="global") |
        Q(alcance="local", restaurante_id=restaurante_id)
    ).prefetch_related("reglas").order_by(
        # Prioridad: local primero, luego global
        "-alcance"
    )

    publisher = get_publisher()

    for promo in promociones:
        # Idempotencia — no aplicar dos veces la misma promo al mismo pedido
        if AplicacionPromocion.objects.filter(
            promocion=promo, pedido_id=UUID(pedido_id)
        ).exists():
            continue

        # Evaluar reglas (todas deben cumplirse — AND)
        if not _cumple_reglas(promo, total, plato_ids, ahora, cliente_id):
            continue

        # Calcular beneficio
        descuento = 0
        puntos_bonus = 0

        if promo.tipo_beneficio == "descuento_pct":
            descuento = float(total) * float(promo.valor) / 100
        elif promo.tipo_beneficio == "descuento_monto":
            descuento = float(promo.valor)
        elif promo.tipo_beneficio == "puntos_extra":
            puntos_bonus = promo.puntos_bonus

        aplicacion = AplicacionPromocion.objects.create(
            promocion=promo,
            pedido_id=UUID(pedido_id),
            cliente_id=cliente_id,
            descuento_aplicado=descuento,
            puntos_bonus_otorgados=puntos_bonus,
        )

        # Acreditar puntos bonus si aplica
        if puntos_bonus > 0:
            try:
                cuenta = CuentaPuntos.objects.get(cliente_id=cliente_id)
                saldo_antes = cuenta.saldo
                cuenta.saldo += puntos_bonus
                cuenta.puntos_totales_historicos += puntos_bonus
                cuenta.actualizar_nivel()
                cuenta.save(update_fields=[
                            "saldo", "puntos_totales_historicos", "nivel"])

                TransaccionPuntos.objects.create(
                    cuenta=cuenta,
                    tipo=TipoTransaccion.BONO,
                    puntos=puntos_bonus,
                    saldo_anterior=saldo_antes,
                    saldo_posterior=cuenta.saldo,
                    pedido_id=UUID(pedido_id),
                    restaurante_id=restaurante_id,
                    promocion_id=promo.id,
                    descripcion=f"Bonus promoción: {promo.nombre}",
                )
            except CuentaPuntos.DoesNotExist:
                pass

        publisher.publish(
            LoyaltyEvents.PROMOCION_APLICADA,
            LoyaltyEventBuilder.promocion_aplicada(aplicacion),
        )

        logger.info(
            f"🎁 Promoción aplicada → {promo.nombre} | pedido {pedido_id}")
        # ✅ Solo una promoción por pedido — evita IntegrityError unique(pedido_id)
        break


def _cumple_reglas(promo, total, plato_ids: set, ahora, cliente_id: UUID) -> bool:
    """Evalúa todas las reglas de una promoción. Devuelve True si todas se cumplen."""
    from app.loyalty.models import TransaccionPuntos, TipoTransaccion

    for regla in promo.reglas.all():
        if regla.tipo_condicion == "monto_minimo":
            if float(total) < float(regla.monto_minimo or 0):
                return False

        elif regla.tipo_condicion == "plato":
            if str(regla.plato_id) not in plato_ids:
                return False

        elif regla.tipo_condicion == "hora":
            if regla.hora_inicio is None or regla.hora_fin is None:
                return False
            if not (regla.hora_inicio <= ahora.hour < regla.hora_fin):
                return False

        elif regla.tipo_condicion == "primer_pedido":
            ya_tiene = TransaccionPuntos.objects.filter(
                cuenta__cliente_id=cliente_id,
                tipo=TipoTransaccion.ACUMULACION,
            ).exists()
            if ya_tiene:
                return False

    return True


# ─────────────────────────────────────────
# HANDLERS PÚBLICOS
# ─────────────────────────────────────────

def handle_pedido_entregado(data: dict) -> None:
    """
    Acumula puntos al cliente cuando el pedido es entregado.
    ✅ Fix: nivel_anterior se captura ANTES de actualizar_nivel().
    """
    try:
        from django.db import transaction
        from app.loyalty.models import (
            CuentaPuntos,
            TransaccionPuntos,
            TipoTransaccion,
        )
        from app.loyalty.events.builders import LoyaltyEventBuilder
        from app.loyalty.events.event_types import LoyaltyEvents
        from app.loyalty.infrastructure.messaging.publisher import get_publisher

        pedido_id = data.get("pedido_id")
        cliente_id_raw = data.get("cliente_id")
        restaurante_id = data.get("restaurante_id")
        total = data.get("total", 0)

        if not pedido_id or not restaurante_id:
            logger.warning("❌ pedido.entregado sin pedido_id o restaurante_id")
            return

        if not cliente_id_raw:
            logger.info(f"⏭️ Pedido anónimo — sin acumulación → {pedido_id}")
            return

        cliente_id = UUID(cliente_id_raw)

        # Idempotencia
        ya_procesado = TransaccionPuntos.objects.filter(
            pedido_id=UUID(pedido_id),
            tipo=TipoTransaccion.ACUMULACION,
        ).exists()

        if ya_procesado:
            logger.info(f"⏭️ Puntos ya acumulados → {pedido_id}")
            return

        puntos_ganados = max(1, int(float(total) * PUNTOS_POR_UNIDAD))

        with transaction.atomic():
            cuenta, _ = CuentaPuntos.objects.get_or_create(
                cliente_id=cliente_id,
                defaults={"saldo": 0, "puntos_totales_historicos": 0},
            )

            saldo_anterior = cuenta.saldo
            # ✅ CORREGIDO: capturar nivel_anterior ANTES de actualizar
            nivel_anterior = cuenta.nivel

            cuenta.saldo += puntos_ganados
            cuenta.puntos_totales_historicos += puntos_ganados
            cuenta.actualizar_nivel()  # modifica cuenta.nivel
            cuenta.save(update_fields=[
                        "saldo", "puntos_totales_historicos", "nivel"])

            TransaccionPuntos.objects.create(
                cuenta=cuenta,
                tipo=TipoTransaccion.ACUMULACION,
                puntos=puntos_ganados,
                saldo_anterior=saldo_anterior,
                saldo_posterior=cuenta.saldo,
                pedido_id=UUID(pedido_id),
                restaurante_id=UUID(restaurante_id),
                descripcion="Acumulación por pedido entregado",
            )

        logger.info(
            f"⭐ Puntos acumulados → cliente {cliente_id} | "
            f"+{puntos_ganados} pts | saldo: {cuenta.saldo}"
        )

        # nivel_anterior capturado antes → ahora sí refleja el cambio real
        get_publisher().publish(
            LoyaltyEvents.PUNTOS_ACUMULADOS,
            LoyaltyEventBuilder.puntos_acumulados(
                cuenta=cuenta,
                pedido_id=pedido_id,
                restaurante_id=str(restaurante_id),
                puntos_ganados=puntos_ganados,
                saldo_anterior=saldo_anterior,
                nivel_anterior=nivel_anterior,   # ✅ valor real pre-actualización
            ),
        )

        _evaluar_promociones(
            pedido_id=pedido_id,
            cliente_id=cliente_id,
            restaurante_id=UUID(restaurante_id),
            data=data,
        )

    except Exception:
        logger.exception("💥 Error en pedido.entregado (loyalty)")
        raise


def handle_pedido_cancelado(data: dict) -> None:
    """
    Revierte los puntos si el pedido había sido acreditado.
    """
    try:
        from django.db import transaction
        from app.loyalty.models import (
            CuentaPuntos,
            TransaccionPuntos,
            TipoTransaccion,
        )

        pedido_id = data.get("pedido_id")
        cliente_id_raw = data.get("cliente_id")

        if not pedido_id or not cliente_id_raw:
            return

        cliente_id = UUID(cliente_id_raw)

        try:
            tx_original = TransaccionPuntos.objects.get(
                pedido_id=UUID(pedido_id),
                tipo=TipoTransaccion.ACUMULACION,
            )
        except TransaccionPuntos.DoesNotExist:
            logger.info(f"⏭️ Sin puntos para revertir → {pedido_id}")
            return

        ya_revertido = TransaccionPuntos.objects.filter(
            pedido_id=UUID(pedido_id),
            tipo=TipoTransaccion.AJUSTE,
        ).exists()

        if ya_revertido:
            logger.info(f"⏭️ Puntos ya revertidos → {pedido_id}")
            return

        puntos_a_revertir = tx_original.puntos

        with transaction.atomic():
            cuenta = CuentaPuntos.objects.select_for_update().get(cliente_id=cliente_id)
            saldo_anterior = cuenta.saldo
            cuenta.saldo = max(0, cuenta.saldo - puntos_a_revertir)
            cuenta.save(update_fields=["saldo"])

            TransaccionPuntos.objects.create(
                cuenta=cuenta,
                tipo=TipoTransaccion.AJUSTE,
                puntos=-puntos_a_revertir,
                saldo_anterior=saldo_anterior,
                saldo_posterior=cuenta.saldo,
                pedido_id=UUID(pedido_id),
                descripcion="Reversión por pedido cancelado",
            )

        logger.info(
            f"↩️ Puntos revertidos → cliente {cliente_id} | "
            f"-{puntos_a_revertir} pts | saldo: {cuenta.saldo}"
        )

    except Exception:
        logger.exception("💥 Error en pedido.cancelado (loyalty)")
        raise

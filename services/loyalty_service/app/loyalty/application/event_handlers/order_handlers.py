# loyalty_service/app/loyalty/application/event_handlers/order_handlers.py
"""
Handlers de eventos del order_service para loyalty_service.

pedido.entregado → acumular puntos + evaluar promociones activas
pedido.cancelado → revertir puntos si el pedido fue acreditado
"""
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

# Puntos por unidad monetaria — configurable por settings si se quiere
PUNTOS_POR_UNIDAD = 1  # 1 punto por cada unidad de moneda


# ─────────────────────────────────────────
# HELPER: evaluar promociones
# ─────────────────────────────────────────

def _evaluar_promociones(pedido_id: str, cliente_id: UUID, restaurante_id: UUID, data: dict):
    """
    Revisa si alguna promoción activa aplica al pedido.
    Condiciones soportadas: monto_minimo, plato, categoria, hora, primer_pedido.
    """
    from django.utils import timezone
    from app.loyalty.models import (
        AplicacionPromocion,
        CuentaPuntos,
        Promocion,
        TransaccionPuntos,
        TipoTransaccion,
        AlcancePromocion,
    )
    from app.loyalty.events.builders import LoyaltyEventBuilder
    from app.loyalty.events.event_types import LoyaltyEvents
    from app.loyalty.infrastructure.messaging.publisher import get_publisher

    ahora = timezone.now()
    total = data.get("total", 0)
    detalles = data.get("detalles", [])
    plato_ids = {d["plato_id"] for d in detalles}

    # Promociones activas aplicables a este restaurante
    promociones = Promocion.objects.filter(
        activa=True,
        fecha_inicio__lte=ahora,
        fecha_fin__gte=ahora,
    ).filter(
        # Global, o específica de este restaurante
        alcance__in=[AlcancePromocion.GLOBAL, AlcancePromocion.LOCAL],
    ).prefetch_related("reglas")

    publisher = get_publisher()

    for promo in promociones:
        # Si es LOCAL verificar que sea para este restaurante
        if promo.alcance == AlcancePromocion.LOCAL:
            if str(promo.restaurante_id) != str(restaurante_id):
                continue

        # Idempotencia — no aplicar dos veces la misma promo al mismo pedido
        if AplicacionPromocion.objects.filter(
            promocion=promo, pedido_id=UUID(pedido_id)
        ).exists():
            continue

        # Evaluar reglas (todas deben cumplirse — AND)
        cumple = True
        for regla in promo.reglas.all():
            if regla.tipo_condicion == "monto_minimo":
                if float(total) < float(regla.monto_minimo or 0):
                    cumple = False
                    break

            elif regla.tipo_condicion == "plato":
                if str(regla.plato_id) not in plato_ids:
                    cumple = False
                    break

            elif regla.tipo_condicion == "hora":
                hora_actual = ahora.hour
                if not (regla.hora_inicio <= hora_actual < regla.hora_fin):
                    cumple = False
                    break

            elif regla.tipo_condicion == "primer_pedido":
                ya_tiene = TransaccionPuntos.objects.filter(
                    cuenta__cliente_id=cliente_id,
                    tipo=TipoTransaccion.ACUMULACION,
                ).exists()
                if ya_tiene:
                    cumple = False
                    break

        if not cumple:
            continue

        # ── Aplicar promoción ──────────────────────────────
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


# ─────────────────────────────────────────
# HANDLERS PÚBLICOS
# ─────────────────────────────────────────

def handle_pedido_entregado(data: dict) -> None:
    """
    Acumula puntos al cliente cuando el pedido es entregado.
    Regla: 1 punto por cada unidad de moneda del total.
    Luego evalúa si alguna promoción aplica.
    """
    try:
        from django.db import transaction
        from app.loyalty.models import (
            CuentaPuntos,
            TransaccionPuntos,
            TipoTransaccion,
            NivelCliente,
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

        # Pedidos anónimos (sin cliente) no acumulan puntos
        if not cliente_id_raw:
            logger.info(
                f"⏭️ Pedido anónimo — sin acumulación de puntos → {pedido_id}")
            return

        cliente_id = UUID(cliente_id_raw)

        # Idempotencia — verificar que no se procesó antes
        from app.loyalty.models import TransaccionPuntos as TP
        ya_procesado = TP.objects.filter(
            pedido_id=UUID(pedido_id),
            tipo=TipoTransaccion.ACUMULACION,
        ).exists()

        if ya_procesado:
            logger.info(f"⏭️ Puntos ya acumulados para pedido → {pedido_id}")
            return

        puntos_ganados = max(1, int(float(total) * PUNTOS_POR_UNIDAD))

        with transaction.atomic():
            # Crear o recuperar cuenta de puntos
            cuenta, _ = CuentaPuntos.objects.get_or_create(
                cliente_id=cliente_id,
                defaults={"saldo": 0, "puntos_totales_historicos": 0},
            )

            saldo_anterior = cuenta.saldo
            nivel_anterior = cuenta.nivel

            # Acumular
            cuenta.saldo += puntos_ganados
            cuenta.puntos_totales_historicos += puntos_ganados
            cuenta.actualizar_nivel()
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
                descripcion=f"Acumulación por pedido entregado",
            )

        logger.info(
            f"⭐ Puntos acumulados → cliente {cliente_id} | "
            f"+{puntos_ganados} pts | saldo: {cuenta.saldo}"
        )

        # Publicar evento
        get_publisher().publish(
            LoyaltyEvents.PUNTOS_ACUMULADOS,
            LoyaltyEventBuilder.puntos_acumulados(
                cuenta=cuenta,
                pedido_id=pedido_id,
                restaurante_id=str(restaurante_id),
                puntos_ganados=puntos_ganados,
                saldo_anterior=saldo_anterior,
                nivel_anterior=nivel_anterior,
            ),
        )

        # Evaluar promociones aplicables
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
    Solo revierte si existe una TransaccionPuntos de ACUMULACION para ese pedido.
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

        # Buscar acumulación previa para este pedido
        try:
            tx_original = TransaccionPuntos.objects.get(
                pedido_id=UUID(pedido_id),
                tipo=TipoTransaccion.ACUMULACION,
            )
        except TransaccionPuntos.DoesNotExist:
            logger.info(
                f"⏭️ Sin puntos previos para revertir → pedido {pedido_id}")
            return

        # Idempotencia — verificar que no se revirtió antes
        ya_revertido = TransaccionPuntos.objects.filter(
            pedido_id=UUID(pedido_id),
            tipo=TipoTransaccion.AJUSTE,
        ).exists()

        if ya_revertido:
            logger.info(f"⏭️ Puntos ya revertidos → pedido {pedido_id}")
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

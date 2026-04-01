# staff_service/app/staff/application/event_handlers/inventory_handlers.py
"""
Handlers de eventos del inventory_service.

staff_service recibe alertas de inventario y las persiste
como AlertaOperacional para que el gerente del local las vea
en su dashboard y pueda actuar (crear orden de compra, etc).
"""
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# HELPER INTERNO
# ─────────────────────────────────────────


def _crear_alerta(data: dict, tipo: str, nivel: str, mensaje: str) -> None:
    """Persiste una AlertaOperacional. Idempotente por referencia_id."""
    try:
        from app.staff.models import AlertaOperacional

        restaurante_id = data.get("restaurante_id")
        referencia_id = data.get("alerta_id") or data.get(
            "lote_id") or data.get("orden_id")

        if not restaurante_id:
            logger.warning(f"❌ {tipo} sin restaurante_id")
            return

        # Idempotencia: no duplicar alertas por el mismo evento
        if referencia_id:
            ya_existe = AlertaOperacional.objects.filter(
                referencia_id=referencia_id,
                tipo=tipo,
            ).exists()
            if ya_existe:
                logger.info(f"⏭️ Alerta ya registrada → {referencia_id}")
                return

        AlertaOperacional.objects.create(
            restaurante_id=restaurante_id,
            tipo=tipo,
            nivel=nivel,
            mensaje=mensaje,
            referencia_id=referencia_id,
        )

        logger.warning(
            f"🚨 AlertaOperacional creada → {tipo} | {restaurante_id}")

    except Exception:
        logger.exception(f"💥 Error creando AlertaOperacional ({tipo})")
        raise


# ─────────────────────────────────────────
# HANDLERS PÚBLICOS
# ─────────────────────────────────────────

def handle_alerta_stock_bajo(data: dict) -> None:
    nombre = data.get("nombre_ingrediente", "ingrediente")
    actual = data.get("nivel_actual", "?")
    minimo = data.get("nivel_minimo", "?")
    unidad = data.get("unidad_medida", "")

    _crear_alerta(
        data=data,
        tipo="stock_bajo",
        nivel="urgente",
        mensaje=f"Stock bajo: {nombre} — actual {actual}{unidad}, mínimo {minimo}{unidad}",
    )


def handle_alerta_agotado(data: dict) -> None:
    nombre = data.get("nombre_ingrediente", "ingrediente")

    _crear_alerta(
        data=data,
        tipo="agotado",
        nivel="critica",
        mensaje=f"Ingrediente AGOTADO: {nombre}. Requiere reposición urgente.",
    )


def handle_alerta_vencimiento_proximo(data: dict) -> None:
    nombre = data.get("nombre_ingrediente", "ingrediente")
    dias = data.get("dias_para_vencer", "?")
    fecha = data.get("fecha_vencimiento", "")

    _crear_alerta(
        data=data,
        tipo="vencimiento",
        nivel="urgente",
        mensaje=f"Lote próximo a vencer: {nombre} — {dias} día(s) restantes (vence {fecha})",
    )


def handle_lote_vencido(data: dict) -> None:
    nombre = data.get("nombre_ingrediente", "lote")
    lote = data.get("numero_lote", "")

    _crear_alerta(
        data=data,
        tipo="vencimiento",
        nivel="critica",
        mensaje=f"Lote VENCIDO retirado: {nombre} — lote #{lote}",
    )


def handle_orden_compra_creada(data: dict) -> None:
    """
    Notifica al gerente que se generó una orden de compra automática
    (típicamente disparada por stock bajo).
    """
    orden_id = data.get("orden_id", "")
    proveedor = data.get("proveedor_id", "")
    total = data.get("total_estimado", "")
    moneda = data.get("moneda", "")

    _crear_alerta(
        data={**data, "alerta_id": orden_id},
        tipo="orden_compra",
        nivel="info",
        mensaje=f"Orden de compra generada — proveedor {proveedor} | total {total} {moneda}",
    )

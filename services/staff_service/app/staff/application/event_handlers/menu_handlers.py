# staff_service/app/staff/application/event_handlers/menu_handlers.py
"""
Handlers de eventos del menu_service para staff_service.

Cambios respecto a la versión anterior:
✅ raise en todos los except (consumer_base aplica NACK + retry)
✅ handle_restaurante_desactivado con firma correcta (solo data)
✅ Normalización de país robusta mantenida
"""
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

_PAIS_NORMALIZE = {
    "co": "CO", "colombia": "CO",
    "mx": "MX", "mexico": "MX", "méxico": "MX",
    "ar": "AR", "argentina": "AR",
    "cl": "CL", "chile": "CL",
    "br": "BR", "brasil": "BR", "brazil": "BR",
    "pe": "PE", "peru": "PE", "perú": "PE",
    "pa": "PA", "panama": "PA", "panamá": "PA",
}


def _normalize_pais(raw: str | None) -> str | None:
    if not raw:
        return None
    return _PAIS_NORMALIZE.get(raw.strip().lower())


# ─────────────────────────────────────────
# 🏪 RESTAURANTE
# ─────────────────────────────────────────

def handle_restaurante_creado(data: dict) -> None:
    try:
        from app.staff.models import RestauranteLocal, ConfiguracionLaboralPais

        restaurante_id = data.get("restaurante_id")
        if not restaurante_id:
            logger.warning("❌ restaurante.creado sin ID")
            return

        pais = _normalize_pais(data.get("pais"))
        if not pais:
            logger.warning(f"⚠️ País inválido: {data.get('pais')}")
            return

        obj, created = RestauranteLocal.objects.update_or_create(
            restaurante_id=UUID(restaurante_id),
            defaults={
                "nombre": data.get("nombre", ""),
                "pais":   pais,
                "ciudad": data.get("ciudad", ""),
                "activo": data.get("activo", True),
            },
        )

        logger.info(
            f"🏪 Restaurante {'CREADO' if created else 'UPSERT'} → {obj.nombre} ({pais})"
        )

        # Asegurar config laboral del país
        ConfiguracionLaboralPais.objects.get_or_create(pais=pais)

    except Exception:
        logger.exception("💥 Error en restaurante.creado")
        raise  # ✅ consumer_base aplica NACK + backoff


def handle_restaurante_actualizado(data: dict) -> None:
    try:
        from app.staff.models import RestauranteLocal

        restaurante_id = data.get("restaurante_id") or data.get("id")
        if not restaurante_id:
            logger.warning("❌ restaurante.actualizado sin ID")
            return

        cambios = data.get("cambios") or data.get("campos_modificados") or {}
        if not cambios:
            logger.warning("⚠️ Evento sin cambios")
            return

        campos_permitidos = {"nombre", "pais", "ciudad", "activo"}
        campos_limpios = {k: v for k,
                          v in cambios.items() if k in campos_permitidos}

        if "pais" in campos_limpios:
            pais = _normalize_pais(campos_limpios["pais"])
            if pais:
                campos_limpios["pais"] = pais
            else:
                logger.warning(f"⚠️ País inválido: {campos_limpios['pais']}")
                campos_limpios.pop("pais")

        if not campos_limpios:
            logger.warning("⚠️ Sin campos válidos para actualizar")
            return

        obj, created = RestauranteLocal.objects.update_or_create(
            restaurante_id=UUID(restaurante_id),
            defaults=campos_limpios,
        )

        logger.info(
            f"{'🆕 Creado por update' if created else '✏️ Actualizado'} → {restaurante_id}")

    except Exception:
        logger.exception("💥 Error en restaurante.actualizado")
        raise


# ✅ solo data, sin origin
def handle_restaurante_desactivado(data: dict) -> None:
    try:
        from app.staff.models import RestauranteLocal

        restaurante_id = data.get("restaurante_id")
        if not restaurante_id:
            logger.warning("❌ restaurante.desactivado sin ID")
            return

        updated = RestauranteLocal.objects.filter(
            restaurante_id=UUID(restaurante_id)
        ).update(activo=False)

        if updated:
            logger.info(f"⛔ Restaurante desactivado → {restaurante_id}")
        else:
            logger.warning(f"⚠️ Restaurante no encontrado → {restaurante_id}")

    except Exception:
        logger.exception("💥 Error en restaurante.desactivado")
        raise

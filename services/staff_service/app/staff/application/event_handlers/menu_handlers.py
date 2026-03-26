# staff_service/app/staff/application/event_handlers/menu_handlers.py
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Normalización de país
# menu_service puede publicar el código ISO ("CO") o el nombre completo
# ("Colombia"). Este mapa cubre ambos casos para que staff sea resiliente
# sin depender del formato exacto del origen.
# ---------------------------------------------------------------------------
_PAIS_NORMALIZE = {

    "CO": "CO",
    "MX": "MX",
    "AR": "AR",
    "CL": "CL",
    "BR": "BR",
    "PE": "PE",
    "PA": "PA",
    # Nombres completos → normalizar a código
    "Colombia":   "CO",
    "México":     "MX",
    "Mexico":     "MX",
    "Argentina":  "AR",
    "Chile":      "CL",
    "Brasil":     "BR",
    "Brazil":     "BR",
    "Perú":       "PE",
    "Peru":       "PE",
    "Panamá":     "PA",
    "Panama":     "PA",
}


def _normalize_pais(raw: str) -> str | None:
    """Convierte nombre completo o código a código ISO de 2 letras."""
    if not raw:
        return None
    return _PAIS_NORMALIZE.get(raw.strip(), None)


# ---------------------------------------------------------------------------
# HANDLERS
# ---------------------------------------------------------------------------

def handle_restaurante_created(data: dict) -> None:
    """
    Crea o actualiza un RestauranteLocal a partir de
    app.menu.restaurante.created
    """
    try:
        from app.staff.models import RestauranteLocal, ConfiguracionLaboralPais

        restaurante_id = data.get("restaurante_id") or data.get("id")
        if not restaurante_id:
            logger.warning(
                "[menu_handlers] restaurante.created sin restaurante_id — ignorado")
            return

        pais = _normalize_pais(data.get("pais", ""))
        if not pais:
            logger.warning(
                "[menu_handlers] restaurante.created con pais no reconocido: '%s' — ignorado",
                data.get("pais"),
            )
            return

        obj, created = RestauranteLocal.objects.update_or_create(
            restaurante_id=restaurante_id,
            defaults={
                "nombre": data.get("nombre", ""),
                "pais":   pais,
                "ciudad": data.get("ciudad", ""),
                "activo": data.get("activo", True),
            },
        )

        logger.info(
            "[menu_handlers] RestauranteLocal %s: %s (pais=%s)",
            "CREADO" if created else "ACTUALIZADO",
            obj.nombre,
            pais,
        )

        # Garantizar configuración laboral para el país
        _, cfg_created = ConfiguracionLaboralPais.objects.get_or_create(
            pais=pais)
        if cfg_created:
            logger.info(
                "[menu_handlers] ConfiguracionLaboralPais creada para pais=%s", pais)

    except Exception:
        logger.exception("[menu_handlers] Error en handle_restaurante_created")


def handle_restaurante_updated(data: dict) -> None:
    """
    Actualiza un RestauranteLocal a partir de
    app.menu.restaurante.updated
    """
    try:
        from app.staff.models import RestauranteLocal

        restaurante_id = data.get("restaurante_id") or data.get("id")
        if not restaurante_id:
            logger.warning(
                "[menu_handlers] restaurante.updated sin restaurante_id — ignorado")
            return

        campos = data.get("campos_modificados", {})

        # Normalizar pais si viene en los campos modificados
        if "pais" in campos:
            pais_normalizado = _normalize_pais(campos["pais"])
            if pais_normalizado:
                campos["pais"] = pais_normalizado
            else:
                logger.warning(
                    "[menu_handlers] restaurante.updated con pais no reconocido: '%s' — campo ignorado",
                    campos["pais"],
                )
                campos.pop("pais")

        campos_validos = {
            k: v for k, v in campos.items()
            if k in ("nombre", "pais", "ciudad")
        }

        if not campos_validos:
            logger.debug(
                "[menu_handlers] restaurante.updated sin campos válidos — ignorado")
            return

        updated = RestauranteLocal.objects.filter(
            restaurante_id=restaurante_id
        ).update(**campos_validos)

        if updated:
            logger.info(
                "[menu_handlers] RestauranteLocal actualizado: %s", restaurante_id)
        else:
            logger.warning(
                "[menu_handlers] restaurante.updated — no existe RestauranteLocal con id=%s",
                restaurante_id,
            )

    except Exception:
        logger.exception("[menu_handlers] Error en handle_restaurante_updated")


def handle_restaurante_deactivated(data: dict) -> None:
    """
    Desactiva un RestauranteLocal a partir de
    app.menu.restaurante.deactivated
    """
    try:
        from app.staff.models import RestauranteLocal

        restaurante_id = data.get("restaurante_id") or data.get("id")
        if not restaurante_id:
            logger.warning(
                "[menu_handlers] restaurante.deactivated sin restaurante_id — ignorado")
            return

        updated = RestauranteLocal.objects.filter(
            restaurante_id=restaurante_id
        ).update(activo=False)

        if updated:
            logger.info(
                "[menu_handlers] RestauranteLocal desactivado: %s", restaurante_id)
        else:
            logger.warning(
                "[menu_handlers] restaurante.deactivated — no existe RestauranteLocal con id=%s",
                restaurante_id,
            )

    except Exception:
        logger.exception(
            "[menu_handlers] Error en handle_restaurante_deactivated")

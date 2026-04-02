# loyalty_service/app/loyalty/application/event_handlers/menu_handlers.py
"""
Handlers de eventos del menu_service para loyalty_service.

loyalty necesita CatalogoPlato y CatalogoCategoria para poder
evaluar promociones con condición tipo=PLATO o tipo=CATEGORIA
sin llamadas HTTP síncronas a menu_service.
"""
import logging
from uuid import UUID

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# 🍽️ PLATOS
# ─────────────────────────────────────────

def handle_plato_creado(data: dict) -> None:
    try:
        from app.loyalty.models import CatalogoPlato

        plato_id = data.get("plato_id")
        if not plato_id:
            logger.warning("❌ plato.creado sin ID")
            return

        obj, created = CatalogoPlato.objects.update_or_create(
            plato_id=UUID(plato_id),
            defaults={
                "nombre":       data.get("nombre", ""),
                "categoria_id": UUID(data["categoria_id"]) if data.get("categoria_id") else None,
                "activo":       True,
            },
        )

        logger.info(
            f"{'🍽️ Plato creado' if created else '♻️ Plato actualizado'} "
            f"→ {obj.nombre}"
        )

    except Exception:
        logger.exception("💥 Error en plato.creado (loyalty)")
        raise


def handle_plato_actualizado(data: dict) -> None:
    try:
        from app.loyalty.models import CatalogoPlato

        plato_id = data.get("plato_id")
        cambios = data.get("cambios", {})

        if not plato_id or not cambios:
            return

        campos_permitidos = {"nombre", "activo", "categoria_id"}
        campos_limpios = {k: v for k,
                          v in cambios.items() if k in campos_permitidos}

        if not campos_limpios:
            return

        CatalogoPlato.objects.filter(
            plato_id=UUID(plato_id)).update(**campos_limpios)
        logger.info(f"✏️ Plato actualizado → {plato_id}")

    except Exception:
        logger.exception("💥 Error en plato.actualizado (loyalty)")
        raise


def handle_plato_desactivado(data: dict) -> None:
    try:
        from app.loyalty.models import CatalogoPlato

        plato_id = data.get("plato_id")
        if not plato_id:
            return

        CatalogoPlato.objects.filter(
            plato_id=UUID(plato_id)).update(activo=False)
        logger.info(f"⛔ Plato desactivado → {plato_id}")

    except Exception:
        logger.exception("💥 Error en plato.desactivado (loyalty)")
        raise


# ─────────────────────────────────────────
# 🗂️ CATEGORÍAS
# ─────────────────────────────────────────

def handle_categoria_creada(data: dict) -> None:
    try:
        from app.loyalty.models import CatalogoCategoria

        categoria_id = data.get("categoria_id")
        if not categoria_id:
            logger.warning("❌ categoria.creada sin ID")
            return

        obj, created = CatalogoCategoria.objects.update_or_create(
            categoria_id=UUID(categoria_id),
            defaults={
                "nombre": data.get("nombre", ""),
                "activo": True,
            },
        )

        logger.info(
            f"{'🗂️ Categoría creada' if created else '♻️ Categoría actualizada'} "
            f"→ {obj.nombre}"
        )

    except Exception:
        logger.exception("💥 Error en categoria.creada (loyalty)")
        raise


def handle_categoria_actualizada(data: dict) -> None:
    try:
        from app.loyalty.models import CatalogoCategoria

        categoria_id = data.get("categoria_id")
        cambios = data.get("cambios", {})

        if not categoria_id or not cambios:
            return

        campos_permitidos = {"nombre", "activo"}
        campos_limpios = {k: v for k,
                          v in cambios.items() if k in campos_permitidos}

        if not campos_limpios:
            return

        CatalogoCategoria.objects.filter(
            categoria_id=UUID(categoria_id)
        ).update(**campos_limpios)

        logger.info(f"✏️ Categoría actualizada → {categoria_id}")

    except Exception:
        logger.exception("💥 Error en categoria.actualizada (loyalty)")
        raise


def handle_categoria_desactivada(data: dict) -> None:
    try:
        from app.loyalty.models import CatalogoCategoria

        categoria_id = data.get("categoria_id")
        if not categoria_id:
            return

        CatalogoCategoria.objects.filter(
            categoria_id=UUID(categoria_id)
        ).update(activo=False)

        logger.info(f"⛔ Categoría desactivada → {categoria_id}")

    except Exception:
        logger.exception("💥 Error en categoria.desactivada (loyalty)")
        raise

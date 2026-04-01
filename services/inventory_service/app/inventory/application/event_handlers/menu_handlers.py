# inventory_service/app/inventory/application/event_handlers/menu_handlers.py
"""
Handlers de eventos del menu_service.

Cambios respecto a la versión anterior:
✅ handle_restaurante_creado agregado (estaba en declare_queues pero sin handler)
✅ Validación con schemas antes de tocar la BD
✅ update_or_create en todos los handlers → idempotente por naturaleza
"""
import logging
from uuid import UUID

from .schemas import (
    IngredienteSchema,
    PlatoIngredienteSchema,
    RestauranteCreadoSchema,
    SchemaError,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# 🏪 RESTAURANTE
# ─────────────────────────────────────────

def handle_restaurante_creado(data: dict) -> None:
    """
    Crea el Almacen principal del restaurante en inventory_service.
    Inventory necesita saber que el restaurante existe antes de
    poder registrar stock en él.
    """
    try:
        from app.inventory.models import Almacen

        payload = RestauranteCreadoSchema.from_dict(data)

        obj, created = Almacen.objects.update_or_create(
            restaurante_id=payload.restaurante_id,
            nombre="Almacén principal",
            defaults={"activo": True},
        )

        logger.info(
            f"{'🏪 Almacén creado' if created else '♻️ Almacén ya existe'} "
            f"→ restaurante {payload.restaurante_id}"
        )

    except SchemaError as e:
        logger.error(f"❌ Payload inválido en restaurante.creado: {e}")
        raise
    except Exception:
        logger.exception("💥 Error en restaurante.creado")
        raise


# ─────────────────────────────────────────
# 🧪 INGREDIENTES
# ─────────────────────────────────────────

def handle_ingrediente_creado(data: dict) -> None:
    try:
        from app.inventory.models import Ingrediente

        payload = IngredienteSchema.from_dict(data)

        obj, created = Ingrediente.objects.update_or_create(
            ingrediente_id=payload.ingrediente_id,
            defaults={
                "nombre":        payload.nombre,
                "unidad_medida": payload.unidad_medida,
                "activo":        True,
            },
        )

        logger.info(
            f"{'🆕 Ingrediente creado' if created else '♻️ Ingrediente actualizado'} → {obj.nombre}"
        )

    except SchemaError as e:
        logger.error(f"❌ Payload inválido en ingrediente.creado: {e}")
        raise
    except Exception:
        logger.exception("💥 Error en ingrediente.creado")
        raise


def handle_ingrediente_actualizado(data: dict) -> None:
    try:
        from app.inventory.models import Ingrediente

        ingrediente_id = data.get("ingrediente_id")
        cambios = data.get("cambios", {})

        if not ingrediente_id:
            logger.warning("❌ ingrediente.actualizado sin ID")
            return

        if not cambios:
            logger.warning("⚠️ Sin cambios en ingrediente.actualizado")
            return

        campos_permitidos = {"nombre", "unidad_medida", "activo"}
        campos_limpios = {k: v for k,
                          v in cambios.items() if k in campos_permitidos}

        if not campos_limpios:
            logger.warning("⚠️ No hay campos válidos para actualizar")
            return

        updated = Ingrediente.objects.filter(
            ingrediente_id=UUID(ingrediente_id)
        ).update(**campos_limpios)

        if updated:
            logger.info(f"✏️ Ingrediente actualizado → {ingrediente_id}")
        else:
            logger.warning(f"⚠️ Ingrediente no encontrado → {ingrediente_id}")

    except Exception:
        logger.exception("💥 Error en ingrediente.actualizado")
        raise


def handle_ingrediente_desactivado(data: dict) -> None:
    try:
        from app.inventory.models import Ingrediente

        ingrediente_id = data.get("ingrediente_id")
        if not ingrediente_id:
            logger.warning("❌ ingrediente.desactivado sin ID")
            return

        updated = Ingrediente.objects.filter(
            ingrediente_id=UUID(ingrediente_id)
        ).update(activo=False)

        if updated:
            logger.info(f"⛔ Ingrediente desactivado → {ingrediente_id}")
        else:
            logger.warning(f"⚠️ Ingrediente no encontrado → {ingrediente_id}")

    except Exception:
        logger.exception("💥 Error en ingrediente.desactivado")
        raise


# ─────────────────────────────────────────
# 🍳 RELACIÓN PLATO - INGREDIENTE (RECETA)
# ─────────────────────────────────────────

def handle_plato_ingrediente_agregado(data: dict) -> None:
    try:
        from app.inventory.models import RecetaPlato

        payload = PlatoIngredienteSchema.from_dict(data)

        RecetaPlato.objects.update_or_create(
            plato_id=payload.plato_id,
            ingrediente_id=payload.ingrediente_id,
            defaults={
                "cantidad":      payload.cantidad,
                "unidad_medida": payload.unidad_medida,
            },
        )

        logger.info(
            f"➕ Ingrediente agregado a receta → plato {payload.plato_id}")

    except SchemaError as e:
        logger.error(f"❌ Payload inválido en plato_ingrediente.agregado: {e}")
        raise
    except Exception:
        logger.exception("💥 Error en plato_ingrediente.agregado")
        raise


def handle_plato_ingrediente_actualizado(data: dict) -> None:
    try:
        from app.inventory.models import RecetaPlato

        plato_id = data.get("plato_id")
        ingrediente_id = data.get("ingrediente_id")
        cantidad_nueva = data.get("cantidad_nueva")

        if not plato_id or not ingrediente_id:
            logger.warning("❌ plato_ingrediente.actualizado incompleto")
            return

        updated = RecetaPlato.objects.filter(
            plato_id=UUID(plato_id),
            ingrediente_id=UUID(ingrediente_id),
        ).update(cantidad=cantidad_nueva)

        if updated:
            logger.info(f"✏️ Receta actualizada → plato {plato_id}")
        else:
            logger.warning(f"⚠️ Receta no encontrada → plato {plato_id}")

    except Exception:
        logger.exception("💥 Error en plato_ingrediente.actualizado")
        raise


def handle_plato_ingrediente_eliminado(data: dict) -> None:
    try:
        from app.inventory.models import RecetaPlato

        plato_id = data.get("plato_id")
        ingrediente_id = data.get("ingrediente_id")

        if not plato_id or not ingrediente_id:
            logger.warning("❌ plato_ingrediente.eliminado incompleto")
            return

        deleted, _ = RecetaPlato.objects.filter(
            plato_id=UUID(plato_id),
            ingrediente_id=UUID(ingrediente_id),
        ).delete()

        if deleted:
            logger.info(
                f"🗑️ Ingrediente removido de receta → plato {plato_id}")
        else:
            logger.warning(f"⚠️ Relación no encontrada → plato {plato_id}")

    except Exception:
        logger.exception("💥 Error en plato_ingrediente.eliminado")
        raise

# order_service/app/orders/application/event_handlers/menu_handlers.py
"""
Handlers de eventos del menu_service para order_service.

order_service necesita copia local de:
- Restaurantes  → validar que el restaurante existe al crear un pedido
- Platos        → snapshot de nombre al crear DetallePedido
- Precios       → precio vigente al momento de crear el pedido

Estos modelos locales NO están en los models.py originales — necesitas crearlos:

    class RestauranteLocal(models.Model):
        restaurante_id = models.UUIDField(unique=True, db_index=True)
        nombre         = models.CharField(max_length=255)
        moneda         = models.CharField(max_length=10)
        activo         = models.BooleanField(default=True)

    class PlatoLocal(models.Model):
        plato_id    = models.UUIDField(unique=True, db_index=True)
        nombre      = models.CharField(max_length=255)
        descripcion = models.TextField(blank=True)
        activo      = models.BooleanField(default=True)

    class PrecioLocal(models.Model):
        precio_id      = models.UUIDField(unique=True, db_index=True)
        plato_id       = models.UUIDField(db_index=True)
        restaurante_id = models.UUIDField(db_index=True)
        precio         = models.DecimalField(max_digits=10, decimal_places=2)
        moneda         = models.CharField(max_length=10)
        activo         = models.BooleanField(default=True)
"""
import logging
from uuid import UUID

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# 🏪 RESTAURANTE
# ─────────────────────────────────────────

def handle_restaurante_creado(data: dict) -> None:
    try:
        from app.orders.models import RestauranteLocal

        restaurante_id = data.get("restaurante_id")
        if not restaurante_id:
            logger.warning("❌ restaurante.creado sin ID")
            return

        obj, created = RestauranteLocal.objects.update_or_create(
            restaurante_id=UUID(restaurante_id),
            defaults={
                "nombre": data.get("nombre", ""),
                "moneda": data.get("moneda", "COP"),
                "activo": True,
            },
        )

        logger.info(
            f"{'🏪 Restaurante creado' if created else '♻️ Restaurante actualizado'} "
            f"→ {obj.nombre}"
        )

    except Exception:
        logger.exception("💥 Error en restaurante.creado (order)")
        raise


# ─────────────────────────────────────────
# 🍽️ PLATOS
# ─────────────────────────────────────────

def handle_plato_creado(data: dict) -> None:
    try:
        from app.orders.models import PlatoLocal

        plato_id = data.get("plato_id")
        if not plato_id:
            logger.warning("❌ plato.creado sin ID")
            return

        obj, created = PlatoLocal.objects.update_or_create(
            plato_id=UUID(plato_id),
            defaults={
                "nombre":      data.get("nombre", ""),
                "descripcion": data.get("descripcion", ""),
                "activo":      True,
            },
        )

        logger.info(
            f"{'🍽️ Plato creado' if created else '♻️ Plato actualizado'} → {obj.nombre}"
        )

    except Exception:
        logger.exception("💥 Error en plato.creado (order)")
        raise


def handle_plato_actualizado(data: dict) -> None:
    try:
        from app.orders.models import PlatoLocal

        plato_id = data.get("plato_id")
        cambios = data.get("cambios", {})

        if not plato_id:
            logger.warning("❌ plato.actualizado sin ID")
            return

        campos_permitidos = {"nombre", "descripcion", "activo"}
        campos_limpios = {k: v for k,
                          v in cambios.items() if k in campos_permitidos}

        if not campos_limpios:
            return

        PlatoLocal.objects.filter(plato_id=UUID(
            plato_id)).update(**campos_limpios)
        logger.info(f"✏️ Plato actualizado → {plato_id}")

    except Exception:
        logger.exception("💥 Error en plato.actualizado (order)")
        raise


def handle_plato_desactivado(data: dict) -> None:
    try:
        from app.orders.models import PlatoLocal

        plato_id = data.get("plato_id")
        if not plato_id:
            return

        PlatoLocal.objects.filter(plato_id=UUID(plato_id)).update(activo=False)
        logger.info(f"⛔ Plato desactivado → {plato_id}")

    except Exception:
        logger.exception("💥 Error en plato.desactivado (order)")
        raise


# ─────────────────────────────────────────
# 💰 PRECIOS
# ─────────────────────────────────────────

def handle_precio_creado(data: dict) -> None:
    try:
        from app.orders.models import PrecioLocal

        precio_id = data.get("precio_id")
        plato_id = data.get("plato_id")
        restaurante_id = data.get("restaurante_id")

        if not all([precio_id, plato_id, restaurante_id]):
            logger.warning("❌ precio.creado incompleto")
            return

        obj, created = PrecioLocal.objects.update_or_create(
            precio_id=UUID(precio_id),
            defaults={
                "plato_id":       UUID(plato_id),
                "restaurante_id": UUID(restaurante_id),
                "precio":         data.get("precio"),
                "moneda":         data.get("moneda", "COP"),
                "activo":         data.get("activo", True),
            },
        )

        logger.info(
            f"{'💰 Precio creado' if created else '♻️ Precio actualizado'} "
            f"→ plato {plato_id} | {obj.precio} {obj.moneda}"
        )

    except Exception:
        logger.exception("💥 Error en precio.creado (order)")
        raise


def handle_precio_actualizado(data: dict) -> None:
    try:
        from app.orders.models import PrecioLocal

        precio_id = data.get("precio_id")
        precio_nuevo = data.get("precio_nuevo")

        if not precio_id:
            logger.warning("❌ precio.actualizado sin ID")
            return

        updated = PrecioLocal.objects.filter(
            precio_id=UUID(precio_id)
        ).update(precio=precio_nuevo)

        if updated:
            logger.info(
                f"✏️ Precio actualizado → {precio_id} | nuevo: {precio_nuevo}")
        else:
            logger.warning(f"⚠️ Precio no encontrado → {precio_id}")

    except Exception:
        logger.exception("💥 Error en precio.actualizado (order)")
        raise


def handle_precio_desactivado(data: dict) -> None:
    try:
        from app.orders.models import PrecioLocal

        precio_id = data.get("precio_id")
        if not precio_id:
            return

        PrecioLocal.objects.filter(
            precio_id=UUID(precio_id)).update(activo=False)
        logger.info(f"⛔ Precio desactivado → {precio_id}")

    except Exception:
        logger.exception("💥 Error en precio.desactivado (order)")
        raise

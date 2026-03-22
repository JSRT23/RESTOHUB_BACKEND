"""
consume_inventory_events.py — inventory_service

Ubicacion: app/inventory/management/commands/consume_inventory_events.py

inventory_service CONSUME eventos de:
  - menu_service   → restaurante, ingrediente, plato_ingrediente
  - order_service  → pedido.confirmado (descontar stock), pedido.cancelado (revertir)

inventory_service PUBLICA eventos hacia:
  - staff_service  → alertas de stock y ordenes de compra
  - gateway        → stock actualizado, lotes, ordenes

Ejecutar:
    python manage.py consume_inventory_events --solo-declarar
    python manage.py consume_inventory_events
"""

import json
import logging

import pika
import pika.exceptions
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "restohub"

# ---------------------------------------------------------------------------
# Queues que inventory_service CONSUME
# ---------------------------------------------------------------------------

QUEUES_PROPIAS = {

    # Todo lo de menu_service que inventory necesita
    "inventory.menu": [
        "app.menu.restaurante.created",
        "app.menu.restaurante.updated",
        "app.menu.restaurante.deactivated",
        "app.menu.ingrediente.created",
        "app.menu.ingrediente.updated",
        "app.menu.ingrediente.deactivated",
        "app.menu.plato_ingrediente.added",
        "app.menu.plato_ingrediente.removed",
        "app.menu.plato_ingrediente.cantidad_updated",
    ],

    # Pedidos de order_service — descontar y revertir stock
    "inventory.order": [
        "app.order.pedido.confirmado",
        "app.order.pedido.cancelado",
    ],

    # Auditoría — recibe todos los eventos que publica inventory
    "inventory.audit": [
        "app.inventory.#",
    ],
}

# ---------------------------------------------------------------------------
# Queues de consumidores de inventory_service
# Se declaran aquí para que existan aunque esos servicios no estén corriendo
# ---------------------------------------------------------------------------

QUEUES_CONSUMIDORES = {

    # staff_service consume alertas y ordenes de compra
    "staff.inventory": [
        "app.inventory.alerta.stock_bajo",
        "app.inventory.alerta.agotado",
        "app.inventory.alerta.vencimiento_proximo",
        "app.inventory.lote.vencido",
        "app.inventory.orden_compra.creada",
        "app.inventory.orden_compra.enviada",
        "app.inventory.orden_compra.cancelada",
    ],

    # order_service consume agotado para rechazar pedidos
    "order.inventory": [
        "app.inventory.alerta.agotado",
    ],

    # gateway consume stock actualizado, lotes y ordenes recibidas
    "gateway.inventory": [
        "app.inventory.stock.actualizado",
        "app.inventory.alerta.stock_bajo",
        "app.inventory.alerta.agotado",
        "app.inventory.lote.recibido",
        "app.inventory.orden_compra.recibida",
    ],
}


class Command(BaseCommand):
    help = (
        "Declara queues de inventory_service y consume eventos de "
        "menu_service y order_service."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--solo-declarar",
            action="store_true",
            default=False,
            help="Solo declara queues y bindings, luego termina.",
        )

    def handle(self, *args, **options):
        from django.conf import settings
        cfg = settings.RABBITMQ

        self.stdout.write("[inventory_consumer] Conectando a RabbitMQ...")

        credentials = pika.PlainCredentials(cfg["USER"], cfg["PASSWORD"])
        params = pika.ConnectionParameters(
            host=cfg["HOST"],
            port=cfg["PORT"],
            virtual_host=cfg["VHOST"],
            credentials=credentials,
            heartbeat=120,
            blocked_connection_timeout=30,
        )

        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type="topic",
            durable=True,
        )

        # — Queues propias —
        self.stdout.write("\n  -- Queues propias (inventory_service consume):")
        for queue_name, routing_keys in QUEUES_PROPIAS.items():
            channel.queue_declare(queue=queue_name, durable=True)
            for rk in routing_keys:
                channel.queue_bind(
                    exchange=EXCHANGE_NAME,
                    queue=queue_name,
                    routing_key=rk,
                )
            self.stdout.write(
                f"    [OK] '{queue_name}' -- {len(routing_keys)} binding(s)"
            )

        # — Queues consumidores —
        self.stdout.write("\n  -- Queues de consumidores (otros servicios):")
        for queue_name, routing_keys in QUEUES_CONSUMIDORES.items():
            channel.queue_declare(queue=queue_name, durable=True)
            for rk in routing_keys:
                channel.queue_bind(
                    exchange=EXCHANGE_NAME,
                    queue=queue_name,
                    routing_key=rk,
                )
            self.stdout.write(
                f"    [OK] '{queue_name}' -- {len(routing_keys)} binding(s)"
            )

        total_q = len(QUEUES_PROPIAS) + len(QUEUES_CONSUMIDORES)
        total_b = sum(
            len(v) for v in {**QUEUES_PROPIAS, **QUEUES_CONSUMIDORES}.values()
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"\n[inventory_consumer] {total_q} queues declaradas, "
                f"{total_b} bindings registrados."
            )
        )

        if options["solo_declarar"]:
            connection.close()
            self.stdout.write(
                "[inventory_consumer] Modo --solo-declarar. Finalizado.")
            return

        # — Modo escucha —
        self.stdout.write(
            "\n[inventory_consumer] Escuchando eventos. Ctrl+C para detener.\n"
        )

        channel.basic_qos(prefetch_count=1)

        for queue_name in ["inventory.menu", "inventory.order"]:
            channel.basic_consume(
                queue=queue_name,
                on_message_callback=self._callback,
            )

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
        finally:
            connection.close()
            self.stdout.write("\n[inventory_consumer] Conexion cerrada.")

    # -----------------------------------------------------------------------
    # Callback principal
    # -----------------------------------------------------------------------

    def _callback(self, channel, method, properties, body):
        event_type = "desconocido"
        try:
            message = json.loads(body)
            event_type = message.get("event_type", "")
            data = message.get("data", {})

            self.stdout.write(f"  [evento] {event_type}")
            self._procesar(event_type, data)

            channel.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as exc:
            logger.error("[inventory_consumer] JSON invalido: %s", exc)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as exc:
            logger.error(
                "[inventory_consumer] Error procesando '%s': %s", event_type, exc
            )
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    # -----------------------------------------------------------------------
    # Router
    # -----------------------------------------------------------------------

    def _procesar(self, event_type: str, data: dict) -> None:
        handlers = {
            # ── menu_service ────────────────────────────────────────────────
            "app.menu.restaurante.created":                self._on_restaurante_created,
            "app.menu.restaurante.updated":                self._on_restaurante_updated,
            "app.menu.restaurante.deactivated":            self._on_restaurante_deactivated,
            "app.menu.ingrediente.created":                self._on_ingrediente_created,
            "app.menu.ingrediente.updated":                self._on_ingrediente_updated,
            "app.menu.ingrediente.deactivated":            self._on_ingrediente_deactivated,
            "app.menu.plato_ingrediente.added":            self._on_plato_ingrediente_added,
            "app.menu.plato_ingrediente.removed":          self._on_plato_ingrediente_removed,
            "app.menu.plato_ingrediente.cantidad_updated": self._on_plato_ingrediente_cantidad,
            # ── order_service ───────────────────────────────────────────────
            "app.order.pedido.confirmado":                 self._on_pedido_confirmado,
            "app.order.pedido.cancelado":                  self._on_pedido_cancelado,
        }
        handler = handlers.get(event_type)
        if handler:
            handler(data)
        else:
            logger.debug(
                "[inventory_consumer] Evento sin handler: %s", event_type)

    # -----------------------------------------------------------------------
    # Handlers — menu_service
    # -----------------------------------------------------------------------

    @transaction.atomic
    def _on_restaurante_created(self, data: dict) -> None:
        """Crea el almacen principal por defecto para el nuevo restaurante."""
        from app.inventory.models import Almacen

        restaurante_id = data.get("restaurante_id")
        if not restaurante_id:
            return

        almacen, created = Almacen.objects.get_or_create(
            restaurante_id=restaurante_id,
            nombre="Almacen Principal",
            defaults={
                "descripcion": "Creado automaticamente al registrar el restaurante.",
                "activo": True,
            },
        )
        action = "creado" if created else "ya existia"
        logger.info(
            "[inventory_consumer] Almacen principal %s para restaurante %s",
            action, restaurante_id,
        )

    @transaction.atomic
    def _on_restaurante_updated(self, data: dict) -> None:
        """Actualiza datos del restaurante si se guarda copia local."""
        restaurante_id = data.get("restaurante_id")
        logger.info(
            "[inventory_consumer] Restaurante actualizado: %s", restaurante_id
        )

    @transaction.atomic
    def _on_restaurante_deactivated(self, data: dict) -> None:
        """Marca almacenes del restaurante como inactivos."""
        from app.inventory.models import Almacen

        restaurante_id = data.get("restaurante_id") or data.get("id")
        if not restaurante_id:
            return

        count = Almacen.objects.filter(
            restaurante_id=restaurante_id
        ).update(activo=False)

        logger.warning(
            "[inventory_consumer] Restaurante %s desactivado — "
            "%d almacen(es) marcados inactivos.",
            restaurante_id, count,
        )

    @transaction.atomic
    def _on_ingrediente_created(self, data: dict) -> None:
        """
        Nuevo ingrediente en menu_service.
        inventory no crea stock automaticamente — se crea con el primer lote.
        """
        logger.info(
            "[inventory_consumer] Nuevo ingrediente disponible: %s (%s)",
            data.get("nombre"), data.get("ingrediente_id"),
        )

    @transaction.atomic
    def _on_ingrediente_updated(self, data: dict) -> None:
        """Actualiza el nombre snapshot en IngredienteInventario y RecetaPlato."""
        from app.inventory.models import IngredienteInventario, RecetaPlato

        ingrediente_id = data.get("ingrediente_id")
        nombre = data.get("nombre")

        if not ingrediente_id or not nombre:
            return

        c1 = IngredienteInventario.objects.filter(
            ingrediente_id=ingrediente_id
        ).update(nombre_ingrediente=nombre)

        c2 = RecetaPlato.objects.filter(
            ingrediente_id=ingrediente_id
        ).update(nombre_ingrediente=nombre)

        logger.info(
            "[inventory_consumer] Nombre snapshot actualizado para ingrediente %s "
            "(%d inventarios, %d recetas)",
            ingrediente_id, c1, c2,
        )

    @transaction.atomic
    def _on_ingrediente_deactivated(self, data: dict) -> None:
        """Marca el ingrediente como descontinuado en inventario."""
        from app.inventory.models import IngredienteInventario

        ingrediente_id = data.get("ingrediente_id")
        if not ingrediente_id:
            return

        count = IngredienteInventario.objects.filter(
            ingrediente_id=ingrediente_id
        ).update(activo=False)

        logger.info(
            "[inventory_consumer] Ingrediente %s desactivado — "
            "%d registro(s) marcados inactivos.",
            ingrediente_id, count,
        )

    @transaction.atomic
    def _on_plato_ingrediente_added(self, data: dict) -> None:
        """Crea o actualiza RecetaPlato cuando menu agrega un ingrediente a un plato."""
        from app.inventory.models import RecetaPlato

        RecetaPlato.objects.update_or_create(
            plato_id=data.get("plato_id"),
            ingrediente_id=data.get("ingrediente_id"),
            defaults={
                "nombre_ingrediente": data.get("nombre_ingrediente", ""),
                "cantidad":           data.get("cantidad"),
                "unidad_medida":      data.get("unidad_medida"),
            },
        )
        logger.info(
            "[inventory_consumer] RecetaPlato creada: plato %s + ingrediente %s",
            data.get("plato_id"), data.get("ingrediente_id"),
        )

    @transaction.atomic
    def _on_plato_ingrediente_removed(self, data: dict) -> None:
        """Elimina RecetaPlato cuando menu quita un ingrediente de un plato."""
        from app.inventory.models import RecetaPlato

        deleted, _ = RecetaPlato.objects.filter(
            plato_id=data.get("plato_id"),
            ingrediente_id=data.get("ingrediente_id"),
        ).delete()
        logger.info(
            "[inventory_consumer] RecetaPlato eliminada: %d registro(s)", deleted
        )

    @transaction.atomic
    def _on_plato_ingrediente_cantidad(self, data: dict) -> None:
        """Actualiza cantidad en RecetaPlato."""
        from app.inventory.models import RecetaPlato

        updated = RecetaPlato.objects.filter(
            plato_id=data.get("plato_id"),
            ingrediente_id=data.get("ingrediente_id"),
        ).update(cantidad=data.get("cantidad_nueva"))
        logger.info(
            "[inventory_consumer] RecetaPlato cantidad actualizada: %d registro(s)",
            updated,
        )

    # -----------------------------------------------------------------------
    # Handlers — order_service
    # -----------------------------------------------------------------------

    @transaction.atomic
    def _on_pedido_confirmado(self, data: dict) -> None:
        """
        Descuenta stock por cada plato del pedido.
        Flujo por detalle:
          1. Buscar RecetaPlato del plato
          2. Por cada ingrediente: consumo = receta.cantidad × cantidad_pedida
          3. Descontar IngredienteInventario con select_for_update
          4. Crear MovimientoInventario tipo SALIDA
          5. Publicar STOCK_ACTUALIZADO
          6. Si agotado o bajo minimo → crear AlertaStock
        """
        from app.inventory.models import (
            Almacen, AlertaStock, IngredienteInventario,
            MovimientoInventario, RecetaPlato,
        )
        from app.inventory.events.event_types import InventoryEvents
        from app.inventory.services.rabbitmq import publish_event

        pedido_id = data.get("pedido_id")
        restaurante_id = data.get("restaurante_id")
        detalles = data.get("detalles", [])

        if not detalles:
            logger.warning(
                "[inventory_consumer] pedido.confirmado sin detalles: %s", pedido_id
            )
            return

        almacen = Almacen.objects.filter(
            restaurante_id=restaurante_id, activo=True
        ).first()

        if not almacen:
            logger.error(
                "[inventory_consumer] Sin almacen activo para restaurante %s",
                restaurante_id,
            )
            return

        for detalle in detalles:
            plato_id = detalle.get("plato_id")
            cantidad_pedida = detalle.get("cantidad", 1)

            recetas = RecetaPlato.objects.filter(plato_id=plato_id)
            if not recetas.exists():
                logger.warning(
                    "[inventory_consumer] Sin RecetaPlato para plato %s", plato_id
                )
                continue

            for receta in recetas:
                consumo = receta.cantidad * cantidad_pedida

                try:
                    inv = IngredienteInventario.objects.select_for_update().get(
                        ingrediente_id=receta.ingrediente_id,
                        almacen=almacen,
                    )
                except IngredienteInventario.DoesNotExist:
                    logger.warning(
                        "[inventory_consumer] Sin inventario para ingrediente %s "
                        "en almacen %s",
                        receta.ingrediente_id, almacen.id,
                    )
                    continue

                cantidad_antes = inv.cantidad_actual
                inv.cantidad_actual = max(inv.cantidad_actual - consumo, 0)
                inv.save(update_fields=["cantidad_actual"])

                MovimientoInventario.objects.create(
                    ingrediente_inventario=inv,
                    tipo_movimiento="SALIDA",
                    cantidad=consumo,
                    cantidad_antes=cantidad_antes,
                    cantidad_despues=inv.cantidad_actual,
                    pedido_id=pedido_id,
                    descripcion=f"Pedido {pedido_id} confirmado.",
                )

                publish_event(InventoryEvents.STOCK_ACTUALIZADO, {
                    "ingrediente_id":    str(receta.ingrediente_id),
                    "almacen_id":        str(almacen.id),
                    "restaurante_id":    str(restaurante_id),
                    "cantidad_anterior": str(cantidad_antes),
                    "cantidad_nueva":    str(inv.cantidad_actual),
                    "unidad_medida":     inv.unidad_medida,
                    "tipo_movimiento":   "SALIDA",
                })

                # Alertas de stock
                if inv.esta_agotado:
                    AlertaStock.objects.get_or_create(
                        ingrediente_inventario=inv,
                        tipo_alerta="AGOTADO",
                        resuelta=False,
                        defaults={
                            "almacen":        almacen,
                            "restaurante_id": restaurante_id,
                            "ingrediente_id": receta.ingrediente_id,
                            "nivel_actual":   inv.cantidad_actual,
                            "nivel_minimo":   inv.nivel_minimo,
                        },
                    )
                elif inv.necesita_reposicion:
                    AlertaStock.objects.get_or_create(
                        ingrediente_inventario=inv,
                        tipo_alerta="STOCK_BAJO",
                        resuelta=False,
                        defaults={
                            "almacen":        almacen,
                            "restaurante_id": restaurante_id,
                            "ingrediente_id": receta.ingrediente_id,
                            "nivel_actual":   inv.cantidad_actual,
                            "nivel_minimo":   inv.nivel_minimo,
                        },
                    )

        logger.info(
            "[inventory_consumer] Stock descontado para pedido %s", pedido_id
        )

    @transaction.atomic
    def _on_pedido_cancelado(self, data: dict) -> None:
        """
        Revierte el stock descontado buscando los MovimientoInventario
        tipo SALIDA del pedido y creando movimientos DEVOLUCION.
        """
        from app.inventory.models import IngredienteInventario, MovimientoInventario
        from app.inventory.events.event_types import InventoryEvents
        from app.inventory.services.rabbitmq import publish_event

        pedido_id = data.get("pedido_id")
        if not pedido_id:
            return

        salidas = MovimientoInventario.objects.filter(
            pedido_id=pedido_id,
            tipo_movimiento="SALIDA",
        ).select_related("ingrediente_inventario__almacen")

        for salida in salidas:
            inv = IngredienteInventario.objects.select_for_update().get(
                pk=salida.ingrediente_inventario_id
            )
            cantidad_antes = inv.cantidad_actual
            inv.cantidad_actual += salida.cantidad
            inv.save(update_fields=["cantidad_actual"])

            MovimientoInventario.objects.create(
                ingrediente_inventario=inv,
                tipo_movimiento="DEVOLUCION",
                cantidad=salida.cantidad,
                cantidad_antes=cantidad_antes,
                cantidad_despues=inv.cantidad_actual,
                pedido_id=pedido_id,
                descripcion=f"Reversion por cancelacion de pedido {pedido_id}.",
            )

            publish_event(InventoryEvents.STOCK_ACTUALIZADO, {
                "ingrediente_id":    str(inv.ingrediente_id),
                "almacen_id":        str(inv.almacen_id),
                "restaurante_id":    str(inv.almacen.restaurante_id),
                "cantidad_anterior": str(cantidad_antes),
                "cantidad_nueva":    str(inv.cantidad_actual),
                "unidad_medida":     inv.unidad_medida,
                "tipo_movimiento":   "DEVOLUCION",
            })

        logger.info(
            "[inventory_consumer] Stock revertido para pedido cancelado %s", pedido_id
        )

"""
Management command que corre el consumer de RabbitMQ para inventory_service.

Escucha dos queues:
  - inventory.menu.events  → eventos de menu_service (app.menu.#)
  - inventory.order.events → pedido.confirmado y pedido.cancelado

Uso: python manage.py consume_inventory_events

En producción este comando debe correr como un proceso separado
en el mismo contenedor o en un worker dedicado.
"""
import json
import logging
import pika
import os
import threading
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

RABBIT_HOST = os.getenv("RABBITMQ_HOST",     "rabbitmq")
RABBIT_USER = os.getenv("RABBITMQ_USER",     "guest")
RABBIT_PASS = os.getenv("RABBITMQ_PASSWORD", "guest")
EXCHANGE_NAME = os.getenv("RABBITMQ_EXCHANGE", "restohub")

# Queues y sus routing keys
QUEUES = {
    "inventory.menu.events": "app.menu.#",
    "inventory.order.events.confirmado": "app.order.pedido.confirmado",
    "inventory.order.events.cancelado":  "app.order.pedido.cancelado",
}


class Command(BaseCommand):
    help = "Consumer RabbitMQ para inventory_service"

    def handle(self, *args, **options):
        credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBIT_HOST,
                credentials=credentials,
                heartbeat=120,
            )
        )
        channel = connection.channel()

        # Declarar exchange
        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type="topic",
            durable=True,
        )

        # Declarar queues y bindings
        for queue_name, routing_key in QUEUES.items():
            channel.queue_declare(queue=queue_name, durable=True)
            channel.queue_bind(
                exchange=EXCHANGE_NAME,
                queue=queue_name,
                routing_key=routing_key,
            )
            self.stdout.write(
                self.style.SUCCESS(f"✓ Queue '{queue_name}' → '{routing_key}'")
            )

        self.stdout.write("\nEscuchando eventos... Ctrl+C para detener.\n")

        def callback(ch, method, properties, body):
            try:
                message = json.loads(body)
                event_type = message.get("event_type", "")
                data = message.get("data", {})

                self.stdout.write(f"[evento] {event_type}")
                self._procesar(event_type, data)

                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                logger.error("Error procesando evento: %s", e)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        # Consumir todas las queues
        for queue_name in QUEUES:
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=queue_name, on_message_callback=callback)

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
            connection.close()
            self.stdout.write(self.style.WARNING("\nConsumer detenido."))

    def _procesar(self, event_type: str, data: dict):
        """Enruta cada evento a su handler correspondiente."""
        handlers = {
            # ── menu_service ──
            "app.menu.restaurante.created":              self._on_restaurante_created,
            "app.menu.ingrediente.created":              self._on_ingrediente_created,
            "app.menu.ingrediente.updated":              self._on_ingrediente_updated,
            "app.menu.ingrediente.deactivated":          self._on_ingrediente_deactivated,
            "app.menu.plato_ingrediente.added":          self._on_plato_ingrediente_added,
            "app.menu.plato_ingrediente.removed":        self._on_plato_ingrediente_removed,
            "app.menu.plato_ingrediente.cantidad_updated": self._on_plato_ingrediente_cantidad,
            # ── order_service ──
            "app.order.pedido.confirmado":               self._on_pedido_confirmado,
            "app.order.pedido.cancelado":                self._on_pedido_cancelado,
        }
        handler = handlers.get(event_type)
        if handler:
            handler(data)
        else:
            logger.debug("Evento sin handler: %s", event_type)

    # ─────────────────────────────────────────
    # Handlers — menu_service
    # ─────────────────────────────────────────

    @transaction.atomic
    def _on_restaurante_created(self, data: dict):
        """Crea el almacén principal por defecto para el nuevo restaurante."""
        from app.inventory.models import Almacen
        restaurante_id = data.get("restaurante_id")
        if not restaurante_id:
            return
        Almacen.objects.get_or_create(
            restaurante_id=restaurante_id,
            nombre="Almacén Principal",
            defaults={
                "descripcion": "Almacén creado automáticamente al registrar el restaurante."},
        )
        logger.info(
            "[inventory] Almacén principal creado para restaurante %s", restaurante_id)

    @transaction.atomic
    def _on_ingrediente_created(self, data: dict):
        """
        Cuando menu_service crea un ingrediente, inventory NO crea
        automáticamente un IngredienteInventario — se crea cuando
        llega el primer lote o manualmente. Solo registra el log.
        """
        logger.info("[inventory] Nuevo ingrediente disponible: %s",
                    data.get("nombre"))

    @transaction.atomic
    def _on_ingrediente_updated(self, data: dict):
        """Actualiza el nombre snapshot en IngredienteInventario y RecetaPlato."""
        from app.inventory.models import IngredienteInventario, RecetaPlato
        ingrediente_id = data.get("ingrediente_id")
        nombre = data.get("nombre")
        if not ingrediente_id or not nombre:
            return

        IngredienteInventario.objects.filter(
            ingrediente_id=ingrediente_id
        ).update(nombre_ingrediente=nombre)

        RecetaPlato.objects.filter(
            ingrediente_id=ingrediente_id
        ).update(nombre_ingrediente=nombre)

        logger.info(
            "[inventory] Snapshot nombre actualizado para ingrediente %s", ingrediente_id)

    @transaction.atomic
    def _on_ingrediente_deactivated(self, data: dict):
        """Loguea — no eliminamos el inventario, solo dejamos constancia."""
        logger.info("[inventory] Ingrediente desactivado en menu_service: %s", data.get(
            "ingrediente_id"))

    @transaction.atomic
    def _on_plato_ingrediente_added(self, data: dict):
        """Crea o actualiza RecetaPlato cuando menu_service agrega un ingrediente a un plato."""
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
            "[inventory] RecetaPlato creada: plato %s + ingrediente %s",
            data.get("plato_id"), data.get("ingrediente_id")
        )

    @transaction.atomic
    def _on_plato_ingrediente_removed(self, data: dict):
        """Elimina RecetaPlato cuando menu_service quita un ingrediente de un plato."""
        from app.inventory.models import RecetaPlato
        deleted, _ = RecetaPlato.objects.filter(
            plato_id=data.get("plato_id"),
            ingrediente_id=data.get("ingrediente_id"),
        ).delete()
        logger.info("[inventory] RecetaPlato eliminada: %d registros", deleted)

    @transaction.atomic
    def _on_plato_ingrediente_cantidad(self, data: dict):
        """Actualiza cantidad en RecetaPlato."""
        from app.inventory.models import RecetaPlato
        updated = RecetaPlato.objects.filter(
            plato_id=data.get("plato_id"),
            ingrediente_id=data.get("ingrediente_id"),
        ).update(cantidad=data.get("cantidad_nueva"))
        logger.info(
            "[inventory] RecetaPlato cantidad actualizada: %d registros", updated)

    # ─────────────────────────────────────────
    # Handlers — order_service
    # ─────────────────────────────────────────

    @transaction.atomic
    def _on_pedido_confirmado(self, data: dict):
        """
        Descuenta stock por cada plato del pedido.

        Flujo:
        1. Por cada detalle del pedido (plato_id + cantidad)
        2. Buscar RecetaPlato del plato
        3. Por cada ingrediente de la receta, calcular consumo:
           consumo = receta.cantidad × detalle.cantidad
        4. Buscar IngredienteInventario en el almacén principal del restaurante
        5. Descontar y crear MovimientoInventario tipo SALIDA
        6. Si cantidad_actual <= nivel_minimo → crear AlertaStock
        """
        from app.inventory.models import (
            RecetaPlato, IngredienteInventario,
            MovimientoInventario, AlertaStock, Almacen
        )
        from app.inventory.services.rabbitmq import publish_event
        from app.inventory.events.event_types import InventoryEvents

        pedido_id = data.get("pedido_id")
        restaurante_id = data.get("restaurante_id")
        detalles = data.get("detalles", [])

        if not detalles:
            logger.warning(
                "[inventory] pedido.confirmado sin detalles: %s", pedido_id)
            return

        # Obtener almacén principal del restaurante
        almacen = Almacen.objects.filter(
            restaurante_id=restaurante_id,
            activo=True,
        ).first()

        if not almacen:
            logger.error(
                "[inventory] No hay almacén activo para restaurante %s", restaurante_id)
            return

        for detalle in detalles:
            plato_id = detalle.get("plato_id")
            cantidad_pedida = detalle.get("cantidad", 1)

            # Obtener receta del plato
            recetas = RecetaPlato.objects.filter(plato_id=plato_id)
            if not recetas.exists():
                logger.warning(
                    "[inventory] Sin RecetaPlato para plato %s", plato_id)
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
                        "[inventory] Sin inventario para ingrediente %s en almacén %s",
                        receta.ingrediente_id, almacen.id
                    )
                    continue

                cantidad_antes = inv.cantidad_actual
                inv.cantidad_actual = max(inv.cantidad_actual - consumo, 0)
                inv.save(update_fields=[
                         "cantidad_actual", "fecha_actualizacion"])

                # Crear movimiento
                MovimientoInventario.objects.create(
                    ingrediente_inventario=inv,
                    tipo_movimiento="SALIDA",
                    cantidad=consumo,
                    cantidad_antes=cantidad_antes,
                    cantidad_despues=inv.cantidad_actual,
                    pedido_id=pedido_id,
                    descripcion=f"Pedido {pedido_id} confirmado.",
                )

                # Publicar stock actualizado
                publish_event(InventoryEvents.STOCK_ACTUALIZADO, {
                    "ingrediente_id":   str(receta.ingrediente_id),
                    "almacen_id":       str(almacen.id),
                    "restaurante_id":   str(restaurante_id),
                    "cantidad_anterior": str(cantidad_antes),
                    "cantidad_nueva":    str(inv.cantidad_actual),
                    "unidad_medida":    inv.unidad_medida,
                    "tipo_movimiento":  "SALIDA",
                })

                # Verificar si necesita alerta
                if inv.esta_agotado:
                    AlertaStock.objects.create(
                        ingrediente_inventario=inv,
                        almacen=almacen,
                        restaurante_id=restaurante_id,
                        ingrediente_id=receta.ingrediente_id,
                        tipo_alerta="AGOTADO",
                        nivel_actual=inv.cantidad_actual,
                        nivel_minimo=inv.nivel_minimo,
                    )
                    publish_event(InventoryEvents.ALERTA_AGOTADO, {
                        "ingrediente_id":    str(receta.ingrediente_id),
                        "restaurante_id":    str(restaurante_id),
                        "almacen_id":        str(almacen.id),
                        "nombre_ingrediente": inv.nombre_ingrediente,
                    })
                elif inv.necesita_reposicion:
                    AlertaStock.objects.create(
                        ingrediente_inventario=inv,
                        almacen=almacen,
                        restaurante_id=restaurante_id,
                        ingrediente_id=receta.ingrediente_id,
                        tipo_alerta="STOCK_BAJO",
                        nivel_actual=inv.cantidad_actual,
                        nivel_minimo=inv.nivel_minimo,
                    )
                    publish_event(InventoryEvents.ALERTA_STOCK_BAJO, {
                        "ingrediente_id":    str(receta.ingrediente_id),
                        "restaurante_id":    str(restaurante_id),
                        "almacen_id":        str(almacen.id),
                        "nombre_ingrediente": inv.nombre_ingrediente,
                        "nivel_actual":      str(inv.cantidad_actual),
                        "nivel_minimo":      str(inv.nivel_minimo),
                        "unidad_medida":     inv.unidad_medida,
                    })

        logger.info("[inventory] Stock descontado para pedido %s", pedido_id)

    @transaction.atomic
    def _on_pedido_cancelado(self, data: dict):
        """
        Revierte el stock descontado buscando los MovimientoInventario
        tipo SALIDA asociados al pedido_id y creando movimientos DEVOLUCION.
        """
        from app.inventory.models import IngredienteInventario, MovimientoInventario
        from app.inventory.services.rabbitmq import publish_event
        from app.inventory.events.event_types import InventoryEvents

        pedido_id = data.get("pedido_id")
        if not pedido_id:
            return

        salidas = MovimientoInventario.objects.filter(
            pedido_id=pedido_id,
            tipo_movimiento="SALIDA",
        ).select_related("ingrediente_inventario")

        for salida in salidas:
            inv = IngredienteInventario.objects.select_for_update().get(
                pk=salida.ingrediente_inventario_id
            )
            cantidad_antes = inv.cantidad_actual
            inv.cantidad_actual += salida.cantidad
            inv.save(update_fields=["cantidad_actual", "fecha_actualizacion"])

            MovimientoInventario.objects.create(
                ingrediente_inventario=inv,
                tipo_movimiento="DEVOLUCION",
                cantidad=salida.cantidad,
                cantidad_antes=cantidad_antes,
                cantidad_despues=inv.cantidad_actual,
                pedido_id=pedido_id,
                descripcion=f"Reversión por cancelación de pedido {pedido_id}.",
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
            "[inventory] Stock revertido para pedido cancelado %s", pedido_id)

    @transaction.atomic
    def _on_orden_compra_recibida_costo(self, data: dict):
        """
        Cuando se recibe una OrdenCompra, actualiza el costo_unitario
        en RecetaPlato para cada ingrediente recibido.

        Por qué: el precio pagado al proveedor en esta orden es el
        costo más actualizado del ingrediente. Permite calcular el
        margen real de ganancia por plato.

        Después de actualizar, publica costo_plato.actualizado
        por cada plato afectado para que analytics_service lo consuma.
        """
        from app.inventory.models import RecetaPlato
        from app.inventory.services.rabbitmq import publish_event
        from app.inventory.events.event_types import InventoryEvents
        from django.utils import timezone
        from django.db.models import Sum, F, ExpressionWrapper, DecimalField

        detalles = data.get("detalles", [])
        if not detalles:
            return

        # platos afectados para publicar su nuevo costo
        platos_afectados = set()

        for detalle in detalles:
            ingrediente_id = detalle.get("ingrediente_id")
            precio_unitario = detalle.get("precio_unitario")

            if not ingrediente_id or not precio_unitario:
                continue

            # Actualizar costo_unitario en todas las RecetaPlato
            # que usen este ingrediente
            actualizados = RecetaPlato.objects.filter(
                ingrediente_id=ingrediente_id
            ).update(
                costo_unitario=precio_unitario,
                fecha_costo_actualizado=timezone.now(),
            )

            if actualizados > 0:
                # Marcar platos afectados
                platos = RecetaPlato.objects.filter(
                    ingrediente_id=ingrediente_id
                ).values_list("plato_id", flat=True).distinct()
                platos_afectados.update(platos)

            logger.info(
                "[inventory] costo_unitario actualizado para ingrediente %s → %s (%d recetas)",
                ingrediente_id, precio_unitario, actualizados
            )

        # Publicar costo_plato.actualizado por cada plato afectado
        for plato_id in platos_afectados:
            recetas = RecetaPlato.objects.filter(plato_id=plato_id)

            ingredientes_data = []
            costo_total = 0

            for receta in recetas:
                costo_ing = receta.costo_ingrediente
                costo_total += costo_ing
                ingredientes_data.append({
                    "ingrediente_id":    str(receta.ingrediente_id),
                    "nombre":            receta.nombre_ingrediente,
                    "cantidad":          str(receta.cantidad),
                    "unidad_medida":     receta.unidad_medida,
                    "costo_unitario":    str(receta.costo_unitario),
                    "costo_ingrediente": str(round(costo_ing, 4)),
                })

            publish_event(InventoryEvents.COSTO_PLATO_ACTUALIZADO, {
                "plato_id":           str(plato_id),
                "costo_total":        str(round(costo_total, 4)),
                "ingredientes":       ingredientes_data,
                "fecha_actualizacion": timezone.now().isoformat(),
            })

            logger.info(
                "[inventory] costo_plato.actualizado publicado: plato %s → costo %s",
                plato_id, round(costo_total, 4)
            )

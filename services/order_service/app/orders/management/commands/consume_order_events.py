"""
consume_order_events.py — order_service

Ubicacion: app/order/management/commands/consume_order_events.py

order_service CONSUME eventos de:
  - menu_service    -> invalidar cache de precios/platos, bloquear restaurantes
  - loyalty_service -> aplicar descuentos de promociones activas

Ejecutar:
    python manage.py consume_order_events --solo-declarar
    python manage.py consume_order_events
"""

import json
import logging
from decimal import Decimal

import pika
import pika.exceptions
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "restohub"

QUEUES_PROPIAS = {
    "order.menu": [
        "app.menu.precio.updated",
        "app.menu.precio.deactivated",
        "app.menu.plato.deactivated",
        "app.menu.restaurante.deactivated",
    ],
    "order.loyalty": [
        "app.loyalty.promocion.aplicada",
    ],
    "order.audit": [
        "app.order.#",
    ],
}

QUEUES_CONSUMIDORES = {
    "inventory.order": [
        "app.order.pedido.confirmado",
        "app.order.pedido.cancelado",
    ],
    "loyalty.order": [
        "app.order.pedido.creado",
        "app.order.pedido.entregado",
        "app.order.pedido.cancelado",
        "app.order.entrega.completada",
        "app.order.detalle.agregado",
    ],
    "staff.order": [
        "app.order.pedido.confirmado",
        "app.order.pedido.entregado",
        "app.order.comanda.creada",
        "app.order.comanda.lista",
        "app.order.entrega.asignada",
        "app.order.entrega.completada",
    ],
}


class Command(BaseCommand):
    help = "Declara queues de order_service y consume eventos de menu_service y loyalty_service."

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

        self.stdout.write("[order_consumer] Conectando a RabbitMQ...")

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

        self.stdout.write("\n  -- Queues propias (order_service consume):")
        for queue_name, routing_keys in QUEUES_PROPIAS.items():
            channel.queue_declare(queue=queue_name, durable=True)
            for rk in routing_keys:
                channel.queue_bind(exchange=EXCHANGE_NAME,
                                   queue=queue_name, routing_key=rk)
            self.stdout.write(
                f"    [OK] '{queue_name}' -- {len(routing_keys)} binding(s)")

        self.stdout.write("\n  -- Queues de consumidores (otros servicios):")
        for queue_name, routing_keys in QUEUES_CONSUMIDORES.items():
            channel.queue_declare(queue=queue_name, durable=True)
            for rk in routing_keys:
                channel.queue_bind(exchange=EXCHANGE_NAME,
                                   queue=queue_name, routing_key=rk)
            self.stdout.write(
                f"    [OK] '{queue_name}' -- {len(routing_keys)} binding(s)")

        total_q = len(QUEUES_PROPIAS) + len(QUEUES_CONSUMIDORES)
        total_b = sum(len(v)
                      for v in {**QUEUES_PROPIAS, **QUEUES_CONSUMIDORES}.values())
        self.stdout.write(self.style.SUCCESS(
            f"\n[order_consumer] {total_q} queues declaradas, {total_b} bindings registrados."
        ))

        if options["solo_declarar"]:
            connection.close()
            self.stdout.write(
                "[order_consumer] Modo --solo-declarar. Finalizado.")
            return

        self.stdout.write(
            "\n[order_consumer] Escuchando eventos. Ctrl+C para detener.\n")
        channel.basic_qos(prefetch_count=1)

        for queue_name in ["order.menu", "order.loyalty"]:
            channel.basic_consume(
                queue=queue_name, on_message_callback=self._callback)

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
        finally:
            connection.close()
            self.stdout.write("\n[order_consumer] Conexion cerrada.")

    def _callback(self, channel, method, properties, body):
        event_type = "desconocido"
        try:
            message = json.loads(body)
            event_type = message.get("event_type", "")
            data = message.get("data", {})
            logger.debug("[order_consumer] Recibido: %s", event_type)
            self._procesar(event_type, data)
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError as exc:
            logger.error("[order_consumer] JSON invalido: %s", exc)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as exc:
            logger.error(
                "[order_consumer] Error procesando '%s': %s", event_type, exc)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def _procesar(self, event_type: str, data: dict) -> None:
        handlers = {
            "app.menu.precio.updated":          self._on_precio_updated,
            "app.menu.precio.deactivated":      self._on_precio_deactivated,
            "app.menu.plato.deactivated":       self._on_plato_deactivated,
            "app.menu.restaurante.deactivated": self._on_restaurante_deactivated,
            "app.loyalty.promocion.aplicada":   self._on_promocion_aplicada,
        }
        handler = handlers.get(event_type)
        if handler:
            handler(data)
        else:
            logger.warning(
                "[order_consumer] Evento sin handler: %s", event_type)

    @transaction.atomic
    def _on_precio_updated(self, data: dict) -> None:
        """
        Precio actualizado en menu_service.
        Los pedidos en curso no se modifican (tienen snapshot del precio al crearlos).
        Los nuevos pedidos consultaran el precio actualizado a menu_service en el momento.
        """
        logger.info(
            "[order_consumer] Precio actualizado — plato %s en restaurante %s: %s %s",
            data.get("plato_id"), data.get("restaurante_id"),
            data.get("precio"), data.get("moneda"),
        )

    @transaction.atomic
    def _on_precio_deactivated(self, data: dict) -> None:
        """
        Precio desactivado — ese plato deja de estar disponible en el restaurante.
        """
        logger.warning(
            "[order_consumer] Precio desactivado — plato %s en restaurante %s.",
            data.get("plato_id"), data.get("restaurante_id"),
        )

    @transaction.atomic
    def _on_plato_deactivated(self, data: dict) -> None:
        """
        Plato desactivado en menu_service.
        Cancela pedidos en estado RECIBIDO que contengan ese plato.
        Los pedidos ya en preparacion se respetan.
        """
        from app.orders.models import Pedido

        plato_id = data.get("plato_id")
        if not plato_id:
            return

        pedidos = Pedido.objects.filter(
            estado="RECIBIDO",
            detalles__plato_id=plato_id,
        ).distinct()

        count = pedidos.count()
        if count:
            pedidos.update(estado="CANCELADO")
            logger.warning(
                "[order_consumer] Plato %s desactivado — %d pedido(s) cancelados.",
                plato_id, count,
            )
        else:
            logger.info(
                "[order_consumer] Plato %s desactivado — sin pedidos RECIBIDO afectados.",
                plato_id,
            )

    @transaction.atomic
    def _on_restaurante_deactivated(self, data: dict) -> None:
        """
        Restaurante desactivado.
        Cancela pedidos RECIBIDOS del restaurante.
        Los pedidos en preparacion se respetan.
        """
        from app.orders.models import Pedido

        restaurante_id = data.get("restaurante_id") or data.get("id")
        if not restaurante_id:
            return

        pedidos = Pedido.objects.filter(
            estado="RECIBIDO", restaurante_id=restaurante_id)
        count = pedidos.count()
        pedidos.update(estado="CANCELADO")

        logger.warning(
            "[order_consumer] Restaurante %s desactivado — %d pedido(s) cancelados.",
            restaurante_id, count,
        )

    @transaction.atomic
    def _on_promocion_aplicada(self, data: dict) -> None:
        """
        loyalty_service determino que una promocion aplica para un pedido.
        Aplica el descuento al total antes de que el pedido sea confirmado.
        """
        from app.orders.models import Pedido

        pedido_id = data.get("pedido_id")
        descuento = data.get("descuento")
        tipo = data.get("tipo_descuento", "absoluto")
        promocion_id = data.get("promocion_id")

        if not pedido_id or descuento is None:
            logger.warning(
                "[order_consumer] promocion.aplicada — datos incompletos: %s", data)
            return

        try:
            pedido = Pedido.objects.get(pk=pedido_id, estado="RECIBIDO")
        except Pedido.DoesNotExist:
            logger.warning(
                "[order_consumer] Pedido no encontrado o ya confirmado: %s", pedido_id)
            return

        desc = Decimal(str(descuento))
        monto = (pedido.total * desc / Decimal("100")).quantize(Decimal("0.01")) \
            if tipo == "porcentaje" else desc

        pedido.total = max(pedido.total - monto, Decimal("0"))
        pedido.save(update_fields=["total"])

        logger.info(
            "[order_consumer] Promocion %s aplicada al pedido %s — descuento: %s",
            promocion_id, pedido_id, monto,
        )

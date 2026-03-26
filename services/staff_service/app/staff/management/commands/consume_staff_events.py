# staff_service/app/staff/management/commands/consume_staff_events.py
import logging
from django.conf import settings
from django.core.management.base import BaseCommand

from app.staff.infrastructure.messaging.connection import get_channel
from app.staff.infrastructure.messaging.consumer_base import BaseConsumer

from app.staff.application.event_handlers.menu_handlers import (
    handle_restaurante_created,
    handle_restaurante_updated,
    handle_restaurante_deactivated,
)

logger = logging.getLogger(__name__)


# 🔥 MISMA CONFIG QUE declare_queues.py
QUEUES = {
    "staff.menu": [
        "app.menu.restaurante.*",
    ],
    "staff.order": [
        "app.order.pedido.confirmado",
        "app.order.comanda.creada",
        "app.order.comanda.lista",
        "app.order.entrega.asignada",
        "app.order.entrega.completada",
        "app.order.pedido.entregado",
    ],
    "staff.inventory": [
        "app.inventory.alerta.stock_bajo",
        "app.inventory.alerta.agotado",
        "app.inventory.alerta.vencimiento_proximo",
        "app.inventory.orden_compra.creada",
    ],
    "staff.audit": [
        "app.staff.#",
    ],
}


class StaffConsumer(BaseConsumer):

    def dispatch(self, event_type: str, data: dict) -> None:

        if event_type == "app.menu.restaurante.created":
            handle_restaurante_created(data)

        elif event_type == "app.menu.restaurante.updated":
            handle_restaurante_updated(data)

        elif event_type == "app.menu.restaurante.deactivated":
            handle_restaurante_deactivated(data)

        else:
            logger.warning("[consumer] Evento no manejado: %s", event_type)


class Command(BaseCommand):
    help = "Consume eventos para staff_service"

    def handle(self, *args, **kwargs):
        self.stdout.write("\n[staff_consumer] Conectando a RabbitMQ...\n")

        channel = get_channel()

        # 🔥 1. Declarar exchange SIEMPRE
        channel.exchange_declare(
            exchange=settings.RABBITMQ["EXCHANGE"],
            exchange_type="topic",
            durable=True,
        )

        # 🔥 2. Declarar TODAS las queues aquí (CLAVE)
        for queue_name, routing_keys in QUEUES.items():

            channel.queue_declare(queue=queue_name, durable=True)

            for routing_key in routing_keys:
                channel.queue_bind(
                    exchange=settings.RABBITMQ["EXCHANGE"],
                    queue=queue_name,
                    routing_key=routing_key,
                )

            self.stdout.write(f"[staff_consumer] Queue lista: {queue_name}")

        consumer = StaffConsumer()

        def callback(ch, method, properties, body):
            try:
                consumer.process_message(body)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception:
                logger.exception("[staff_consumer] Error procesando mensaje")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_qos(prefetch_count=1)

        # 🔥 3. Consumir DESPUÉS de declarar
        for queue_name in QUEUES.keys():
            channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback
            )
            self.stdout.write(f"[staff_consumer] Suscrito a: {queue_name}")

        self.stdout.write(
            "\n[staff_consumer] Escuchando eventos — Ctrl+C para salir\n"
        )

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            self.stdout.write("\n[staff_consumer] Detenido")
            channel.stop_consuming()
        finally:
            try:
                channel.connection.close()
            except Exception:
                pass
            self.stdout.write("[staff_consumer] Conexión cerrada\n")

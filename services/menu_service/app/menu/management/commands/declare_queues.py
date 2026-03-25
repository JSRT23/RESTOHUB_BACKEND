# menu_service/app/menu/management/commands/declare_queues.py

import logging

import pika
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CONFIGURACIÓN CENTRAL DE QUEUES
# ---------------------------------------------------------------------------

QUEUES = {

    # inventory_service
    "inventory.menu": [
        "app.menu.plato.*",
        "app.menu.ingrediente.*",
        "app.menu.plato_ingrediente.*",
        "app.menu.restaurante.*",
    ],

    # order_service
    "order.menu": [
        "app.menu.precio.*",
        "app.menu.plato.activated",
        "app.menu.plato.deactivated",
        "app.menu.restaurante.deactivated",
    ],

    # loyalty_service
    "loyalty.menu": [
        "app.menu.plato.*",
        "app.menu.precio.*",
        "app.menu.categoria.*",
        "app.menu.restaurante.*",
    ],

    # staff_service
    "staff.menu": [
        "app.menu.restaurante.*",
    ],

    # auditoría (solo desarrollo)
    "menu.audit": [
        "app.menu.#",
    ],
}


class Command(BaseCommand):
    help = "Declara todas las queues y bindings de menu_service en RabbitMQ"

    def handle(self, *args, **kwargs):

        cfg = settings.RABBITMQ

        self.stdout.write("\n[declare_queues] Conectando a RabbitMQ...\n")

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

        # -------------------------------------------------------------------
        # EXCHANGE
        # -------------------------------------------------------------------
        channel.exchange_declare(
            exchange=cfg["EXCHANGE"],
            exchange_type="topic",
            durable=True,
        )

        total_bindings = 0

        # -------------------------------------------------------------------
        # QUEUES + BINDINGS
        # -------------------------------------------------------------------
        for queue_name, routing_keys in QUEUES.items():

            channel.queue_declare(
                queue=queue_name,
                durable=True,
            )

            for routing_key in routing_keys:
                channel.queue_bind(
                    exchange=cfg["EXCHANGE"],
                    queue=queue_name,
                    routing_key=routing_key,
                )
                total_bindings += 1

            self.stdout.write(
                f"[OK] {queue_name} → {len(routing_keys)} bindings"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✔ {len(QUEUES)} queues declaradas "
                f"con {total_bindings} bindings\n"
            )
        )

        connection.close()
        self.stdout.write("[declare_queues] Finalizado.\n")

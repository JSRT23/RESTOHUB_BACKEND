# menu_service/app/menu/management/commands/declare_queues.py
# app/menu/management/commands/declare_queues.py

from django.core.management.base import BaseCommand
from django.conf import settings

from app.menu.infrastructure.messaging.core.connection import crear_canal
from app.menu.infrastructure.messaging.config.exchanges import declarar_exchange
from app.menu.infrastructure.messaging.config.routing_keys import RoutingKey
from app.menu.infrastructure.messaging.config.queues import Queues


class Command(BaseCommand):
    help = "Declara colas y bindings en RabbitMQ"

    def handle(self, *args, **options):

        conexion, canal = crear_canal()

        # 🔹 Declarar exchange
        declarar_exchange(canal)

        # 🔹 Declarar cola
        canal.queue_declare(
            queue=Queues.MENU_QUEUE,
            durable=True
        )

        # 🔹 Bindings
        routing_keys = [
            "app.menu.#",
        ]

        for key in routing_keys:
            canal.queue_bind(
                exchange=settings.RABBITMQ["EXCHANGE"],
                queue=Queues.MENU_QUEUE,
                routing_key=key
            )

        conexion.close()

        self.stdout.write(self.style.SUCCESS(
            "✅ Colas y bindings declarados correctamente"))

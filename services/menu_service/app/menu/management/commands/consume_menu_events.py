# menu_service/app/menu/management/commands/consume_menu_events.py
from django.core.management.base import BaseCommand
from app.menu.infrastructure.messaging.consumer.base_consumer import BaseConsumer
from app.menu.infrastructure.messaging.consumer.handlers.menu_handler import manejar_evento_menu
from app.menu.infrastructure.messaging.config.routing_keys import RoutingKey
from app.menu.infrastructure.messaging.config.queues import Queues


class Command(BaseCommand):
    help = "Inicia el consumer de eventos de menu_service"

    def handle(self, *args, **options):

        consumer = BaseConsumer(
            queue_name=Queues.MENU_QUEUE,
            routing_keys=[
                "app.menu.#",
            ],
            handler=manejar_evento_menu
        )

        self.stdout.write(self.style.SUCCESS(
            "🚀 Iniciando consumer de menu_service..."))

        consumer.iniciar()

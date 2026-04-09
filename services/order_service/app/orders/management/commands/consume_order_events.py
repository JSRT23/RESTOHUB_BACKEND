# order_service/app/orders/management/commands/consume_order_events.py
import logging

from django.core.management.base import BaseCommand

from app.orders.infrastructure.messaging.consumer_base import BaseConsumer

from app.orders.application.event_handlers.staff_handlers import (
    handle_cocina_asignacion_creada,
    handle_cocina_asignacion_completada,
    handle_entrega_asignada,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Inicia el consumer de order_service"

    def handle(self, *args, **options):
        consumer = BaseConsumer(service="order")

        # ── staff_service — mueve el estado del pedido ─────────────────────
        consumer.register("app.staff.cocina.asignacion.creada",
                          handle_cocina_asignacion_creada)
        consumer.register("app.staff.cocina.asignacion.completada",
                          handle_cocina_asignacion_completada)
        consumer.register("app.staff.entrega.asignada",
                          handle_entrega_asignada)

        logger.info("🚀 Order consumer iniciado")
        self.stdout.write("🔵 Order consumer escuchando eventos...")
        consumer.start()

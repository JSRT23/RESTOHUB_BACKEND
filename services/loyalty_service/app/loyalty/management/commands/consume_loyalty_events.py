# loyalty_service/app/loyalty/management/commands/consume_loyalty_events.py
import logging

from django.core.management.base import BaseCommand

from app.loyalty.infrastructure.messaging.consumer_base import BaseConsumer

from app.loyalty.application.event_handlers.order_handlers import (
    handle_pedido_entregado,
    handle_pedido_cancelado,
)
from app.loyalty.application.event_handlers.menu_handlers import (
    handle_plato_creado,
    handle_plato_actualizado,
    handle_plato_desactivado,
    handle_categoria_creada,
    handle_categoria_actualizada,
    handle_categoria_desactivada,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Inicia el consumer de loyalty_service"

    def handle(self, *args, **options):
        consumer = BaseConsumer(service="loyalty")

        # ── Pedidos (order_service) ───────────────────────────
        consumer.register("app.order.pedido.entregado",
                          handle_pedido_entregado)
        consumer.register("app.order.pedido.cancelado",
                          handle_pedido_cancelado)

        # ── Platos (menu_service) ─────────────────────────────
        consumer.register("app.menu.plato.creado",      handle_plato_creado)
        consumer.register("app.menu.plato.actualizado",
                          handle_plato_actualizado)
        consumer.register("app.menu.plato.desactivado",
                          handle_plato_desactivado)

        # ── Categorías (menu_service) ─────────────────────────
        consumer.register("app.menu.categoria.creada",
                          handle_categoria_creada)
        consumer.register("app.menu.categoria.actualizada",
                          handle_categoria_actualizada)
        consumer.register("app.menu.categoria.desactivada",
                          handle_categoria_desactivada)

        logger.info("🚀 Loyalty consumer iniciado")
        consumer.start()

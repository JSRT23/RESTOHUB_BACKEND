# inventory_service/app/inventory/management/commands/consume_inventory_events.py
"""
Entry point del consumer de inventory_service.

Responsabilidad única: registrar handlers y arrancar.
Toda la lógica de conexión, reintentos y DLQ vive en BaseConsumer.

Antes de ejecutar este comando, correr declare_queues:
    python manage.py declare_queues
    python manage.py consume_inventory_events
"""
import logging

from django.core.management.base import BaseCommand

from app.inventory.infrastructure.messaging.consumer_base import BaseConsumer

from app.inventory.application.event_handlers.menu_handlers import (
    handle_ingrediente_creado,
    handle_ingrediente_actualizado,
    handle_ingrediente_desactivado,
    handle_plato_ingrediente_agregado,
    handle_plato_ingrediente_actualizado,
    handle_plato_ingrediente_eliminado,
    handle_restaurante_creado,
)
from app.inventory.application.event_handlers.order_handlers import (
    handle_pedido_cancelado,
    handle_pedido_confirmado,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Inicia el consumer de inventory_service"

    def handle(self, *args, **options):
        consumer = BaseConsumer(service="inventory")

        # ── Restaurante ───────────────────────────────────────────
        consumer.register("app.menu.restaurante.creado",
                          handle_restaurante_creado)

        # ── Ingredientes ──────────────────────────────────────────
        consumer.register("app.menu.ingrediente.creado",
                          handle_ingrediente_creado)
        consumer.register("app.menu.ingrediente.actualizado",
                          handle_ingrediente_actualizado)
        consumer.register("app.menu.ingrediente.desactivado",
                          handle_ingrediente_desactivado)

        # ── Recetas ───────────────────────────────────────────────
        consumer.register("app.menu.plato_ingrediente.agregado",
                          handle_plato_ingrediente_agregado)
        consumer.register("app.menu.plato_ingrediente.actualizado",
                          handle_plato_ingrediente_actualizado)
        consumer.register("app.menu.plato_ingrediente.eliminado",
                          handle_plato_ingrediente_eliminado)

        # ── Pedidos ───────────────────────────────────────────────
        consumer.register("app.order.pedido.confirmado",
                          handle_pedido_confirmado)
        consumer.register("app.order.pedido.cancelado",
                          handle_pedido_cancelado)

        logger.info("🚀 Inventory consumer iniciado")
        consumer.start()

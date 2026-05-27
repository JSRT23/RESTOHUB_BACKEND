# inventory_service/app/inventory/apps.py
import logging
import os
import threading

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.inventory"

    def ready(self):
        import app.inventory.signals

        if os.environ.get("RUN_MAIN") == "true":
            return

        thread = threading.Thread(
            target=self._start_consumer,
            daemon=True,
            name="inventory-consumer",
        )
        thread.start()

    def _start_consumer(self):
        import time
        time.sleep(5)

        try:
            from app.inventory.infrastructure.messaging.consumer_base import BaseConsumer
            from app.inventory.application.event_handlers.menu_handlers import (
                handle_restaurante_creado,
                handle_ingrediente_creado,
                handle_ingrediente_actualizado,
                handle_ingrediente_desactivado,
                handle_plato_ingrediente_agregado,
                handle_plato_ingrediente_actualizado,
                handle_plato_ingrediente_eliminado,
            )
            from app.inventory.application.event_handlers.order_handlers import (
                handle_pedido_confirmado,
                handle_pedido_cancelado,
            )

            consumer = BaseConsumer(service="inventory")

            consumer.register("app.menu.restaurante.creado",
                              handle_restaurante_creado)
            consumer.register("app.menu.ingrediente.creado",
                              handle_ingrediente_creado)
            consumer.register("app.menu.ingrediente.actualizado",
                              handle_ingrediente_actualizado)
            consumer.register("app.menu.ingrediente.desactivado",
                              handle_ingrediente_desactivado)
            consumer.register("app.menu.plato_ingrediente.agregado",
                              handle_plato_ingrediente_agregado)
            consumer.register("app.menu.plato_ingrediente.actualizado",
                              handle_plato_ingrediente_actualizado)
            consumer.register("app.menu.plato_ingrediente.eliminado",
                              handle_plato_ingrediente_eliminado)
            consumer.register("app.order.pedido.confirmado",
                              handle_pedido_confirmado)
            consumer.register("app.order.pedido.cancelado",
                              handle_pedido_cancelado)

            logger.info("🚀 Inventory consumer arrancado en background thread")
            consumer.start()

        except Exception:
            logger.exception("💥 Error arrancando inventory consumer")

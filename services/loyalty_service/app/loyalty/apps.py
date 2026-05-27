# loyalty_service/app/loyalty/apps.py
import logging
import os
import threading

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class LoyaltyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.loyalty"

    def ready(self):
        import app.loyalty.signals

        if os.environ.get("RUN_MAIN") == "true":
            return

        thread = threading.Thread(
            target=self._start_consumer,
            daemon=True,
            name="loyalty-consumer",
        )
        thread.start()

    def _start_consumer(self):
        import time
        time.sleep(5)

        try:
            from app.loyalty.infrastructure.messaging.consumer_base import BaseConsumer
            from app.loyalty.application.event_handlers.menu_handlers import (
                handle_plato_creado,
                handle_plato_actualizado,
                handle_plato_desactivado,
                handle_categoria_creada,
                handle_categoria_actualizada,
                handle_categoria_desactivada,
            )
            from app.loyalty.application.event_handlers.order_handlers import (
                handle_pedido_entregado,
                handle_pedido_cancelado,
            )

            consumer = BaseConsumer(service="loyalty")

            consumer.register("app.order.pedido.entregado",
                              handle_pedido_entregado)
            consumer.register("app.order.pedido.cancelado",
                              handle_pedido_cancelado)
            consumer.register("app.menu.plato.creado",
                              handle_plato_creado)
            consumer.register("app.menu.plato.actualizado",
                              handle_plato_actualizado)
            consumer.register("app.menu.plato.desactivado",
                              handle_plato_desactivado)
            consumer.register("app.menu.categoria.creada",
                              handle_categoria_creada)
            consumer.register("app.menu.categoria.actualizada",
                              handle_categoria_actualizada)
            consumer.register("app.menu.categoria.desactivada",
                              handle_categoria_desactivada)

            logger.info("🚀 Loyalty consumer arrancado en background thread")
            consumer.start()

        except Exception:
            logger.exception("💥 Error arrancando loyalty consumer")

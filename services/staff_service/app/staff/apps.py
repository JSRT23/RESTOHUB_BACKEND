# staff_service/app/staff/apps.py
import logging
import os
import threading

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class StaffConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.staff"

    def ready(self):
        import app.staff.signals  # señales existentes — no tocar

        # En desarrollo con runserver hay doble ready(); solo arrancar una vez
        if os.environ.get("RUN_MAIN") == "true":
            return

        thread = threading.Thread(
            target=self._start_consumer,
            daemon=True,
            name="staff-consumer",
        )
        thread.start()

    def _start_consumer(self):
        import time
        time.sleep(5)  # esperar a que gunicorn/Django termine de arrancar

        try:
            from app.staff.infrastructure.messaging.consumer_base import BaseConsumer
            from app.staff.application.event_handlers.menu_handlers import (
                handle_restaurante_creado,
                handle_restaurante_actualizado,
                handle_restaurante_desactivado,
            )
            from app.staff.application.event_handlers.inventory_handlers import (
                handle_alerta_stock_bajo,
                handle_alerta_agotado,
                handle_alerta_vencimiento_proximo,
                handle_lote_vencido,
                handle_orden_compra_creada,
            )
            from app.staff.application.event_handlers.order_handlers import (
                handle_pedido_confirmado,
                handle_entrega_asignada,
            )

            consumer = BaseConsumer(service="staff")

            consumer.register("app.menu.restaurante.creado",
                              handle_restaurante_creado)
            consumer.register("app.menu.restaurante.actualizado",
                              handle_restaurante_actualizado)
            consumer.register("app.menu.restaurante.desactivado",
                              handle_restaurante_desactivado)
            consumer.register("app.inventory.alerta.stock_bajo",
                              handle_alerta_stock_bajo)
            consumer.register("app.inventory.alerta.agotado",
                              handle_alerta_agotado)
            consumer.register(
                "app.inventory.alerta.vencimiento_proximo", handle_alerta_vencimiento_proximo)
            consumer.register("app.inventory.lote.vencido",
                              handle_lote_vencido)
            consumer.register("app.inventory.orden_compra.creada",
                              handle_orden_compra_creada)
            consumer.register("app.order.pedido.confirmado",
                              handle_pedido_confirmado)
            consumer.register("app.order.entrega.asignada",
                              handle_entrega_asignada)

            logger.info("🚀 Staff consumer arrancado en background thread")
            consumer.start()

        except Exception:
            logger.exception("💥 Error arrancando staff consumer")

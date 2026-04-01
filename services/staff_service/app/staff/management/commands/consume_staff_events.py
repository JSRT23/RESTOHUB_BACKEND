# staff_service/app/staff/management/commands/consume_staff_events.py
import logging

from django.core.management.base import BaseCommand

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

logger = logging.getLogger(__name__)
# Log visible al iniciar el contenedor


class Command(BaseCommand):
    help = "Inicia el consumer de staff_service"

    def handle(self, *args, **options):
        print("🔵 Iniciando consumer de staff_services...")
        consumer = BaseConsumer(service="staff")

        # ── Restaurantes (menu_service) ───────────────────────
        consumer.register("app.menu.restaurante.creado",
                          handle_restaurante_creado)
        consumer.register("app.menu.restaurante.actualizado",
                          handle_restaurante_actualizado)
        consumer.register("app.menu.restaurante.desactivado",
                          handle_restaurante_desactivado)

        # ── Alertas de inventario (inventory_service) ─────────
        consumer.register("app.inventory.alerta.stock_bajo",
                          handle_alerta_stock_bajo)
        consumer.register("app.inventory.alerta.agotado",
                          handle_alerta_agotado)
        consumer.register("app.inventory.alerta.vencimiento_proximo",
                          handle_alerta_vencimiento_proximo)
        consumer.register("app.inventory.lote.vencido",
                          handle_lote_vencido)
        consumer.register("app.inventory.orden_compra.creada",
                          handle_orden_compra_creada)

        # ── Pedidos (order_service) ───────────────────────────
        consumer.register("app.order.pedido.confirmado",
                          handle_pedido_confirmado)
        consumer.register("app.order.entrega.asignada",
                          handle_entrega_asignada)

        logger.info("🚀 Staff consumer iniciado")
        consumer.start()

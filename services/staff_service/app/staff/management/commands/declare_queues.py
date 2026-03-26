# staff_service/app/staff/management/commands/declare_queues.py
import logging

import pika
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIGURACIÓN CENTRAL DE QUEUES
# ---------------------------------------------------------------------------
QUEUES = {
    # menu_service → solo restaurantes (lo único que staff necesita de menu)
    "staff.menu": [
        "app.menu.restaurante.*",
    ],
    # order_service → pedidos y entregas que afectan a cocina y repartidores
    "staff.order": [
        "app.order.pedido.confirmado",
        "app.order.comanda.creada",
        "app.order.comanda.lista",
        "app.order.entrega.asignada",
        "app.order.entrega.completada",
        "app.order.pedido.entregado",
    ],
    # inventory_service → alertas que generan AlertaOperacional en staff
    "staff.inventory": [
        "app.inventory.alerta.stock_bajo",
        "app.inventory.alerta.agotado",
        "app.inventory.alerta.vencimiento_proximo",
        "app.inventory.orden_compra.creada",
    ],
    # auditoría — escucha todo lo de staff (solo desarrollo)
    "staff.audit": [
        "app.staff.#",
    ],
}


class Command(BaseCommand):
    help = "Declara todas las queues y bindings de staff_service en RabbitMQ"

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

        # Exchange
        channel.exchange_declare(
            exchange=cfg["EXCHANGE"],
            exchange_type="topic",
            durable=True,
        )

        total_bindings = 0

        for queue_name, routing_keys in QUEUES.items():
            # queue_declare es idempotente — si ya existe no hace nada,
            # si no existe la crea. NUNCA queue_delete en producción.
            channel.queue_declare(queue=queue_name, durable=True)

            for routing_key in routing_keys:
                channel.queue_bind(
                    exchange=cfg["EXCHANGE"],
                    queue=queue_name,
                    routing_key=routing_key,
                )
                total_bindings += 1

            self.stdout.write(
                f"[OK] {queue_name} → {len(routing_keys)} bindings")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✔ {len(QUEUES)} queues declaradas "
                f"con {total_bindings} bindings\n"
            )
        )

        connection.close()
        self.stdout.write("[declare_queues] Finalizado.\n")

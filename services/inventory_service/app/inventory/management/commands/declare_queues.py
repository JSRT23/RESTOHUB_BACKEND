# inventory_service/app/inventory/management/commands/declare_queues.py
from django.core.management.base import BaseCommand

from app.inventory.infrastructure.messaging.connection import get_rabbitmq_connection
from app.inventory.infrastructure.messaging.topology import (
    get_bindings,
    get_dlq,
    get_dlx,
    get_exchange,
    get_queue,
)

SERVICE = "inventory"


class Command(BaseCommand):
    help = "Declara exchange, colas, DLQ y bindings para inventory_service"

    def handle(self, *args, **options):
        exchange = get_exchange()
        dlx = get_dlx()

        connection = get_rabbitmq_connection()
        channel = connection.channel()

        channel.exchange_declare(
            exchange=exchange,
            exchange_type="topic",
            durable=True,
        )
        self.stdout.write(f"✅ Exchange → {exchange}")

        channel.exchange_declare(
            exchange=dlx,
            exchange_type="direct",
            durable=True,
        )
        self.stdout.write(f"✅ DLX → {dlx}")

        queue_name = get_queue(SERVICE)
        dlq_name = get_dlq(SERVICE)

        channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange":    dlx,
                "x-dead-letter-routing-key": dlq_name,
            },
        )
        self.stdout.write(f"✅ Cola → {queue_name}")

        channel.queue_declare(queue=dlq_name, durable=True)
        channel.queue_bind(
            exchange=dlx,
            queue=dlq_name,
            routing_key=dlq_name,
        )
        self.stdout.write(f"✅ DLQ → {dlq_name}")

        self.stdout.write("\n🔗 Bindings:")
        for routing_key in get_bindings(SERVICE):
            channel.queue_bind(
                exchange=exchange,
                queue=queue_name,
                routing_key=routing_key,
            )
            self.stdout.write(f"   → {routing_key}")

        connection.close()
        self.stdout.write(self.style.SUCCESS(
            "\n✅ Topología de inventory_service declarada correctamente"
        ))

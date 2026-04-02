# loyalty_service/app/loyalty/management/commands/declare_queues.py
from django.core.management.base import BaseCommand

from app.loyalty.infrastructure.messaging.connection import get_rabbitmq_connection
from app.loyalty.infrastructure.messaging.topology import (
    get_bindings,
    get_dlq,
    get_dlx,
    get_exchange,
    get_queue,
)

SERVICE = "loyalty"


class Command(BaseCommand):
    help = "Declara exchange, colas, DLQ y bindings para loyalty_service"

    def handle(self, *args, **options):
        connection = get_rabbitmq_connection()
        channel = connection.channel()

        channel.exchange_declare(
            exchange=get_exchange(),
            exchange_type="topic",
            durable=True,
        )
        self.stdout.write(f"✅ Exchange → {get_exchange()}")

        channel.exchange_declare(
            exchange=get_dlx(),
            exchange_type="direct",
            durable=True,
        )
        self.stdout.write(f"✅ DLX → {get_dlx()}")

        queue_name = get_queue(SERVICE)
        dlq_name = get_dlq(SERVICE)

        channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange":    get_dlx(),
                "x-dead-letter-routing-key": dlq_name,
            },
        )
        self.stdout.write(f"✅ Cola → {queue_name}")

        channel.queue_declare(queue=dlq_name, durable=True)
        channel.queue_bind(
            exchange=get_dlx(),
            queue=dlq_name,
            routing_key=dlq_name,
        )
        self.stdout.write(f"✅ DLQ → {dlq_name}")

        self.stdout.write("\n🔗 Bindings:")
        for routing_key in get_bindings(SERVICE):
            channel.queue_bind(
                exchange=get_exchange(),
                queue=queue_name,
                routing_key=routing_key,
            )
            self.stdout.write(f"   → {routing_key}")

        connection.close()
        self.stdout.write(self.style.SUCCESS(
            "\n✅ Topología de loyalty_service declarada correctamente"
        ))

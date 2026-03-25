# menu_service/app/menu/management/commands/consume_menu_events.py
import json
import logging

import pika
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Escucha eventos de menu_service en modo auditoría (menu.audit)"

    def handle(self, *args, **kwargs):

        cfg = settings.RABBITMQ

        self.stdout.write("\n[menu_audit] Conectando a RabbitMQ...\n")

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

        # Asegurar exchange
        channel.exchange_declare(
            exchange=cfg["EXCHANGE"],
            exchange_type="topic",
            durable=True,
        )

        # Asegurar queue de auditoría
        channel.queue_declare(queue="menu.audit", durable=True)

        # Bind wildcard total
        channel.queue_bind(
            exchange=cfg["EXCHANGE"],
            queue="menu.audit",
            routing_key="app.menu.#",
        )

        self.stdout.write(
            "[menu_audit] Escuchando eventos... Ctrl+C para salir\n"
        )

        channel.basic_qos(prefetch_count=1)

        channel.basic_consume(
            queue="menu.audit",
            on_message_callback=self._callback,
        )

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            self.stdout.write("\n[menu_audit] Detenido por el usuario")
            channel.stop_consuming()
        finally:
            connection.close()
            self.stdout.write("[menu_audit] Conexión cerrada")

    # -----------------------------------------------------------------------
    # CALLBACK
    # -----------------------------------------------------------------------

    def _callback(self, channel, method, properties, body):

        try:
            message = json.loads(body)

            event_type = message.get("event_type", "—")
            event_id = message.get("event_id", "—")
            data = message.get("data", {})

            self.stdout.write(
                f"\n{'='*60}\n"
                f"EVENTO: {event_type}\n"
                f"ID    : {event_id}\n"
                f"DATA  : {json.dumps(data, indent=4, ensure_ascii=False)}\n"
            )

        except json.JSONDecodeError as e:
            self.stderr.write(f"[menu_audit] Error JSON: {e}")

        finally:
            channel.basic_ack(delivery_tag=method.delivery_tag)

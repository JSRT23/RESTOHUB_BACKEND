# menu_service/app/menu/management/commands/consume_menu_events.py

import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from app.menu.infrastructure.messaging.connection import get_channel

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Escucha eventos de menu_service en modo auditoría (queue: menu.audit)"

    def handle(self, *args, **kwargs):
        self.stdout.write("\n[menu_audit] Conectando a RabbitMQ...\n")

        channel = get_channel()

        # 🔥 1. Declarar exchange SIEMPRE
        channel.exchange_declare(
            exchange=settings.RABBITMQ["EXCHANGE"],
            exchange_type="topic",
            durable=True,
        )

        # 🔥 2. Declarar queue
        channel.queue_declare(
            queue="menu.audit",
            durable=True,
        )

        # 🔥 3. HACER EL BIND (ESTO ES LO QUE TE FALTABA)
        channel.queue_bind(
            exchange=settings.RABBITMQ["EXCHANGE"],
            queue="menu.audit",
            routing_key="app.menu.#",
        )

        self.stdout.write(
            "[menu_audit] Escuchando en menu.audit (app.menu.#) — Ctrl+C para salir\n"
        )

        channel.basic_qos(prefetch_count=1)

        channel.basic_consume(
            queue="menu.audit",
            on_message_callback=self._on_message,
        )

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            self.stdout.write("\n[menu_audit] Detenido por el usuario")
            channel.stop_consuming()
        finally:
            try:
                channel.connection.close()
            except Exception:
                pass
            self.stdout.write("[menu_audit] Conexión cerrada\n")

    # -----------------------------------------------------------------------
    # CALLBACK
    # -----------------------------------------------------------------------

    def _on_message(self, channel, method, properties, body):
        try:
            message = json.loads(body)

            event_type = message.get("event_type", "—")
            event_id = message.get("event_id", "—")
            data = message.get("data", {})

            self.stdout.write(
                f"\n🔥🔥 EVENTO RECIBIDO 🔥🔥\n"
                f"{'=' * 60}\n"
                f"ROUTING: {method.routing_key}\n"
                f"EVENTO : {event_type}\n"
                f"ID     : {event_id}\n"
                f"DATA   : {json.dumps(data, indent=4, ensure_ascii=False)}\n"
            )

        except json.JSONDecodeError as e:
            self.stderr.write(f"[menu_audit] JSON inválido: {e}")

        finally:
            channel.basic_ack(delivery_tag=method.delivery_tag)

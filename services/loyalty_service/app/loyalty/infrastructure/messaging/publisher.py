# loyalty_service/app/loyalty/infrastructure/messaging/publisher.py
import json
import logging
import uuid
from datetime import datetime, timezone

import pika
from django.conf import settings

from .connection import get_rabbitmq_connection
from .topology import get_exchange

logger = logging.getLogger(__name__)

_publisher: "EventPublisher | None" = None


def get_publisher() -> "EventPublisher":
    global _publisher

    if _publisher is None:
        _publisher = EventPublisher()
        return _publisher

    try:
        if _publisher.channel is None or _publisher.channel.is_closed:
            logger.warning("⚠️ Canal publisher cerrado — recreando")
            _publisher = EventPublisher()
    except Exception:
        _publisher = EventPublisher()

    return _publisher


class EventPublisher:
    def __init__(self):
        connection = get_rabbitmq_connection()
        self.channel = connection.channel()

        self.channel.exchange_declare(
            exchange=get_exchange(),
            exchange_type="topic",
            durable=True,
        )
        self.channel.confirm_delivery()
        logger.info("📤 EventPublisher (loyalty) listo")

    def publish(self, event_type: str, data: dict) -> bool:
        envelope = {
            "event_id":       str(uuid.uuid4()),
            "event_type":     event_type,
            "timestamp":      datetime.now(tz=timezone.utc).isoformat(),
            "service_origin": getattr(settings, "SERVICE_NAME", "loyalty_service"),
            "version":        "1.0",
            "data":           data,
        }

        try:
            self.channel.basic_publish(
                exchange=get_exchange(),
                routing_key=event_type,
                body=json.dumps(envelope),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
            )
            logger.info(f"📤 Publicado → {event_type}")
            return True

        except pika.exceptions.UnroutableError:
            logger.error(f"🚫 Sin destino → {event_type}")
            return False

        except Exception:
            logger.exception(f"💥 Error publicando '{event_type}'")
            return False

# menu_service/app/menu/infrastructure/messaging/publisher.py
# menu_service/app/menu/infrastructure/messaging/publisher.py

import json
import logging
import pika
from django.conf import settings

from app.menu.events.builders import build_event
from app.menu.infrastructure.messaging.connection import get_channel

logger = logging.getLogger(__name__)


def publish_event(event_type: str, data: dict) -> None:
    try:
        message = build_event(event_type, data)
        body = json.dumps(message, default=str)

        channel = get_channel()

        channel.basic_publish(
            exchange=settings.RABBITMQ["EXCHANGE"],
            routing_key=event_type,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )

        print(f"📡 EVENTO PUBLICADO: {event_type}")

    except Exception:
        logger.exception("[publisher] Error publicando evento")

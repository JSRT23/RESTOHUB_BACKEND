import json
import logging
import uuid
from datetime import datetime, timezone

import pika

from django.conf import settings
from app.menu.infrastructure.messaging.connection import get_channel

logger = logging.getLogger(__name__)


def _build_message(event_type: str, data: dict) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service_origin": "menu_service",
        "version": "1.0",
        "data": data,
    }


def publish_event(event_type: str, data: dict) -> None:
    try:
        message = _build_message(event_type, data)
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

    except Exception as e:

        raise

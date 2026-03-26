# staff_service/app/staff/infrastructure/messaging/publisher.py
import json
import logging

import pika
from django.conf import settings

from app.staff.events.builders import build_event
from app.staff.infrastructure.messaging.connection import get_channel

logger = logging.getLogger(__name__)


def publish_event(event_type: str, data: dict) -> None:
    """
    Publica un evento en RabbitMQ.

    - Construye el envelope estándar via build_event() (builders.py).
    - Usa el canal singleton de connection.py (reconecta automáticamente).
    - En caso de error loguea y NO relanza — un fallo de mensajería nunca
      debe abortar una operación de base de datos ya confirmada.
    """
    try:
        message = build_event(event_type, data)
        body = json.dumps(message, default=str)

        channel = get_channel()
        channel.basic_publish(
            exchange=settings.RABBITMQ["EXCHANGE"],
            routing_key=event_type,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,                # persistente
                content_type="application/json",
            ),
        )
        logger.debug("[publisher] Publicado: %s", event_type)

    except Exception:
        # Logueamos con stack trace completo pero NO relanzamos.
        # El signal ya terminó su trabajo en DB; perder el evento es
        # preferible a revertir una transacción por un fallo de red.
        logger.exception(
            "[publisher] Error publicando evento '%s'", event_type)

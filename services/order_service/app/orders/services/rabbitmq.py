import json
import uuid
import logging
import os
import pika
import pika.exceptions
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# Config desde variables de entorno
# ─────────────────────────────────────────
RABBIT_HOST = os.getenv("RABBITMQ_HOST",     "rabbitmq")
RABBIT_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBIT_USER = os.getenv("RABBITMQ_USER",     "guest")
RABBIT_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBIT_VHOST = os.getenv("RABBITMQ_VHOST",    "/")
EXCHANGE_NAME = os.getenv("RABBITMQ_EXCHANGE", "restohub")

# ─────────────────────────────────────────
# Conexión persistente
# ─────────────────────────────────────────
_connection = None
_channel = None


def _get_channel():
    global _connection, _channel

    try:
        if _connection is None or _connection.is_closed:
            credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
            params = pika.ConnectionParameters(
                host=RABBIT_HOST,
                port=RABBIT_PORT,
                virtual_host=RABBIT_VHOST,
                credentials=credentials,
                heartbeat=60,
                blocked_connection_timeout=30,
            )
            _connection = pika.BlockingConnection(params)
            logger.info("[RabbitMQ] Conexión establecida con %s", RABBIT_HOST)

        if _channel is None or _channel.is_closed:
            _channel = _connection.channel()
            _channel.exchange_declare(
                exchange=EXCHANGE_NAME,
                exchange_type="topic",
                durable=True,
            )
            logger.info("[RabbitMQ] Canal listo — exchange '%s'",
                        EXCHANGE_NAME)

    except pika.exceptions.AMQPConnectionError as e:
        logger.error("[RabbitMQ] No se pudo conectar: %s", e)
        _connection = None
        _channel = None
        raise

    return _channel


def _build_message(event_type: str, data: dict) -> dict:
    return {
        "event_id":       str(uuid.uuid4()),
        "event_type":     event_type,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "service_origin": "order_service",
        "version":        "1.0",
        "data":           data,
    }


def publish_event(event_type: str, data: dict) -> bool:
    """
    Publica un evento en el exchange topic de RabbitMQ.
    Retorna True si se publicó, False si falló — nunca lanza excepción.
    """
    message = _build_message(event_type, data)

    try:
        channel = _get_channel()
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=event_type,
            body=json.dumps(message, default=str),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
        logger.info("[RabbitMQ] ✓ %s | event_id: %s",
                    event_type, message["event_id"])
        return True

    except pika.exceptions.AMQPConnectionError as e:
        logger.error(
            "[RabbitMQ] ✗ Conexión caída al publicar '%s': %s", event_type, e)
        global _connection, _channel
        _connection = None
        _channel = None
        return False

    except Exception as e:
        logger.error(
            "[RabbitMQ] ✗ Error inesperado al publicar '%s': %s", event_type, e)
        return False

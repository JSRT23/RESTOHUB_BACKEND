import json
import uuid
import logging
import os
import pika
import pika.exceptions
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

RABBIT_HOST = os.getenv("RABBITMQ_HOST",     "rabbitmq")
RABBIT_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBIT_USER = os.getenv("RABBITMQ_USER",     "guest")
RABBIT_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBIT_VHOST = os.getenv("RABBITMQ_VHOST",    "/")
EXCHANGE_NAME = os.getenv("RABBITMQ_EXCHANGE", "restohub")

_connection = None
_channel = None


def _is_connected() -> bool:
    try:
        return (
            _connection is not None and _connection.is_open
            and _channel is not None and _channel.is_open
        )
    except Exception:
        return False


def _connect():
    global _connection, _channel
    credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
    params = pika.ConnectionParameters(
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        virtual_host=RABBIT_VHOST,
        credentials=credentials,
        heartbeat=120,
        blocked_connection_timeout=30,
        connection_attempts=3,
        retry_delay=2,
    )
    _connection = pika.BlockingConnection(params)
    _channel = _connection.channel()
    _channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="topic",
        durable=True,
    )
    logger.info("[RabbitMQ] inventory_service conectado a %s", RABBIT_HOST)


def _get_channel():
    global _connection, _channel
    if not _is_connected():
        try:
            if _connection and not _connection.is_closed:
                _connection.close()
        except Exception:
            pass
        _connection = None
        _channel = None
        _connect()
    return _channel


def _build_message(event_type: str, data: dict) -> dict:
    return {
        "event_id":       str(uuid.uuid4()),
        "event_type":     event_type,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "service_origin": "inventory_service",
        "version":        "1.0",
        "data":           data,
    }


def publish_event(event_type: str, data: dict) -> bool:
    """
    Publica un evento en RabbitMQ.
    Reconecta automáticamente si la conexión está caída.
    Nunca lanza excepción — no interrumpe el flujo principal.
    """
    global _connection, _channel
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

    except (
        pika.exceptions.AMQPConnectionError,
        pika.exceptions.StreamLostError,
        pika.exceptions.ConnectionClosedByBroker,
    ) as e:
        logger.warning(
            "[RabbitMQ] Conexión caída (%s) — reintentando...", type(e).__name__)
        _connection = None
        _channel = None
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
            logger.info("[RabbitMQ] ✓ %s (reintento ok)", event_type)
            return True
        except Exception as retry_err:
            logger.error("[RabbitMQ] ✗ Reintento fallido '%s': %s",
                         event_type, retry_err)
            return False

    except Exception as e:
        logger.error("[RabbitMQ] ✗ Error inesperado '%s': %s", event_type, e)
        return False

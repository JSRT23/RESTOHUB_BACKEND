import json
import logging
import os
import uuid
from datetime import datetime, timezone

import pika
import pika.exceptions

logger = logging.getLogger(__name__)

EXCHANGE_NAME = os.getenv("RABBITMQ_EXCHANGE", "restohub")

_connection = None
_channel = None


# ---------------------------------------------------------------------------
# Gestión de conexión
# ---------------------------------------------------------------------------

def _is_connected() -> bool:
    try:
        return (
            _connection is not None and _connection.is_open
            and _channel is not None and _channel.is_open
        )
    except Exception:
        return False


def _connect() -> None:
    global _connection, _channel

    from django.conf import settings
    cfg = settings.RABBITMQ

    credentials = pika.PlainCredentials(cfg["USER"], cfg["PASSWORD"])
    params = pika.ConnectionParameters(
        host=cfg["HOST"],
        port=cfg["PORT"],
        virtual_host=cfg["VHOST"],
        credentials=credentials,
        heartbeat=120,
        connection_attempts=3,
        retry_delay=2,
        blocked_connection_timeout=30,
    )
    _connection = pika.BlockingConnection(params)
    _channel = _connection.channel()
    _channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="topic",
        durable=True,
    )
    logger.info("[order_rabbitmq] Conectado al exchange '%s'", EXCHANGE_NAME)


def _get_channel():
    global _connection, _channel

    if not _is_connected():
        logger.warning(
            "[order_rabbitmq] Canal no disponible — reconectando...")
        try:
            if _connection and not _connection.is_closed:
                _connection.close()
        except Exception:
            pass
        _connection = None
        _channel = None
        _connect()

    return _channel


# ---------------------------------------------------------------------------
# Construcción del mensaje
# ---------------------------------------------------------------------------

def _build_message(event_type: str, data: dict) -> dict:
    return {
        "event_id":       str(uuid.uuid4()),
        "event_type":     event_type,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "service_origin": "order_service",
        "version":        "1.0",
        "data":           data,
    }


# ---------------------------------------------------------------------------
# Publicación — nunca lanza excepción
# ---------------------------------------------------------------------------

def publish_event(event_type: str, data: dict) -> None:
    message = _build_message(event_type, data)
    body = json.dumps(message, default=str)

    try:
        channel = _get_channel()
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=event_type,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )
        logger.debug(
            "[order_rabbitmq] Publicado '%s' | event_id: %s",
            event_type, message["event_id"],
        )

    except pika.exceptions.AMQPConnectionError as exc:
        logger.error(
            "[order_rabbitmq] Conexión caída al publicar '%s': %s", event_type, exc
        )
        global _connection, _channel
        _connection = None
        _channel = None

    except Exception as exc:
        logger.error(
            "[order_rabbitmq] Error inesperado al publicar '%s': %s", event_type, exc
        )

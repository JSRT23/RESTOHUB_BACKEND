# staff_sercevice/app/staff/infrastructure/messaging/connection.py
import pika
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

_connection = None
_channel = None


def _build_parameters():
    cfg = settings.RABBITMQ

    credentials = pika.PlainCredentials(
        cfg["USER"],
        cfg["PASSWORD"]
    )

    return pika.ConnectionParameters(
        host=cfg["HOST"],
        port=cfg["PORT"],
        virtual_host=cfg["VHOST"],
        credentials=credentials,
        heartbeat=cfg.get("HEARTBEAT", 120),
        blocked_connection_timeout=cfg.get("BLOCKED_CONNECTION_TIMEOUT", 30),
        connection_attempts=cfg.get("CONNECTION_ATTEMPTS", 5),
        retry_delay=cfg.get("RETRY_DELAY", 3),
        client_properties={"connection_name": "staff_service"}
    )


def _connect():
    global _connection, _channel

    params = _build_parameters()

    _connection = pika.BlockingConnection(params)
    _channel = _connection.channel()

    _channel.exchange_declare(
        exchange=settings.RABBITMQ["EXCHANGE"],
        exchange_type="topic",
        durable=True,
    )

    logger.info("[RabbitMQ] Conectado (staff_service)")


def get_channel():
    global _connection, _channel

    try:
        if _connection and _connection.is_open and _channel and _channel.is_open:
            return _channel
    except Exception:
        pass

    try:
        if _connection:
            _connection.close()
    except Exception:
        pass

    _connection = None
    _channel = None

    _connect()
    return _channel

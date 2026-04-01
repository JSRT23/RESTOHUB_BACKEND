# staff_service/app/staff/infrastructure/messaging/connection.py
import logging
import threading

import pika
from django.conf import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_connection: pika.BlockingConnection | None = None


def _build_parameters() -> pika.ConnectionParameters:
    r = settings.RABBITMQ
    return pika.ConnectionParameters(
        host=r["HOST"],
        port=r["PORT"],
        virtual_host=r["VHOST"],
        credentials=pika.PlainCredentials(r["USER"], r["PASSWORD"]),
        heartbeat=600,
        blocked_connection_timeout=300,
    )


def get_rabbitmq_connection() -> pika.BlockingConnection:
    """
    Singleton de conexión. Una sola TCP por proceso.
    Recrea si la conexión está cerrada.
    """
    global _connection

    with _lock:
        if _connection is None or _connection.is_closed:
            logger.info("🐇 Creando conexión a RabbitMQ (staff)...")
            _connection = pika.BlockingConnection(_build_parameters())
            logger.info("✅ Conexión establecida")

    return _connection


def close_connection() -> None:
    global _connection

    with _lock:
        if _connection and not _connection.is_closed:
            try:
                _connection.close()
                logger.info("🔌 Conexión RabbitMQ cerrada")
            except Exception:
                logger.exception("Error cerrando conexión")
        _connection = None

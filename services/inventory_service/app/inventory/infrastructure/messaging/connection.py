# inventory_service/app/inventory/infrastructure/messaging/connection.py
import logging
import threading

import pika
from django.conf import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_connection: pika.BlockingConnection | None = None


def _build_parameters() -> pika.ConnectionParameters:
    return pika.ConnectionParameters(
        host=settings.RABBITMQ["HOST"],
        port=settings.RABBITMQ["PORT"],
        virtual_host=settings.RABBITMQ["VHOST"],
        credentials=pika.PlainCredentials(
            settings.RABBITMQ["USER"],
            settings.RABBITMQ["PASSWORD"],
        ),
        heartbeat=600,
        blocked_connection_timeout=300,
    )


def get_rabbitmq_connection() -> pika.BlockingConnection:
    """
    Singleton de conexión a RabbitMQ.

    - Una sola conexión TCP por proceso.
    - Thread-safe: usa un lock para evitar doble creación.
    - Si la conexión está cerrada, la recrea automáticamente.

    Cada operación que necesite un canal debe pedir
    connection.channel() — los canales son baratos, las conexiones no.
    """
    global _connection

    with _lock:
        if _connection is None or _connection.is_closed:
            logger.info("🐇 Creando conexión a RabbitMQ...")
            _connection = pika.BlockingConnection(_build_parameters())
            logger.info("✅ Conexión establecida")

    return _connection


def close_connection() -> None:
    """Cierra la conexión global (usar solo en shutdown)."""
    global _connection

    with _lock:
        if _connection and not _connection.is_closed:
            try:
                _connection.close()
                logger.info("🔌 Conexión RabbitMQ cerrada")
            except Exception:
                logger.exception("Error cerrando conexión")
        _connection = None

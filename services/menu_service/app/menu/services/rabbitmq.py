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
    """Verifica si la conexión y canal están activos sin lanzar excepción."""
    try:
        return (
            _connection is not None and _connection.is_open
            and _channel is not None and _channel.is_open
        )
    except Exception:
        return False


def _connect() -> None:
    """
    Abre conexión y canal. Declara el exchange topic durable.
    Llamado internamente por _get_channel() — nunca directamente.
    """
    global _connection, _channel

    from django.conf import settings
    cfg = settings.RABBITMQ

    credentials = pika.PlainCredentials(cfg["USER"], cfg["PASSWORD"])
    params = pika.ConnectionParameters(
        host=cfg["HOST"],
        port=cfg["PORT"],
        virtual_host=cfg["VHOST"],
        credentials=credentials,
        heartbeat=120,              # staff también usa 120
        connection_attempts=3,      # reintentos automáticos al conectar
        retry_delay=2,              # segundos entre intentos
        blocked_connection_timeout=30,
    )
    _connection = pika.BlockingConnection(params)
    _channel = _connection.channel()
    _channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="topic",
        durable=True,
    )
    logger.info("[menu_rabbitmq] Conectado al exchange '%s'", EXCHANGE_NAME)


def _get_channel():
    """
    Retorna el canal activo. Si la conexión está caída la reconecta.
    Resetea _connection/_channel antes de reconectar para evitar
    estados inconsistentes con el socket anterior.
    """
    global _connection, _channel

    if not _is_connected():
        logger.warning("[menu_rabbitmq] Canal no disponible — reconectando...")
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
    """
    Estructura estándar de todos los eventos de menu_service.

    {
        "event_id":       UUID único por evento (idempotencia en consumidores)
        "event_type":     routing key exacta  (ej: "app.menu.plato.created")
        "timestamp":      ISO 8601 UTC
        "service_origin": "menu_service"
        "version":        "1.0"
        "data":           payload específico del evento
    }
    """
    return {
        "event_id":       str(uuid.uuid4()),
        "event_type":     event_type,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "service_origin": "menu_service",
        "version":        "1.0",
        "data":           data,
    }


# ---------------------------------------------------------------------------
# Publicación
# Nunca lanza excepción — el save() del modelo nunca se interrumpe.
# Si RabbitMQ no está disponible el evento se pierde pero la operación
# de negocio se completa. En producción usar outbox pattern para garantía.
# ---------------------------------------------------------------------------

def publish_event(event_type: str, data: dict) -> None:
    message = _build_message(event_type, data)
    body = json.dumps(message, default=str)

    try:
        channel = _get_channel()
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=event_type,        # consumidores filtran con wildcards
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,           # persistente: sobrevive restart del broker
                content_type="application/json",
            ),
        )
        logger.debug(
            "[menu_rabbitmq] Publicado '%s' | event_id: %s",
            event_type, message["event_id"],
        )

    except pika.exceptions.AMQPConnectionError as exc:
        logger.error(
            "[menu_rabbitmq] Conexión caída al publicar '%s': %s", event_type, exc
        )
        # Resetear para forzar reconexión en el próximo evento
        global _connection, _channel
        _connection = None
        _channel = None

    except Exception as exc:
        logger.error(
            "[menu_rabbitmq] Error inesperado al publicar '%s': %s", event_type, exc
        )

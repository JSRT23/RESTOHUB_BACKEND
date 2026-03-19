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
# Conexión persistente (singleton)
# ─────────────────────────────────────────
_connection = None
_channel = None


def _get_channel():
    """
    Retorna el canal activo. Si la conexión está caída la reconecta.
    Usa una sola conexión reutilizable en lugar de abrir/cerrar
    en cada evento (mucho más eficiente).
    """
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
            # Exchange topic: permite rutas como app.menu.plato.*
            # Varios servicios pueden suscribirse con sus propias queues
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


# ─────────────────────────────────────────
# Payload estándar
# ─────────────────────────────────────────
def _build_message(event_type: str, data: dict) -> dict:
    """
    Estructura estándar para todos los eventos de menu_service.

    {
        "event_id":       "uuid4",
        "event_type":     "app.menu.plato.created",
        "timestamp":      "2025-01-01T12:00:00+00:00",
        "service_origin": "menu_service",
        "version":        "1.0",
        "data": { ... payload específico ... }
    }

    - event_id: UUID único por evento, permite idempotencia en consumidores.
    - service_origin: identifica de qué servicio viene sin ambigüedad.
    - version: facilita migraciones futuras del schema del evento.
    """
    return {
        "event_id":       str(uuid.uuid4()),
        "event_type":     event_type,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "service_origin": "menu_service",
        "version":        "1.0",
        "data":           data,
    }


# ─────────────────────────────────────────
# Publicación
# ─────────────────────────────────────────
def publish_event(event_type: str, data: dict) -> bool:
    """
    Publica un evento en el exchange topic de RabbitMQ.

    El routing_key ES el event_type (ej: "app.menu.plato.created"),
    lo que permite a los consumidores suscribirse con wildcards:
        - "app.menu.plato.*"  → solo eventos de plato
        - "app.menu.#"        → todos los eventos de menu_service
        - "app.#"             → todos los eventos de la plataforma

    Si RabbitMQ no está disponible, loguea el error y retorna False
    sin lanzar excepción — el save() del modelo no se interrumpe.
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
                delivery_mode=2,        # persistente: sobrevive restart del broker
            ),
        )
        logger.info(
            "[RabbitMQ] ✓ %s | event_id: %s",
            event_type,
            message["event_id"],
        )
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

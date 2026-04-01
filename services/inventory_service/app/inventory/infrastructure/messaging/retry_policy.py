# inventory_service/app/inventory/infrastructure/messaging/retry_policy.py
import logging

from .topology import MAX_RETRIES

logger = logging.getLogger(__name__)


def get_retry_count(properties) -> int:
    """
    Extrae cuántas veces fue reintentado el mensaje.
    RabbitMQ llena x-death automáticamente en cada NACK + requeue=False.
    """
    headers = properties.headers or {}
    x_death = headers.get("x-death", [])

    if not x_death:
        return 0

    # x-death es una lista de dicts; el primero es el más reciente
    return x_death[0].get("count", 0)


def should_retry(properties) -> bool:
    """True si todavía quedan intentos disponibles."""
    return get_retry_count(properties) < MAX_RETRIES


def get_backoff_seconds(properties) -> float:
    """
    Backoff exponencial: 2^intento segundos.
    intento 0 → 1s  (primer fallo)
    intento 1 → 2s
    intento 2 → 4s
    intento 3 → DLQ (no se llama este método)
    """
    count = get_retry_count(properties)
    return 2 ** count

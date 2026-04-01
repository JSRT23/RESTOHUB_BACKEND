# staff_service/app/staff/infrastructure/messaging/retry_policy.py
import logging

from .topology import MAX_RETRIES

logger = logging.getLogger(__name__)


def get_retry_count(properties) -> int:
    headers = properties.headers or {}
    x_death = headers.get("x-death", [])
    if not x_death:
        return 0
    return x_death[0].get("count", 0)


def should_retry(properties) -> bool:
    return get_retry_count(properties) < MAX_RETRIES


def get_backoff_seconds(properties) -> float:
    """
    Backoff exponencial: 2^intento segundos.
    intento 0 → 1s | 1 → 2s | 2 → 4s | 3+ → DLQ
    """
    return 2 ** get_retry_count(properties)

# order_service/app/orders/infrastructure/messaging/retry_policy.py
from .topology import MAX_RETRIES


def get_retry_count(properties) -> int:
    headers = properties.headers or {}
    x_death = headers.get("x-death", [])
    if not x_death:
        return 0
    return x_death[0].get("count", 0)


def should_retry(properties) -> bool:
    return get_retry_count(properties) < MAX_RETRIES


def get_backoff_seconds(properties) -> float:
    """2^intento: 1s → 2s → 4s → DLQ"""
    return 2 ** get_retry_count(properties)

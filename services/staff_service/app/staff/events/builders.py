# staff_service/app/staff/events/builders.py
import uuid
from datetime import datetime, timezone


def build_event(event_type: str, data: dict) -> dict:
    """
    Construye la estructura estándar de eventos para RabbitMQ.
    Todos los microservicios deben respetar este formato para mantener
    consistencia en el ecosistema RestoHub.
    """
    return {
        "event_id":       str(uuid.uuid4()),
        "event_type":     event_type,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "service_origin": "staff_service",
        "version":        "1.0",
        "data":           data,
    }

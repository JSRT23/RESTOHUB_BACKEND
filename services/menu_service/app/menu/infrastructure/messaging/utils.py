# menu_service/app/menu/infrastructure/messaging/utils.py

from app.menu.infrastructure.messaging.publisher import publish_event


def publish_after_commit(event_type: str, data: dict):
    """
    🔥 FIX CRÍTICO:
    Eliminamos on_commit porque en Docker + DRF puede provocar
    comportamiento intermitente (uno sí / uno no).

    Publicamos directo.
    """
    print(f"📡 PUBLICANDO EVENTO DIRECTO: {event_type}")
    publish_event(event_type, data)

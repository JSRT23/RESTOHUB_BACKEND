import uuid
from datetime import datetime

from app.menu.infrastructure.messaging.core.connection import crear_canal
from app.menu.infrastructure.messaging.core.serializer import SerializadorEventos
from app.menu.infrastructure.messaging.config.exchanges import declarar_exchange
from django.conf import settings


class PublicadorEventoMixin:

    def publicar_evento(self, event_type: str, data: dict):
        conexion, canal = crear_canal()

        declarar_exchange(canal)

        evento = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "service_origin": "menu_service",
            "version": "1.0",
            "data": data
        }

        print(f"📤 Publicando evento: {event_type}")

        mensaje = SerializadorEventos.serializar(evento)

        canal.basic_publish(
            exchange=settings.RABBITMQ["EXCHANGE"],
            routing_key=event_type,
            body=mensaje,
        )

        conexion.close()

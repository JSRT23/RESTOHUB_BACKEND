# menu_service/app/menu/infrastructure/messaging/producer/publisher.py
import json
import pika
import logging

from django.conf import settings

from messaging.core.connection import get_connection
from messaging.core.serializer import EventSerializer
from messaging.config.exchanges import Exchanges


logger = logging.getLogger(__name__)


class Publisher:
    """
    Encargado de publicar eventos en RabbitMQ.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.connection = None
        self.channel = None

        self._connect()

    # =========================================================
    # 🔌 CONEXIÓN
    # =========================================================

    def _connect(self):
        try:
            self.connection = get_connection()
            self.channel = self.connection.channel()

            # Declarar exchange (idempotente)
            self.channel.exchange_declare(
                exchange=Exchanges.MENU,
                exchange_type="topic",
                durable=True
            )

        except Exception as e:
            logger.error(f"Error conectando a RabbitMQ: {e}")
            raise

    # =========================================================
    # 📡 PUBLICAR EVENTO
    # =========================================================

    def publish(self, event_type: str, data: dict):
        """
        Publica un evento en RabbitMQ.
        """

        try:
            event = EventSerializer.build_event(
                event_type=event_type,
                data=data,
                service=self.service_name
            )

            self.channel.basic_publish(
                exchange=Exchanges.MENU,
                routing_key=event_type,
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2  # persistente
                )
            )

            logger.info(f"Evento publicado: {event_type}")

        except Exception as e:
            logger.error(f"Error publicando evento {event_type}: {e}")
            raise

    # =========================================================
    # ❌ CERRAR CONEXIÓN
    # =========================================================

    def close(self):
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except Exception as e:
            logger.warning(f"Error cerrando conexión RabbitMQ: {e}")

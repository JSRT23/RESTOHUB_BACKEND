# menu_service/app/menu/infrastructure/messaging/mixins/publish_event.py
import ssl
import uuid
import logging
from datetime import datetime

import pika
from django.conf import settings

from app.menu.infrastructure.messaging.core.serializer import SerializadorEventos
from app.menu.infrastructure.messaging.config.exchanges import declarar_exchange

logger = logging.getLogger(__name__)


class PublicadorEventoMixin:
    _rabbitmq_conexion = None
    _rabbitmq_canal = None

    def _get_canal(self):
        if self._rabbitmq_canal is None or self._rabbitmq_canal.is_closed:
            rmq = settings.RABBITMQ

            credenciales = pika.PlainCredentials(rmq["USER"], rmq["PASSWORD"])
            parametros = pika.ConnectionParameters(
                host=rmq["HOST"],
                port=rmq["PORT"],
                virtual_host=rmq["VHOST"],
                credentials=credenciales,
                heartbeat=rmq["HEARTBEAT"],
                blocked_connection_timeout=rmq["BLOCKED_CONNECTION_TIMEOUT"],
                connection_attempts=rmq["CONNECTION_ATTEMPTS"],
                retry_delay=rmq["RETRY_DELAY"],
            )

            # SSL para CloudAMQP
            if rmq.get("USE_SSL"):
                ssl_context = ssl.create_default_context()
                parametros.ssl_options = pika.SSLOptions(
                    ssl_context, rmq["HOST"])

            self._rabbitmq_conexion = pika.BlockingConnection(parametros)
            self._rabbitmq_canal = self._rabbitmq_conexion.channel()
            declarar_exchange(self._rabbitmq_canal)

        return self._rabbitmq_canal

    def publicar_evento(self, event_type: str, data: dict):
        evento = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "service_origin": "menu_service",
            "version": "1.0",
            "data": data,
        }

        try:
            canal = self._get_canal()
            canal.basic_publish(
                exchange=settings.RABBITMQ["EXCHANGE"],
                routing_key=event_type,
                body=SerializadorEventos.serializar(evento),
                properties=pika.BasicProperties(delivery_mode=2),
            )
            logger.info(f"📤 Evento publicado: {event_type}")
        except Exception as e:
            logger.error(f"❌ Error publicando evento {event_type}: {e}")
        finally:
            self._cerrar_conexion()

    def _cerrar_conexion(self):
        try:
            if self._rabbitmq_conexion and not self._rabbitmq_conexion.is_closed:
                self._rabbitmq_conexion.close()
        except Exception as e:
            logger.warning(f"⚠️ Error cerrando conexión RabbitMQ: {e}")
        finally:
            self._rabbitmq_conexion = None
            self._rabbitmq_canal = None

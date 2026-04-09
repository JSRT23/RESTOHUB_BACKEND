# menu_service/app/menu/infrastructure/messaging/mixins/publish_event.py
import uuid
import logging
from datetime import datetime

import pika
from django.conf import settings

from app.menu.infrastructure.messaging.core.serializer import SerializadorEventos
from app.menu.infrastructure.messaging.config.exchanges import declarar_exchange

logger = logging.getLogger(__name__)


class PublicadorEventoMixin:
    """
    Mixin que añade publicación de eventos a RabbitMQ sobre cualquier ViewSet.

    Mejora respecto a la versión anterior:
    - Usa una sola conexión por request (lazy init).
    - Cierra la conexión al finalizar el ciclo de vida del objeto.
    - Loggea errores en lugar de silenciarlos.
    """

    _rabbitmq_conexion = None
    _rabbitmq_canal = None

    # ─────────────────────────────────────────
    # Conexión lazy (se abre solo cuando se necesita)
    # ─────────────────────────────────────────

    def _get_canal(self):
        if self._rabbitmq_canal is None or self._rabbitmq_canal.is_closed:
            credenciales = pika.PlainCredentials(
                settings.RABBITMQ["USER"],
                settings.RABBITMQ["PASSWORD"]
            )
            parametros = pika.ConnectionParameters(
                host=settings.RABBITMQ["HOST"],
                port=settings.RABBITMQ["PORT"],
                virtual_host=settings.RABBITMQ["VHOST"],
                credentials=credenciales,
                heartbeat=settings.RABBITMQ["HEARTBEAT"],
                blocked_connection_timeout=settings.RABBITMQ["BLOCKED_CONNECTION_TIMEOUT"],
                connection_attempts=settings.RABBITMQ["CONNECTION_ATTEMPTS"],
                retry_delay=settings.RABBITMQ["RETRY_DELAY"],
            )
            self._rabbitmq_conexion = pika.BlockingConnection(parametros)
            self._rabbitmq_canal = self._rabbitmq_conexion.channel()
            declarar_exchange(self._rabbitmq_canal)

        return self._rabbitmq_canal

    # ─────────────────────────────────────────
    # Publicar evento
    # ─────────────────────────────────────────

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
                properties=pika.BasicProperties(
                    delivery_mode=2),  # persistente
            )
            logger.info(f"📤 Evento publicado: {event_type}")
        except Exception as e:
            logger.error(f"❌ Error publicando evento {event_type}: {e}")
        finally:
            self._cerrar_conexion()

    # ─────────────────────────────────────────
    # Cierre seguro
    # ─────────────────────────────────────────

    def _cerrar_conexion(self):
        try:
            if self._rabbitmq_conexion and not self._rabbitmq_conexion.is_closed:
                self._rabbitmq_conexion.close()
        except Exception as e:
            logger.warning(f"⚠️ Error cerrando conexión RabbitMQ: {e}")
        finally:
            self._rabbitmq_conexion = None
            self._rabbitmq_canal = None

# inventory_service/app/inventory/infrastructure/messaging/consumer_base.py
import json
import logging
import time

import pika

from .connection import get_rabbitmq_connection
from .retry_policy import get_backoff_seconds, should_retry
from .topology import get_bindings, get_dlq, get_dlx, get_exchange, get_queue

logger = logging.getLogger(__name__)


class BaseConsumer:
    """
    Consumer base para inventory_service.

    ✅ Reconexión automática con backoff
    ✅ NACK real (no ACK en fallo)
    ✅ Backoff exponencial entre reintentos (x-death)
    ✅ Dead Letter Queue después de MAX_RETRIES
    ✅ Router interno: routing_key → handler
    ✅ prefetch_count=1
    """

    def __init__(self, service: str):
        self.service = service
        self.queue_name = get_queue(service)
        self.dlq_name = get_dlq(service)
        self.routing_keys = get_bindings(service)

        self._handlers: dict[str, callable] = {}

        self.connection = None
        self.channel = None

    def register(self, event_type: str, handler: callable) -> None:
        self._handlers[event_type] = handler
        logger.debug(f"📋 Handler registrado → {event_type}")

    def _connect(self) -> None:
        self.connection = get_rabbitmq_connection()
        self.channel = self.connection.channel()

        exchange = get_exchange()
        dlx = get_dlx()

        self.channel.exchange_declare(
            exchange=exchange,
            exchange_type="topic",
            durable=True,
        )
        self.channel.exchange_declare(
            exchange=dlx,
            exchange_type="direct",
            durable=True,
        )

        self.channel.queue_declare(
            queue=self.queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange":    dlx,
                "x-dead-letter-routing-key": self.dlq_name,
            },
        )

        self.channel.queue_declare(queue=self.dlq_name, durable=True)
        self.channel.queue_bind(
            exchange=dlx,
            queue=self.dlq_name,
            routing_key=self.dlq_name,
        )

        for key in self.routing_keys:
            self.channel.queue_bind(
                exchange=exchange,
                queue=self.queue_name,
                routing_key=key,
            )

        self.channel.basic_qos(prefetch_count=1)
        logger.info(f"📡 Conectado → {self.queue_name}")

    def _callback(self, ch, method, properties, body) -> None:
        event_type = None

        try:
            message = json.loads(body)
            event_type = message.get("event_type")
            data = message.get("data", {})

            logger.info(f"📥 {event_type}")

            handler = self._handlers.get(event_type)

            if not handler:
                logger.warning(
                    f"⚠️ Sin handler para '{event_type}' — descartando")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            handler(data)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception:
            logger.exception(f"💥 Error procesando '{event_type}'")

            if should_retry(properties):
                backoff = get_backoff_seconds(properties)
                logger.warning(f"🔁 Reintentando en {backoff}s...")
                time.sleep(backoff)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            else:
                logger.error(f"🪦 Enviando a DLQ → {self.dlq_name}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start(self) -> None:
        while True:
            try:
                self._connect()
                self.channel.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=self._callback,
                )
                logger.info(
                    f"🚀 Inventory consumer '{self.service}' escuchando...")
                self.channel.start_consuming()

            except pika.exceptions.AMQPConnectionError:
                logger.warning(
                    "🔌 RabbitMQ no disponible — reintentando en 5s...")
                time.sleep(5)

            except KeyboardInterrupt:
                logger.info("🛑 Consumer detenido manualmente")
                break

            except Exception:
                logger.exception("💥 Error crítico — reintentando en 5s")
                time.sleep(5)

            finally:
                try:
                    if self.connection and not self.connection.is_closed:
                        self.connection.close()
                except Exception:
                    pass

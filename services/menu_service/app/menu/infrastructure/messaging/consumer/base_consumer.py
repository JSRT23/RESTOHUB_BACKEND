# menu_service/app/menu/infrastructure/messaging/consumer/base_consumer.py
from app.menu.infrastructure.messaging.core.connection import crear_canal
from app.menu.infrastructure.messaging.core.serializer import SerializadorEventos
from app.menu.infrastructure.messaging.config.exchanges import declarar_exchange
from django.conf import settings


class BaseConsumer:

    def __init__(self, queue_name, routing_keys, handler):
        self.queue_name = queue_name
        self.routing_keys = routing_keys
        self.handler = handler

    def iniciar(self):
        conexion, canal = crear_canal()

        declarar_exchange(canal)

        canal.queue_declare(queue=self.queue_name, durable=True)

        for key in self.routing_keys:
            canal.queue_bind(
                exchange=settings.RABBITMQ["EXCHANGE"],
                queue=self.queue_name,
                routing_key=key
            )

        canal.basic_qos(prefetch_count=1)

        def callback(ch, method, properties, body):
            try:
                evento = SerializadorEventos.deserializar(body)
                self.handler(evento)

                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                print(f"Error procesando evento: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        canal.basic_consume(
            queue=self.queue_name,
            on_message_callback=callback
        )

        print(f"🟢 Escuchando cola: {self.queue_name}")
        canal.start_consuming()

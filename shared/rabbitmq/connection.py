import time
import pika
import os


def get_rabbit_connection():
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")

    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=host)
            )
            print("✅ Conectado a RabbitMQ")
            return connection
        except Exception:
            print("⏳ Reintentando conexión a RabbitMQ...")
            time.sleep(5)

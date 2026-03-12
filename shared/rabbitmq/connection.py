import pika
import os


def get_rabbit_connection():

    host = os.getenv("RABBITMQ_HOST", "rabbitmq")

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=host)
    )

    return connection

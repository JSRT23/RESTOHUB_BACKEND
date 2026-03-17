import pika
import json
import os
from datetime import datetime

RABBIT_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
QUEUE_NAME = "menu_events"


def publish_event(event_name: str, data: dict):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBIT_HOST)
    )
    channel = connection.channel()

    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    message = {
        "event": event_name,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }

    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2)  # persistente
    )

    connection.close()

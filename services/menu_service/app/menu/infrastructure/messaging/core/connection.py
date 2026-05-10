# menu_service/app/menu/infrastructure/messaging/core/connection.py
import ssl
import pika
from django.conf import settings


def crear_conexion():
    rmq = settings.RABBITMQ

    credenciales = pika.PlainCredentials(
        rmq["USER"],
        rmq["PASSWORD"]
    )

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

    # SSL para CloudAMQP (puerto 5671 / amqps://)
    if rmq.get("USE_SSL"):
        ssl_context = ssl.create_default_context()
        parametros.ssl_options = pika.SSLOptions(ssl_context, rmq["HOST"])

    return pika.BlockingConnection(parametros)


def crear_canal():
    conexion = crear_conexion()
    canal = conexion.channel()
    return conexion, canal

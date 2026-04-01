# menu_service/app/menu/infrastructure/messaging/core/connection.py
import pika
from django.conf import settings


def crear_conexion():
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

    return pika.BlockingConnection(parametros)


def crear_canal():
    conexion = crear_conexion()
    canal = conexion.channel()
    return conexion, canal

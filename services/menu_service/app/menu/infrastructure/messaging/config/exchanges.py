# menu_service/app/menu/infrastructure/messaging/config/exchange.py

from django.conf import settings


def declarar_exchange(canal):
    canal.exchange_declare(
        exchange=settings.RABBITMQ["EXCHANGE"],
        exchange_type="topic",
        durable=True
    )

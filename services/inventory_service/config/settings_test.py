# config/settings_test.py
from config.settings import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Desactivar RabbitMQ en tests — se mockea en conftest
RABBITMQ = {
    "HOST": "localhost",
    "PORT": 5672,
    "USER": "guest",
    "PASSWORD": "guest",
    "VHOST": "/",
    "EXCHANGE": "restohub",
}

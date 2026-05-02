from config.settings import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"]},
}

# RabbitMQ — valores dummy para tests (siempre se mockea publicar_evento)
RABBITMQ = {
    "HOST": "localhost",
    "PORT": 5672,
    "USER": "test",
    "PASSWORD": "test",
    "VHOST": "/",
    "EXCHANGE": "test",
    "HEARTBEAT": 60,
    "BLOCKED_CONNECTION_TIMEOUT": 10,
    "CONNECTION_ATTEMPTS": 1,
    "RETRY_DELAY": 1,
}

# config/settings_test.py
from config.settings import *  # noqa

# ── Base de datos en memoria ──────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME":   ":memory:",
    }
}

# ── Paginación desactivada ────────────────────────────────────────────────────
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_PAGINATION_CLASS": None,
    "PAGE_SIZE": None,
}

# ── RabbitMQ → fallo instantáneo (port 1) ────────────────────────────────────
RABBITMQ = {
    "HOST":     "localhost",
    "PORT":     1,
    "USER":     "test",
    "PASSWORD": "test",
    "VHOST":    "/",
    "EXCHANGE": "restohub",
}

# ── Silenciar logs de pika y signals ─────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root":     {"handlers": ["null"]},
    "loggers": {
        "pika":                    {"handlers": ["null"], "propagate": False},
        "app.orders.signals":      {"handlers": ["null"], "propagate": False},
    },
}

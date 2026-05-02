# config/settings_test.py
from config.settings import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME":   ":memory:",
    }
}

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_PAGINATION_CLASS": None,
    "PAGE_SIZE": None,
}

# Cache en memoria — sin Redis real
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

RABBITMQ = {
    "HOST": "localhost", "PORT": 1,
    "USER": "test", "PASSWORD": "test",
    "VHOST": "/", "EXCHANGE": "restohub",
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"]},
    "loggers": {
        "pika":                    {"handlers": ["null"], "propagate": False},
        "app.loyalty.signals":     {"handlers": ["null"], "propagate": False},
    },
}

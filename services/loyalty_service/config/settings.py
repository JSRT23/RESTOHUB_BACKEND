"""
Django settings for loyalty_service.
Soporta desarrollo (DEBUG=True) y producción (DEBUG=False).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────
# SEGURIDAD
# ─────────────────────────────────────────
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = ["*"]

# ─────────────────────────────────────────
# APLICACIONES
# ─────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
]

LOCAL_APPS = [
    "app.loyalty.apps.LoyaltyConfig",
]

INSTALLED_APPS = ["django_prometheus"] + \
    DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
# ↑ django_prometheus debe ser PRIMERO

# ─────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",  # ← PRIMERO
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # ← reemplaza CommonMiddleware
    "config.middleware.SafeCommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",   # ← ÚLTIMO
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ─────────────────────────────────────────
# BASE DE DATOS
# ─────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE":   "django_prometheus.db.backends.postgresql",  # ← instrumenta queries
        "NAME":     os.getenv("POSTGRES_DB"),
        "USER":     os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST":     os.getenv("POSTGRES_HOST"),
        "PORT":     os.getenv("POSTGRES_PORT", "5432"),
        "OPTIONS": {
            "sslmode": os.getenv("POSTGRES_SSLMODE", "require"),
        } if not DEBUG else {},
    }
}

# ─────────────────────────────────────────
# REDIS — Upstash en prod, local en dev
# ─────────────────────────────────────────
_redis_url = os.getenv("REDIS_URL")

if _redis_url:
    _redis_location = _redis_url
else:
    _redis_host = os.getenv("REDIS_HOST", "redis")
    _redis_port = os.getenv("REDIS_PORT", "6379")
    _redis_db = os.getenv("REDIS_DB",   "0")
    _redis_location = f"redis://{_redis_host}:{_redis_port}/{_redis_db}"

CACHES = {
    "default": {
        "BACKEND":  "django_redis.cache.RedisCache",
        "LOCATION": _redis_location,
        "OPTIONS": {
            "CLIENT_CLASS":      "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "CONNECTION_POOL_KWARGS": {
                "ssl_cert_reqs": None,
            } if _redis_url else {},
        },
        "KEY_PREFIX": "loyalty",
    }
}

REDIS_PUNTOS_TTL = int(os.getenv("REDIS_PUNTOS_TTL", 300))

# ─────────────────────────────────────────
# RABBITMQ
# ─────────────────────────────────────────
RABBITMQ = {
    "HOST":                       os.getenv("RABBITMQ_HOST",           "localhost"),
    "PORT":                       int(os.getenv("RABBITMQ_PORT",       5672)),
    "USER":                       os.getenv("RABBITMQ_USER",           "guest"),
    "PASSWORD":                   os.getenv("RABBITMQ_PASSWORD",       "guest"),
    "VHOST":                      os.getenv("RABBITMQ_VHOST",          "/"),
    "EXCHANGE":                   os.getenv("RABBITMQ_EXCHANGE",       "restohub"),
    "HEARTBEAT":                  int(os.getenv("RABBITMQ_HEARTBEAT",  60)),
    "BLOCKED_CONNECTION_TIMEOUT": int(os.getenv("RABBITMQ_BLOCKED_TIMEOUT", 30)),
    "CONNECTION_ATTEMPTS":        int(os.getenv("RABBITMQ_CONN_ATTEMPTS",   5)),
    "RETRY_DELAY":                int(os.getenv("RABBITMQ_RETRY_DELAY",     3)),
    "USE_SSL": os.getenv("RABBITMQ_USE_SSL", "False") == "True",
}

SERVICE_NAME = os.getenv("SERVICE_NAME", "loyalty_service")

# ─────────────────────────────────────────
# DRF
# ─────────────────────────────────────────
_renderers = ["rest_framework.renderers.JSONRenderer"]
if DEBUG:
    _renderers.append("rest_framework.renderers.BrowsableAPIRenderer")

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": _renderers,
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# ─────────────────────────────────────────
# INTERNACIONALIZACIÓN
# ─────────────────────────────────────────
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# ─────────────────────────────────────────
# ARCHIVOS ESTÁTICOS
# ─────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers":  ["console"],
            "level":     "ERROR",
            "propagate": False,
        },
    },
}

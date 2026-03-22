import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = ["*"]

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
    "app.loyalty",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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

# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT"),
    }
}

# ---------------------------------------------------------------------------
# Redis — caché de saldos de puntos
#
# Se usa django-redis como backend. Cada saldo de puntos se guarda con la
# key "puntos:{cliente_id}" y un TTL configurable (default 5 min).
#
# Por qué allkeys-lru en Redis:
#   loyalty_service tiene acceso de lectura frecuente y escritura baja.
#   Si Redis se llena, preferimos evictar las keys menos usadas antes de
#   fallar — el peor caso es un cache miss que va a PostgreSQL.
# ---------------------------------------------------------------------------

_redis_host = os.getenv("REDIS_HOST", "redis")
_redis_port = os.getenv("REDIS_PORT", "6379")
_redis_db = os.getenv("REDIS_DB", "0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{_redis_host}:{_redis_port}/{_redis_db}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Si Redis cae, el cache falla silenciosamente (no rompe la app)
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "loyalty",
    }
}

# TTL por defecto para saldo de puntos (segundos)
REDIS_PUNTOS_TTL = int(os.getenv("REDIS_PUNTOS_TTL", 300))

# ---------------------------------------------------------------------------
# RabbitMQ
# ---------------------------------------------------------------------------

RABBITMQ = {
    "HOST":     os.getenv("RABBITMQ_HOST",     "rabbitmq"),
    "PORT":     int(os.getenv("RABBITMQ_PORT", 5672)),
    "USER":     os.getenv("RABBITMQ_USER",     "guest"),
    "PASSWORD": os.getenv("RABBITMQ_PASSWORD", "guest"),
    "VHOST":    os.getenv("RABBITMQ_VHOST",    "/"),
    "EXCHANGE": os.getenv("RABBITMQ_EXCHANGE", "restohub"),
}

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------

_renderers = ["rest_framework.renderers.JSONRenderer"]
if DEBUG:
    _renderers.append("rest_framework.renderers.BrowsableAPIRenderer")

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": _renderers,
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# ---------------------------------------------------------------------------
# Internacionalización
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

"""
Django settings for staff_service.
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
# Nota: la variable es DJANGO_SECRET_KEY (no SECRET_KEY) para este servicio
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY",
                       "django-insecure-staff-dev-key-cambiar-en-produccion")

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

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
    "app.staff.apps.StaffConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ← estáticos en prod
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

# ─────────────────────────────────────────
# BASE DE DATOS
# ─────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        # SSL requerido en Render (conexión externa)
        "OPTIONS": {
            "sslmode": os.getenv("POSTGRES_SSLMODE", "require"),
        } if not DEBUG else {},
    }
}

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
    # SSL para CloudAMQP (puerto 5671)
    "USE_SSL": os.getenv("RABBITMQ_USE_SSL", "False") == "True",
}

SERVICE_NAME = os.getenv("SERVICE_NAME", "staff_service")

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
# PASSWORDS
# ─────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

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
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

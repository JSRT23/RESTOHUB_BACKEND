"""
Django settings for auth_service.
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
SECRET_KEY = os.getenv(
    "SECRET_KEY", "django-insecure-auth-service-change-in-prod")

# Clave JWT — debe ser la misma en gateway_service
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "restohub-jwt-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = int(os.getenv("JWT_ACCESS_MINUTES", "60"))
JWT_REFRESH_TOKEN_LIFETIME_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "7"))

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*"]

# ─────────────────────────────────────────
# APLICACIONES
# ─────────────────────────────────────────
INSTALLED_APPS = [
    "django_prometheus",                        # ← debe ir PRIMERO
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "app.auth.apps.AuthConfig",
]

# ─────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",  # ← PRIMERO
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # ← reemplaza CommonMiddleware
    "config.middleware.SafeCommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
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
        "ENGINE": "django_prometheus.db.backends.postgresql",  # ← instrumenta queries
        "NAME":     os.getenv("POSTGRES_DB",       os.getenv("DB_NAME",     "auth_db")),
        "USER":     os.getenv("POSTGRES_USER",     os.getenv("DB_USER",     "restohub")),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", os.getenv("DB_PASSWORD", "restohub")),
        "HOST":     os.getenv("POSTGRES_HOST",     os.getenv("DB_HOST",     "postgres")),
        "PORT":     os.getenv("POSTGRES_PORT",     os.getenv("DB_PORT",     "5432")),
        "OPTIONS": {
            "sslmode": os.getenv("POSTGRES_SSLMODE", "require"),
        } if not DEBUG else {},
    }
}

AUTH_USER_MODEL = "auth_app.Usuario"

# ─────────────────────────────────────────
# DRF
# ─────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

# ─────────────────────────────────────────
# CORS
# ─────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

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

SERVICE_NAME = "auth_service"

# ─────────────────────────────────────────
# RESEND — email transaccional
# ─────────────────────────────────────────
RESEND_API_KEY = os.getenv("RESEND_API_KEY",    "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
RESEND_REPLY_TO = os.getenv("RESEND_REPLY_TO",   "")

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
        "app.auth.email_service": {
            "handlers":  ["console"],
            "level":     "DEBUG",
            "propagate": False,
        },
        "django.request": {
            "handlers":  ["console"],
            "level":     "ERROR",
            "propagate": False,
        },
    },
}

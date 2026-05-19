"""
Django settings for gateway_service.
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
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-gateway")
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
    "graphene_django",
    "corsheaders",
    "app.gateway",
]

GRAPHENE = {
    "SCHEMA": "app.gateway.graphql.schema.schema"
}

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
    "app.gateway.middleware.jwt_middleware.JWTMiddleware",
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ─────────────────────────────────────────
# CORS
# ─────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
] + [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

CORS_ALLOW_ALL_ORIGINS = DEBUG

# ─────────────────────────────────────────
# BASE DE DATOS — SQLite en memoria
# (gateway no persiste datos propios;
#  no se instrumenta con django_prometheus.db porque es SQLite)
# ─────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# ─────────────────────────────────────────
# JWT — misma clave que auth_service
# ─────────────────────────────────────────
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "restohub-jwt-secret-change-in-prod")
JWT_ALGORITHM = "HS256"

# ─────────────────────────────────────────
# URLs de microservicios internos
# ─────────────────────────────────────────
AUTH_SERVICE_URL = os.getenv(
    "AUTH_SERVICE_URL",      "http://auth_service:8000")
MENU_SERVICE_URL = os.getenv(
    "MENU_SERVICE_URL",      "http://menu_service:8000")
ORDER_SERVICE_URL = os.getenv(
    "ORDER_SERVICE_URL",     "http://order_service:8000")
STAFF_SERVICE_URL = os.getenv(
    "STAFF_SERVICE_URL",     "http://staff_service:8000")
INVENTORY_SERVICE_URL = os.getenv(
    "INVENTORY_SERVICE_URL", "http://inventory_service:8000")
LOYALTY_SERVICE_URL = os.getenv(
    "LOYALTY_SERVICE_URL",   "http://loyalty_service:8000")

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

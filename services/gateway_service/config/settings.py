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
    "django_prometheus",
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

GRAPHENE = {"SCHEMA": "app.gateway.graphql.schema.schema"}

# ─────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "config.middleware.SafeCommonMiddleware",
    "app.gateway.middleware.jwt_middleware.JWTMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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
# ─────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME":   ":memory:",
    }
}

# ─────────────────────────────────────────
# JWT
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
    "LOYALTY_SERVICE_URL",  "http://loyalty_service:8000")

# ─────────────────────────────────────────
# MERCADOPAGO
# ─────────────────────────────────────────
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
MP_PUBLIC_KEY = os.getenv("MP_PUBLIC_KEY",   "")

# FIX: default a Vercel, no a localhost
# En Render ya tienes MP_ACCESS_TOKEN y MP_PUBLIC_KEY configurados
# Agregar también: FRONTEND_URL=https://restohub-nine.vercel.app
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://restohub-nine.vercel.app")

# ─────────────────────────────────────────
# EMAIL — mismo sistema que auth_service
# Desarrollo  → EMAIL_BACKEND=gmail  (por defecto)
# Producción  → EMAIL_BACKEND=brevo  (agregar en Render)
# ─────────────────────────────────────────
EMAIL_BACKEND_CUSTOM = os.getenv("EMAIL_BACKEND", "gmail")

# Brevo SMTP (producción en Render)
BREVO_SMTP_USER = os.getenv("BREVO_SMTP_USER",     "")
BREVO_SMTP_PASSWORD = os.getenv("BREVO_SMTP_PASSWORD", "")

# Gmail SMTP (desarrollo local)
EMAIL_HOST = os.getenv("EMAIL_HOST",          "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT",      "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER",     "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

EMAIL_FROM = os.getenv(
    "EMAIL_FROM",
    f"RestoHub <{os.getenv('BREVO_SMTP_USER', '')}>" if os.getenv("EMAIL_BACKEND") == "brevo"
    else f"RestoHub <{os.getenv('EMAIL_HOST_USER', '')}>"
)

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
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}

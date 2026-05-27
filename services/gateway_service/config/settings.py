"""
Django settings for gateway_service.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-gateway")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = ["*"]

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

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

# ─────────────────────────────────────────
# CORS
# ─────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
] + [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
CORS_ALLOW_ALL_ORIGINS = DEBUG

# ─────────────────────────────────────────
# BASE DE DATOS
# ─────────────────────────────────────────
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# ─────────────────────────────────────────
# JWT
# ─────────────────────────────────────────
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "restohub-jwt-secret-change-in-prod")
JWT_ALGORITHM = "HS256"

# ─────────────────────────────────────────
# URLs de microservicios
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
# MERCADOPAGO
# ─────────────────────────────────────────
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
MP_PUBLIC_KEY = os.getenv("MP_PUBLIC_KEY",   "")
FRONTEND_URL = os.getenv("FRONTEND_URL",    "https://restohub-nine.vercel.app")

# ─────────────────────────────────────────
# EMAIL
# Desarrollo  → EMAIL_BACKEND=gmail
# Producción  → EMAIL_BACKEND=brevo
# ─────────────────────────────────────────
EMAIL_BACKEND_CUSTOM = os.getenv("EMAIL_BACKEND", "gmail")

# Brevo API HTTP (producción)
BREVO_API_KEY = os.getenv("BREVO_API_KEY",      "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME",  "RestoHub")

# Gmail SMTP (desarrollo local)
EMAIL_HOST = os.getenv("EMAIL_HOST",          "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT",      "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER",     "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_FROM = os.getenv(
    "EMAIL_FROM",          f"RestoHub <{os.getenv('EMAIL_HOST_USER', '')}>")

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
# LOGGING — incluye pagos para debug MP
# ─────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request":       {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "app.gateway.views.pagos": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}

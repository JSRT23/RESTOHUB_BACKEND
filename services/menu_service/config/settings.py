"""
Django settings for menu_service.
Soporta desarrollo (DEBUG=True) y producción (DEBUG=False).
"""

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────
# SEGURIDAD
# ─────────────────────────────────────────
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-41zwd347!ii2@tn+cr0$%$t4qi=fmkx1mv5@(9!gfbg_dn1g5@"
)

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# ─────────────────────────────────────────
# APLICACIONES
# ─────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'graphene_django',
    "django_filters",
    'rest_framework',
    'app.menu.apps.MenuConfig',
]

GRAPHENE = {
    "SCHEMA": "config.schema.schema"
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ← para archivos estáticos en prod
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend"
    ]
}

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

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
        # SSL requerido en Render
        "OPTIONS": {
            "sslmode": os.getenv("POSTGRES_SSLMODE", "require"),
        } if not DEBUG else {},
    }
}

# ─────────────────────────────────────────
# RABBITMQ
# ─────────────────────────────────────────
RABBITMQ = {
    "HOST":     os.getenv("RABBITMQ_HOST", "localhost"),
    "PORT":     int(os.getenv("RABBITMQ_PORT", 5672)),
    "USER":     os.getenv("RABBITMQ_USER", "restohub"),
    "PASSWORD": os.getenv("RABBITMQ_PASSWORD", "restohub"),
    "VHOST":    os.getenv("RABBITMQ_VHOST", "/"),
    "EXCHANGE": os.getenv("RABBITMQ_EXCHANGE", "restohub"),
    "HEARTBEAT": int(os.getenv("RABBITMQ_HEARTBEAT", 60)),
    "BLOCKED_CONNECTION_TIMEOUT": int(os.getenv("RABBITMQ_BLOCKED_TIMEOUT", 30)),
    "CONNECTION_ATTEMPTS": int(os.getenv("RABBITMQ_CONN_ATTEMPTS", 5)),
    "RETRY_DELAY": int(os.getenv("RABBITMQ_RETRY_DELAY", 3)),
    # SSL para CloudAMQP (puerto 5671)
    "USE_SSL": os.getenv("RABBITMQ_USE_SSL", "False") == "True",
}

# ─────────────────────────────────────────
# PASSWORDS
# ─────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
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
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

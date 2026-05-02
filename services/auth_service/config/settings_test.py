# config/settings_test.py
# Settings exclusivos para pytest — sobreescribe lo necesario del settings.py principal.
# pytest.ini apunta a este archivo vía DJANGO_SETTINGS_MODULE.

from config.settings import *  # noqa: F401, F403

# ── Base de datos en memoria ──────────────────────────────────────────────────
# SQLite en memoria: sin Docker, sin postgres, tests corren standalone.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME":   ":memory:",
    }
}

# ── Passwords — hasher rápido para no perder tiempo en bcrypt ────────────────
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ── JWT — tiempos cortos para poder probar expiración fácilmente ─────────────
JWT_SECRET_KEY = "test-secret-key-restohub"
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = 1    # 1 minuto → fácil probar expirado
JWT_REFRESH_TOKEN_LIFETIME_DAYS = 1

# ── Email — nunca enviar emails reales en tests ──────────────────────────────
# Los tests que necesiten verificar email usan mock de email_service.
RESEND_API_KEY = "test-fake-api-key"
RESEND_FROM_EMAIL = "test@restohub.test"

# ── Silenciar logs en tests ───────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"]},
}

# ── Desactivar CORS y middleware innecesario en tests ────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

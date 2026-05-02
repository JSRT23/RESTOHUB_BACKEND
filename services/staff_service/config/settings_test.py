# config/settings_test.py
from config.settings import *  # noqa

# ── Base de datos en memoria ──────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME":   ":memory:",
    }
}

# ── Paginación desactivada en tests ───────────────────────────────────────────
# Causa raíz de "assert 4 == 1": res.data tenía {count, results} en vez de lista.
# En tests queremos acceder directo a res.data como lista.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,                          # hereda todo lo demás
    "DEFAULT_PAGINATION_CLASS": None,          # ← desactiva paginación
    "PAGE_SIZE": None,
}

# ── RabbitMQ apuntando a localhost:1 para fallar inmediatamente ───────────────
# Sin esto los signals de Django intentan conectar a RabbitMQ real → spam de errores
# y los tests tardan ~2s extra cada uno por timeouts de conexión.
# Los signals ya tienen try/except → el error es silencioso pero lento.
# Apuntar a puerto 1 hace que falle instantáneamente sin timeout.
RABBITMQ = {
    "HOST":     "localhost",
    "PORT":     1,           # ← puerto que no existe → fallo inmediato
    "USER":     "test",
    "PASSWORD": "test",
    "VHOST":    "/",
    "EXCHANGE": "restohub",
}

# ── Password hasher rápido ────────────────────────────────────────────────────
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ── Silenciar logs en tests ───────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root":     {"handlers": ["null"]},
    "loggers": {
        "pika":             {"handlers": ["null"], "propagate": False},
        "app.staff.signals": {"handlers": ["null"], "propagate": False},
    },
}

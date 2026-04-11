# gateway_service/app/gateway/middleware/permissions.py
"""
Decoradores de permiso para resolvers GraphQL del gateway.

Uso:
    @require_auth
    def resolve_pedidos(self, info, ...):
        ...

    @require_roles("admin_central", "gerente_local")
    def resolve_crear_restaurante(self, info, ...):
        ...

    @require_mismo_restaurante("gerente_local", "supervisor")
    def resolve_empleados(self, info, restaurante_id=None, ...):
        # Si el usuario es gerente_local, solo ve su restaurante
        ...

El payload del JWT en request.jwt_user tiene la forma:
    {
        "user_id": "uuid",
        "rol": "gerente_local",
        "nombre": "...",
        "email": "...",
        "restaurante_id": "uuid",   # si aplica
        "empleado_id": "uuid",      # si aplica
    }
"""
import logging
from functools import wraps

import graphene

logger = logging.getLogger(__name__)


def _get_jwt_user(info):
    """Extrae jwt_user del contexto del request."""
    request = info.context
    return getattr(request, "jwt_user", None)


def _error(message: str, code: str = "FORBIDDEN"):
    """Retorna un error GraphQL estándar."""
    raise Exception(f"[{code}] {message}")


def require_auth(func):
    """Exige que el request tenga un JWT válido."""
    @wraps(func)
    def wrapper(self, info, *args, **kwargs):
        user = _get_jwt_user(info)
        if not user:
            _error("Debes iniciar sesión para acceder a este recurso.",
                   "UNAUTHENTICATED")
        return func(self, info, *args, **kwargs)
    return wrapper


def require_roles(*roles):
    """
    Exige JWT válido + rol en la lista permitida.
    Uso: @require_roles("admin_central", "gerente_local")
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, info, *args, **kwargs):
            user = _get_jwt_user(info)
            if not user:
                _error("Debes iniciar sesión.", "UNAUTHENTICATED")
            if user.get("rol") not in roles:
                _error(
                    f"Acceso denegado. Roles permitidos: {list(roles)}.",
                    "FORBIDDEN",
                )
            return func(self, info, *args, **kwargs)
        return wrapper
    return decorator


def require_mismo_restaurante(*roles_con_restriccion):
    """
    Para roles en roles_con_restriccion, filtra automáticamente por su restaurante_id.
    admin_central siempre pasa sin restricción.

    Inyecta _restaurante_id_filtro en kwargs para que el resolver lo use.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, info, *args, **kwargs):
            user = _get_jwt_user(info)
            if not user:
                _error("Debes iniciar sesión.", "UNAUTHENTICATED")

            rol = user.get("rol")

            if rol == "admin_central":
                # Admin ve todo — no se restringe
                kwargs["_jwt_user"] = user
                return func(self, info, *args, **kwargs)

            if rol in roles_con_restriccion:
                restaurante_id = user.get("restaurante_id")
                if not restaurante_id:
                    _error("Tu cuenta no tiene restaurante asignado.", "FORBIDDEN")
                # Sobrescribe restaurante_id del argumento con el del token
                kwargs["restaurante_id"] = restaurante_id
                kwargs["_jwt_user"] = user
                return func(self, info, *args, **kwargs)

            _error(
                f"Acceso denegado. Rol '{rol}' no tiene permiso.", "FORBIDDEN")
        return wrapper
    return decorator


def get_user_restaurante(info) -> str | None:
    """Helper para obtener restaurante_id del usuario autenticado."""
    user = _get_jwt_user(info)
    return user.get("restaurante_id") if user else None


def get_jwt_user(info) -> dict | None:
    """Helper para obtener el payload completo del JWT."""
    return _get_jwt_user(info)

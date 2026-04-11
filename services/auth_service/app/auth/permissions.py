import jwt
from functools import wraps
from rest_framework.response import Response
from rest_framework import status

from .tokens import verificar_token
from .models import Usuario, Rol


def get_usuario_from_request(request):
    """
    Extrae y verifica el JWT del header Authorization.
    Retorna (usuario, payload) o lanza excepción.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise PermissionError("Token no proporcionado.")

    token = auth_header.split(" ", 1)[1]
    payload = verificar_token(token, tipo="access")
    usuario = Usuario.objects.filter(
        id=payload["user_id"], activo=True).first()
    if not usuario:
        raise PermissionError("Usuario no encontrado o inactivo.")
    return usuario, payload


def requiere_auth(func):
    """Exige JWT válido. Inyecta request.usuario y request.jwt_payload."""
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        try:
            usuario, payload = get_usuario_from_request(request)
        except (PermissionError, jwt.ExpiredSignatureError):
            return Response(
                {"detail": "Token expirado o inválido."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except jwt.InvalidTokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
        request.usuario = usuario
        request.jwt_payload = payload
        return func(self, request, *args, **kwargs)
    return wrapper


def requiere_rol(*roles):
    """Exige JWT válido + que el rol esté en la lista permitida."""
    def decorator(func):
        @wraps(func)
        @requiere_auth
        def wrapper(self, request, *args, **kwargs):
            if request.usuario.rol not in roles:
                return Response(
                    {"detail": f"Acceso denegado. Rol requerido: {list(roles)}."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator

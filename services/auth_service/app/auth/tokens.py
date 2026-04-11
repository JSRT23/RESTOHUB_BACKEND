import jwt
import uuid
from datetime import datetime, timedelta, timezone

from django.conf import settings


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def generar_access_token(usuario) -> str:
    """Genera un JWT de acceso firmado con el payload según el rol del usuario."""
    payload = usuario.get_jwt_payload()
    payload["token_type"] = "access"
    payload["exp"] = _now() + \
        timedelta(minutes=settings.JWT_ACCESS_TOKEN_LIFETIME_MINUTES)
    payload["iat"] = _now()
    payload["jti"] = str(uuid.uuid4())

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def generar_refresh_token(usuario) -> tuple[str, datetime]:
    """
    Genera un refresh token y retorna (token_str, expira_at).
    El refresh token solo lleva user_id y tipo — sin datos de rol.
    """
    expira_at = _now() + timedelta(days=settings.JWT_REFRESH_TOKEN_LIFETIME_DAYS)
    payload = {
        "user_id": str(usuario.id),
        "token_type": "refresh",
        "exp": expira_at,
        "iat": _now(),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY,
                       algorithm=settings.JWT_ALGORITHM)
    return token, expira_at


def verificar_token(token: str, tipo: str = "access") -> dict:
    """
    Verifica y decodifica un JWT.
    Lanza jwt.ExpiredSignatureError o jwt.InvalidTokenError si es inválido.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    if payload.get("token_type") != tipo:
        raise jwt.InvalidTokenError(f"Se esperaba token de tipo '{tipo}'.")
    return payload

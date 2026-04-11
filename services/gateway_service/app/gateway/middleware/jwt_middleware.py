# gateway_service/app/gateway/middleware/jwt_middleware.py
"""
Middleware JWT del gateway.

Lee el token del header Authorization, lo verifica con JWT_SECRET_KEY
(mismo secreto que auth_service) e inyecta el payload en request.jwt_user.

Los resolvers usan @require_auth / @require_roles del módulo permissions.
"""
import logging

import jwt
from django.conf import settings

logger = logging.getLogger(__name__)


class JWTMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.secret_key = getattr(
            settings, "JWT_SECRET_KEY", "restohub-jwt-secret-change-in-prod")
        self.algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")

    def __call__(self, request):
        request.jwt_user = None
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm],
                )
                if payload.get("token_type") != "access":
                    raise jwt.InvalidTokenError("Token type incorrecto")
                request.jwt_user = payload
                logger.debug("[JWT] Usuario autenticado: %s (%s)",
                             payload.get("email"), payload.get("rol"))
            except jwt.ExpiredSignatureError:
                logger.debug("[JWT] Token expirado")
            except jwt.InvalidTokenError as exc:
                logger.debug("[JWT] Token inválido: %s", exc)

        return self.get_response(request)

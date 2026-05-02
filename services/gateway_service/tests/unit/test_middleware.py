# tests/unit/test_middleware.py
"""
Tests del JWTMiddleware y helpers de permisos.
"""
import uuid
import pytest
import jwt
from django.test import RequestFactory

from app.gateway.middleware.jwt_middleware import JWTMiddleware
from app.gateway.middleware.permissions import get_jwt_user, require_auth


JWT_SECRET = "test-secret-key"
JWT_ALGO = "HS256"


def _make_token(rol="admin_central", restaurante_id=None, token_type="access", **extra):
    payload = {
        "token_type":     token_type,
        "user_id":        str(uuid.uuid4()),
        "email":          "test@test.com",
        "rol":            rol,
        "restaurante_id": str(restaurante_id) if restaurante_id else None,
        **extra,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


class TestJWTMiddleware:

    def _middleware(self, request):
        """Corre el middleware sobre el request y retorna el request modificado."""
        from django.conf import settings
        settings.JWT_SECRET_KEY = JWT_SECRET
        settings.JWT_ALGORITHM = JWT_ALGO

        def get_response(req):
            return req

        mw = JWTMiddleware(get_response)
        return mw(request)

    def test_sin_header_jwt_user_es_none(self):
        rf = RequestFactory()
        req = rf.post("/graphql/")
        self._middleware(req)
        assert req.jwt_user is None

    def test_bearer_valido_inyecta_jwt_user(self):
        token = _make_token(rol="gerente_local")
        rf = RequestFactory()
        req = rf.post("/graphql/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self._middleware(req)
        assert req.jwt_user is not None
        assert req.jwt_user["rol"] == "gerente_local"

    def test_token_expirado_jwt_user_es_none(self):
        import time
        payload = {
            "token_type": "access",
            "user_id": str(uuid.uuid4()),
            "rol": "cajero",
            "exp": int(time.time()) - 100,  # ya expiró
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
        rf = RequestFactory()
        req = rf.post("/graphql/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self._middleware(req)
        assert req.jwt_user is None

    def test_token_con_firma_incorrecta_jwt_user_es_none(self):
        token = _make_token()
        token_tampereado = token[:-5] + "XXXXX"
        rf = RequestFactory()
        req = rf.post(
            "/graphql/", HTTP_AUTHORIZATION=f"Bearer {token_tampereado}")
        self._middleware(req)
        assert req.jwt_user is None

    def test_token_tipo_refresh_es_rechazado(self):
        token = _make_token(token_type="refresh")
        rf = RequestFactory()
        req = rf.post("/graphql/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self._middleware(req)
        assert req.jwt_user is None

    def test_header_sin_bearer_prefix_es_ignorado(self):
        token = _make_token()
        rf = RequestFactory()
        req = rf.post("/graphql/", HTTP_AUTHORIZATION=token)  # sin "Bearer "
        self._middleware(req)
        assert req.jwt_user is None

    def test_jwt_user_contiene_restaurante_id(self):
        rid = uuid.uuid4()
        token = _make_token(rol="gerente_local", restaurante_id=rid)
        rf = RequestFactory()
        req = rf.post("/graphql/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self._middleware(req)
        assert req.jwt_user["restaurante_id"] == str(rid)


class TestGetJwtUser:

    def test_retorna_none_sin_jwt_user(self):
        rf = RequestFactory()
        req = rf.post("/graphql/")
        req.jwt_user = None

        class FakeInfo:
            context = req

        assert get_jwt_user(FakeInfo()) is None

    def test_retorna_payload_con_jwt_user(self):
        rf = RequestFactory()
        req = rf.post("/graphql/")
        req.jwt_user = {"rol": "supervisor", "user_id": "abc"}

        class FakeInfo:
            context = req

        user = get_jwt_user(FakeInfo())
        assert user["rol"] == "supervisor"

# tests/integration/test_login.py
# POST /api/auth/login/
# POST /api/auth/refresh/
# POST /api/auth/logout/
# POST /api/auth/verificar/

import pytest
from django.urls import reverse

from app.auth.models import RefreshToken
from app.auth.tokens import generar_access_token, generar_refresh_token
from tests.factories import UsuarioFactory, RefreshTokenFactory


# ═══════════════════════════════════════════════════════════════════════════════
# LoginView  POST /api/auth/login/
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoginView:

    URL = "/api/auth/login/"

    def test_login_exitoso_retorna_tokens(self, db, api_client):
        u = UsuarioFactory(email="chef@gmail.com")
        res = api_client.post(self.URL, {
            "email": "chef@gmail.com",
            "password": "testpass123",
        })
        assert res.status_code == 200
        assert "access_token" in res.data
        assert "refresh_token" in res.data
        assert res.data["token_type"] == "Bearer"

    def test_login_crea_refresh_token_en_db(self, db, api_client):
        u = UsuarioFactory(email="crea@gmail.com")
        res = api_client.post(self.URL, {
            "email": "crea@gmail.com",
            "password": "testpass123",
        })
        assert res.status_code == 200
        assert RefreshToken.objects.filter(usuario=u).exists()

    def test_login_retorna_datos_usuario(self, db, api_client):
        u = UsuarioFactory(email="datos@gmail.com")
        res = api_client.post(self.URL, {
            "email": "datos@gmail.com",
            "password": "testpass123",
        })
        assert res.status_code == 200
        assert res.data["usuario"]["email"] == u.email
        assert res.data["usuario"]["rol"] == u.rol
        assert "password" not in res.data["usuario"]

    def test_login_password_incorrecto_retorna_400(self, db, api_client):
        UsuarioFactory(email="wrong@gmail.com")
        res = api_client.post(self.URL, {
            "email": "wrong@gmail.com",
            "password": "incorrect",
        })
        assert res.status_code == 400

    def test_login_email_inexistente_retorna_400(self, db, api_client):
        res = api_client.post(self.URL, {
            "email": "nadie@gmail.com",
            "password": "pass123",
        })
        assert res.status_code == 400

    def test_login_usuario_inactivo_retorna_400(self, db, api_client):
        UsuarioFactory.inactivo(email="off@gmail.com")
        res = api_client.post(self.URL, {
            "email": "off@gmail.com",
            "password": "testpass123",
        })
        assert res.status_code == 400

    def test_login_email_no_verificado_retorna_403(self, db, api_client):
        UsuarioFactory.no_verificado(email="noverif@gmail.com")
        res = api_client.post(self.URL, {
            "email": "noverif@gmail.com",
            "password": "testpass123",
        })
        assert res.status_code == 403
        assert res.data["codigo"] == "EMAIL_NO_VERIFICADO"
        assert "email" in res.data

    def test_login_sin_email_retorna_400(self, db, api_client):
        res = api_client.post(self.URL, {"password": "pass"})
        assert res.status_code == 400

    def test_login_sin_password_retorna_400(self, db, api_client):
        res = api_client.post(self.URL, {"email": "a@gmail.com"})
        assert res.status_code == 400

    def test_login_body_vacio_retorna_400(self, db, api_client):
        res = api_client.post(self.URL, {})
        assert res.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# RefreshView  POST /api/auth/refresh/
# ═══════════════════════════════════════════════════════════════════════════════

class TestRefreshView:

    URL = "/api/auth/refresh/"

    def test_refresh_valido_retorna_nuevo_access_token(self, db, api_client, refresh_token_admin):
        res = api_client.post(self.URL, {"refresh_token": refresh_token_admin})
        assert res.status_code == 200
        assert "access_token" in res.data
        assert res.data["token_type"] == "Bearer"

    def test_refresh_revocado_retorna_401(self, db, api_client):
        u = UsuarioFactory()
        token_str, expira_at = generar_refresh_token(u)
        RefreshToken.objects.create(
            usuario=u, token=token_str, expira_at=expira_at, revocado=True
        )
        res = api_client.post(self.URL, {"refresh_token": token_str})
        assert res.status_code == 401

    def test_refresh_expirado_retorna_401(self, db, api_client):
        import uuid
        import jwt as pyjwt
        from datetime import datetime, timezone as dt_tz, timedelta
        from django.conf import settings

        u = UsuarioFactory()
        payload = {
            "user_id": str(u.id),
            "token_type": "refresh",
            "exp": datetime.now(tz=dt_tz.utc) - timedelta(seconds=10),
            "iat": datetime.now(tz=dt_tz.utc) - timedelta(days=8),
            "jti": str(uuid.uuid4()),
        }
        token_exp = pyjwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        res = api_client.post(self.URL, {"refresh_token": token_exp})
        assert res.status_code == 401

    def test_refresh_malformado_retorna_401(self, db, api_client):
        res = api_client.post(self.URL, {"refresh_token": "no.es.jwt"})
        assert res.status_code == 401

    def test_refresh_sin_body_retorna_400(self, db, api_client):
        res = api_client.post(self.URL, {})
        assert res.status_code == 400

    def test_refresh_usuario_inactivo_retorna_401(self, db, api_client):
        u = UsuarioFactory.inactivo()
        token_str, expira_at = generar_refresh_token(u)
        RefreshToken.objects.create(
            usuario=u, token=token_str, expira_at=expira_at)
        res = api_client.post(self.URL, {"refresh_token": token_str})
        assert res.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# LogoutView  POST /api/auth/logout/
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogoutView:

    URL = "/api/auth/logout/"

    def test_logout_revoca_refresh_token(self, db, api_client, usuario_admin, refresh_token_admin):
        token_acceso = generar_access_token(usuario_admin)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_acceso}")
        res = api_client.post(self.URL, {"refresh_token": refresh_token_admin})
        assert res.status_code == 200
        assert RefreshToken.objects.filter(
            token=refresh_token_admin, revocado=True
        ).exists()

    def test_logout_sin_refresh_token_igual_retorna_200(self, db, api_client, usuario_admin):
        """Logout sin refresh_token es válido — solo cierra la sesión de access."""
        token = generar_access_token(usuario_admin)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = api_client.post(self.URL, {})
        assert res.status_code == 200

    def test_logout_sin_autenticacion_retorna_401(self, db, api_client):
        res = api_client.post(self.URL, {})
        assert res.status_code == 401

    def test_logout_no_revoca_tokens_de_otro_usuario(self, db, api_client, usuario_admin):
        """El logout solo revoca el RT del propio usuario, no el de otros."""
        otro = UsuarioFactory()
        token_otro_str, expira_at = generar_refresh_token(otro)
        rt_otro = RefreshToken.objects.create(
            usuario=otro, token=token_otro_str, expira_at=expira_at
        )

        token_admin = generar_access_token(usuario_admin)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_admin}")
        api_client.post(self.URL, {"refresh_token": token_otro_str})

        # RT de otro usuario NO debe estar revocado
        rt_otro.refresh_from_db()
        assert rt_otro.revocado is False


# ═══════════════════════════════════════════════════════════════════════════════
# VerificarTokenView  POST /api/auth/verificar/
# ═══════════════════════════════════════════════════════════════════════════════

class TestVerificarTokenView:

    URL = "/api/auth/verificar/"

    def test_token_valido_retorna_valido_true(self, db, api_client, usuario_admin):
        token = generar_access_token(usuario_admin)
        res = api_client.post(self.URL, {"token": token})
        assert res.status_code == 200
        assert res.data["valido"] is True
        assert "payload" in res.data
        assert res.data["payload"]["user_id"] == str(usuario_admin.id)

    def test_token_expirado_retorna_401(self, db, api_client):
        import uuid
        import jwt as pyjwt
        from datetime import datetime, timezone as dt_tz, timedelta
        from django.conf import settings

        u = UsuarioFactory()
        payload = u.get_jwt_payload()
        payload["token_type"] = "access"
        payload["exp"] = datetime.now(tz=dt_tz.utc) - timedelta(seconds=10)
        payload["iat"] = datetime.now(tz=dt_tz.utc) - timedelta(minutes=61)
        payload["jti"] = str(uuid.uuid4())

        token_exp = pyjwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        res = api_client.post(self.URL, {"token": token_exp})
        assert res.status_code == 401
        assert res.data["valido"] is False

    def test_token_invalido_retorna_401(self, db, api_client):
        res = api_client.post(self.URL, {"token": "garbage.token.here"})
        assert res.status_code == 401
        assert res.data["valido"] is False

    def test_sin_token_retorna_400(self, db, api_client):
        res = api_client.post(self.URL, {})
        assert res.status_code == 400

# tests/unit/test_tokens.py
# Pruebas unitarias de tokens.py:
# generar_access_token, generar_refresh_token, verificar_token.

import time
import uuid
from datetime import timedelta

import jwt
import pytest
from django.utils import timezone

from app.auth.models import Rol
from app.auth.tokens import (
    generar_access_token,
    generar_refresh_token,
    verificar_token,
)
from tests.factories import UsuarioFactory


class TestGenerarAccessToken:

    def test_retorna_string(self, db):
        u = UsuarioFactory()
        token = generar_access_token(u)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_tiene_tres_partes_jwt(self, db):
        u = UsuarioFactory()
        token = generar_access_token(u)
        assert token.count(".") == 2

    def test_payload_tipo_access(self, db, settings):
        u = UsuarioFactory()
        token = generar_access_token(u)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["token_type"] == "access"

    def test_payload_contiene_user_id(self, db, settings):
        u = UsuarioFactory()
        token = generar_access_token(u)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["user_id"] == str(u.id)

    def test_payload_contiene_rol_email_nombre(self, db, settings):
        u = UsuarioFactory(rol=Rol.GERENTE_LOCAL)
        token = generar_access_token(u)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["rol"] == Rol.GERENTE_LOCAL
        assert payload["email"] == u.email
        assert payload["nombre"] == u.nombre

    def test_payload_admin_sin_restaurante_id(self, db, settings):
        u = UsuarioFactory.admin()
        token = generar_access_token(u)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert "restaurante_id" not in payload

    def test_payload_gerente_con_restaurante_id(self, db, settings):
        rid = uuid.uuid4()
        u = UsuarioFactory.gerente(restaurante_id=rid)
        token = generar_access_token(u)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["restaurante_id"] == str(rid)

    def test_payload_mesero_con_empleado_id(self, db, settings):
        eid = uuid.uuid4()
        u = UsuarioFactory.mesero(empleado_id=eid)
        token = generar_access_token(u)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["empleado_id"] == str(eid)

    def test_tiene_exp_e_iat(self, db, settings):
        u = UsuarioFactory()
        token = generar_access_token(u)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert "exp" in payload
        assert "iat" in payload
        assert payload["exp"] > payload["iat"]

    def test_tiene_jti_unico(self, db, settings):
        u = UsuarioFactory()
        t1 = generar_access_token(u)
        t2 = generar_access_token(u)
        p1 = jwt.decode(t1, settings.JWT_SECRET_KEY,
                        algorithms=[settings.JWT_ALGORITHM])
        p2 = jwt.decode(t2, settings.JWT_SECRET_KEY,
                        algorithms=[settings.JWT_ALGORITHM])
        assert p1["jti"] != p2["jti"]

    def test_tokens_distintos_usuarios_no_comparten_jti(self, db, settings):
        u1 = UsuarioFactory()
        u2 = UsuarioFactory()
        t1 = generar_access_token(u1)
        t2 = generar_access_token(u2)
        p1 = jwt.decode(t1, settings.JWT_SECRET_KEY,
                        algorithms=[settings.JWT_ALGORITHM])
        p2 = jwt.decode(t2, settings.JWT_SECRET_KEY,
                        algorithms=[settings.JWT_ALGORITHM])
        assert p1["jti"] != p2["jti"]
        assert p1["user_id"] != p2["user_id"]


class TestGenerarRefreshToken:

    def test_retorna_tupla_string_y_datetime(self, db):
        u = UsuarioFactory()
        result = generar_refresh_token(u)
        assert isinstance(result, tuple)
        assert len(result) == 2
        token_str, expira_at = result
        assert isinstance(token_str, str)

    def test_expira_at_en_el_futuro(self, db):
        u = UsuarioFactory()
        _, expira_at = generar_refresh_token(u)
        assert expira_at > timezone.now()

    def test_payload_tipo_refresh(self, db, settings):
        u = UsuarioFactory()
        token_str, _ = generar_refresh_token(u)
        payload = jwt.decode(
            token_str,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["token_type"] == "refresh"

    def test_payload_solo_tiene_user_id(self, db, settings):
        """Refresh token NO debe exponer rol, email ni otros datos sensibles."""
        u = UsuarioFactory.admin()
        token_str, _ = generar_refresh_token(u)
        payload = jwt.decode(
            token_str,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["user_id"] == str(u.id)
        assert "rol" not in payload
        assert "email" not in payload
        assert "restaurante_id" not in payload

    def test_dos_refresh_tokens_distintos(self, db):
        u = UsuarioFactory()
        t1, _ = generar_refresh_token(u)
        t2, _ = generar_refresh_token(u)
        assert t1 != t2


class TestVerificarToken:

    def test_access_token_valido(self, db):
        u = UsuarioFactory()
        token = generar_access_token(u)
        payload = verificar_token(token, tipo="access")
        assert payload["user_id"] == str(u.id)
        assert payload["token_type"] == "access"

    def test_refresh_token_valido(self, db):
        u = UsuarioFactory()
        token_str, _ = generar_refresh_token(u)
        payload = verificar_token(token_str, tipo="refresh")
        assert payload["user_id"] == str(u.id)
        assert payload["token_type"] == "refresh"

    def test_tipo_incorrecto_lanza_error(self, db):
        """Pasar un access token cuando se espera refresh debe fallar."""
        u = UsuarioFactory()
        access = generar_access_token(u)
        with pytest.raises(jwt.InvalidTokenError):
            verificar_token(access, tipo="refresh")

    def test_tipo_refresh_con_access_esperado_lanza_error(self, db):
        u = UsuarioFactory()
        refresh, _ = generar_refresh_token(u)
        with pytest.raises(jwt.InvalidTokenError):
            verificar_token(refresh, tipo="access")

    def test_token_malformado_lanza_error(self, db):
        with pytest.raises(jwt.InvalidTokenError):
            verificar_token("esto.no.es.un.jwt", tipo="access")

    def test_token_con_firma_incorrecta_lanza_error(self, db):
        u = UsuarioFactory()
        token = generar_access_token(u)
        # Corromper la firma (última parte)
        partes = token.split(".")
        partes[2] = partes[2][:-4] + "XXXX"
        token_corrupto = ".".join(partes)
        with pytest.raises(jwt.InvalidTokenError):
            verificar_token(token_corrupto, tipo="access")

    def test_token_expirado_lanza_expired_signature_error(self, db, settings):
        """
        Usamos settings_test.py con JWT_ACCESS_TOKEN_LIFETIME_MINUTES = 1.
        Creamos un token con exp en el pasado manipulando el payload.
        """
        import time
        from datetime import datetime, timezone as dt_tz

        u = UsuarioFactory()
        payload = u.get_jwt_payload()
        payload["token_type"] = "access"
        payload["exp"] = datetime.now(tz=dt_tz.utc) - timedelta(seconds=10)
        payload["iat"] = datetime.now(tz=dt_tz.utc) - timedelta(seconds=70)
        payload["jti"] = str(uuid.uuid4())

        token_expirado = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            verificar_token(token_expirado, tipo="access")

    def test_token_vacio_lanza_error(self, db):
        with pytest.raises(Exception):
            verificar_token("", tipo="access")

    def test_verificar_sin_tipo_usa_access_por_defecto(self, db):
        u = UsuarioFactory()
        token = generar_access_token(u)
        payload = verificar_token(token)   # sin pasar tipo
        assert payload["token_type"] == "access"

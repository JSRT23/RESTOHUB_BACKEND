# tests/unit/test_permissions.py
# Pruebas unitarias de los decoradores requiere_auth y requiere_rol.
# Se usan views mínimas en memoria — sin URL routing real.

import pytest
from django.test import RequestFactory
from rest_framework.response import Response
from rest_framework.views import APIView

from app.auth.models import Rol
from app.auth.permissions import requiere_auth, requiere_rol
from app.auth.tokens import generar_access_token
from tests.factories import UsuarioFactory


# ── View mínima para testear los decoradores ──────────────────────────────────

class _VistaAuth(APIView):
    @requiere_auth
    def get(self, request):
        return Response({"ok": True, "rol": request.usuario.rol})


class _VistaAdmin(APIView):
    @requiere_rol(Rol.ADMIN_CENTRAL)
    def get(self, request):
        return Response({"ok": True})


class _VistaAdminOGerente(APIView):
    @requiere_rol(Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL)
    def get(self, request):
        return Response({"ok": True})


def _hacer_request(factory, token=None):
    """Crea un GET request con o sin Authorization header."""
    headers = {}
    if token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return factory.get("/fake/", **headers)


# ═══════════════════════════════════════════════════════════════════════════════
# requiere_auth
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequiereAuth:

    def test_sin_token_retorna_401(self, db):
        factory = RequestFactory()
        request = factory.get("/fake/")
        response = _VistaAuth.as_view()(request)
        assert response.status_code == 401

    def test_token_valido_pasa(self, db):
        u = UsuarioFactory()
        token = generar_access_token(u)
        factory = RequestFactory()
        request = _hacer_request(factory, token=token)
        response = _VistaAuth.as_view()(request)
        assert response.status_code == 200

    def test_token_valido_inyecta_usuario_en_request(self, db):
        u = UsuarioFactory(rol=Rol.COCINERO)
        token = generar_access_token(u)
        factory = RequestFactory()
        request = _hacer_request(factory, token=token)
        response = _VistaAuth.as_view()(request)
        assert response.data["rol"] == Rol.COCINERO

    def test_token_malformado_retorna_401(self, db):
        factory = RequestFactory()
        request = _hacer_request(factory, token="no.es.jwt")
        response = _VistaAuth.as_view()(request)
        assert response.status_code == 401

    def test_token_expirado_retorna_401(self, db):
        import uuid
        import jwt as pyjwt
        from datetime import datetime, timezone as dt_tz, timedelta
        from django.conf import settings

        u = UsuarioFactory()
        payload = u.get_jwt_payload()
        payload["token_type"] = "access"
        payload["exp"] = datetime.now(tz=dt_tz.utc) - timedelta(seconds=10)
        payload["iat"] = datetime.now(tz=dt_tz.utc) - timedelta(seconds=70)
        payload["jti"] = str(uuid.uuid4())

        token_exp = pyjwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        factory = RequestFactory()
        request = _hacer_request(factory, token=token_exp)
        response = _VistaAuth.as_view()(request)
        assert response.status_code == 401

    def test_usuario_inactivo_retorna_401(self, db):
        """Token válido pero el usuario fue desactivado después de firmarlo."""
        u = UsuarioFactory.inactivo()
        token = generar_access_token(u)
        factory = RequestFactory()
        request = _hacer_request(factory, token=token)
        response = _VistaAuth.as_view()(request)
        assert response.status_code == 401

    def test_header_sin_bearer_retorna_401(self, db):
        u = UsuarioFactory()
        token = generar_access_token(u)
        factory = RequestFactory()
        # Sin "Bearer " prefix
        request = factory.get("/fake/", HTTP_AUTHORIZATION=token)
        response = _VistaAuth.as_view()(request)
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# requiere_rol
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequiereRol:

    def test_rol_correcto_pasa(self, db):
        u = UsuarioFactory.admin()
        token = generar_access_token(u)
        factory = RequestFactory()
        request = _hacer_request(factory, token=token)
        response = _VistaAdmin.as_view()(request)
        assert response.status_code == 200

    def test_rol_incorrecto_retorna_403(self, db):
        u = UsuarioFactory.mesero()
        token = generar_access_token(u)
        factory = RequestFactory()
        request = _hacer_request(factory, token=token)
        response = _VistaAdmin.as_view()(request)
        assert response.status_code == 403

    def test_sin_token_retorna_401_no_403(self, db):
        """Sin token → 401 (no autenticado), no 403 (sin permisos)."""
        factory = RequestFactory()
        request = factory.get("/fake/")
        response = _VistaAdmin.as_view()(request)
        assert response.status_code == 401

    def test_multiples_roles_permitidos(self, db):
        gerente = UsuarioFactory.gerente()
        admin = UsuarioFactory.admin()
        factory = RequestFactory()

        for u in [gerente, admin]:
            token = generar_access_token(u)
            request = _hacer_request(factory, token=token)
            response = _VistaAdminOGerente.as_view()(request)
            assert response.status_code == 200, f"Falló para rol {u.rol}"

    def test_rol_no_en_lista_retorna_403(self, db):
        mesero = UsuarioFactory.mesero()
        token = generar_access_token(mesero)
        factory = RequestFactory()
        request = _hacer_request(factory, token=token)
        response = _VistaAdminOGerente.as_view()(request)
        assert response.status_code == 403

    @pytest.mark.parametrize("rol", [
        Rol.SUPERVISOR, Rol.COCINERO, Rol.MESERO, Rol.CAJERO, Rol.REPARTIDOR
    ])
    def test_operativos_no_pueden_acceder_a_vista_admin(self, db, rol):
        u = UsuarioFactory(rol=rol)
        token = generar_access_token(u)
        factory = RequestFactory()
        request = _hacer_request(factory, token=token)
        response = _VistaAdmin.as_view()(request)
        assert response.status_code == 403

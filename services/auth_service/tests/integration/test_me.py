# tests/integration/test_me.py
# GET  /api/auth/me/
# PATCH /api/auth/me/
# POST /api/auth/cambiar-password/

import pytest

from app.auth.models import RefreshToken
from app.auth.tokens import generar_access_token
from tests.factories import RefreshTokenFactory, UsuarioFactory


# ═══════════════════════════════════════════════════════════════════════════════
# MeView  GET /api/auth/me/
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeViewGet:

    URL = "/api/auth/me/"

    def test_retorna_datos_del_usuario_autenticado(self, db, client_admin, usuario_admin):
        res = client_admin.get(self.URL)
        assert res.status_code == 200
        assert res.data["email"] == usuario_admin.email
        assert res.data["rol"] == usuario_admin.rol
        assert res.data["nombre"] == usuario_admin.nombre

    def test_no_expone_password(self, db, client_admin):
        res = client_admin.get(self.URL)
        assert "password" not in res.data

    def test_retorna_id_como_uuid_string(self, db, client_admin, usuario_admin):
        res = client_admin.get(self.URL)
        assert str(res.data["id"]) == str(usuario_admin.id)

    def test_sin_autenticacion_retorna_401(self, db, api_client):
        res = api_client.get(self.URL)
        assert res.status_code == 401

    def test_retorna_restaurante_id_para_gerente(self, db, client_gerente, usuario_gerente):
        res = client_gerente.get(self.URL)
        assert res.status_code == 200
        assert str(res.data["restaurante_id"]) == str(
            usuario_gerente.restaurante_id)

    def test_admin_tiene_restaurante_id_null(self, db, client_admin):
        res = client_admin.get(self.URL)
        assert res.data["restaurante_id"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# MeView  PATCH /api/auth/me/
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeViewPatch:

    URL = "/api/auth/me/"

    def test_patch_nombre_exitoso(self, db, client_admin, usuario_admin):
        res = client_admin.patch(self.URL, {"nombre": "Nuevo Nombre"})
        assert res.status_code == 200
        usuario_admin.refresh_from_db()
        assert usuario_admin.nombre == "Nuevo Nombre"

    def test_patch_no_permite_cambiar_rol(self, db, client_mesero, usuario_mesero):
        """El PATCH de me/ solo permite cambiar 'nombre' — no el rol."""
        from app.auth.models import Rol
        res = client_mesero.patch(self.URL, {"rol": Rol.ADMIN_CENTRAL})
        # El campo se ignora silenciosamente o da error
        usuario_mesero.refresh_from_db()
        assert usuario_mesero.rol == Rol.MESERO

    def test_patch_no_permite_cambiar_email(self, db, client_admin, usuario_admin):
        email_original = usuario_admin.email
        client_admin.patch(self.URL, {"email": "otro@gmail.com"})
        usuario_admin.refresh_from_db()
        assert usuario_admin.email == email_original

    def test_sin_autenticacion_retorna_401(self, db, api_client):
        res = api_client.patch(self.URL, {"nombre": "Hacker"})
        assert res.status_code == 401

    def test_patch_nombre_vacio_retorna_400(self, db, client_admin):
        res = client_admin.patch(self.URL, {"nombre": ""})
        assert res.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# CambiarPasswordView  POST /api/auth/cambiar-password/
# ═══════════════════════════════════════════════════════════════════════════════

class TestCambiarPasswordView:

    URL = "/api/auth/cambiar-password/"

    def test_cambio_exitoso(self, db, client_admin, usuario_admin):
        res = client_admin.post(self.URL, {
            "password_actual":  "testpass123",
            "password_nuevo":   "NuevaSegura456!",
            "password_confirm": "NuevaSegura456!",
        })
        assert res.status_code == 200
        usuario_admin.refresh_from_db()
        assert usuario_admin.check_password("NuevaSegura456!")

    def test_cambio_revoca_todos_los_refresh_tokens(self, db, client_admin, usuario_admin):
        from app.auth.tokens import generar_refresh_token
        from django.utils import timezone
        token_str, expira_at = generar_refresh_token(usuario_admin)
        RefreshToken.objects.create(
            usuario=usuario_admin, token=token_str, expira_at=expira_at
        )
        client_admin.post(self.URL, {
            "password_actual":  "testpass123",
            "password_nuevo":   "NuevaSegura456!",
            "password_confirm": "NuevaSegura456!",
        })
        activos = RefreshToken.objects.filter(
            usuario=usuario_admin, revocado=False)
        assert not activos.exists()

    def test_password_actual_incorrecto_retorna_400(self, db, client_admin):
        res = client_admin.post(self.URL, {
            "password_actual":  "incorrecta",
            "password_nuevo":   "Nueva456!",
            "password_confirm": "Nueva456!",
        })
        assert res.status_code == 400
        assert "password_actual" in res.data

    def test_passwords_no_coinciden_retorna_400(self, db, client_admin):
        res = client_admin.post(self.URL, {
            "password_actual":  "testpass123",
            "password_nuevo":   "Nueva456!",
            "password_confirm": "Diferente789!",
        })
        assert res.status_code == 400

    def test_password_nuevo_muy_corto_retorna_400(self, db, client_admin):
        res = client_admin.post(self.URL, {
            "password_actual":  "testpass123",
            "password_nuevo":   "corta",
            "password_confirm": "corta",
        })
        assert res.status_code == 400

    def test_sin_autenticacion_retorna_401(self, db, api_client):
        res = api_client.post(self.URL, {
            "password_actual":  "testpass123",
            "password_nuevo":   "Nueva456!",
            "password_confirm": "Nueva456!",
        })
        assert res.status_code == 401

    def test_body_vacio_retorna_400(self, db, client_admin):
        res = client_admin.post(self.URL, {})
        assert res.status_code == 400

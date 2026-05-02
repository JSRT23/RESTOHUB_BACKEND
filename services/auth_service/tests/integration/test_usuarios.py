# tests/integration/test_usuarios.py
# GET    /api/auth/usuarios/
# GET    /api/auth/usuarios/<pk>/
# PATCH  /api/auth/usuarios/<pk>/
# DELETE /api/auth/usuarios/<pk>/
# POST   /api/auth/usuarios/desactivar/
# POST   /api/auth/usuarios/activar/
# POST   /api/auth/usuarios/vincular-empleado/

import uuid
import pytest

from app.auth.models import Rol, Usuario
from tests.factories import UsuarioFactory


# ═══════════════════════════════════════════════════════════════════════════════
# UsuariosView  GET /api/auth/usuarios/
# ═══════════════════════════════════════════════════════════════════════════════

class TestUsuariosListView:

    URL = "/api/auth/usuarios/"

    def test_admin_ve_todos_los_usuarios(self, db, client_admin):
        UsuarioFactory.mesero()
        UsuarioFactory.gerente()
        res = client_admin.get(self.URL)
        assert res.status_code == 200
        assert len(res.data) >= 2

    def test_gerente_solo_ve_su_restaurante(self, db, client_gerente, usuario_gerente):
        # Mesero del mismo restaurante
        UsuarioFactory.mesero(restaurante_id=usuario_gerente.restaurante_id)
        # Mesero de otro restaurante
        UsuarioFactory.mesero(restaurante_id=uuid.uuid4())
        res = client_gerente.get(self.URL)
        assert res.status_code == 200
        for u in res.data:
            assert str(u["restaurante_id"]) == str(
                usuario_gerente.restaurante_id)

    def test_mesero_no_puede_listar_usuarios(self, db, client_mesero):
        res = client_mesero.get(self.URL)
        assert res.status_code == 403

    def test_sin_autenticacion_retorna_401(self, db, api_client):
        res = api_client.get(self.URL)
        assert res.status_code == 401

    def test_admin_puede_filtrar_por_rol(self, db, client_admin):
        UsuarioFactory.mesero()
        UsuarioFactory.cocinero()
        res = client_admin.get(self.URL, {"rol": Rol.MESERO})
        assert res.status_code == 200
        for u in res.data:
            assert u["rol"] == Rol.MESERO

    def test_admin_puede_filtrar_por_activo(self, db, client_admin):
        UsuarioFactory.inactivo()
        res = client_admin.get(self.URL, {"activo": "false"})
        assert res.status_code == 200
        for u in res.data:
            assert u["activo"] is False

    def test_resultado_no_expone_passwords(self, db, client_admin):
        UsuarioFactory()
        res = client_admin.get(self.URL)
        for u in res.data:
            assert "password" not in u


# ═══════════════════════════════════════════════════════════════════════════════
# UsuarioDetailView  GET/PATCH/DELETE /api/auth/usuarios/<pk>/
# ═══════════════════════════════════════════════════════════════════════════════

class TestUsuarioDetailView:

    def _url(self, pk):
        return f"/api/auth/usuarios/{pk}/"

    # ── GET ───────────────────────────────────────────────────────────────────

    def test_admin_puede_ver_cualquier_usuario(self, db, client_admin):
        u = UsuarioFactory.mesero()
        res = client_admin.get(self._url(u.id))
        assert res.status_code == 200
        assert res.data["email"] == u.email

    def test_gerente_puede_ver_usuario_de_su_restaurante(self, db, client_gerente, usuario_gerente):
        u = UsuarioFactory.mesero(
            restaurante_id=usuario_gerente.restaurante_id)
        res = client_gerente.get(self._url(u.id))
        assert res.status_code == 200

    def test_gerente_no_puede_ver_usuario_de_otro_restaurante(self, db, client_gerente):
        u = UsuarioFactory.mesero(restaurante_id=uuid.uuid4())
        res = client_gerente.get(self._url(u.id))
        assert res.status_code == 403

    def test_usuario_inexistente_retorna_404(self, db, client_admin):
        res = client_admin.get(self._url(uuid.uuid4()))
        assert res.status_code == 404

    def test_mesero_no_puede_ver_detail(self, db, client_mesero):
        u = UsuarioFactory()
        res = client_mesero.get(self._url(u.id))
        assert res.status_code == 403

    # ── PATCH ─────────────────────────────────────────────────────────────────

    def test_admin_puede_cambiar_rol(self, db, client_admin):
        u = UsuarioFactory.mesero()
        res = client_admin.patch(self._url(u.id), {"rol": Rol.CAJERO})
        assert res.status_code == 200
        u.refresh_from_db()
        assert u.rol == Rol.CAJERO

    def test_admin_puede_cambiar_activo(self, db, client_admin):
        u = UsuarioFactory()
        res = client_admin.patch(self._url(u.id), {"activo": False})
        assert res.status_code == 200
        u.refresh_from_db()
        assert u.activo is False

    def test_gerente_solo_puede_cambiar_nombre_y_activo(self, db, client_gerente, usuario_gerente):
        u = UsuarioFactory.mesero(
            restaurante_id=usuario_gerente.restaurante_id)
        res = client_gerente.patch(self._url(u.id), {
            "nombre": "Nombre Nuevo",
            "rol":    Rol.ADMIN_CENTRAL,  # ignorado para gerente
        })
        assert res.status_code == 200
        u.refresh_from_db()
        assert u.nombre == "Nombre Nuevo"
        assert u.rol == Rol.MESERO  # no cambió

    # ── DELETE (soft) ─────────────────────────────────────────────────────────

    def test_admin_puede_desactivar_usuario(self, db, client_admin):
        u = UsuarioFactory()
        res = client_admin.delete(self._url(u.id))
        assert res.status_code == 200
        u.refresh_from_db()
        assert u.activo is False

    def test_gerente_no_puede_hacer_delete(self, db, client_gerente, usuario_gerente):
        u = UsuarioFactory.mesero(
            restaurante_id=usuario_gerente.restaurante_id)
        res = client_gerente.delete(self._url(u.id))
        assert res.status_code == 403

    def test_mesero_no_puede_hacer_delete(self, db, client_mesero):
        u = UsuarioFactory()
        res = client_mesero.delete(self._url(u.id))
        assert res.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# DesactivarUsuarioView  POST /api/auth/usuarios/desactivar/
# ═══════════════════════════════════════════════════════════════════════════════

class TestDesactivarUsuarioView:

    URL = "/api/auth/usuarios/desactivar/"

    def test_admin_desactiva_usuario(self, db, client_admin):
        u = UsuarioFactory.mesero()
        res = client_admin.post(self.URL, {"email": u.email})
        assert res.status_code == 200
        u.refresh_from_db()
        assert u.activo is False

    def test_desactivar_revoca_refresh_tokens(self, db, client_admin):
        from app.auth.tokens import generar_refresh_token
        from app.auth.models import RefreshToken
        u = UsuarioFactory.mesero()
        token_str, expira_at = generar_refresh_token(u)
        RefreshToken.objects.create(
            usuario=u, token=token_str, expira_at=expira_at)
        client_admin.post(self.URL, {"email": u.email})
        assert not RefreshToken.objects.filter(
            usuario=u, revocado=False).exists()

    def test_gerente_desactiva_usuario_de_su_restaurante(self, db, client_gerente, usuario_gerente):
        u = UsuarioFactory.mesero(
            restaurante_id=usuario_gerente.restaurante_id)
        res = client_gerente.post(self.URL, {"email": u.email})
        assert res.status_code == 200

    def test_gerente_no_puede_desactivar_de_otro_restaurante(self, db, client_gerente):
        u = UsuarioFactory.mesero(restaurante_id=uuid.uuid4())
        res = client_gerente.post(self.URL, {"email": u.email})
        assert res.status_code == 403

    def test_no_puede_desactivarse_a_si_mismo(self, db, client_admin, usuario_admin):
        res = client_admin.post(self.URL, {"email": usuario_admin.email})
        assert res.status_code == 403

    def test_gerente_no_puede_desactivar_otro_gerente(self, db, client_gerente, usuario_gerente):
        otro_gerente = UsuarioFactory.gerente(
            restaurante_id=usuario_gerente.restaurante_id)
        res = client_gerente.post(self.URL, {"email": otro_gerente.email})
        assert res.status_code == 403

    def test_usuario_ya_inactivo_retorna_ok(self, db, client_admin):
        u = UsuarioFactory.inactivo()
        res = client_admin.post(self.URL, {"email": u.email})
        assert res.status_code == 200
        assert res.data["ok"] is True

    def test_email_inexistente_retorna_404(self, db, client_admin):
        res = client_admin.post(self.URL, {"email": "nadie@gmail.com"})
        assert res.status_code == 404

    def test_sin_email_retorna_400(self, db, client_admin):
        res = client_admin.post(self.URL, {})
        assert res.status_code == 400

    def test_mesero_no_puede_desactivar(self, db, client_mesero):
        u = UsuarioFactory()
        res = client_mesero.post(self.URL, {"email": u.email})
        assert res.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# ActivarUsuarioView  POST /api/auth/usuarios/activar/
# ═══════════════════════════════════════════════════════════════════════════════

class TestActivarUsuarioView:

    URL = "/api/auth/usuarios/activar/"

    def test_admin_activa_usuario(self, db, client_admin):
        u = UsuarioFactory.inactivo()
        res = client_admin.post(self.URL, {"email": u.email})
        assert res.status_code == 200
        u.refresh_from_db()
        assert u.activo is True

    def test_usuario_ya_activo_retorna_ok(self, db, client_admin):
        u = UsuarioFactory()
        res = client_admin.post(self.URL, {"email": u.email})
        assert res.status_code == 200
        assert res.data["ok"] is True

    def test_gerente_activa_operativo_de_su_restaurante(self, db, client_gerente, usuario_gerente):
        u = UsuarioFactory.inactivo(
            restaurante_id=usuario_gerente.restaurante_id)
        res = client_gerente.post(self.URL, {"email": u.email})
        assert res.status_code == 200

    def test_gerente_no_puede_activar_de_otro_restaurante(self, db, client_gerente):
        u = UsuarioFactory.inactivo(restaurante_id=uuid.uuid4())
        res = client_gerente.post(self.URL, {"email": u.email})
        assert res.status_code == 403

    def test_sin_autenticacion_retorna_401(self, db, api_client):
        u = UsuarioFactory.inactivo()
        res = api_client.post(self.URL, {"email": u.email})
        assert res.status_code == 401

    def test_email_inexistente_retorna_404(self, db, client_admin):
        res = client_admin.post(self.URL, {"email": "nadie@gmail.com"})
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# VincularEmpleadoView  POST /api/auth/usuarios/vincular-empleado/
# ═══════════════════════════════════════════════════════════════════════════════

class TestVincularEmpleadoView:

    URL = "/api/auth/usuarios/vincular-empleado/"

    def test_admin_vincula_empleado(self, db, client_admin):
        u = UsuarioFactory.mesero()
        eid = uuid.uuid4()
        res = client_admin.post(self.URL, {
            "email":       u.email,
            "empleado_id": str(eid),
        })
        assert res.status_code == 200
        assert res.data["ok"] is True
        u.refresh_from_db()
        assert u.empleado_id == eid

    def test_gerente_vincula_empleado_de_su_restaurante(self, db, client_gerente, usuario_gerente):
        u = UsuarioFactory.mesero(
            restaurante_id=usuario_gerente.restaurante_id)
        eid = uuid.uuid4()
        res = client_gerente.post(self.URL, {
            "email":       u.email,
            "empleado_id": str(eid),
        })
        assert res.status_code == 200

    def test_gerente_no_puede_vincular_de_otro_restaurante(self, db, client_gerente):
        u = UsuarioFactory.mesero(restaurante_id=uuid.uuid4())
        res = client_gerente.post(self.URL, {
            "email":       u.email,
            "empleado_id": str(uuid.uuid4()),
        })
        assert res.status_code == 403

    def test_uuid_invalido_retorna_400(self, db, client_admin):
        u = UsuarioFactory.mesero()
        res = client_admin.post(self.URL, {
            "email":       u.email,
            "empleado_id": "no-es-uuid",
        })
        assert res.status_code == 400

    def test_email_inexistente_retorna_404(self, db, client_admin):
        res = client_admin.post(self.URL, {
            "email":       "nadie@gmail.com",
            "empleado_id": str(uuid.uuid4()),
        })
        assert res.status_code == 404

    def test_sin_email_retorna_400(self, db, client_admin):
        res = client_admin.post(self.URL, {"empleado_id": str(uuid.uuid4())})
        assert res.status_code == 400

    def test_sin_empleado_id_retorna_400(self, db, client_admin):
        u = UsuarioFactory.mesero()
        res = client_admin.post(self.URL, {"email": u.email})
        assert res.status_code == 400

    def test_mesero_no_puede_vincular(self, db, client_mesero):
        u = UsuarioFactory()
        res = client_mesero.post(self.URL, {
            "email":       u.email,
            "empleado_id": str(uuid.uuid4()),
        })
        assert res.status_code == 403

    def test_sin_autenticacion_retorna_401(self, db, api_client):
        u = UsuarioFactory()
        res = api_client.post(self.URL, {
            "email":       u.email,
            "empleado_id": str(uuid.uuid4()),
        })
        assert res.status_code == 401

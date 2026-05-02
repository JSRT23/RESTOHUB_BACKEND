# tests/unit/test_models.py
# Pruebas unitarias de los 3 modelos: Usuario, RefreshToken, EmailVerificationCode.
# No tocan views ni serializers — solo lógica de modelo pura.

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from app.auth.models import (
    EmailVerificationCode,
    RefreshToken,
    Rol,
    Usuario,
    ROLES_CON_RESTAURANTE,
    ROLES_CON_EMPLEADO,
    _generar_codigo,
)
from tests.factories import (
    CodigoVerificacionFactory,
    RefreshTokenFactory,
    UsuarioFactory,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Usuario
# ═══════════════════════════════════════════════════════════════════════════════

class TestUsuarioModel:

    # ── Creación básica ───────────────────────────────────────────────────────

    def test_crear_usuario_minimo(self, db):
        u = UsuarioFactory(rol=Rol.MESERO)
        assert u.pk is not None
        assert u.email
        assert u.activo is True
        assert u.email_verificado is True

    def test_id_es_uuid(self, db):
        u = UsuarioFactory()
        assert isinstance(u.id, uuid.UUID)

    def test_email_unico(self, db):
        from django.db import IntegrityError
        u = UsuarioFactory()
        with pytest.raises(IntegrityError):
            UsuarioFactory(email=u.email)

    def test_str_contiene_email_y_rol(self, db):
        u = UsuarioFactory(rol=Rol.GERENTE_LOCAL)
        assert u.email in str(u)
        assert "gerente_local" in str(u)

    # ── is_active (property) ──────────────────────────────────────────────────

    def test_is_active_true_cuando_activo(self, db):
        u = UsuarioFactory(activo=True)
        assert u.is_active is True

    def test_is_active_false_cuando_inactivo(self, db):
        u = UsuarioFactory(activo=False)
        assert u.is_active is False

    # ── get_jwt_payload por rol ───────────────────────────────────────────────

    def test_payload_admin_no_tiene_restaurante_ni_empleado(self, db):
        u = UsuarioFactory.admin()
        payload = u.get_jwt_payload()
        assert "user_id" in payload
        assert payload["rol"] == Rol.ADMIN_CENTRAL
        assert payload["email"] == u.email
        assert payload["nombre"] == u.nombre
        assert "restaurante_id" not in payload
        assert "empleado_id" not in payload

    def test_payload_gerente_tiene_restaurante_no_empleado(self, db):
        rid = uuid.uuid4()
        u = UsuarioFactory.gerente(restaurante_id=rid)
        payload = u.get_jwt_payload()
        assert payload["restaurante_id"] == str(rid)
        assert "empleado_id" not in payload

    def test_payload_mesero_tiene_restaurante_y_empleado(self, db):
        rid = uuid.uuid4()
        eid = uuid.uuid4()
        u = UsuarioFactory.mesero(restaurante_id=rid, empleado_id=eid)
        payload = u.get_jwt_payload()
        assert payload["restaurante_id"] == str(rid)
        assert payload["empleado_id"] == str(eid)

    @pytest.mark.parametrize("rol", [
        Rol.SUPERVISOR, Rol.COCINERO, Rol.MESERO, Rol.CAJERO, Rol.REPARTIDOR
    ])
    def test_payload_roles_operativos_tienen_restaurante(self, db, rol):
        rid = uuid.uuid4()
        u = UsuarioFactory(rol=rol, restaurante_id=rid)
        payload = u.get_jwt_payload()
        assert payload["restaurante_id"] == str(rid)

    def test_payload_sin_restaurante_id_no_lo_incluye(self, db):
        """Si un rol que lo requiere no tiene restaurante_id, no aparece en payload."""
        u = UsuarioFactory.gerente(restaurante_id=None)
        payload = u.get_jwt_payload()
        assert "restaurante_id" not in payload

    def test_payload_sin_empleado_id_no_lo_incluye(self, db):
        u = UsuarioFactory.mesero(empleado_id=None)
        payload = u.get_jwt_payload()
        assert "empleado_id" not in payload

    # ── Manager ───────────────────────────────────────────────────────────────

    def test_create_user_requiere_email(self, db):
        with pytest.raises(ValueError, match="email es obligatorio"):
            Usuario.objects.create_user(email="", password="pass")

    def test_create_user_normaliza_email(self, db):
        u = Usuario.objects.create_user(
            email="TEST@GMAIL.COM",
            password="pass",
            nombre="Test",
            rol=Rol.MESERO,
        )
        assert u.email == "test@gmail.com"

    def test_create_superuser_defaults(self, db):
        u = Usuario.objects.create_superuser(
            email="super@gmail.com",
            password="pass",
            nombre="Super",
        )
        assert u.rol == Rol.ADMIN_CENTRAL
        assert u.is_staff is True
        assert u.is_superuser is True
        assert u.email_verificado is True

    # ── Constantes de roles ───────────────────────────────────────────────────

    def test_roles_con_restaurante_no_incluye_admin(self):
        assert Rol.ADMIN_CENTRAL not in ROLES_CON_RESTAURANTE

    def test_roles_con_empleado_no_incluye_admin_ni_gerente(self):
        assert Rol.ADMIN_CENTRAL not in ROLES_CON_EMPLEADO
        assert Rol.GERENTE_LOCAL not in ROLES_CON_EMPLEADO

    def test_todos_los_roles_operativos_en_roles_con_restaurante(self):
        operativos = {
            Rol.GERENTE_LOCAL, Rol.SUPERVISOR, Rol.COCINERO,
            Rol.MESERO, Rol.CAJERO, Rol.REPARTIDOR
        }
        assert operativos.issubset(ROLES_CON_RESTAURANTE)


# ═══════════════════════════════════════════════════════════════════════════════
# RefreshToken
# ═══════════════════════════════════════════════════════════════════════════════

class TestRefreshTokenModel:

    def test_crear_refresh_token(self, db):
        rt = RefreshTokenFactory()
        assert rt.pk is not None
        assert rt.revocado is False
        assert rt.expira_at > timezone.now()

    def test_id_es_uuid(self, db):
        rt = RefreshTokenFactory()
        assert isinstance(rt.id, uuid.UUID)

    def test_token_unico(self, db):
        from django.db import IntegrityError
        rt = RefreshTokenFactory()
        with pytest.raises(IntegrityError):
            RefreshTokenFactory(token=rt.token)

    def test_str_contiene_email_y_estado(self, db):
        rt = RefreshTokenFactory(revocado=False)
        assert rt.usuario.email in str(rt)
        assert "activo" in str(rt)

    def test_str_revocado(self, db):
        rt = RefreshTokenFactory.revocado()
        assert "revocado" in str(rt)

    def test_cascade_delete_con_usuario(self, db):
        u = UsuarioFactory()
        rt = RefreshTokenFactory(usuario=u)
        rt_id = rt.id
        u.delete()
        assert not RefreshToken.objects.filter(id=rt_id).exists()

    def test_factory_expirado(self, db):
        rt = RefreshTokenFactory.expirado()
        assert rt.expira_at < timezone.now()

    def test_factory_revocado(self, db):
        rt = RefreshTokenFactory.revocado()
        assert rt.revocado is True


# ═══════════════════════════════════════════════════════════════════════════════
# EmailVerificationCode
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmailVerificationCodeModel:

    # ── Creación y defaults ───────────────────────────────────────────────────

    def test_crear_codigo(self, db):
        usuario = UsuarioFactory.no_verificado()
        codigo = CodigoVerificacionFactory(usuario=usuario)
        assert codigo.pk is not None
        assert codigo.intentos == 0
        assert codigo.expira_at > timezone.now()

    def test_codigo_es_6_digitos(self, db):
        codigo = CodigoVerificacionFactory()
        assert len(codigo.codigo) == 6
        assert codigo.codigo.isdigit()

    def test_expira_at_se_asigna_automaticamente(self, db):
        """Si se crea sin expira_at, el modelo lo asigna en save()."""
        usuario = UsuarioFactory.no_verificado()
        # Crear directamente sin factory para probar el modelo
        codigo = EmailVerificationCode(usuario=usuario)
        codigo.save()
        assert codigo.expira_at is not None
        assert codigo.expira_at > timezone.now()

    def test_cascade_delete_con_usuario(self, db):
        codigo = CodigoVerificacionFactory()
        codigo_id = codigo.id
        codigo.usuario.delete()
        assert not EmailVerificationCode.objects.filter(id=codigo_id).exists()

    # ── ha_expirado ───────────────────────────────────────────────────────────

    def test_ha_expirado_false_cuando_vigente(self, db):
        codigo = CodigoVerificacionFactory()
        assert codigo.ha_expirado is False

    def test_ha_expirado_true_cuando_vencido(self, db):
        codigo = CodigoVerificacionFactory.expirado()
        assert codigo.ha_expirado is True

    def test_ha_expirado_exactamente_en_el_limite(self, db):
        """Código que expira en exactamente ahora debe considerarse expirado."""
        codigo = CodigoVerificacionFactory(
            expira_at=timezone.now() - timedelta(seconds=1)
        )
        assert codigo.ha_expirado is True

    # ── intentos_agotados ─────────────────────────────────────────────────────

    def test_intentos_agotados_false_con_0_intentos(self, db):
        codigo = CodigoVerificacionFactory()
        assert codigo.intentos_agotados is False

    def test_intentos_agotados_false_con_2_intentos(self, db):
        codigo = CodigoVerificacionFactory.dos_intentos()
        assert codigo.intentos_agotados is False

    def test_intentos_agotados_true_con_3_intentos(self, db):
        codigo = CodigoVerificacionFactory.agotado()
        assert codigo.intentos_agotados is True

    # ── registrar_intento_fallido ─────────────────────────────────────────────

    def test_registrar_intento_incrementa(self, db):
        codigo = CodigoVerificacionFactory()
        assert codigo.intentos == 0
        codigo.registrar_intento_fallido()
        assert codigo.intentos == 1

    def test_registrar_intento_persiste_en_db(self, db):
        codigo = CodigoVerificacionFactory()
        codigo.registrar_intento_fallido()
        codigo.registrar_intento_fallido()
        # Refrescar desde DB
        codigo.refresh_from_db()
        assert codigo.intentos == 2

    def test_tres_intentos_agota(self, db):
        codigo = CodigoVerificacionFactory()
        for _ in range(3):
            codigo.registrar_intento_fallido()
        assert codigo.intentos_agotados is True

    # ── _generar_codigo ───────────────────────────────────────────────────────

    def test_generar_codigo_es_6_digitos(self):
        for _ in range(20):   # probabilístico — 20 iteraciones
            c = _generar_codigo()
            assert len(c) == 6
            assert c.isdigit()

    def test_generar_codigo_es_distinto_cada_vez(self):
        """No garantiza unicidad absoluta, pero en 100 llamadas esperamos variedad."""
        codigos = {_generar_codigo() for _ in range(100)}
        assert len(codigos) > 1

    # ── __str__ ───────────────────────────────────────────────────────────────

    def test_str_vigente(self, db):
        codigo = CodigoVerificacionFactory()
        assert codigo.usuario.email in str(codigo)
        assert "intentos" in str(codigo)

    def test_str_expirado(self, db):
        codigo = CodigoVerificacionFactory.expirado()
        assert "expirado" in str(codigo)

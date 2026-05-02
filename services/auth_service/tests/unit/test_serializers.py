# tests/unit/test_serializers.py
# Pruebas unitarias de los serializers — sin HTTP, sin views.
# Se llaman directamente con .is_valid() y .validated_data.

import uuid

import pytest

from app.auth.models import Rol
from app.auth.serializers import (
    CambiarPasswordSerializer,
    LoginSerializer,
    RegistroSerializer,
    UsuarioSerializer,
)
from tests.factories import UsuarioFactory


# ═══════════════════════════════════════════════════════════════════════════════
# LoginSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoginSerializer:

    def test_credenciales_validas(self, db):
        u = UsuarioFactory(email="chef@gmail.com")
        s = LoginSerializer(
            data={"email": "chef@gmail.com", "password": "testpass123"})
        assert s.is_valid(), s.errors
        assert s.validated_data["usuario"] == u

    def test_password_incorrecto(self, db):
        UsuarioFactory(email="chef@gmail.com")
        s = LoginSerializer(
            data={"email": "chef@gmail.com", "password": "wrong"})
        assert not s.is_valid()
        assert "non_field_errors" in s.errors

    def test_email_inexistente(self, db):
        s = LoginSerializer(
            data={"email": "nadie@gmail.com", "password": "pass"})
        assert not s.is_valid()

    def test_usuario_inactivo_falla(self, db):
        UsuarioFactory.inactivo(email="off@gmail.com")
        s = LoginSerializer(
            data={"email": "off@gmail.com", "password": "testpass123"})
        assert not s.is_valid()
        assert "non_field_errors" in s.errors

    def test_email_requerido(self, db):
        s = LoginSerializer(data={"password": "pass"})
        assert not s.is_valid()
        assert "email" in s.errors

    def test_password_requerido(self, db):
        s = LoginSerializer(data={"email": "a@gmail.com"})
        assert not s.is_valid()
        assert "password" in s.errors

    def test_password_no_aparece_en_validated_data(self, db):
        """password es write_only — no debe exponerse."""
        u = UsuarioFactory(email="x@gmail.com")
        s = LoginSerializer(
            data={"email": "x@gmail.com", "password": "testpass123"})
        assert s.is_valid()
        assert "password" not in s.validated_data


# ═══════════════════════════════════════════════════════════════════════════════
# RegistroSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistroSerializer:

    def _data_valido(self, **overrides):
        rid = uuid.uuid4()
        base = {
            "email":            "nuevo@gmail.com",
            "nombre":           "Juan Ramos",
            "password":         "Segura123!",
            "password_confirm": "Segura123!",
            "rol":              Rol.MESERO,
            "restaurante_id":   str(rid),
        }
        base.update(overrides)
        return base

    def test_datos_validos_mesero(self, db, mocker):
        mocker.patch(
            "app.auth.serializers.validar_email_completo",
            return_value=(True, ""),
        )
        s = RegistroSerializer(data=self._data_valido())
        assert s.is_valid(), s.errors

    def test_passwords_no_coinciden(self, db, mocker):
        mocker.patch(
            "app.auth.serializers.validar_email_completo",
            return_value=(True, ""),
        )
        data = self._data_valido(password_confirm="Distinta456!")
        s = RegistroSerializer(data=data)
        assert not s.is_valid()
        assert "password_confirm" in str(s.errors)

    def test_password_muy_corto(self, db, mocker):
        mocker.patch(
            "app.auth.serializers.validar_email_completo",
            return_value=(True, ""),
        )
        data = self._data_valido(password="corta", password_confirm="corta")
        s = RegistroSerializer(data=data)
        assert not s.is_valid()
        assert "password" in s.errors

    def test_rol_con_restaurante_requiere_restaurante_id(self, db, mocker):
        mocker.patch(
            "app.auth.serializers.validar_email_completo",
            return_value=(True, ""),
        )
        data = self._data_valido(restaurante_id=None)
        s = RegistroSerializer(data=data)
        assert not s.is_valid()
        assert "restaurante_id" in str(s.errors)

    def test_admin_central_sin_restaurante_id_es_valido(self, db, mocker):
        mocker.patch(
            "app.auth.serializers.validar_email_completo",
            return_value=(True, ""),
        )
        data = {
            "email":            "admin@gmail.com",
            "nombre":           "Admin",
            "password":         "Segura123!",
            "password_confirm": "Segura123!",
            "rol":              Rol.ADMIN_CENTRAL,
        }
        s = RegistroSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_admin_central_con_restaurante_id_falla(self, db, mocker):
        mocker.patch(
            "app.auth.serializers.validar_email_completo",
            return_value=(True, ""),
        )
        data = {
            "email":            "admin2@gmail.com",
            "nombre":           "Admin",
            "password":         "Segura123!",
            "password_confirm": "Segura123!",
            "rol":              Rol.ADMIN_CENTRAL,
            "restaurante_id":   str(uuid.uuid4()),
        }
        s = RegistroSerializer(data=data)
        assert not s.is_valid()
        assert "restaurante_id" in str(s.errors)

    def test_email_invalido_falla(self, db, mocker):
        mocker.patch(
            "app.auth.serializers.validar_email_completo",
            return_value=(False, "El dominio no existe."),
        )
        data = self._data_valido(email="fake@dominiofalso12345.xyz")
        s = RegistroSerializer(data=data)
        assert not s.is_valid()
        assert "email" in s.errors

    def test_create_hashea_password(self, db, mocker):
        mocker.patch(
            "app.auth.serializers.validar_email_completo",
            return_value=(True, ""),
        )
        s = RegistroSerializer(data=self._data_valido())
        assert s.is_valid()
        usuario = s.save()
        # La contraseña guardada no es el texto plano
        assert usuario.password != "Segura123!"
        assert usuario.check_password("Segura123!")

    @pytest.mark.parametrize("rol", [
        Rol.SUPERVISOR, Rol.COCINERO, Rol.MESERO, Rol.CAJERO, Rol.REPARTIDOR
    ])
    def test_roles_operativos_requieren_restaurante_id(self, db, mocker, rol):
        mocker.patch(
            "app.auth.serializers.validar_email_completo",
            return_value=(True, ""),
        )
        data = self._data_valido(rol=rol, restaurante_id=None)
        s = RegistroSerializer(data=data)
        assert not s.is_valid()


# ═══════════════════════════════════════════════════════════════════════════════
# UsuarioSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestUsuarioSerializer:

    def test_serializa_campos_correctos(self, db):
        u = UsuarioFactory()
        data = UsuarioSerializer(u).data
        assert data["email"] == u.email
        assert data["nombre"] == u.nombre
        assert data["rol"] == u.rol
        assert str(data["id"]) == str(u.id)

    def test_no_expone_password(self, db):
        u = UsuarioFactory()
        data = UsuarioSerializer(u).data
        assert "password" not in data

    def test_campos_read_only(self, db):
        u = UsuarioFactory()
        s = UsuarioSerializer(
            u, data={"id": str(uuid.uuid4()), "nombre": "Nuevo"}, partial=True)
        assert s.is_valid()
        # id no debe cambiar (read_only)
        s.save()
        assert str(u.id) == str(UsuarioSerializer(u).data["id"])

    def test_restaurante_id_puede_ser_null(self, db):
        u = UsuarioFactory.admin()
        data = UsuarioSerializer(u).data
        assert data["restaurante_id"] is None

    def test_activo_aparece_en_data(self, db):
        u = UsuarioFactory(activo=False)
        data = UsuarioSerializer(u).data
        assert data["activo"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# CambiarPasswordSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestCambiarPasswordSerializer:

    def test_datos_validos(self):
        s = CambiarPasswordSerializer(data={
            "password_actual": "vieja123",
            "password_nuevo":  "Nueva456!",
            "password_confirm": "Nueva456!",
        })
        assert s.is_valid(), s.errors

    def test_passwords_no_coinciden(self):
        s = CambiarPasswordSerializer(data={
            "password_actual":  "vieja123",
            "password_nuevo":   "Nueva456!",
            "password_confirm": "Diferente789!",
        })
        assert not s.is_valid()
        assert "password_confirm" in str(s.errors)

    def test_password_nuevo_muy_corto(self):
        s = CambiarPasswordSerializer(data={
            "password_actual":  "vieja123",
            "password_nuevo":   "corta",
            "password_confirm": "corta",
        })
        assert not s.is_valid()
        assert "password_nuevo" in s.errors

    def test_campos_requeridos(self):
        s = CambiarPasswordSerializer(data={})
        assert not s.is_valid()
        assert "password_actual" in s.errors
        assert "password_nuevo" in s.errors
        assert "password_confirm" in s.errors

    def test_write_only_no_expone_passwords(self):
        s = CambiarPasswordSerializer(data={
            "password_actual":  "vieja123",
            "password_nuevo":   "Nueva456!",
            "password_confirm": "Nueva456!",
        })
        assert s.is_valid()
        # Los campos write_only no aparecen en .data
        assert "password_actual" not in s.data
        assert "password_nuevo" not in s.data

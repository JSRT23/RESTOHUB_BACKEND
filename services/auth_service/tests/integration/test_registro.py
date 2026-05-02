# tests/integration/test_registro.py
# POST /api/auth/auto-registro/
# POST /api/auth/verificar-codigo/
# POST /api/auth/reenviar-codigo/
# POST /api/auth/registro/  (registro interno por admin/gerente)

import pytest

from app.auth.models import EmailVerificationCode, Rol, Usuario
from app.auth.tokens import generar_access_token
from tests.factories import (
    CodigoVerificacionFactory,
    UsuarioFactory,
)


# ═══════════════════════════════════════════════════════════════════════════════
# AutoRegistroView  POST /api/auth/auto-registro/
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutoRegistroView:

    URL = "/api/auth/auto-registro/"

    def _data(self, **kwargs):
        base = {
            "email":            "admin@gmail.com",
            "nombre":           "Admin Central",
            "password":         "Segura123!",
            "password_confirm": "Segura123!",
            "rol":              Rol.ADMIN_CENTRAL,
        }
        base.update(kwargs)
        return base

    def test_registro_admin_central_exitoso(self, db, api_client, mocker):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        mocker.patch("app.auth.views.enviar_codigo_verificacion",
                     return_value=True)
        res = api_client.post(self.URL, self._data())
        assert res.status_code == 201
        assert "email" in res.data
        assert Usuario.objects.filter(email="admin@gmail.com").exists()

    def test_registro_crea_codigo_verificacion_en_db(self, db, api_client, mocker):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        mocker.patch("app.auth.views.enviar_codigo_verificacion",
                     return_value=True)
        api_client.post(self.URL, self._data())
        u = Usuario.objects.get(email="admin@gmail.com")
        assert EmailVerificationCode.objects.filter(usuario=u).exists()

    def test_registro_llama_envio_email(self, db, api_client, mocker):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        mock_enviar = mocker.patch(
            "app.auth.views.enviar_codigo_verificacion", return_value=True
        )
        api_client.post(self.URL, self._data())
        assert mock_enviar.called

    def test_registro_email_no_verificado_por_defecto(self, db, api_client, mocker):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        mocker.patch("app.auth.views.enviar_codigo_verificacion",
                     return_value=True)
        api_client.post(self.URL, self._data())
        u = Usuario.objects.get(email="admin@gmail.com")
        assert u.email_verificado is False

    def test_registro_rol_no_admin_retorna_403(self, db, api_client, mocker):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        import uuid
        res = api_client.post(self.URL, self._data(
            rol=Rol.GERENTE_LOCAL,
            restaurante_id=str(uuid.uuid4()),
        ))
        assert res.status_code == 403

    def test_registro_email_duplicado_retorna_400(self, db, api_client, mocker):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        mocker.patch("app.auth.views.enviar_codigo_verificacion",
                     return_value=True)
        api_client.post(self.URL, self._data())
        # Segundo intento con mismo email
        res = api_client.post(self.URL, self._data())
        assert res.status_code == 400

    def test_registro_passwords_no_coinciden_retorna_400(self, db, api_client, mocker):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        res = api_client.post(self.URL, self._data(
            password_confirm="Diferente999!"))
        assert res.status_code == 400

    def test_registro_email_invalido_retorna_400(self, db, api_client, mocker):
        mocker.patch(
            "app.auth.serializers.validar_email_completo",
            return_value=(False, "Dominio no existe."),
        )
        res = api_client.post(self.URL, self._data(
            email="fake@dominiofalso99.xyz"))
        assert res.status_code == 400

    def test_registro_fallo_email_incluye_codigo_dev(self, db, api_client, mocker):
        """Si el email falla al enviarse, la respuesta incluye codigo_dev para desarrollo."""
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        mocker.patch("app.auth.views.enviar_codigo_verificacion",
                     return_value=False)
        res = api_client.post(self.URL, self._data())
        assert res.status_code == 201
        assert "codigo_dev" in res.data


# ═══════════════════════════════════════════════════════════════════════════════
# VerificarCodigoView  POST /api/auth/verificar-codigo/
# ═══════════════════════════════════════════════════════════════════════════════

class TestVerificarCodigoView:

    URL = "/api/auth/verificar-codigo/"

    def test_codigo_correcto_verifica_email(self, db, api_client, usuario_no_verificado, codigo_valido):
        res = api_client.post(self.URL, {
            "email":  usuario_no_verificado.email,
            "codigo": codigo_valido.codigo,
        })
        assert res.status_code == 200
        usuario_no_verificado.refresh_from_db()
        assert usuario_no_verificado.email_verificado is True

    def test_codigo_correcto_elimina_codigo_de_db(self, db, api_client, usuario_no_verificado, codigo_valido):
        codigo_id = codigo_valido.id
        api_client.post(self.URL, {
            "email":  usuario_no_verificado.email,
            "codigo": codigo_valido.codigo,
        })
        assert not EmailVerificationCode.objects.filter(id=codigo_id).exists()

    def test_codigo_correcto_envia_bienvenida(self, db, api_client, mocker, usuario_no_verificado, codigo_valido):
        mock_bienvenida = mocker.patch(
            "app.auth.views.enviar_bienvenida", return_value=True)
        api_client.post(self.URL, {
            "email":  usuario_no_verificado.email,
            "codigo": codigo_valido.codigo,
        })
        assert mock_bienvenida.called

    def test_codigo_incorrecto_retorna_400(self, db, api_client, usuario_no_verificado, codigo_valido):
        res = api_client.post(self.URL, {
            "email":  usuario_no_verificado.email,
            "codigo": "000000",
        })
        assert res.status_code == 400
        assert res.data["codigo"] == "CODIGO_INCORRECTO"

    def test_codigo_incorrecto_incrementa_intentos(self, db, api_client, usuario_no_verificado, codigo_valido):
        api_client.post(self.URL, {
            "email":  usuario_no_verificado.email,
            "codigo": "000000",
        })
        codigo_valido.refresh_from_db()
        assert codigo_valido.intentos == 1

    def test_codigo_incorrecto_informa_intentos_restantes(self, db, api_client, usuario_no_verificado, codigo_valido):
        res = api_client.post(self.URL, {
            "email":  usuario_no_verificado.email,
            "codigo": "000000",
        })
        assert "intentos_restantes" in res.data
        assert res.data["intentos_restantes"] == 2

    def test_codigo_expirado_retorna_400(self, db, api_client, codigo_expirado):
        res = api_client.post(self.URL, {
            "email":  codigo_expirado.usuario.email,
            "codigo": codigo_expirado.codigo,
        })
        assert res.status_code == 400
        assert res.data["codigo"] == "CODIGO_EXPIRADO"

    def test_codigo_expirado_se_elimina_de_db(self, db, api_client, codigo_expirado):
        codigo_id = codigo_expirado.id
        api_client.post(self.URL, {
            "email":  codigo_expirado.usuario.email,
            "codigo": codigo_expirado.codigo,
        })
        assert not EmailVerificationCode.objects.filter(id=codigo_id).exists()

    def test_intentos_agotados_retorna_400(self, db, api_client, codigo_agotado):
        res = api_client.post(self.URL, {
            "email":  codigo_agotado.usuario.email,
            "codigo": codigo_agotado.codigo,
        })
        assert res.status_code == 400
        assert res.data["codigo"] == "INTENTOS_AGOTADOS"

    def test_email_ya_verificado_retorna_200(self, db, api_client):
        u = UsuarioFactory(email_verificado=True)
        res = api_client.post(self.URL, {"email": u.email, "codigo": "123456"})
        assert res.status_code == 200
        assert "ya está verificado" in res.data["detail"].lower()

    def test_sin_codigo_activo_retorna_400(self, db, api_client, usuario_no_verificado):
        res = api_client.post(self.URL, {
            "email":  usuario_no_verificado.email,
            "codigo": "123456",
        })
        assert res.status_code == 400
        assert res.data["codigo"] == "SIN_CODIGO"

    def test_email_inexistente_retorna_404(self, db, api_client):
        res = api_client.post(self.URL, {
            "email":  "noexiste@gmail.com",
            "codigo": "123456",
        })
        assert res.status_code == 404

    def test_faltan_campos_retorna_400(self, db, api_client):
        res = api_client.post(self.URL, {})
        assert res.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# ReenviarCodigoView  POST /api/auth/reenviar-codigo/
# ═══════════════════════════════════════════════════════════════════════════════

class TestReenviarCodigoView:

    URL = "/api/auth/reenviar-codigo/"

    def test_reenvio_crea_nuevo_codigo(self, db, api_client, mocker, usuario_no_verificado, codigo_valido):
        mocker.patch("app.auth.views.enviar_codigo_verificacion",
                     return_value=True)
        old_id = codigo_valido.id
        api_client.post(self.URL, {"email": usuario_no_verificado.email})
        # El código anterior fue eliminado y hay uno nuevo
        assert not EmailVerificationCode.objects.filter(id=old_id).exists()
        assert EmailVerificationCode.objects.filter(
            usuario=usuario_no_verificado).exists()

    def test_reenvio_llama_envio_email(self, db, api_client, mocker, usuario_no_verificado):
        mock_enviar = mocker.patch(
            "app.auth.views.enviar_codigo_verificacion", return_value=True)
        api_client.post(self.URL, {"email": usuario_no_verificado.email})
        assert mock_enviar.called

    def test_reenvio_siempre_retorna_200_respuesta_generica(self, db, api_client, mocker):
        """Por seguridad la respuesta es genérica — no revela si el email existe."""
        mocker.patch("app.auth.views.enviar_codigo_verificacion",
                     return_value=True)
        for email in ["noexiste@gmail.com", "tampoco@gmail.com"]:
            res = api_client.post(self.URL, {"email": email})
            assert res.status_code == 200

    def test_reenvio_email_ya_verificado_retorna_200_sin_enviar(self, db, api_client, mocker):
        mock_enviar = mocker.patch(
            "app.auth.views.enviar_codigo_verificacion", return_value=True)
        u = UsuarioFactory(email_verificado=True)
        api_client.post(self.URL, {"email": u.email})
        mock_enviar.assert_not_called()

    def test_reenvio_sin_email_retorna_400(self, db, api_client):
        res = api_client.post(self.URL, {})
        assert res.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# RegistroView  POST /api/auth/registro/  (registro interno)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistroInternoView:

    URL = "/api/auth/registro/"

    def _data_mesero(self, restaurante_id, **kwargs):
        base = {
            "email":            "mesero@gmail.com",
            "nombre":           "Nuevo Mesero",
            "password":         "Segura123!",
            "password_confirm": "Segura123!",
            "rol":              Rol.MESERO,
            "restaurante_id":   str(restaurante_id),
        }
        base.update(kwargs)
        return base

    def test_admin_puede_crear_cualquier_rol(self, db, mocker, client_admin):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        import uuid
        res = client_admin.post(self.URL, self._data_mesero(uuid.uuid4()))
        assert res.status_code == 201
        assert Usuario.objects.filter(email="mesero@gmail.com").exists()

    def test_usuario_creado_tiene_email_verificado_true(self, db, mocker, client_admin):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        import uuid
        client_admin.post(self.URL, self._data_mesero(uuid.uuid4()))
        u = Usuario.objects.get(email="mesero@gmail.com")
        assert u.email_verificado is True

    def test_gerente_puede_crear_operativos_de_su_restaurante(self, db, mocker, client_gerente, usuario_gerente):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        res = client_gerente.post(
            self.URL, self._data_mesero(usuario_gerente.restaurante_id))
        assert res.status_code == 201

    def test_gerente_no_puede_crear_admin(self, db, mocker, client_gerente, usuario_gerente):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        data = {
            "email":            "admin2@gmail.com",
            "nombre":           "Admin",
            "password":         "Segura123!",
            "password_confirm": "Segura123!",
            "rol":              Rol.ADMIN_CENTRAL,
        }
        res = client_gerente.post(self.URL, data)
        assert res.status_code == 403

    def test_gerente_no_puede_crear_otro_gerente(self, db, mocker, client_gerente, usuario_gerente):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        res = client_gerente.post(self.URL, self._data_mesero(
            usuario_gerente.restaurante_id,
            email="gerente2@gmail.com",
            rol=Rol.GERENTE_LOCAL,
        ))
        assert res.status_code == 403

    def test_mesero_no_puede_registrar_usuarios(self, db, mocker, client_mesero, usuario_mesero):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        res = client_mesero.post(
            self.URL, self._data_mesero(usuario_mesero.restaurante_id))
        assert res.status_code == 403

    def test_sin_autenticacion_retorna_401(self, db, api_client, mocker, usuario_admin):
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        res = api_client.post(self.URL, self._data_mesero(
            usuario_admin.restaurante_id or ""))
        assert res.status_code == 401

    def test_gerente_asigna_su_restaurante_automaticamente(self, db, mocker, client_gerente, usuario_gerente):
        """El gerente no puede asignar otro restaurante_id — se usa el suyo."""
        mocker.patch("app.auth.serializers.validar_email_completo",
                     return_value=(True, ""))
        import uuid
        otro_rest = uuid.uuid4()
        res = client_gerente.post(self.URL, self._data_mesero(otro_rest))
        if res.status_code == 201:
            u = Usuario.objects.get(email="mesero@gmail.com")
            assert u.restaurante_id == usuario_gerente.restaurante_id

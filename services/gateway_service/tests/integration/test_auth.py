# tests/integration/test_auth.py
"""
Tests de queries y mutations de autenticación.
Todos los clientes HTTP están mockeados.
"""
import uuid
import pytest
from tests.conftest import gql, make_request
from app.gateway.graphql.schema import schema


# ═══════════════════════════════════════════════════════════════════════════
# QUERY: me
# ═══════════════════════════════════════════════════════════════════════════

ME_QUERY = """
query {
  me {
    id
    email
    rol
  }
}
"""


class TestQueryMe:

    def test_me_autenticado(self):
        result = gql(ME_QUERY, rol="gerente_local")
        assert result.errors is None
        assert result.data["me"]["rol"] == "gerente_local"
        assert result.data["me"]["email"] == "gerente_local@test.com"

    def test_me_sin_auth_lanza_error(self):
        result = gql(ME_QUERY)  # sin rol → jwt_user = None
        assert result.errors is not None
        assert any("UNAUTHENTICATED" in str(e) for e in result.errors)


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION: login
# ═══════════════════════════════════════════════════════════════════════════

LOGIN_MUTATION = """
mutation Login($email: String!, $password: String!) {
  login(email: $email, password: $password) {
    ok
    error
    payload {
      accessToken
      refreshToken
    }
  }
}
"""


class TestMutationLogin:

    def test_login_exitoso(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.login",
            return_value={
                "access_token":  "tok_access",
                "refresh_token": "tok_refresh",
                "usuario": {"id": str(uuid.uuid4()), "email": "u@test.com", "rol": "cajero"},
            },
        )
        result = gql(LOGIN_MUTATION, {
                     "email": "u@test.com", "password": "pass123"})
        assert result.errors is None
        assert result.data["login"]["ok"] is True
        assert result.data["login"]["payload"]["accessToken"] == "tok_access"

    def test_login_credenciales_invalidas(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.login",
            return_value={
                "_error": True, "detail": "Credenciales inválidas.", "codigo": "INVALID"},
        )
        result = gql(LOGIN_MUTATION, {
                     "email": "x@test.com", "password": "wrong"})
        assert result.errors is None
        assert result.data["login"]["ok"] is False
        assert result.data["login"]["error"] is not None

    def test_login_servicio_caido(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.login",
            return_value=None,
        )
        result = gql(LOGIN_MUTATION, {"email": "x@test.com", "password": "p"})
        assert result.data["login"]["ok"] is False
        assert "conexión" in result.data["login"]["error"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION: autoRegistro
# ═══════════════════════════════════════════════════════════════════════════

AUTO_REGISTRO = """
mutation {
  autoRegistro(
    email: "nuevo@test.com"
    nombre: "Nuevo Usuario"
    password: "pass1234"
    passwordConfirm: "pass1234"
  ) {
    ok
    error
    emailEnviado
  }
}
"""


class TestMutationAutoRegistro:

    def test_registro_exitoso(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.auto_registro",
            return_value={"email_enviado": True},
        )
        result = gql(AUTO_REGISTRO)
        assert result.errors is None
        assert result.data["autoRegistro"]["ok"] is True
        assert result.data["autoRegistro"]["emailEnviado"] is True

    def test_registro_email_duplicado(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.auto_registro",
            return_value={"_error": True, "email": [
                "Ya existe una cuenta con este email."]},
        )
        result = gql(AUTO_REGISTRO)
        assert result.data["autoRegistro"]["ok"] is False
        assert result.data["autoRegistro"]["error"] is not None

    def test_registro_servicio_caido(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.auto_registro",
            return_value=None,
        )
        result = gql(AUTO_REGISTRO)
        assert result.data["autoRegistro"]["ok"] is False


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION: registrarUsuario (requiere admin/gerente)
# ═══════════════════════════════════════════════════════════════════════════

REGISTRAR_USUARIO = """
mutation {
  registrarUsuario(
    email: "emp@test.com"
    nombre: "Emp Test"
    password: "pass1234"
    passwordConfirm: "pass1234"
    rol: "cajero"
  ) {
    ok
    error
    usuario { id email rol }
  }
}
"""


class TestMutationRegistrarUsuario:

    def test_admin_puede_registrar(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.registro",
            return_value={"id": str(uuid.uuid4()),
                          "email": "emp@test.com", "rol": "cajero"},
        )
        result = gql(REGISTRAR_USUARIO, rol="admin_central")
        assert result.errors is None
        assert result.data["registrarUsuario"]["ok"] is True

    def test_gerente_puede_registrar(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.registro",
            return_value={"id": str(uuid.uuid4()),
                          "email": "emp@test.com", "rol": "cajero"},
        )
        result = gql(REGISTRAR_USUARIO, rol="gerente_local")
        assert result.data["registrarUsuario"]["ok"] is True

    def test_cajero_no_puede_registrar(self):
        result = gql(REGISTRAR_USUARIO, rol="cajero")
        assert result.data["registrarUsuario"]["ok"] is False
        assert "permiso" in result.data["registrarUsuario"]["error"].lower()

    def test_anonimo_no_puede_registrar(self):
        result = gql(REGISTRAR_USUARIO)  # sin rol
        assert result.data["registrarUsuario"]["ok"] is False


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION: desactivarUsuario / activarUsuario
# ═══════════════════════════════════════════════════════════════════════════

class TestMutationActivarDesactivar:

    DESACTIVAR = """
    mutation { desactivarUsuario(email: "x@test.com") { ok error } }
    """
    ACTIVAR = """
    mutation { activarUsuario(email: "x@test.com") { ok error } }
    """

    def test_admin_desactiva(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.desactivar_usuario",
            return_value={"ok": True},
        )
        result = gql(self.DESACTIVAR, rol="admin_central")
        assert result.data["desactivarUsuario"]["ok"] is True

    def test_supervisor_no_puede_desactivar(self):
        result = gql(self.DESACTIVAR, rol="supervisor")
        assert result.data["desactivarUsuario"]["ok"] is False

    def test_admin_activa(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.activar_usuario",
            return_value={"ok": True},
        )
        result = gql(self.ACTIVAR, rol="admin_central")
        assert result.data["activarUsuario"]["ok"] is True

    def test_cocinero_no_puede_activar(self):
        result = gql(self.ACTIVAR, rol="cocinero")
        assert result.data["activarUsuario"]["ok"] is False


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION: vincularEmpleadoId
# ═══════════════════════════════════════════════════════════════════════════

VINCULAR = """
mutation {
  vincularEmpleadoId(email: "emp@test.com", empleadoId: "abc123") {
    ok error
  }
}
"""


class TestMutationVincularEmpleadoId:

    def test_admin_vincula(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.vincular_empleado",
            return_value={"ok": True},
        )
        result = gql(VINCULAR, rol="admin_central")
        assert result.data["vincularEmpleadoId"]["ok"] is True

    def test_gerente_vincula(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.vincular_empleado",
            return_value={"ok": True},
        )
        result = gql(VINCULAR, rol="gerente_local")
        assert result.data["vincularEmpleadoId"]["ok"] is True

    def test_cajero_no_vincula(self):
        result = gql(VINCULAR, rol="cajero")
        assert result.data["vincularEmpleadoId"]["ok"] is False

    def test_servicio_falla(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.auth.mutations.auth_client.vincular_empleado",
            return_value={"_error": True, "detail": "No encontrado."},
        )
        result = gql(VINCULAR, rol="admin_central")
        assert result.data["vincularEmpleadoId"]["ok"] is False

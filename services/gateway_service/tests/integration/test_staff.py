# tests/integration/test_staff.py
import uuid
import pytest
from tests.conftest import gql


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION: crearEmpleado
# ═══════════════════════════════════════════════════════════════════════════

CREAR_EMPLEADO = """
mutation {
  crearEmpleado(
    nombre: "Ana"
    apellido: "García"
    documento: "123456789"
    email: "ana@test.com"
    rol: "cajero"
    pais: "CO"
    restaurante: "abc123"
  ) {
    ok errores
    empleado { id nombre }
  }
}
"""


class TestCrearEmpleado:

    def _mock_staff(self, mocker, data):
        return mocker.patch(
            "app.gateway.graphql.services.staff.mutations.staff_client.crear_empleado",
            return_value=data,
        )

    def _mock_auth(self, mocker, data=None):
        return mocker.patch(
            "app.gateway.graphql.services.staff.mutations.auth_client.vincular_empleado",
            return_value=data or {"ok": True},
        )

    def test_crear_empleado_exitoso(self, mocker):
        eid = str(uuid.uuid4())
        self._mock_staff(
            mocker, {"id": eid, "nombre": "Ana", "apellido": "García"})
        self._mock_auth(mocker)
        result = gql(CREAR_EMPLEADO, rol="admin_central")
        assert result.errors is None
        assert result.data["crearEmpleado"]["ok"] is True
        assert result.data["crearEmpleado"]["empleado"]["id"] == eid

    def test_crear_empleado_error_servicio(self, mocker):
        self._mock_staff(mocker, None)
        result = gql(CREAR_EMPLEADO, rol="admin_central")
        assert result.data["crearEmpleado"]["ok"] is False
        assert result.data["crearEmpleado"]["errores"] is not None

    def test_crear_empleado_error_validacion(self, mocker):
        self._mock_staff(
            mocker, {"_error": True, "email": ["Email ya registrado."]})
        result = gql(CREAR_EMPLEADO, rol="gerente_local")
        assert result.data["crearEmpleado"]["ok"] is False
        assert "email" in result.data["crearEmpleado"]["errores"]

    def test_vincular_auth_falla_no_revierte_empleado(self, mocker):
        """Si vincular en auth falla, el empleado ya fue creado — no se revierte."""
        eid = str(uuid.uuid4())
        self._mock_staff(mocker, {"id": eid, "nombre": "Ana"})
        self._mock_auth(
            mocker, {"_error": True, "detail": "No se pudo vincular."})
        result = gql(CREAR_EMPLEADO, rol="admin_central")
        # El empleado se creó OK — la vinculación de auth es best-effort
        assert result.data["crearEmpleado"]["ok"] is True


# ═══════════════════════════════════════════════════════════════════════════
# MUTATIONS: Turnos
# ═══════════════════════════════════════════════════════════════════════════

class TestTurnos:

    def _turno_data(self):
        return {
            "id": str(uuid.uuid4()),
            "estado": "programado",
            "fechaInicio": "2026-05-01T08:00:00",
            "fechaFin": "2026-05-01T16:00:00",
        }

    def test_crear_turno(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.staff.mutations.staff_client.crear_turno",
            return_value=self._turno_data(),
        )
        result = gql("""
        mutation {
          crearTurno(
            empleado: "emp123"
            restauranteId: "rest123"
            fechaInicio: "2026-05-01T08:00:00"
            fechaFin: "2026-05-01T16:00:00"
          ) { ok errores turno { id estado } }
        }
        """, rol="supervisor")
        assert result.errors is None
        assert result.data["crearTurno"]["ok"] is True
        assert result.data["crearTurno"]["turno"]["estado"] == "programado"

    def test_crear_turno_falla(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.staff.mutations.staff_client.crear_turno",
            return_value=None,
        )
        result = gql("""
        mutation {
          crearTurno(
            empleado: "emp123" restauranteId: "r" fechaInicio: "x" fechaFin: "y"
          ) { ok errores }
        }
        """, rol="admin_central")
        assert result.data["crearTurno"]["ok"] is False

    def test_iniciar_turno(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.staff.mutations.staff_client.iniciar_turno",
            return_value={**self._turno_data(), "estado": "activo"},
        )
        result = gql("""
        mutation { iniciarTurno(turnoId: "t1") { ok turno { estado } } }
        """, rol="supervisor")
        assert result.data["iniciarTurno"]["ok"] is True
        assert result.data["iniciarTurno"]["turno"]["estado"] == "activo"

    def test_cancelar_turno(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.staff.mutations.staff_client.cancelar_turno",
            return_value={**self._turno_data(), "estado": "cancelado"},
        )
        result = gql("""
        mutation { cancelarTurno(turnoId: "t1") { ok turno { estado } } }
        """, rol="supervisor")
        assert result.data["cancelarTurno"]["ok"] is True

    def test_completar_turno(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.staff.mutations.staff_client._post",
            return_value={**self._turno_data(), "estado": "completado"},
        )
        result = gql("""
        mutation { completarTurno(turnoId: "t1") { ok turno { estado } } }
        """, rol="supervisor")
        assert result.data["completarTurno"]["ok"] is True
        assert result.data["completarTurno"]["turno"]["estado"] == "completado"

    def test_completar_turno_error_servicio(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.staff.mutations.staff_client._post",
            return_value={"_error": True, "detail": "Turno no está activo."},
        )
        result = gql("""
        mutation { completarTurno(turnoId: "t1") { ok errores } }
        """, rol="supervisor")
        assert result.data["completarTurno"]["ok"] is False
        assert "activo" in result.data["completarTurno"]["errores"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# MUTATIONS: Asistencia
# ═══════════════════════════════════════════════════════════════════════════

class TestAsistencia:

    def test_registrar_entrada_qr(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.staff.mutations.staff_client.registrar_entrada",
            return_value={"id": str(uuid.uuid4()),
                          "horaEntrada": "2026-05-01T08:00:00"},
        )
        result = gql("""
        mutation {
          registrarEntrada(qrToken: "tok123") {
            ok errores registro { id }
          }
        }
        """, rol="cocinero")
        assert result.errors is None
        assert result.data["registrarEntrada"]["ok"] is True

    def test_registrar_entrada_sin_token_ni_turno_falla(self):
        result = gql("""
        mutation { registrarEntrada { ok errores } }
        """, rol="cocinero")
        assert result.data["registrarEntrada"]["ok"] is False
        assert "qr_token" in result.data["registrarEntrada"]["errores"].lower() or \
               "turno_id" in result.data["registrarEntrada"]["errores"].lower() or \
               "requiere" in result.data["registrarEntrada"]["errores"].lower()

    def test_registrar_salida(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.staff.mutations.staff_client.registrar_salida",
            return_value={"id": str(uuid.uuid4()),
                          "horaSalida": "2026-05-01T16:05:00"},
        )
        result = gql("""
        mutation { registrarSalida(turnoId: "t1") { ok errores } }
        """, rol="cocinero")
        assert result.data["registrarSalida"]["ok"] is True


# ═══════════════════════════════════════════════════════════════════════════
# MUTATIONS: ActivarEmpleado (solo admin_central)
# ═══════════════════════════════════════════════════════════════════════════

class TestActivarEmpleado:

    def test_admin_puede_activar(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.staff.mutations.staff_client.editar_empleado",
            return_value={"id": "emp1", "activo": True},
        )
        result = gql("""
        mutation { activarEmpleado(empleadoId: "emp1") { ok errores } }
        """, rol="admin_central")
        assert result.data["activarEmpleado"]["ok"] is True

    def test_gerente_no_puede_activar(self):
        result = gql("""
        mutation { activarEmpleado(empleadoId: "emp1") { ok errores } }
        """, rol="gerente_local")
        assert result.data["activarEmpleado"]["ok"] is False
        assert "admin" in result.data["activarEmpleado"]["errores"].lower()

    def test_generar_nomina_sin_empleado_ni_restaurante(self):
        result = gql("""
        mutation {
          generarNomina(periodoInicio: "2026-04-01", periodoFin: "2026-04-30") {
            ok errores
          }
        }
        """, rol="gerente_local")
        assert result.data["generarNomina"]["ok"] is False
        assert "empleado_id" in result.data["generarNomina"]["errores"].lower() or \
               "restaurante_id" in result.data["generarNomina"]["errores"].lower(
        )

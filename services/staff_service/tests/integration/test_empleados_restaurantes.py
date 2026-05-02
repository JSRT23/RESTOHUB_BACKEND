# tests/integration/test_empleados_restaurantes.py
import uuid
import pytest
from datetime import date

from tests.conftest import (
    RestauranteLocalFactory,
    EmpleadoFactory,
    ConfiguracionLaboralPaisFactory,
)

RESTAURANTES_URL = "/api/staff/restaurantes/"
EMPLEADOS_URL = "/api/staff/empleados/"


# ═══════════════════════════════════════════════════════════
# RestauranteLocal
# ═══════════════════════════════════════════════════════════

class TestRestauranteLocalViewSet:

    def test_listar_restaurantes(self, db, api_client):
        RestauranteLocalFactory.create_batch(3)
        res = api_client.get(RESTAURANTES_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_detalle_restaurante(self, db, api_client, restaurante):
        res = api_client.get(f"{RESTAURANTES_URL}{restaurante.id}/")
        assert res.status_code == 200
        assert str(res.data["restaurante_id"]) == str(
            restaurante.restaurante_id)

    def test_restaurante_inexistente_404(self, db, api_client):
        res = api_client.get(f"{RESTAURANTES_URL}{uuid.uuid4()}/")
        assert res.status_code == 404

    def test_filtrar_por_pais(self, db, api_client):
        RestauranteLocalFactory(pais="CO")
        RestauranteLocalFactory(pais="MX")
        res = api_client.get(f"{RESTAURANTES_URL}?pais=CO")
        assert res.status_code == 200
        assert all(r["pais"] == "CO" for r in res.data)

    def test_filtrar_por_activo(self, db, api_client):
        RestauranteLocalFactory(activo=True)
        RestauranteLocalFactory(activo=False)
        res = api_client.get(f"{RESTAURANTES_URL}?activo=true")
        assert res.status_code == 200
        assert all(r["activo"] for r in res.data)

    def test_no_permite_post(self, db, api_client):
        res = api_client.post(RESTAURANTES_URL, {})
        assert res.status_code == 405

    def test_config_laboral_action(self, db, api_client, restaurante):
        ConfiguracionLaboralPaisFactory(pais=restaurante.pais)
        res = api_client.get(
            f"{RESTAURANTES_URL}{restaurante.id}/config-laboral/")
        assert res.status_code == 200
        assert "horas_max_diarias" in res.data

    def test_config_laboral_sin_config_404(self, db, api_client, restaurante):
        res = api_client.get(
            f"{RESTAURANTES_URL}{restaurante.id}/config-laboral/")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════
# Empleado
# ═══════════════════════════════════════════════════════════

class TestEmpleadoViewSet:

    def _payload(self, restaurante, pais="CO"):
        return {
            "nombre": "Carlos",
            "apellido": "Ruiz",
            "documento": f"CC{uuid.uuid4().int % 10**8:08d}",
            "email": f"carlos{uuid.uuid4().hex[:6]}@test.com",
            "telefono": "3009876543",
            "rol": "cajero",
            "pais": pais,
            "restaurante": str(restaurante.restaurante_id),
        }

    def test_listar_empleados(self, db, api_client, empleado):
        res = api_client.get(EMPLEADOS_URL)
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_crear_empleado(self, db, api_client, restaurante):
        res = api_client.post(
            EMPLEADOS_URL, self._payload(restaurante), format="json")
        assert res.status_code == 201
        assert res.data["nombre"] == "Carlos"

    def test_crear_empleado_restaurante_invalido(self, db, api_client):
        payload = self._payload(RestauranteLocalFactory.build())
        res = api_client.post(EMPLEADOS_URL, payload, format="json")
        assert res.status_code == 400

    def test_detalle_empleado(self, db, api_client, empleado):
        res = api_client.get(f"{EMPLEADOS_URL}{empleado.id}/")
        assert res.status_code == 200
        assert res.data["email"] == empleado.email

    def test_actualizar_empleado(self, db, api_client, empleado, restaurante):
        res = api_client.patch(
            f"{EMPLEADOS_URL}{empleado.id}/",
            {"telefono": "3119999999"},
            format="json",
        )
        assert res.status_code == 200
        assert res.data["telefono"] == "3119999999"

    def test_no_permite_delete(self, db, api_client, empleado):
        res = api_client.delete(f"{EMPLEADOS_URL}{empleado.id}/")
        assert res.status_code == 405

    def test_desactivar_empleado(self, db, api_client, empleado):
        res = api_client.post(f"{EMPLEADOS_URL}{empleado.id}/desactivar/")
        assert res.status_code == 200
        assert res.data["activo"] is False

    def test_desactivar_ya_inactivo_falla(self, db, api_client, empleado):
        empleado.activo = False
        empleado.save()
        res = api_client.post(f"{EMPLEADOS_URL}{empleado.id}/desactivar/")
        assert res.status_code == 400

    def test_filtrar_por_rol(self, db, api_client, restaurante):
        EmpleadoFactory(restaurante=restaurante, rol="cocinero")
        EmpleadoFactory(restaurante=restaurante, rol="mesero")
        res = api_client.get(f"{EMPLEADOS_URL}?rol=cocinero")
        assert res.status_code == 200
        assert all(e["rol"] == "cocinero" for e in res.data)

    def test_filtrar_por_activo(self, db, api_client, restaurante):
        EmpleadoFactory(restaurante=restaurante, activo=True)
        EmpleadoFactory(restaurante=restaurante, activo=False)
        res = api_client.get(f"{EMPLEADOS_URL}?activo=true")
        assert all(e["activo"] for e in res.data)

    def test_filtrar_por_restaurante(self, db, api_client):
        r1 = RestauranteLocalFactory()
        r2 = RestauranteLocalFactory()
        EmpleadoFactory(restaurante=r1)
        EmpleadoFactory(restaurante=r2)
        res = api_client.get(
            f"{EMPLEADOS_URL}?restaurante_id={r1.restaurante_id}")
        assert len(res.data) == 1

    def test_list_usa_serializer_ligero(self, db, api_client, empleado):
        res = api_client.get(EMPLEADOS_URL)
        assert "created_at" not in res.data[0]
        assert "nombre" in res.data[0]

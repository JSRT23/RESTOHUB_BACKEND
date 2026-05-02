# tests/integration/test_transacciones.py
# GET /api/loyalty/transacciones/ (requiere cliente_id o pedido_id)

import uuid
import pytest

from tests.conftest import CuentaPuntosFactory, TransaccionPuntosFactory

TRANSACCIONES_URL = "/api/loyalty/transacciones/"


class TestTransaccionPuntosViewSet:

    def test_listar_sin_filtro_falla(self, db, api_client):
        res = api_client.get(TRANSACCIONES_URL)
        assert res.status_code == 400
        assert "detail" in res.data

    def test_listar_por_cliente_id(self, db, api_client):
        cuenta = CuentaPuntosFactory()
        TransaccionPuntosFactory(cuenta=cuenta)
        TransaccionPuntosFactory(cuenta=cuenta)
        res = api_client.get(
            f"{TRANSACCIONES_URL}?cliente_id={cuenta.cliente_id}")
        assert res.status_code == 200
        assert len(res.data) == 2

    def test_listar_por_pedido_id(self, db, api_client):
        pid = uuid.uuid4()
        cuenta = CuentaPuntosFactory()
        TransaccionPuntosFactory(cuenta=cuenta, pedido_id=pid)
        TransaccionPuntosFactory(cuenta=cuenta, pedido_id=uuid.uuid4())
        res = api_client.get(f"{TRANSACCIONES_URL}?pedido_id={pid}")
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_filtrar_por_tipo(self, db, api_client):
        cuenta = CuentaPuntosFactory()
        TransaccionPuntosFactory(cuenta=cuenta, tipo="acumulacion")
        TransaccionPuntosFactory(cuenta=cuenta, tipo="canje", puntos=-50,
                                 saldo_anterior=100, saldo_posterior=50)
        res = api_client.get(
            f"{TRANSACCIONES_URL}?cliente_id={cuenta.cliente_id}&tipo=acumulacion")
        assert all(t["tipo"] == "acumulacion" for t in res.data)

    def test_transaccion_incluye_cliente_id(self, db, api_client):
        cuenta = CuentaPuntosFactory()
        TransaccionPuntosFactory(cuenta=cuenta)
        res = api_client.get(
            f"{TRANSACCIONES_URL}?cliente_id={cuenta.cliente_id}")
        assert "cliente_id" in res.data[0]

    def test_no_permite_post(self, db, api_client):
        res = api_client.post(TRANSACCIONES_URL, {})
        assert res.status_code == 405

    def test_cliente_sin_transacciones_devuelve_lista_vacia(self, db, api_client):
        cid = uuid.uuid4()
        res = api_client.get(f"{TRANSACCIONES_URL}?cliente_id={cid}")
        assert res.status_code == 200
        assert res.data == []


class TestCatalogos:

    def test_listar_platos(self, db, api_client):
        from tests.conftest import CatalogoPlatoFactory
        CatalogoPlatoFactory.create_batch(3)
        res = api_client.get("/api/loyalty/catalogo/platos/")
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_filtrar_platos_activos(self, db, api_client):
        from tests.conftest import CatalogoPlatoFactory
        CatalogoPlatoFactory(activo=True)
        CatalogoPlatoFactory(activo=False)
        res = api_client.get("/api/loyalty/catalogo/platos/?activo=true")
        assert all(p["activo"] for p in res.data)

    def test_listar_categorias(self, db, api_client):
        from tests.conftest import CatalogoCategoriaFactory
        CatalogoCategoriaFactory.create_batch(2)
        res = api_client.get("/api/loyalty/catalogo/categorias/")
        assert res.status_code == 200
        assert len(res.data) == 2

    def test_no_permite_post_platos(self, db, api_client):
        res = api_client.post("/api/loyalty/catalogo/platos/", {})
        assert res.status_code == 405

    def test_no_permite_post_categorias(self, db, api_client):
        res = api_client.post("/api/loyalty/catalogo/categorias/", {})
        assert res.status_code == 405

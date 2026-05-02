# tests/integration/test_cupones.py
# GET  /api/loyalty/cupones/
# POST /api/loyalty/cupones/
# GET  /api/loyalty/cupones/{id}/
# GET  /api/loyalty/cupones/validar/?codigo=...
# POST /api/loyalty/cupones/{id}/canjear/

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from app.loyalty.models import Cupon
from tests.conftest import CuponFactory, PromocionFactory

CUPONES_URL = "/api/loyalty/cupones/"


def _payload(**kwargs):
    base = {
        "tipo_descuento": "porcentaje",
        "valor_descuento": "10.00",
        "limite_uso": 1,
        "fecha_inicio": str(date.today()),
        "fecha_fin":    str(date.today() + timedelta(days=30)),
    }
    base.update(kwargs)
    return base


class TestCuponCRUD:

    def test_listar_cupones(self, db, api_client, cupon):
        res = api_client.get(CUPONES_URL)
        assert res.status_code == 200
        assert len(res.data) >= 1

    def test_crear_cupon_sin_codigo(self, db, api_client):
        res = api_client.post(CUPONES_URL, _payload(), format="json")
        assert res.status_code == 201
        assert res.data["codigo"]
        assert len(res.data["codigo"]) == 8

    def test_crear_cupon_con_codigo(self, db, api_client):
        res = api_client.post(CUPONES_URL, _payload(
            codigo="MANUAL01"), format="json")
        assert res.status_code == 201
        assert res.data["codigo"] == "MANUAL01"

    def test_crear_cupon_fecha_fin_pasada_falla(self, db, api_client):
        res = api_client.post(CUPONES_URL, _payload(
            fecha_fin=str(date.today() - timedelta(days=1)),
        ), format="json")
        assert res.status_code == 400

    def test_crear_con_promocion(self, db, api_client):
        promo = PromocionFactory()
        res = api_client.post(CUPONES_URL, _payload(
            promocion=str(promo.id),
        ), format="json")
        assert res.status_code == 201

    def test_detalle_cupon(self, db, api_client, cupon):
        res = api_client.get(f"{CUPONES_URL}{cupon.id}/")
        assert res.status_code == 200
        assert res.data["codigo"] == cupon.codigo

    def test_detalle_incluye_disponible(self, db, api_client, cupon):
        res = api_client.get(f"{CUPONES_URL}{cupon.id}/")
        assert "disponible" in res.data

    def test_cupon_inexistente_404(self, db, api_client):
        res = api_client.get(f"{CUPONES_URL}{uuid.uuid4()}/")
        assert res.status_code == 404

    def test_filtrar_por_activo(self, db, api_client, cupon, cupon_agotado):
        res = api_client.get(f"{CUPONES_URL}?activo=true")
        ids = [str(c["id"]) for c in res.data]
        assert str(cupon.id) in ids
        assert str(cupon_agotado.id) not in ids

    def test_filtrar_por_cliente(self, db, api_client):
        cid = uuid.uuid4()
        c1 = CuponFactory(cliente_id=cid)
        c2 = CuponFactory()
        res = api_client.get(f"{CUPONES_URL}?cliente_id={cid}")
        ids = [str(c["id"]) for c in res.data]
        assert str(c1.id) in ids
        assert str(c2.id) not in ids

    def test_no_permite_delete(self, db, api_client, cupon):
        res = api_client.delete(f"{CUPONES_URL}{cupon.id}/")
        assert res.status_code == 405

    def test_no_permite_patch(self, db, api_client, cupon):
        res = api_client.patch(f"{CUPONES_URL}{cupon.id}/", {})
        assert res.status_code == 405


class TestValidarCupon:

    def test_validar_cupon_disponible(self, db, api_client, cupon):
        res = api_client.get(f"{CUPONES_URL}validar/?codigo={cupon.codigo}")
        assert res.status_code == 200
        assert res.data["disponible"] is True

    def test_validar_cupon_agotado(self, db, api_client, cupon_agotado):
        res = api_client.get(
            f"{CUPONES_URL}validar/?codigo={cupon_agotado.codigo}")
        assert res.status_code == 200
        assert res.data["cupon"]["disponible"] is False
        assert "detail" in res.data

    def test_validar_cupon_expirado(self, db, api_client, cupon_expirado):
        res = api_client.get(
            f"{CUPONES_URL}validar/?codigo={cupon_expirado.codigo}")
        assert res.status_code == 200
        assert res.data["cupon"]["disponible"] is False

    def test_validar_cupon_inexistente_404(self, db, api_client):
        res = api_client.get(f"{CUPONES_URL}validar/?codigo=NOEXISTE")
        assert res.status_code == 404

    def test_validar_sin_codigo_400(self, db, api_client):
        res = api_client.get(f"{CUPONES_URL}validar/")
        assert res.status_code == 400

    def test_validar_case_insensitive(self, db, api_client):
        c = CuponFactory(codigo="ABCD1234")
        res = api_client.get(f"{CUPONES_URL}validar/?codigo=abcd1234")
        assert res.status_code == 200
        assert res.data["codigo"] == "ABCD1234"


class TestCanjearCupon:

    def test_canjear_cupon_disponible(self, db, api_client, cupon):
        res = api_client.post(f"{CUPONES_URL}{cupon.id}/canjear/", {})
        assert res.status_code == 200
        cupon.refresh_from_db()
        assert cupon.usos_actuales == 1

    def test_canjear_desactiva_al_agotar(self, db, api_client, cupon):
        assert cupon.limite_uso == 1
        api_client.post(f"{CUPONES_URL}{cupon.id}/canjear/", {})
        cupon.refresh_from_db()
        assert cupon.activo is False

    def test_canjear_multi_uso(self, db, api_client):
        c = CuponFactory(limite_uso=3, usos_actuales=0)
        api_client.post(f"{CUPONES_URL}{c.id}/canjear/", {})
        c.refresh_from_db()
        assert c.usos_actuales == 1
        assert c.activo is True  # todavía tiene usos restantes

    def test_canjear_cupon_agotado_falla(self, db, api_client, cupon_agotado):
        res = api_client.post(f"{CUPONES_URL}{cupon_agotado.id}/canjear/", {})
        assert res.status_code == 400

    def test_canjear_cupon_expirado_falla(self, db, api_client, cupon_expirado):
        res = api_client.post(f"{CUPONES_URL}{cupon_expirado.id}/canjear/", {})
        assert res.status_code == 400

    def test_canjear_cupon_inactivo_falla(self, db, api_client):
        c = CuponFactory.inactivo()
        res = api_client.post(f"{CUPONES_URL}{c.id}/canjear/", {})
        assert res.status_code == 400

    def test_canjear_con_pedido_id(self, db, api_client, cupon):
        res = api_client.post(f"{CUPONES_URL}{cupon.id}/canjear/",
                              {"pedido_id": str(uuid.uuid4())}, format="json")
        assert res.status_code == 200

    def test_canjear_inexistente_404(self, db, api_client):
        res = api_client.post(f"{CUPONES_URL}{uuid.uuid4()}/canjear/", {})
        assert res.status_code == 404

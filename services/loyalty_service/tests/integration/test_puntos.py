# tests/integration/test_puntos.py
# GET  /api/loyalty/puntos/{cliente_id}/
# POST /api/loyalty/puntos/acumular/
# POST /api/loyalty/puntos/canjear/

import uuid
import pytest
from django.core.cache import cache

from app.loyalty.models import CuentaPuntos, TransaccionPuntos, NivelCliente
from tests.conftest import CuentaPuntosFactory, TransaccionPuntosFactory

PUNTOS_URL = "/api/loyalty/puntos/"


class TestPuntosRetrieve:

    def test_cuenta_existente(self, db, api_client, cuenta):
        res = api_client.get(f"{PUNTOS_URL}{cuenta.cliente_id}/")
        assert res.status_code == 200
        assert res.data["saldo"] == cuenta.saldo
        assert str(res.data["cliente_id"]) == str(cuenta.cliente_id)

    def test_cliente_sin_cuenta_404(self, db, api_client):
        res = api_client.get(f"{PUNTOS_URL}{uuid.uuid4()}/")
        assert res.status_code == 404

    def test_respuesta_incluye_nivel(self, db, api_client, cuenta):
        res = api_client.get(f"{PUNTOS_URL}{cuenta.cliente_id}/")
        assert "nivel" in res.data
        assert "nivel_display" in res.data

    def test_cache_hit_devuelve_saldo(self, db, api_client, cuenta):
        # Primera llamada — cache miss → DB
        res1 = api_client.get(f"{PUNTOS_URL}{cuenta.cliente_id}/")
        assert res1.data["_cache"] is False
        # Segunda llamada — cache hit
        res2 = api_client.get(f"{PUNTOS_URL}{cuenta.cliente_id}/")
        assert res2.data["_cache"] is True
        assert res2.data["saldo"] == cuenta.saldo

    def test_cache_invalida_despues_de_acumular(self, db, api_client, cuenta):
        # Poblar caché
        api_client.get(f"{PUNTOS_URL}{cuenta.cliente_id}/")
        # Acumular (invalida caché)
        api_client.post(f"{PUNTOS_URL}acumular/", {
            "cliente_id": str(cuenta.cliente_id),
            "puntos": 100,
        }, format="json")
        # Debe ir a DB de nuevo
        res = api_client.get(f"{PUNTOS_URL}{cuenta.cliente_id}/")
        assert res.data["_cache"] is False
        assert res.data["saldo"] == cuenta.saldo + 100


class TestAcumularPuntos:

    def test_acumular_cuenta_existente(self, db, api_client, cuenta):
        saldo_antes = cuenta.saldo
        res = api_client.post(f"{PUNTOS_URL}acumular/", {
            "cliente_id": str(cuenta.cliente_id),
            "puntos": 200,
        }, format="json")
        assert res.status_code == 201
        assert res.data["saldo"] == saldo_antes + 200

    def test_acumular_crea_cuenta_si_no_existe(self, db, api_client):
        cid = uuid.uuid4()
        res = api_client.post(f"{PUNTOS_URL}acumular/", {
            "cliente_id": str(cid),
            "puntos": 300,
        }, format="json")
        assert res.status_code == 201
        assert CuentaPuntos.objects.filter(cliente_id=cid).exists()

    def test_acumular_crea_transaccion(self, db, api_client, cuenta):
        api_client.post(f"{PUNTOS_URL}acumular/", {
            "cliente_id": str(cuenta.cliente_id),
            "puntos": 150,
        }, format="json")
        assert TransaccionPuntos.objects.filter(
            cuenta=cuenta, tipo="acumulacion", puntos=150
        ).exists()

    def test_acumular_actualiza_historicos(self, db, api_client, cuenta):
        historicos_antes = cuenta.puntos_totales_historicos
        api_client.post(f"{PUNTOS_URL}acumular/", {
            "cliente_id": str(cuenta.cliente_id),
            "puntos": 100,
        }, format="json")
        cuenta.refresh_from_db()
        assert cuenta.puntos_totales_historicos == historicos_antes + 100

    def test_acumular_sube_nivel_a_plata(self, db, api_client):
        cuenta = CuentaPuntosFactory(saldo=900, puntos_totales_historicos=900)
        res = api_client.post(f"{PUNTOS_URL}acumular/", {
            "cliente_id": str(cuenta.cliente_id),
            "puntos": 200,
        }, format="json")
        assert res.status_code == 201
        assert res.data["nivel"] == NivelCliente.PLATA

    def test_acumular_puntos_cero_falla(self, db, api_client):
        res = api_client.post(f"{PUNTOS_URL}acumular/", {
            "cliente_id": str(uuid.uuid4()),
            "puntos": 0,
        }, format="json")
        assert res.status_code == 400

    def test_acumular_registra_saldo_anterior_y_posterior(self, db, api_client, cuenta):
        saldo_antes = cuenta.saldo
        api_client.post(f"{PUNTOS_URL}acumular/", {
            "cliente_id": str(cuenta.cliente_id),
            "puntos": 75,
        }, format="json")
        tx = TransaccionPuntos.objects.filter(
            cuenta=cuenta).latest("created_at")
        assert tx.saldo_anterior == saldo_antes
        assert tx.saldo_posterior == saldo_antes + 75


class TestCanjearPuntos:

    def test_canjear_saldo_suficiente(self, db, api_client, cuenta_con_saldo):
        saldo_antes = cuenta_con_saldo.saldo
        res = api_client.post(f"{PUNTOS_URL}canjear/", {
            "cliente_id": str(cuenta_con_saldo.cliente_id),
            "puntos": 200,
        }, format="json")
        assert res.status_code == 200
        assert res.data["saldo"] == saldo_antes - 200

    def test_canjear_crea_transaccion_negativa(self, db, api_client, cuenta_con_saldo):
        api_client.post(f"{PUNTOS_URL}canjear/", {
            "cliente_id": str(cuenta_con_saldo.cliente_id),
            "puntos": 100,
        }, format="json")
        tx = TransaccionPuntos.objects.filter(
            cuenta=cuenta_con_saldo, tipo="canje"
        ).first()
        assert tx is not None
        assert tx.puntos == -100

    def test_canjear_saldo_insuficiente_falla(self, db, api_client, cuenta):
        res = api_client.post(f"{PUNTOS_URL}canjear/", {
            "cliente_id": str(cuenta.cliente_id),
            "puntos": cuenta.saldo + 1,
        }, format="json")
        assert res.status_code == 400

    def test_canjear_sin_cuenta_falla(self, db, api_client):
        res = api_client.post(f"{PUNTOS_URL}canjear/", {
            "cliente_id": str(uuid.uuid4()),
            "puntos": 100,
        }, format="json")
        assert res.status_code == 400

    def test_canjear_invalida_cache(self, db, api_client, cuenta_con_saldo):
        # Poblar caché
        api_client.get(f"{PUNTOS_URL}{cuenta_con_saldo.cliente_id}/")
        # Canjear
        api_client.post(f"{PUNTOS_URL}canjear/", {
            "cliente_id": str(cuenta_con_saldo.cliente_id),
            "puntos": 100,
        }, format="json")
        # Debe ir a DB
        res = api_client.get(f"{PUNTOS_URL}{cuenta_con_saldo.cliente_id}/")
        assert res.data["_cache"] is False
        assert res.data["saldo"] == cuenta_con_saldo.saldo - 100

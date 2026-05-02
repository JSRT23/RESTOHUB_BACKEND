# tests/integration/test_comandas.py
# GET  /api/orders/comandas/
# POST /api/orders/comandas/
# POST /api/orders/comandas/<pk>/iniciar/
# POST /api/orders/comandas/<pk>/lista/

import uuid
import pytest

from app.orders.models import EstadoComanda, EstacionCocina
from tests.conftest import ComandaCocinaFactory, PedidoFactory

COMANDAS_URL = "/api/orders/comandas/"


def url(pk, action=""):
    base = f"{COMANDAS_URL}{pk}/"
    return f"{base}{action}/" if action else base


# ═══════════════════════════════════════════════════════════════════════════════
# LIST  GET /api/orders/comandas/
# ═══════════════════════════════════════════════════════════════════════════════

class TestComandaList:

    def test_listar_comandas(self, db, api_client):
        p = PedidoFactory.en_preparacion()
        ComandaCocinaFactory.create_batch(3, pedido=p)
        res = api_client.get(COMANDAS_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_lista_incluye_campos_esperados(self, db, api_client, comanda):
        res = api_client.get(COMANDAS_URL)
        assert res.status_code == 200
        item = res.data[0]
        assert "id" in item
        assert "estacion" in item
        assert "estado" in item
        assert "hora_envio" in item

    def test_filtrar_por_estado(self, db, api_client):
        p = PedidoFactory.en_preparacion()
        ComandaCocinaFactory(pedido=p, estado=EstadoComanda.PENDIENTE)
        ComandaCocinaFactory.preparando(pedido=p)
        res = api_client.get(f"{COMANDAS_URL}?estado=PENDIENTE")
        assert res.status_code == 200
        assert all(c["estado"] == "PENDIENTE" for c in res.data)

    def test_filtrar_por_estacion(self, db, api_client):
        p = PedidoFactory.en_preparacion()
        ComandaCocinaFactory(pedido=p, estacion=EstacionCocina.PARRILLA)
        ComandaCocinaFactory(pedido=p, estacion=EstacionCocina.BEBIDAS)
        res = api_client.get(f"{COMANDAS_URL}?estacion=PARRILLA")
        assert all(c["estacion"] == "PARRILLA" for c in res.data)

    def test_filtrar_por_pedido(self, db, api_client):
        p1 = PedidoFactory.en_preparacion()
        p2 = PedidoFactory.en_preparacion()
        ComandaCocinaFactory(pedido=p1)
        ComandaCocinaFactory(pedido=p2)
        res = api_client.get(f"{COMANDAS_URL}?pedido_id={p1.id}")
        assert len(res.data) == 1
        assert str(res.data[0]["pedido"]) == str(p1.id)

    def test_lista_incluye_numero_dia(self, db, api_client):
        p = PedidoFactory.en_preparacion(numero_dia=5)
        ComandaCocinaFactory(pedido=p)
        res = api_client.get(COMANDAS_URL)
        assert res.data[0]["numero_dia"] == 5


# ═══════════════════════════════════════════════════════════════════════════════
# CREATE  POST /api/orders/comandas/
# ═══════════════════════════════════════════════════════════════════════════════

class TestComandaCreate:

    def test_crear_comanda_para_pedido_recibido(self, db, api_client, pedido):
        res = api_client.post(COMANDAS_URL, {
            "pedido":   str(pedido.id),
            "estacion": "GENERAL",
        }, format="json")
        assert res.status_code == 201
        # ComandaCocinaWriteSerializer solo devuelve campos de entrada (pedido, estacion).
        # Verificamos estado en DB.
        from app.orders.models import ComandaCocina, EstadoComanda
        comanda = ComandaCocina.objects.filter(pedido=pedido).first()
        assert comanda is not None
        assert comanda.estado == EstadoComanda.PENDIENTE

    def test_crear_comanda_para_pedido_en_preparacion(self, db, api_client, pedido_en_preparacion):
        res = api_client.post(COMANDAS_URL, {
            "pedido":   str(pedido_en_preparacion.id),
            "estacion": "PARRILLA",
        }, format="json")
        assert res.status_code == 201

    def test_crear_comanda_pedido_cancelado_falla(self, db, api_client, pedido_cancelado):
        res = api_client.post(COMANDAS_URL, {
            "pedido":   str(pedido_cancelado.id),
            "estacion": "GENERAL",
        }, format="json")
        assert res.status_code == 400

    def test_crear_comanda_pedido_entregado_falla(self, db, api_client, pedido_entregado):
        res = api_client.post(COMANDAS_URL, {
            "pedido":   str(pedido_entregado.id),
            "estacion": "BEBIDAS",
        }, format="json")
        assert res.status_code == 400

    def test_crear_comanda_pedido_inexistente_falla(self, db, api_client):
        res = api_client.post(COMANDAS_URL, {
            "pedido":   str(uuid.uuid4()),
            "estacion": "GENERAL",
        }, format="json")
        assert res.status_code == 400

    @pytest.mark.parametrize("estacion", [
        "PARRILLA", "BEBIDAS", "POSTRES", "FRIOS", "GENERAL"
    ])
    def test_crear_comanda_todas_estaciones(self, db, api_client, pedido, estacion):
        res = api_client.post(COMANDAS_URL, {
            "pedido":   str(pedido.id),
            "estacion": estacion,
        }, format="json")
        assert res.status_code == 201
        assert res.data["estacion"] == estacion


# ═══════════════════════════════════════════════════════════════════════════════
# INICIAR  POST /api/orders/comandas/<pk>/iniciar/
# ═══════════════════════════════════════════════════════════════════════════════

class TestComandaIniciar:

    def test_iniciar_comanda_pendiente(self, db, api_client, comanda):
        res = api_client.post(url(comanda.id, "iniciar"))
        assert res.status_code == 200
        assert res.data["estado"] == "PREPARANDO"

    def test_iniciar_comanda_ya_preparando_falla(self, db, api_client, comanda_preparando):
        res = api_client.post(url(comanda_preparando.id, "iniciar"))
        assert res.status_code == 400
        assert "detail" in res.data

    def test_iniciar_comanda_ya_lista_falla(self, db, api_client):
        p = PedidoFactory.en_preparacion()
        c = ComandaCocinaFactory.lista(pedido=p)
        res = api_client.post(url(c.id, "iniciar"))
        assert res.status_code == 400

    def test_iniciar_comanda_inexistente_404(self, db, api_client):
        res = api_client.post(url(uuid.uuid4(), "iniciar"))
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# LISTA  POST /api/orders/comandas/<pk>/lista/
# ═══════════════════════════════════════════════════════════════════════════════

class TestComandaLista:

    def test_marcar_lista_desde_preparando(self, db, api_client, comanda_preparando):
        res = api_client.post(url(comanda_preparando.id, "lista"))
        assert res.status_code == 200
        assert res.data["estado"] == "LISTO"

    def test_marcar_lista_registra_hora_fin(self, db, api_client, comanda_preparando):
        res = api_client.post(url(comanda_preparando.id, "lista"))
        assert res.data["hora_fin"] is not None

    def test_marcar_lista_registra_tiempo_preparacion(self, db, api_client, comanda_preparando):
        res = api_client.post(url(comanda_preparando.id, "lista"))
        assert res.data["tiempo_preparacion_segundos"] is not None
        assert res.data["tiempo_preparacion_segundos"] >= 0

    def test_marcar_lista_desde_pendiente_falla(self, db, api_client, comanda):
        res = api_client.post(url(comanda.id, "lista"))
        assert res.status_code == 400
        assert "detail" in res.data

    def test_marcar_lista_inexistente_404(self, db, api_client):
        res = api_client.post(url(uuid.uuid4(), "lista"))
        assert res.status_code == 404

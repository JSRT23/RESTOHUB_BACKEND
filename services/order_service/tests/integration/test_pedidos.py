# tests/integration/test_pedidos.py
# GET    /api/orders/pedidos/
# POST   /api/orders/pedidos/
# GET    /api/orders/pedidos/<pk>/
# PATCH  /api/orders/pedidos/<pk>/
# POST   /api/orders/pedidos/<pk>/confirmar/
# POST   /api/orders/pedidos/<pk>/cancelar/
# POST   /api/orders/pedidos/<pk>/marcar_listo/
# POST   /api/orders/pedidos/<pk>/entregar/
# GET    /api/orders/pedidos/<pk>/seguimiento/
# GET    /api/orders/pedidos/<pk>/detalles/

import uuid
import pytest
from decimal import Decimal

from app.orders.models import EstadoPedido, MetodoPago, Pedido, SeguimientoPedido
from tests.conftest import DetallePedidoFactory, PedidoFactory

PEDIDOS_URL = "/api/orders/pedidos/"


def url(pk, action=""):
    base = f"{PEDIDOS_URL}{pk}/"
    return f"{base}{action}/" if action else base


# ═══════════════════════════════════════════════════════════════════════════════
# LIST  GET /api/orders/pedidos/
# ═══════════════════════════════════════════════════════════════════════════════

class TestPedidoList:

    def test_listar_pedidos(self, db, api_client):
        PedidoFactory.create_batch(3)
        res = api_client.get(PEDIDOS_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_lista_usa_serializer_ligero(self, db, api_client):
        PedidoFactory()
        res = api_client.get(PEDIDOS_URL)
        assert "detalles" not in res.data[0]
        assert "estado" in res.data[0]

    def test_filtrar_por_estado(self, db, api_client):
        PedidoFactory(estado=EstadoPedido.RECIBIDO)
        PedidoFactory(estado=EstadoPedido.ENTREGADO)
        res = api_client.get(f"{PEDIDOS_URL}?estado=RECIBIDO")
        assert res.status_code == 200
        assert all(p["estado"] == "RECIBIDO" for p in res.data)

    def test_filtrar_por_restaurante(self, db, api_client):
        rid = uuid.uuid4()
        PedidoFactory(restaurante_id=rid)
        PedidoFactory(restaurante_id=uuid.uuid4())
        res = api_client.get(f"{PEDIDOS_URL}?restaurante_id={rid}")
        assert len(res.data) == 1
        assert str(res.data[0]["restaurante_id"]) == str(rid)

    def test_filtrar_por_canal(self, db, api_client):
        PedidoFactory(canal="TPV")
        PedidoFactory(canal="APP")
        res = api_client.get(f"{PEDIDOS_URL}?canal=TPV")
        assert all(p["canal"] == "TPV" for p in res.data)

    def test_filtrar_por_cliente(self, db, api_client):
        cid = uuid.uuid4()
        PedidoFactory(cliente_id=cid)
        PedidoFactory(cliente_id=uuid.uuid4())
        res = api_client.get(f"{PEDIDOS_URL}?cliente_id={cid}")
        assert len(res.data) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# CREATE  POST /api/orders/pedidos/
# ═══════════════════════════════════════════════════════════════════════════════

class TestPedidoCreate:

    def _payload(self, **kwargs):
        base = {
            "restaurante_id": str(uuid.uuid4()),
            "canal":          "TPV",
            "moneda":         "COP",
            "detalles": [{
                "plato_id":        str(uuid.uuid4()),
                "nombre_plato":    "Hamburguesa",
                "precio_unitario": "18000",
                "cantidad":        1,
            }],
        }
        base.update(kwargs)
        return base

    def test_crear_pedido_exitoso(self, db, api_client):
        res = api_client.post(PEDIDOS_URL, self._payload(), format="json")
        assert res.status_code == 201
        assert res.data["estado"] == "RECIBIDO"

    def test_crear_retorna_pedido_completo(self, db, api_client):
        res = api_client.post(PEDIDOS_URL, self._payload(), format="json")
        assert "detalles" in res.data
        assert "seguimientos" in res.data
        assert len(res.data["detalles"]) == 1

    def test_crear_calcula_total(self, db, api_client):
        payload = self._payload(detalles=[
            {"plato_id": str(uuid.uuid4()), "nombre_plato": "A",
             "precio_unitario": "10000", "cantidad": 2},
            {"plato_id": str(uuid.uuid4()), "nombre_plato": "B",
             "precio_unitario": "5000",  "cantidad": 1},
        ])
        res = api_client.post(PEDIDOS_URL, payload, format="json")
        assert res.status_code == 201
        assert float(res.data["total"]) == 25000.0

    def test_crear_asigna_numero_dia(self, db, api_client):
        res = api_client.post(PEDIDOS_URL, self._payload(), format="json")
        assert res.data["numero_dia"] is not None
        assert res.data["numero_dia"] >= 1

    def test_crear_numero_dia_incremental(self, db, api_client):
        rid = str(uuid.uuid4())
        r1 = api_client.post(PEDIDOS_URL, self._payload(
            restaurante_id=rid), format="json")
        r2 = api_client.post(PEDIDOS_URL, self._payload(
            restaurante_id=rid), format="json")
        assert r2.data["numero_dia"] == r1.data["numero_dia"] + 1

    def test_crear_sin_detalles_falla(self, db, api_client):
        res = api_client.post(
            PEDIDOS_URL, self._payload(detalles=[]), format="json")
        assert res.status_code == 400

    def test_crear_genera_seguimiento_recibido(self, db, api_client):
        res = api_client.post(PEDIDOS_URL, self._payload(), format="json")
        pedido_id = res.data["id"]
        assert SeguimientoPedido.objects.filter(
            pedido_id=pedido_id, estado="RECIBIDO"
        ).exists()

    def test_crear_con_cliente_id(self, db, api_client):
        cid = str(uuid.uuid4())
        res = api_client.post(PEDIDOS_URL, self._payload(
            cliente_id=cid), format="json")
        assert res.status_code == 201
        assert str(res.data["cliente_id"]) == cid


# ═══════════════════════════════════════════════════════════════════════════════
# DETAIL  GET /api/orders/pedidos/<pk>/
# ═══════════════════════════════════════════════════════════════════════════════

class TestPedidoDetail:

    def test_obtener_pedido(self, db, api_client, pedido):
        res = api_client.get(url(pedido.id))
        assert res.status_code == 200
        assert str(res.data["id"]) == str(pedido.id)

    def test_pedido_incluye_detalles(self, db, api_client, pedido_con_detalle):
        res = api_client.get(url(pedido_con_detalle.id))
        assert "detalles" in res.data
        assert len(res.data["detalles"]) == 1

    def test_pedido_incluye_seguimientos(self, db, api_client, pedido):
        SeguimientoPedido.objects.create(pedido=pedido, estado="RECIBIDO")
        res = api_client.get(url(pedido.id))
        assert len(res.data["seguimientos"]) >= 1

    def test_pedido_inexistente_404(self, db, api_client):
        res = api_client.get(url(uuid.uuid4()))
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSICIONES DE ESTADO
# ═══════════════════════════════════════════════════════════════════════════════

class TestPedidoConfirmar:

    def test_confirmar_pedido_recibido(self, db, api_client, pedido):
        res = api_client.post(url(pedido.id, "confirmar"))
        assert res.status_code == 200
        assert res.data["estado"] == "EN_PREPARACION"

    def test_confirmar_crea_seguimiento(self, db, api_client, pedido):
        api_client.post(url(pedido.id, "confirmar"))
        assert SeguimientoPedido.objects.filter(
            pedido=pedido, estado="EN_PREPARACION"
        ).exists()

    def test_confirmar_no_recibido_falla(self, db, api_client, pedido_en_preparacion):
        res = api_client.post(url(pedido_en_preparacion.id, "confirmar"))
        assert res.status_code == 400

    def test_confirmar_con_descripcion(self, db, api_client, pedido):
        res = api_client.post(url(pedido.id, "confirmar"),
                              {"descripcion": "Iniciando preparación"})
        assert res.status_code == 200


class TestPedidoCancelar:

    def test_cancelar_pedido_recibido(self, db, api_client, pedido):
        res = api_client.post(url(pedido.id, "cancelar"))
        assert res.status_code == 200
        assert res.data["estado"] == "CANCELADO"

    def test_cancelar_pedido_en_preparacion(self, db, api_client, pedido_en_preparacion):
        res = api_client.post(url(pedido_en_preparacion.id, "cancelar"))
        assert res.status_code == 200
        assert res.data["estado"] == "CANCELADO"

    def test_cancelar_entregado_falla(self, db, api_client, pedido_entregado):
        res = api_client.post(url(pedido_entregado.id, "cancelar"))
        assert res.status_code == 400

    def test_cancelar_ya_cancelado_falla(self, db, api_client, pedido_cancelado):
        res = api_client.post(url(pedido_cancelado.id, "cancelar"))
        assert res.status_code == 400


class TestPedidoMarcarListo:

    def test_marcar_listo_desde_preparacion(self, db, api_client, pedido_en_preparacion):
        res = api_client.post(url(pedido_en_preparacion.id, "marcar_listo"))
        assert res.status_code == 200
        assert res.data["estado"] == "LISTO"

    def test_marcar_listo_desde_recibido_falla(self, db, api_client, pedido):
        res = api_client.post(url(pedido.id, "marcar_listo"))
        assert res.status_code == 400

    def test_marcar_listo_crea_seguimiento(self, db, api_client, pedido_en_preparacion):
        api_client.post(url(pedido_en_preparacion.id, "marcar_listo"))
        assert SeguimientoPedido.objects.filter(
            pedido=pedido_en_preparacion, estado="LISTO"
        ).exists()


class TestPedidoEntregar:

    def test_entregar_desde_listo(self, db, api_client, pedido_listo):
        res = api_client.post(url(pedido_listo.id, "entregar"))
        assert res.status_code == 200
        assert res.data["estado"] == "ENTREGADO"

    def test_entregar_desde_en_camino(self, db, api_client):
        p = PedidoFactory.en_camino()
        res = api_client.post(url(p.id, "entregar"))
        assert res.status_code == 200

    def test_entregar_registra_metodo_pago(self, db, api_client, pedido_listo):
        res = api_client.post(url(pedido_listo.id, "entregar"),
                              {"metodo_pago": "efectivo"})
        assert res.status_code == 200
        pedido_listo.refresh_from_db()
        assert pedido_listo.metodo_pago == MetodoPago.EFECTIVO

    def test_entregar_desde_recibido_falla(self, db, api_client, pedido):
        res = api_client.post(url(pedido.id, "entregar"))
        assert res.status_code == 400

    def test_entregar_crea_seguimiento(self, db, api_client, pedido_listo):
        api_client.post(url(pedido_listo.id, "entregar"))
        assert SeguimientoPedido.objects.filter(
            pedido=pedido_listo, estado="ENTREGADO"
        ).exists()


# ═══════════════════════════════════════════════════════════════════════════════
# SEGUIMIENTO  GET /api/orders/pedidos/<pk>/seguimiento/
# ═══════════════════════════════════════════════════════════════════════════════

class TestPedidoSeguimiento:

    def test_listar_seguimientos(self, db, api_client, pedido):
        SeguimientoPedido.objects.create(pedido=pedido, estado="RECIBIDO")
        SeguimientoPedido.objects.create(
            pedido=pedido, estado="EN_PREPARACION")
        res = api_client.get(url(pedido.id, "seguimiento"))
        assert res.status_code == 200
        assert len(res.data) == 2

    def test_seguimientos_ordenados_por_fecha(self, db, api_client, pedido):
        SeguimientoPedido.objects.create(pedido=pedido, estado="RECIBIDO")
        SeguimientoPedido.objects.create(
            pedido=pedido, estado="EN_PREPARACION")
        res = api_client.get(url(pedido.id, "seguimiento"))
        estados = [s["estado"] for s in res.data]
        assert estados[0] == "RECIBIDO"
        assert estados[1] == "EN_PREPARACION"


# ═══════════════════════════════════════════════════════════════════════════════
# DETALLES  GET/POST /api/orders/pedidos/<pk>/detalles/
# ═══════════════════════════════════════════════════════════════════════════════

class TestPedidoDetalles:

    def test_listar_detalles(self, db, api_client, pedido_con_detalle):
        res = api_client.get(url(pedido_con_detalle.id, "detalles"))
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_agregar_detalle_a_recibido(self, db, api_client, pedido):
        res = api_client.post(url(pedido.id, "detalles"), {
            "plato_id":        str(uuid.uuid4()),
            "nombre_plato":    "Bebida",
            "precio_unitario": "3000",
            "cantidad":        2,
        }, format="json")
        assert res.status_code == 201

    def test_agregar_detalle_actualiza_total(self, db, api_client):
        # Creamos el pedido vía API para que el total real esté en DB
        create_res = api_client.post(PEDIDOS_URL, {
            "restaurante_id": str(uuid.uuid4()),
            "canal": "TPV",
            "moneda": "COP",
            "detalles": [{
                "plato_id": str(uuid.uuid4()),
                "nombre_plato": "Base",
                "precio_unitario": "10000",
                "cantidad": 1,
            }],
        }, format="json")
        assert create_res.status_code == 201
        pedido_id = create_res.data["id"]
        total_inicial = Decimal(str(create_res.data["total"]))

        detalle_res = api_client.post(url(pedido_id, "detalles"), {
            "plato_id":        str(uuid.uuid4()),
            "nombre_plato":    "Extra",
            "precio_unitario": "5000",
            "cantidad":        2,
        }, format="json")
        assert detalle_res.status_code == 201

        from app.orders.models import Pedido
        pedido = Pedido.objects.get(id=pedido_id)
        assert pedido.total == Decimal("20000")

    def test_agregar_detalle_a_en_preparacion_falla(self, db, api_client, pedido_en_preparacion):
        res = api_client.post(url(pedido_en_preparacion.id, "detalles"), {
            "plato_id":        str(uuid.uuid4()),
            "nombre_plato":    "Extra",
            "precio_unitario": "5000",
            "cantidad":        1,
        }, format="json")
        assert res.status_code == 400

# tests/integration/test_entregas.py
import uuid
import pytest

from app.orders.models import EstadoEntrega, EstadoPedido
from tests.conftest import PedidoFactory, EntregaPedidoFactory

ENTREGAS_URL = "/api/orders/entregas/"


class TestEntregaPedidoViewSet:

    def test_listar_entregas(self, db, api_client, entrega):
        res = api_client.get(ENTREGAS_URL)
        assert res.status_code == 200
        assert len(res.data) >= 1

    def test_crear_entrega_local(self, db, api_client, pedido_listo):
        res = api_client.post(ENTREGAS_URL, {
            "pedido":       str(pedido_listo.id),
            "tipo_entrega": "LOCAL",
        }, format="json")
        assert res.status_code == 201
        # EntregaPedidoWriteSerializer no incluye estado_entrega (campo de salida).
        # Verificamos en DB.
        from app.orders.models import EntregaPedido, EstadoEntrega
        entrega = EntregaPedido.objects.filter(pedido=pedido_listo).first()
        assert entrega is not None
        assert entrega.estado_entrega == EstadoEntrega.PENDIENTE

    def test_crear_entrega_delivery_con_direccion(self, db, api_client, pedido_listo):
        res = api_client.post(ENTREGAS_URL, {
            "pedido":          str(pedido_listo.id),
            "tipo_entrega":    "DELIVERY",
            "direccion":       "Calle 10 # 5-20, Bogotá",
            "repartidor_id":   str(uuid.uuid4()),
            "repartidor_nombre": "Carlos Ruiz",
        }, format="json")
        assert res.status_code == 201

    def test_crear_entrega_delivery_sin_direccion_falla(self, db, api_client, pedido_listo):
        res = api_client.post(ENTREGAS_URL, {
            "pedido":       str(pedido_listo.id),
            "tipo_entrega": "DELIVERY",
        }, format="json")
        assert res.status_code == 400

    def test_crear_segunda_entrega_falla(self, db, api_client, pedido_listo):
        EntregaPedidoFactory(pedido=pedido_listo)
        res = api_client.post(ENTREGAS_URL, {
            "pedido":       str(pedido_listo.id),
            "tipo_entrega": "LOCAL",
        }, format="json")
        assert res.status_code == 400

    def test_detalle_entrega(self, db, api_client, entrega):
        res = api_client.get(f"{ENTREGAS_URL}{entrega.id}/")
        assert res.status_code == 200
        assert str(res.data["id"]) == str(entrega.id)

    def test_entrega_inexistente_404(self, db, api_client):
        res = api_client.get(f"{ENTREGAS_URL}{uuid.uuid4()}/")
        assert res.status_code == 404

    def test_filtrar_por_estado(self, db, api_client, pedido_listo):
        EntregaPedidoFactory(pedido=pedido_listo)
        otro = PedidoFactory.listo()
        e2 = EntregaPedidoFactory.en_camino(pedido=otro)
        res = api_client.get(f"{ENTREGAS_URL}?estado_entrega=PENDIENTE")
        assert all(e["estado_entrega"] ==
                   EstadoEntrega.PENDIENTE for e in res.data)

    def test_filtrar_por_tipo(self, db, api_client):
        p1 = PedidoFactory.listo()
        p2 = PedidoFactory.listo()
        EntregaPedidoFactory(pedido=p1, tipo_entrega="LOCAL")
        EntregaPedidoFactory(pedido=p2, tipo_entrega="PICKUP")
        res = api_client.get(f"{ENTREGAS_URL}?tipo_entrega=LOCAL")
        assert all(e["tipo_entrega"] == "LOCAL" for e in res.data)

    def test_no_permite_delete(self, db, api_client, entrega):
        res = api_client.delete(f"{ENTREGAS_URL}{entrega.id}/")
        assert res.status_code == 405

    def test_no_permite_patch(self, db, api_client, entrega):
        res = api_client.patch(f"{ENTREGAS_URL}{entrega.id}/", {})
        assert res.status_code == 405


class TestEntregaEnCamino:

    def test_en_camino_desde_pendiente(self, db, api_client, entrega):
        res = api_client.post(f"{ENTREGAS_URL}{entrega.id}/en_camino/")
        assert res.status_code == 200
        assert res.data["estado_entrega"] == EstadoEntrega.EN_CAMINO

    def test_en_camino_registra_fecha_salida(self, db, api_client, entrega):
        api_client.post(f"{ENTREGAS_URL}{entrega.id}/en_camino/")
        entrega.refresh_from_db()
        assert entrega.fecha_salida is not None

    def test_en_camino_actualiza_pedido_a_en_camino(self, db, api_client, entrega):
        # El pedido está en LISTO; al poner entrega en camino debe pasar a EN_CAMINO
        api_client.post(f"{ENTREGAS_URL}{entrega.id}/en_camino/")
        entrega.pedido.refresh_from_db()
        assert entrega.pedido.estado == EstadoPedido.EN_CAMINO

    def test_en_camino_ya_iniciada_falla(self, db, api_client, entrega_en_camino):
        res = api_client.post(
            f"{ENTREGAS_URL}{entrega_en_camino.id}/en_camino/")
        assert res.status_code == 400

    def test_en_camino_inexistente_404(self, db, api_client):
        res = api_client.post(f"{ENTREGAS_URL}{uuid.uuid4()}/en_camino/")
        assert res.status_code == 404


class TestEntregaCompletar:

    def test_completar_desde_en_camino(self, db, api_client, entrega_en_camino):
        res = api_client.post(
            f"{ENTREGAS_URL}{entrega_en_camino.id}/completar/")
        assert res.status_code == 200
        assert res.data["estado_entrega"] == EstadoEntrega.ENTREGADO

    def test_completar_registra_fecha_entrega_real(self, db, api_client, entrega_en_camino):
        api_client.post(f"{ENTREGAS_URL}{entrega_en_camino.id}/completar/")
        entrega_en_camino.refresh_from_db()
        assert entrega_en_camino.fecha_entrega_real is not None

    def test_completar_pone_pedido_en_entregado(self, db, api_client, entrega_en_camino):
        api_client.post(f"{ENTREGAS_URL}{entrega_en_camino.id}/completar/")
        entrega_en_camino.pedido.refresh_from_db()
        assert entrega_en_camino.pedido.estado == EstadoPedido.ENTREGADO

    def test_completar_desde_pendiente_falla(self, db, api_client, entrega):
        res = api_client.post(f"{ENTREGAS_URL}{entrega.id}/completar/")
        assert res.status_code == 400

    def test_completar_inexistente_404(self, db, api_client):
        res = api_client.post(f"{ENTREGAS_URL}{uuid.uuid4()}/completar/")
        assert res.status_code == 404


class TestEntregaFallo:

    def test_fallo_desde_en_camino(self, db, api_client, entrega_en_camino):
        res = api_client.post(f"{ENTREGAS_URL}{entrega_en_camino.id}/fallo/")
        assert res.status_code == 200
        assert res.data["estado_entrega"] == EstadoEntrega.FALLIDO

    def test_fallo_persiste_en_db(self, db, api_client, entrega_en_camino):
        api_client.post(f"{ENTREGAS_URL}{entrega_en_camino.id}/fallo/")
        entrega_en_camino.refresh_from_db()
        assert entrega_en_camino.estado_entrega == EstadoEntrega.FALLIDO

    def test_fallo_desde_pendiente_falla(self, db, api_client, entrega):
        res = api_client.post(f"{ENTREGAS_URL}{entrega.id}/fallo/")
        assert res.status_code == 400

    def test_fallo_desde_entregado_falla(self, db, api_client):
        p = PedidoFactory.entregado()
        e = EntregaPedidoFactory(
            pedido=p,
            estado_entrega=EstadoEntrega.ENTREGADO,
        )
        res = api_client.post(f"{ENTREGAS_URL}{e.id}/fallo/")
        assert res.status_code == 400

    def test_fallo_inexistente_404(self, db, api_client):
        res = api_client.post(f"{ENTREGAS_URL}{uuid.uuid4()}/fallo/")
        assert res.status_code == 404

# tests/integration/test_order.py
import uuid
import pytest
from tests.conftest import gql


def _pedido_data():
    return {
        "id":            str(uuid.uuid4()),
        "estado":        "RECIBIDO",
        "canal":         "TPV",
        "total":         "25000.00",
        "numeroDia":     1,
        "restauranteId": str(uuid.uuid4()),
    }


def _comanda_data(estado="PENDIENTE"):
    return {
        "id":      str(uuid.uuid4()),
        "estado":  estado,
        "estacion": "GENERAL",
        "pedido":  str(uuid.uuid4()),
    }


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION: crearPedido — permisos por rol
# ═══════════════════════════════════════════════════════════════════════════

CREAR_PEDIDO = """
mutation {
  crearPedido(
    restauranteId: "rest1"
    canal: "TPV"
    moneda: "COP"
    detalles: [{
      platoId: "p1"
      nombrePlato: "Hamburguesa"
      precioUnitario: 15000
      cantidad: 1
    }]
  ) { ok error pedido { id estado } }
}
"""


class TestCrearPedido:

    def _mock(self, mocker, data=None):
        mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.crear_pedido",
            return_value=data or _pedido_data(),
        )
        mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.crear_comanda",
            return_value=_comanda_data(),
        )

    def test_admin_puede_crear_pedido(self, mocker):
        self._mock(mocker)
        result = gql(CREAR_PEDIDO, rol="admin_central")
        assert result.errors is None
        assert result.data["crearPedido"]["ok"] is True
        assert result.data["crearPedido"]["pedido"]["estado"] == "RECIBIDO"

    def test_mesero_puede_crear_pedido(self, mocker):
        self._mock(mocker)
        result = gql(CREAR_PEDIDO, rol="mesero")
        assert result.data["crearPedido"]["ok"] is True

    def test_cajero_puede_crear_pedido(self, mocker):
        self._mock(mocker)
        result = gql(CREAR_PEDIDO, rol="cajero")
        assert result.data["crearPedido"]["ok"] is True

    def test_cocinero_no_puede_crear_pedido(self):
        result = gql(CREAR_PEDIDO, rol="cocinero")
        assert result.data["crearPedido"]["ok"] is False
        assert "permiso" in result.data["crearPedido"]["error"].lower()

    def test_repartidor_no_puede_crear_pedido(self):
        result = gql(CREAR_PEDIDO, rol="repartidor")
        assert result.data["crearPedido"]["ok"] is False

    def test_anonimo_no_puede_crear_pedido(self):
        result = gql(CREAR_PEDIDO)
        assert result.data["crearPedido"]["ok"] is False

    def test_servicio_caido_retorna_error(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.crear_pedido",
            return_value=None,
        )
        result = gql(CREAR_PEDIDO, rol="admin_central")
        assert result.data["crearPedido"]["ok"] is False

    def test_crear_pedido_crea_comanda_automaticamente(self, mocker):
        """Al crear pedido exitoso, se debe crear una comanda GENERAL automáticamente."""
        crear_comanda_mock = mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.crear_comanda",
            return_value=_comanda_data(),
        )
        mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.crear_pedido",
            return_value=_pedido_data(),
        )
        gql(CREAR_PEDIDO, rol="mesero")
        crear_comanda_mock.assert_called_once()
        call_args = crear_comanda_mock.call_args[0][0]
        assert call_args["estacion"] == "GENERAL"


# ═══════════════════════════════════════════════════════════════════════════
# MUTATIONS: Transiciones de estado
# ═══════════════════════════════════════════════════════════════════════════

class TestTransicionesPedido:

    def test_confirmar_pedido_cajero(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.confirmar_pedido",
            return_value={**_pedido_data(), "estado": "EN_PREPARACION"},
        )
        result = gql("""
        mutation { confirmarPedido(id: "p1") { ok error pedido { estado } } }
        """, rol="cajero")
        assert result.data["confirmarPedido"]["ok"] is True
        assert result.data["confirmarPedido"]["pedido"]["estado"] == "EN_PREPARACION"

    def test_confirmar_pedido_cocinero_no_puede(self):
        result = gql("""
        mutation { confirmarPedido(id: "p1") { ok error } }
        """, rol="cocinero")
        assert result.data["confirmarPedido"]["ok"] is False

    def test_cancelar_pedido_supervisor(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.cancelar_pedido",
            return_value={**_pedido_data(), "estado": "CANCELADO"},
        )
        result = gql("""
        mutation { cancelarPedido(id: "p1") { ok pedido { estado } } }
        """, rol="supervisor")
        assert result.data["cancelarPedido"]["ok"] is True

    def test_marcar_listo_cocinero(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.marcar_listo",
            return_value={**_pedido_data(), "estado": "LISTO"},
        )
        result = gql("""
        mutation { marcarListo(id: "p1") { ok pedido { estado } } }
        """, rol="cocinero")
        assert result.data["marcarListo"]["ok"] is True

    def test_marcar_listo_cajero_no_puede(self):
        result = gql("""
        mutation { marcarListo(id: "p1") { ok error } }
        """, rol="cajero")
        assert result.data["marcarListo"]["ok"] is False

    def test_entregar_pedido_cajero(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.entregar_pedido",
            return_value={**_pedido_data(), "estado": "ENTREGADO"},
        )
        result = gql("""
        mutation {
          entregarPedido(id: "p1", metodoPago: "efectivo") {
            ok pedido { estado }
          }
        }
        """, rol="cajero")
        assert result.data["entregarPedido"]["ok"] is True

    def test_entregar_pedido_mesero_no_puede(self):
        result = gql("""
        mutation { entregarPedido(id: "p1") { ok error } }
        """, rol="mesero")
        assert result.data["entregarPedido"]["ok"] is False


# ═══════════════════════════════════════════════════════════════════════════
# MUTATIONS: Comandas
# ═══════════════════════════════════════════════════════════════════════════

class TestComandas:

    def test_iniciar_comanda_cocinero(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.iniciar_comanda",
            return_value=_comanda_data("PREPARANDO"),
        )
        mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.confirmar_pedido",
            return_value=_pedido_data(),
        )
        result = gql("""
        mutation { iniciarComanda(id: "c1") { ok comanda { estado } } }
        """, rol="cocinero")
        assert result.data["iniciarComanda"]["ok"] is True
        assert result.data["iniciarComanda"]["comanda"]["estado"] == "PREPARANDO"

    def test_iniciar_comanda_avanza_pedido_a_en_preparacion(self, mocker):
        """IniciarComanda también confirma el pedido (RECIBIDO → EN_PREPARACION)."""
        mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.iniciar_comanda",
            return_value={**_comanda_data(), "pedido": "pid123"},
        )
        confirmar_mock = mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.confirmar_pedido",
            return_value=_pedido_data(),
        )
        gql("""
        mutation { iniciarComanda(id: "c1") { ok } }
        """, rol="cocinero")
        confirmar_mock.assert_called_once()

    def test_comanda_lista_marca_pedido_listo(self, mocker):
        """ComandaLista también marca el pedido como LISTO."""
        mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.comanda_lista",
            return_value={**_comanda_data("LISTO"), "pedido": "pid123"},
        )
        marcar_mock = mocker.patch(
            "app.gateway.graphql.services.order.mutations.order_client.marcar_listo",
            return_value=_pedido_data(),
        )
        result = gql("""
        mutation { comandaLista(id: "c1") { ok comanda { estado } } }
        """, rol="cocinero")
        assert result.data["comandaLista"]["ok"] is True
        marcar_mock.assert_called_once()

    def test_cajero_no_puede_iniciar_comanda(self):
        result = gql("""
        mutation { iniciarComanda(id: "c1") { ok error } }
        """, rol="cajero")
        assert result.data["iniciarComanda"]["ok"] is False


# ═══════════════════════════════════════════════════════════════════════════
# QUERIES: Pedidos
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryPedidos:

    def test_listar_pedidos_lista_directa(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.order.queries.order_client.get_pedidos",
            return_value=[_pedido_data(), _pedido_data()],
        )
        result = gql("""
        query { pedidos { id estado } }
        """, rol="admin_central")
        assert result.errors is None
        assert len(result.data["pedidos"]) == 2

    def test_listar_pedidos_paginado_unwrap(self, mocker):
        """order_client puede retornar respuesta paginada {count, results} — debe unwrap."""
        mocker.patch(
            "app.gateway.graphql.services.order.queries.order_client.get_pedidos",
            return_value={"count": 2, "results": [
                _pedido_data(), _pedido_data()]},
        )
        result = gql("""
        query { pedidos { id } }
        """, rol="admin_central")
        assert len(result.data["pedidos"]) == 2

    def test_listar_pedidos_error_retorna_lista_vacia(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.order.queries.order_client.get_pedidos",
            return_value={"_error": True},
        )
        result = gql("""
        query { pedidos { id } }
        """, rol="admin_central")
        assert result.data["pedidos"] == []

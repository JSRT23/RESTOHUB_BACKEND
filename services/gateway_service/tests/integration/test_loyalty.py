# tests/integration/test_loyalty.py
import uuid
import pytest
from tests.conftest import gql


def _cuenta():
    return {"clienteId": str(uuid.uuid4()), "saldo": 500, "nivel": "BRONCE", "cache": False}


def _cupon():
    return {
        "id": str(uuid.uuid4()),
        "codigo": "TEST0001",
        "disponible": True,
        "tipoDescuento": "porcentaje",
        "valorDescuento": "10.00",
    }


# ═══════════════════════════════════════════════════════════════════════════
# QUERY: puntosCliente — cache hit/miss
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryPuntosCliente:

    def test_puntos_cliente_existente(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.loyalty.queries.loyalty_client.get_puntos",
            return_value={"cliente_id": str(
                uuid.uuid4()), "saldo": 750, "nivel": "PLATA", "_cache": False},
        )
        result = gql("""
        query { puntosCliente(clienteId: "cid1") { saldo nivel } }
        """, rol="cajero")
        assert result.errors is None
        assert result.data["puntosCliente"]["saldo"] == 750
        assert result.data["puntosCliente"]["nivel"] == "PLATA"

    def test_puntos_cliente_no_existe_retorna_null(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.loyalty.queries.loyalty_client.get_puntos",
            return_value=None,
        )
        result = gql("""
        query { puntosCliente(clienteId: "noexiste") { saldo } }
        """, rol="cajero")
        assert result.errors is None
        assert result.data["puntosCliente"] is None

    def test_puntos_renombra_underscore_cache(self, mocker):
        """El resolver renombra _cache → cache para que GraphQL lo resuelva."""
        mocker.patch(
            "app.gateway.graphql.services.loyalty.queries.loyalty_client.get_puntos",
            return_value={"cliente_id": "x", "saldo": 100,
                          "nivel": "BRONCE", "_cache": True},
        )
        result = gql("""
        query { puntosCliente(clienteId: "x") { saldo } }
        """, rol="cajero")
        # Solo verificamos que no rompe — _cache → cache debe manejarse
        assert result.errors is None


# ═══════════════════════════════════════════════════════════════════════════
# MUTATIONS: Acumular / Canjear puntos
# ═══════════════════════════════════════════════════════════════════════════

class TestPuntosMutations:

    def test_acumular_puntos(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.loyalty.mutations.loyalty_client.acumular_puntos",
            return_value={"cliente_id": "c1", "saldo": 600, "nivel": "BRONCE"},
        )
        result = gql("""
        mutation {
          acumularPuntos(clienteId: "c1", puntos: 100) {
            ok errores cuenta { saldo nivel }
          }
        }
        """, rol="cajero")
        assert result.errors is None
        assert result.data["acumularPuntos"]["ok"] is True
        assert result.data["acumularPuntos"]["cuenta"]["saldo"] == 600

    def test_acumular_puntos_servicio_caido(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.loyalty.mutations.loyalty_client.acumular_puntos",
            return_value=None,
        )
        result = gql("""
        mutation { acumularPuntos(clienteId: "c1", puntos: 100) { ok errores } }
        """, rol="cajero")
        assert result.data["acumularPuntos"]["ok"] is False

    def test_canjear_puntos_exitoso(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.loyalty.mutations.loyalty_client.canjear_puntos",
            return_value={"cliente_id": "c1", "saldo": 400, "nivel": "BRONCE"},
        )
        result = gql("""
        mutation {
          canjearPuntos(clienteId: "c1", puntos: 100) {
            ok errores cuenta { saldo }
          }
        }
        """, rol="cajero")
        assert result.data["canjearPuntos"]["ok"] is True
        assert result.data["canjearPuntos"]["cuenta"]["saldo"] == 400

    def test_canjear_saldo_insuficiente(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.loyalty.mutations.loyalty_client.canjear_puntos",
            return_value=None,
        )
        result = gql("""
        mutation { canjearPuntos(clienteId: "c1", puntos: 9999) { ok errores } }
        """, rol="cajero")
        assert result.data["canjearPuntos"]["ok"] is False


# ═══════════════════════════════════════════════════════════════════════════
# MUTATIONS: Cupones
# ═══════════════════════════════════════════════════════════════════════════

class TestCupones:

    def test_canjear_cupon_disponible(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.loyalty.mutations.loyalty_client.canjear_cupon",
            return_value={**_cupon(), "usos_actuales": 1},
        )
        result = gql("""
        mutation { canjearCupon(cuponId: "cupon1") { ok errores cupon { codigo } } }
        """, rol="cajero")
        assert result.errors is None
        assert result.data["canjearCupon"]["ok"] is True

    def test_canjear_cupon_no_disponible(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.loyalty.mutations.loyalty_client.canjear_cupon",
            return_value=None,
        )
        result = gql("""
        mutation { canjearCupon(cuponId: "cupon1") { ok errores } }
        """, rol="cajero")
        assert result.data["canjearCupon"]["ok"] is False

    def test_validar_cupon_disponible(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.loyalty.queries.loyalty_client.validar_cupon",
            return_value=_cupon(),
        )
        result = gql("""
        query { validarCupon(codigo: "TEST0001") { codigo disponible } }
        """, rol="cajero")
        assert result.errors is None
        assert result.data["validarCupon"]["codigo"] == "TEST0001"

    def test_validar_cupon_no_disponible_retorna_cupon(self, mocker):
        """Cuando el cupón existe pero no está disponible, devuelve {detail, cupon}."""
        mocker.patch(
            "app.gateway.graphql.services.loyalty.queries.loyalty_client.validar_cupon",
            return_value={"detail": "Agotado.", "cupon": {
                **_cupon(), "disponible": False}},
        )
        result = gql("""
        query { validarCupon(codigo: "TEST0001") { disponible } }
        """, rol="cajero")
        assert result.data["validarCupon"]["disponible"] is False

    def test_validar_cupon_inexistente_retorna_null(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.loyalty.queries.loyalty_client.validar_cupon",
            return_value={"detail": "No encontrado."},
        )
        result = gql("""
        query { validarCupon(codigo: "NOEXISTE") { codigo } }
        """, rol="cajero")
        assert result.data["validarCupon"] is None


# ═══════════════════════════════════════════════════════════════════════════
# MUTATIONS: Promociones — evaluar
# ═══════════════════════════════════════════════════════════════════════════

class TestPromociones:

    EVALUAR = """
    mutation {
      evaluarPromocion(
        pedidoId: "ped1"
        clienteId: "cli1"
        restauranteId: "rest1"
        total: 30000
      ) { ok errores aplicacion { descuentoAplicado } }
    }
    """

    def test_evaluar_promo_aplica(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.loyalty.mutations.loyalty_client.evaluar_promocion",
            return_value={"id": str(uuid.uuid4()),
                          "descuento_aplicado": "3000.00"},
        )
        result = gql(self.EVALUAR, rol="cajero")
        assert result.errors is None
        assert result.data["evaluarPromocion"]["ok"] is True
        assert result.data["evaluarPromocion"]["aplicacion"]["descuentoAplicado"] == "3000.00"

    def test_evaluar_sin_promo_aplicable(self, mocker):
        """Cuando no hay promo, retorna {detail} sin id → aplicacion=None."""
        mocker.patch(
            "app.gateway.graphql.services.loyalty.mutations.loyalty_client.evaluar_promocion",
            return_value={"detail": "Ninguna promoción aplica."},
        )
        result = gql(self.EVALUAR, rol="cajero")
        assert result.data["evaluarPromocion"]["ok"] is True
        assert result.data["evaluarPromocion"]["aplicacion"] is None

    def test_evaluar_servicio_caido(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.loyalty.mutations.loyalty_client.evaluar_promocion",
            return_value=None,
        )
        result = gql(self.EVALUAR, rol="cajero")
        assert result.data["evaluarPromocion"]["ok"] is False

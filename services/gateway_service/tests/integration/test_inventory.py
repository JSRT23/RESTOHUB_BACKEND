# tests/integration/test_inventory.py
import uuid
import pytest
from tests.conftest import gql


def _proveedor():
    return {"id": str(uuid.uuid4()), "nombre": "Proveedor Test", "pais": "CO", "alcance": "LOCAL"}


def _almacen():
    return {"id": str(uuid.uuid4()), "nombre": "Bodega Principal", "restauranteId": str(uuid.uuid4())}


def _stock():
    return {"id": str(uuid.uuid4()), "nombreIngrediente": "Pollo", "cantidadActual": "10.00"}


def _orden():
    return {"id": str(uuid.uuid4()), "estado": "BORRADOR", "total": "500000.00"}


# ═══════════════════════════════════════════════════════════════════════════
# QUERY: proveedores — acceso por rol
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryProveedores:

    def test_admin_ve_todos(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.inventory.queries.inventory_client.get_proveedores",
            return_value=[_proveedor(), _proveedor()],
        )
        result = gql("query { proveedores { id nombre } }",
                     rol="admin_central")
        assert result.errors is None
        assert len(result.data["proveedores"]) == 2

    def test_cocinero_no_ve_proveedores(self):
        result = gql("query { proveedores { id } }", rol="cocinero")
        assert result.data["proveedores"] == []

    def test_anonimo_no_ve_proveedores(self):
        result = gql("query { proveedores { id } }")
        assert result.data["proveedores"] == []


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION: crearProveedor — reglas de negocio
# ═══════════════════════════════════════════════════════════════════════════

class TestCrearProveedor:

    MUTATION = """
    mutation($nombre: String!, $pais: String!, $alcance: String) {
      crearProveedor(nombre: $nombre, pais: $pais, alcance: $alcance) {
        ok error proveedor { id nombre alcance }
      }
    }
    """

    def test_admin_crea_global(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.inventory.mutations.inventory_client.crear_proveedor",
            return_value={**_proveedor(), "alcance": "GLOBAL"},
        )
        result = gql(self.MUTATION, {"nombre": "P", "pais": "CO", "alcance": "GLOBAL"},
                     rol="admin_central")
        assert result.data["crearProveedor"]["ok"] is True
        assert result.data["crearProveedor"]["proveedor"]["alcance"] == "GLOBAL"

    def test_admin_pais_sin_pais_destino_falla(self):
        result = gql(self.MUTATION, {"nombre": "P", "pais": "CO", "alcance": "PAIS"},
                     rol="admin_central")
        assert result.data["crearProveedor"]["ok"] is False
        assert "pais_destino" in result.data["crearProveedor"]["error"].lower()

    def test_gerente_crea_local(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.inventory.mutations.inventory_client.crear_proveedor",
            return_value={**_proveedor(), "alcance": "LOCAL"},
        )
        rid = uuid.uuid4()
        result = gql(self.MUTATION, {"nombre": "P", "pais": "CO"},
                     rol="gerente_local", restaurante_id=rid)
        assert result.data["crearProveedor"]["ok"] is True

    def test_gerente_sin_restaurante_falla(self):
        result = gql(self.MUTATION, {"nombre": "P",
                     "pais": "CO"}, rol="gerente_local")
        assert result.data["crearProveedor"]["ok"] is False
        assert "restaurante" in result.data["crearProveedor"]["error"].lower()

    def test_cajero_no_puede_crear(self):
        result = gql(self.MUTATION, {"nombre": "P",
                     "pais": "CO"}, rol="cajero")
        assert result.data["crearProveedor"]["ok"] is False


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION: crearAlmacen
# ═══════════════════════════════════════════════════════════════════════════

class TestCrearAlmacen:

    MUTATION = """
    mutation {
      crearAlmacen(restauranteId: "rest1", nombre: "Bodega") {
        ok error almacen { id nombre }
      }
    }
    """

    def test_gerente_puede_crear(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.inventory.mutations.inventory_client.crear_almacen",
            return_value=_almacen(),
        )
        result = gql(self.MUTATION, rol="gerente_local",
                     restaurante_id=uuid.uuid4())
        assert result.data["crearAlmacen"]["ok"] is True

    def test_supervisor_no_puede_crear(self):
        result = gql(self.MUTATION, rol="supervisor")
        assert result.data["crearAlmacen"]["ok"] is False


# ═══════════════════════════════════════════════════════════════════════════
# QUERY: stock — resolución por restaurante_id
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryStock:

    def test_stock_por_almacen_id(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.inventory.queries.inventory_client.get_stock",
            return_value=[_stock(), _stock()],
        )
        result = gql("""
        query { stock(almacenId: "alm1") { id nombreIngrediente } }
        """, rol="gerente_local")
        assert len(result.data["stock"]) == 2

    def test_stock_por_restaurante_id_resuelve_almacen(self, mocker):
        """Cuando se pasa restaurante_id sin almacen_id, el gateway resuelve el almacén."""
        mocker.patch(
            "app.gateway.graphql.services.inventory.queries.inventory_client.get_almacenes",
            return_value=[{"id": "alm1"}],
        )
        get_stock_mock = mocker.patch(
            "app.gateway.graphql.services.inventory.queries.inventory_client.get_stock",
            return_value=[_stock()],
        )
        result = gql("""
        query { stock(restauranteId: "rest1") { id } }
        """, rol="cocinero")
        assert result.errors is None
        # Verifica que llamó con el almacen_id resuelto
        get_stock_mock.assert_called_once()
        assert get_stock_mock.call_args.kwargs.get("almacen_id") == "alm1"


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION: crearOrdenCompra
# ═══════════════════════════════════════════════════════════════════════════

class TestOrdenesCompra:

    MUTATION = """
    mutation {
      crearOrdenCompra(
        proveedorId: "prov1"
        moneda: "COP"
        detalles: [{
          ingredienteId: "ing1"
          nombreIngrediente: "Pollo"
          unidadMedida: "kg"
          cantidad: 10
          precioUnitario: 12000
        }]
      ) { ok error orden { id estado } }
    }
    """

    def test_gerente_crea_orden(self, mocker):
        mocker.patch(
            "app.gateway.graphql.services.inventory.mutations.inventory_client.crear_orden_compra",
            return_value=_orden(),
        )
        result = gql(self.MUTATION, rol="gerente_local",
                     restaurante_id=uuid.uuid4())
        assert result.data["crearOrdenCompra"]["ok"] is True
        assert result.data["crearOrdenCompra"]["orden"]["estado"] == "BORRADOR"

    def test_cocinero_no_puede_crear_orden(self):
        result = gql(self.MUTATION, rol="cocinero")
        assert result.data["crearOrdenCompra"]["ok"] is False

    def test_resolver_alerta_inventario_directo(self, mocker):
        """Testa la lógica de permisos del resolver de inventory directamente."""
        from app.gateway.graphql.services.inventory import mutations as inv_mut
        from tests.conftest import make_request

        class FakeInfo:
            context = make_request(rol="gerente_local",
                                   restaurante_id=__import__("uuid").uuid4())

        mocker.patch(
            "app.gateway.graphql.services.inventory.mutations.inventory_client.resolver_alerta",
            return_value={"id": "alerta1", "estado": "resuelta"},
        )
        result = inv_mut.ResolverAlerta().mutate(FakeInfo(), id="alerta1")
        assert result.ok is True

    def test_cajero_no_puede_resolver_alerta_directo(self):
        """Cajero no tiene permiso — verificado directamente en el resolver."""
        from app.gateway.graphql.services.inventory import mutations as inv_mut
        from tests.conftest import make_request

        class FakeInfo:
            context = make_request(rol="cajero")

        result = inv_mut.ResolverAlerta().mutate(FakeInfo(), id="alerta1")
        assert result.ok is False
        assert "permiso" in result.error.lower()

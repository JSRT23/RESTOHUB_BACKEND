# tests/integration/test_proveedores_almacenes.py
import uuid
import pytest

from tests.conftest import (
    ProveedorFactory, AlmacenFactory, IngredienteInventarioFactory,
)

PROVEEDORES_URL = "/api/inventory/proveedores/"
ALMACENES_URL = "/api/inventory/almacenes/"


# ═══════════════════════════════════════════════════════════════════════════════
# Proveedor
# ═══════════════════════════════════════════════════════════════════════════════

class TestProveedorViewSet:

    def test_listar_proveedores(self, db, api_client):
        ProveedorFactory.create_batch(3)
        res = api_client.get(PROVEEDORES_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_crear_proveedor_global(self, db, api_client):
        res = api_client.post(PROVEEDORES_URL, {
            "nombre": "Dist. Nacional", "pais": "Colombia",
            "alcance": "GLOBAL", "moneda_preferida": "COP"
        })
        assert res.status_code == 201
        assert res.data["nombre"] == "Dist. Nacional"
        assert res.data["alcance"] == "GLOBAL"

    def test_crear_retorna_id_uuid(self, db, api_client):
        res = api_client.post(PROVEEDORES_URL, {
            "nombre": "Dist. X", "pais": "Colombia", "alcance": "GLOBAL"
        })
        assert res.status_code == 201
        uuid.UUID(res.data["id"])  # no lanza si es UUID válido

    def test_detalle_proveedor(self, db, api_client, proveedor):
        res = api_client.get(f"{PROVEEDORES_URL}{proveedor.id}/")
        assert res.status_code == 200
        assert res.data["nombre"] == proveedor.nombre

    def test_proveedor_inexistente_retorna_404(self, db, api_client):
        res = api_client.get(f"{PROVEEDORES_URL}{uuid.uuid4()}/")
        assert res.status_code == 404

    def test_actualizar_proveedor(self, db, api_client, proveedor):
        res = api_client.patch(
            f"{PROVEEDORES_URL}{proveedor.id}/", {"nombre": "Dist. Actualizada"})
        assert res.status_code == 200
        assert res.data["nombre"] == "Dist. Actualizada"

    def test_no_permite_delete(self, db, api_client, proveedor):
        res = api_client.delete(f"{PROVEEDORES_URL}{proveedor.id}/")
        assert res.status_code == 405

    def test_filtrar_por_activo(self, db, api_client):
        ProveedorFactory(activo=True)
        ProveedorFactory(activo=False)
        res = api_client.get(f"{PROVEEDORES_URL}?activo=true")
        assert res.status_code == 200
        assert all(p["activo"] is True for p in res.data)

    def test_filtrar_por_pais(self, db, api_client):
        ProveedorFactory(pais="Colombia")
        ProveedorFactory(pais="México")
        res = api_client.get(f"{PROVEEDORES_URL}?pais=Colombia")
        assert res.status_code == 200
        assert all("Colombia" in p["pais"] for p in res.data)

    def test_filtrar_scope_gerente_incluye_global(self, db, api_client):
        rest_id = str(uuid.uuid4())
        global_p = ProveedorFactory(alcance="GLOBAL")
        local_p = ProveedorFactory(
            alcance="LOCAL",
            creado_por_restaurante_id=uuid.uuid4())  # otro restaurante
        res = api_client.get(
            f"{PROVEEDORES_URL}?scope=gerente&restaurante_id={rest_id}"
            f"&pais_destino=Colombia")
        ids = [p["id"] for p in res.data]
        assert str(global_p.id) in ids
        assert str(local_p.id) not in ids

    def test_filtrar_scope_gerente_incluye_local_propio(self, db, api_client):
        rest_id = uuid.uuid4()
        local_p = ProveedorFactory(
            alcance="LOCAL", creado_por_restaurante_id=rest_id)
        res = api_client.get(
            f"{PROVEEDORES_URL}?scope=gerente&restaurante_id={rest_id}")
        ids = [p["id"] for p in res.data]
        assert str(local_p.id) in ids

    def test_crear_alcance_pais_sin_pais_destino_falla(self, db, api_client):
        res = api_client.post(PROVEEDORES_URL, {
            "nombre": "Dist.", "pais": "Colombia",
            "alcance": "PAIS",
        })
        assert res.status_code == 400

    def test_list_usa_serializer_ligero(self, db, api_client):
        ProveedorFactory()
        res = api_client.get(PROVEEDORES_URL)
        assert res.status_code == 200
        # El list serializer no expone fecha_creacion (solo el detail)
        assert "fecha_creacion" not in res.data[0]


# ═══════════════════════════════════════════════════════════════════════════════
# Almacén
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlmacenViewSet:

    def test_listar_almacenes(self, db, api_client):
        AlmacenFactory.create_batch(3)
        res = api_client.get(ALMACENES_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_crear_almacen(self, db, api_client):
        res = api_client.post(ALMACENES_URL, {
            "restaurante_id": str(uuid.uuid4()),
            "nombre": "Bodega Principal",
        })
        assert res.status_code == 201
        assert res.data["nombre"] == "Bodega Principal"

    def test_nombre_vacio_falla(self, db, api_client):
        res = api_client.post(ALMACENES_URL, {
            "restaurante_id": str(uuid.uuid4()),
            "nombre": "   ",
        })
        assert res.status_code == 400

    def test_detalle_almacen(self, db, api_client, almacen):
        res = api_client.get(f"{ALMACENES_URL}{almacen.id}/")
        assert res.status_code == 200
        assert res.data["nombre"] == almacen.nombre

    def test_detalle_incluye_conteos(self, db, api_client, almacen):
        IngredienteInventarioFactory(almacen=almacen)
        IngredienteInventarioFactory(almacen=almacen)
        res = api_client.get(f"{ALMACENES_URL}{almacen.id}/")
        assert res.data["total_ingredientes"] == 2

    def test_actualizar_almacen(self, db, api_client, almacen):
        res = api_client.patch(
            f"{ALMACENES_URL}{almacen.id}/", {"nombre": "Bodega Norte"})
        assert res.status_code == 200
        assert res.data["nombre"] == "Bodega Norte"

    def test_no_permite_delete(self, db, api_client, almacen):
        res = api_client.delete(f"{ALMACENES_URL}{almacen.id}/")
        assert res.status_code == 405

    def test_filtrar_por_restaurante(self, db, api_client):
        rid = uuid.uuid4()
        AlmacenFactory(restaurante_id=rid)
        AlmacenFactory()
        res = api_client.get(f"{ALMACENES_URL}?restaurante_id={rid}")
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_filtrar_por_activo(self, db, api_client):
        AlmacenFactory(activo=True)
        AlmacenFactory(activo=False)
        res = api_client.get(f"{ALMACENES_URL}?activo=false")
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["activo"] is False

    def test_stock_action(self, db, api_client, almacen):
        IngredienteInventarioFactory(almacen=almacen)
        res = api_client.get(f"{ALMACENES_URL}{almacen.id}/stock/")
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_stock_action_filtra_bajo_minimo(self, db, api_client, almacen):
        from decimal import Decimal
        IngredienteInventarioFactory(
            almacen=almacen,
            cantidad_actual=Decimal("5.000"),
            nivel_minimo=Decimal("10.000"))
        IngredienteInventarioFactory(
            almacen=almacen,
            cantidad_actual=Decimal("50.000"),
            nivel_minimo=Decimal("10.000"))
        res = api_client.get(
            f"{ALMACENES_URL}{almacen.id}/stock/?bajo_minimo=true")
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_almacen_inexistente_retorna_404(self, db, api_client):
        res = api_client.get(f"{ALMACENES_URL}{uuid.uuid4()}/")
        assert res.status_code == 404

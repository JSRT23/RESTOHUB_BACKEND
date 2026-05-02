# tests/integration/test_ordenes_recetas.py
import uuid
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from app.inventory.models import (
    OrdenCompra, DetalleOrdenCompra, LoteIngrediente,
    IngredienteInventario, EstadoOrdenCompra,
)
from tests.conftest import (
    ProveedorFactory, AlmacenFactory, OrdenCompraFactory,
    DetalleOrdenCompraFactory, RecetaPlatoFactory,
    IngredienteInventarioFactory,
)

ORDENES_URL = "/api/inventory/ordenes-compra/"
RECETAS_URL = "/api/inventory/recetas/"


# ═══════════════════════════════════════════════════════════════════════════════
# Orden de Compra
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrdenCompraViewSet:

    def _payload_base(self, proveedor, restaurante_id=None):
        return {
            "proveedor": str(proveedor.id),
            "restaurante_id": str(restaurante_id or uuid.uuid4()),
            "moneda": "COP",
            "detalles": [
                {
                    "ingrediente_id": str(uuid.uuid4()),
                    "nombre_ingrediente": "Arroz",
                    "unidad_medida": "kg",
                    "cantidad": "10.000",
                    "precio_unitario": "3000.00",
                }
            ],
        }

    def test_listar_ordenes(self, db, api_client):
        OrdenCompraFactory.create_batch(3)
        res = api_client.get(ORDENES_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_crear_orden(self, db, api_client):
        proveedor = ProveedorFactory()
        res = api_client.post(
            ORDENES_URL, self._payload_base(proveedor),
            format="json")
        assert res.status_code == 201
        assert res.data["estado"] == "BORRADOR"

    def test_crear_calcula_total(self, db, api_client):
        proveedor = ProveedorFactory()
        res = api_client.post(
            ORDENES_URL, self._payload_base(proveedor),
            format="json")
        assert res.status_code == 201
        # 10 * 3000 = 30000
        assert Decimal(str(res.data["total_estimado"])) == Decimal("30000.00")

    def test_crear_sin_detalles_falla(self, db, api_client):
        proveedor = ProveedorFactory()
        payload = self._payload_base(proveedor)
        payload["detalles"] = []
        res = api_client.post(ORDENES_URL, payload, format="json")
        assert res.status_code == 400

    def test_crear_precio_cero_falla(self, db, api_client):
        proveedor = ProveedorFactory()
        payload = self._payload_base(proveedor)
        payload["detalles"][0]["precio_unitario"] = "0.00"
        res = api_client.post(ORDENES_URL, payload, format="json")
        assert res.status_code == 400

    def test_detalle_orden(self, db, api_client, orden):
        res = api_client.get(f"{ORDENES_URL}{orden.id}/")
        assert res.status_code == 200
        assert "detalles" in res.data

    def test_filtrar_por_estado(self, db, api_client):
        OrdenCompraFactory(estado=EstadoOrdenCompra.BORRADOR)
        OrdenCompraFactory(estado=EstadoOrdenCompra.ENVIADA)
        res = api_client.get(f"{ORDENES_URL}?estado=BORRADOR")
        assert res.status_code == 200
        assert all(o["estado"] == "BORRADOR" for o in res.data)

    def test_filtrar_por_restaurante(self, db, api_client):
        rid = uuid.uuid4()
        OrdenCompraFactory(restaurante_id=rid)
        OrdenCompraFactory()
        res = api_client.get(f"{ORDENES_URL}?restaurante_id={rid}")
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_filtrar_por_proveedor(self, db, api_client):
        p1 = ProveedorFactory()
        p2 = ProveedorFactory()
        OrdenCompraFactory(proveedor=p1)
        OrdenCompraFactory(proveedor=p2)
        res = api_client.get(f"{ORDENES_URL}?proveedor_id={p1.id}")
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_list_usa_serializer_ligero(self, db, api_client):
        OrdenCompraFactory()
        res = api_client.get(ORDENES_URL)
        assert "detalles" not in res.data[0]

    # ── Enviar ────────────────────────────────────────────────────────────────

    def test_enviar_orden_borrador(self, db, api_client, orden):
        res = api_client.post(f"{ORDENES_URL}{orden.id}/enviar/")
        assert res.status_code == 200
        assert res.data["estado"] == "ENVIADA"

    def test_enviar_orden_pendiente(self, db, api_client):
        orden = OrdenCompraFactory(estado=EstadoOrdenCompra.PENDIENTE)
        res = api_client.post(f"{ORDENES_URL}{orden.id}/enviar/")
        assert res.status_code == 200
        assert res.data["estado"] == "ENVIADA"

    def test_enviar_orden_ya_enviada_falla(self, db, api_client, orden_enviada):
        res = api_client.post(f"{ORDENES_URL}{orden_enviada.id}/enviar/")
        assert res.status_code == 400

    def test_enviar_orden_cancelada_falla(self, db, api_client):
        orden = OrdenCompraFactory(estado=EstadoOrdenCompra.CANCELADA)
        res = api_client.post(f"{ORDENES_URL}{orden.id}/enviar/")
        assert res.status_code == 400

    # ── Cancelar ──────────────────────────────────────────────────────────────

    def test_cancelar_orden_borrador(self, db, api_client, orden):
        res = api_client.post(f"{ORDENES_URL}{orden.id}/cancelar/")
        assert res.status_code == 200
        assert res.data["estado"] == "CANCELADA"

    def test_cancelar_orden_enviada(self, db, api_client, orden_enviada):
        res = api_client.post(f"{ORDENES_URL}{orden_enviada.id}/cancelar/")
        assert res.status_code == 200
        assert res.data["estado"] == "CANCELADA"

    def test_cancelar_orden_recibida_falla(self, db, api_client):
        orden = OrdenCompraFactory(estado=EstadoOrdenCompra.RECIBIDA)
        res = api_client.post(f"{ORDENES_URL}{orden.id}/cancelar/")
        assert res.status_code == 400

    def test_cancelar_orden_ya_cancelada_falla(self, db, api_client):
        orden = OrdenCompraFactory(estado=EstadoOrdenCompra.CANCELADA)
        res = api_client.post(f"{ORDENES_URL}{orden.id}/cancelar/")
        assert res.status_code == 400

    # ── Recibir ───────────────────────────────────────────────────────────────

    def test_recibir_orden_enviada(self, db, api_client):
        restaurante_id = uuid.uuid4()
        almacen = AlmacenFactory(restaurante_id=restaurante_id)
        proveedor = ProveedorFactory()
        orden = OrdenCompraFactory(
            proveedor=proveedor,
            restaurante_id=restaurante_id,
            estado=EstadoOrdenCompra.ENVIADA)
        ingr_id = uuid.uuid4()
        detalle = DetalleOrdenCompraFactory(
            orden=orden,
            ingrediente_id=ingr_id,
            unidad_medida="kg",
            cantidad=Decimal("10.000"))

        res = api_client.post(
            f"{ORDENES_URL}{orden.id}/recibir/",
            {
                "detalles": [
                    {
                        "detalle_id": str(detalle.id),
                        "cantidad_recibida": "10.000",
                        "numero_lote": "LOTE-RECIBIDO",
                        "fecha_vencimiento": (
                            date.today() + timedelta(days=90)).isoformat(),
                    }
                ]
            },
            format="json"
        )
        assert res.status_code == 200
        # Lote creado
        assert LoteIngrediente.objects.filter(
            ingrediente_id=ingr_id).exists()
        # Stock actualizado
        inv = IngredienteInventario.objects.filter(
            ingrediente_id=ingr_id, almacen=almacen).first()
        assert inv is not None
        assert inv.cantidad_actual == Decimal("10.000")

    def test_recibir_orden_no_enviada_falla(self, db, api_client, orden):
        detalle = DetalleOrdenCompraFactory(orden=orden)
        res = api_client.post(
            f"{ORDENES_URL}{orden.id}/recibir/",
            {
                "detalles": [
                    {
                        "detalle_id": str(detalle.id),
                        "cantidad_recibida": "5.000",
                        "numero_lote": "LOTE-001",
                        "fecha_vencimiento": (
                            date.today() + timedelta(days=90)).isoformat(),
                    }
                ]
            },
            format="json"
        )
        assert res.status_code == 400

    def test_recibir_sin_detalle_valido_falla(self, db, api_client, orden_enviada):
        res = api_client.post(
            f"{ORDENES_URL}{orden_enviada.id}/recibir/",
            {
                "detalles": [
                    {
                        "detalle_id": str(uuid.uuid4()),  # no existe
                        "cantidad_recibida": "5.000",
                        "numero_lote": "LOTE-001",
                        "fecha_vencimiento": (
                            date.today() + timedelta(days=90)).isoformat(),
                    }
                ]
            },
            format="json"
        )
        assert res.status_code == 400

    def test_recibir_sin_almacen_activo_falla(self, db, api_client):
        proveedor = ProveedorFactory()
        restaurante_id = uuid.uuid4()
        # Sin almacén para ese restaurante
        orden = OrdenCompraFactory(
            proveedor=proveedor,
            restaurante_id=restaurante_id,
            estado=EstadoOrdenCompra.ENVIADA)
        detalle = DetalleOrdenCompraFactory(orden=orden)
        res = api_client.post(
            f"{ORDENES_URL}{orden.id}/recibir/",
            {
                "detalles": [
                    {
                        "detalle_id": str(detalle.id),
                        "cantidad_recibida": "5.000",
                        "numero_lote": "LOTE-001",
                        "fecha_vencimiento": (
                            date.today() + timedelta(days=90)).isoformat(),
                    }
                ]
            },
            format="json"
        )
        assert res.status_code == 400

    def test_orden_inexistente_retorna_404(self, db, api_client):
        res = api_client.get(f"{ORDENES_URL}{uuid.uuid4()}/")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# RecetaPlato
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecetaPlatoViewSet:

    def test_listar_recetas(self, db, api_client):
        RecetaPlatoFactory.create_batch(3)
        res = api_client.get(RECETAS_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_filtrar_por_plato(self, db, api_client):
        plato_id = uuid.uuid4()
        RecetaPlatoFactory(plato_id=plato_id)
        RecetaPlatoFactory(plato_id=plato_id)
        RecetaPlatoFactory()  # otro plato
        res = api_client.get(f"{RECETAS_URL}?plato_id={plato_id}")
        assert res.status_code == 200
        assert len(res.data) == 2

    def test_no_permite_post(self, db, api_client):
        res = api_client.post(RECETAS_URL, {})
        assert res.status_code == 405

    def test_costo_plato_retorna_estructura(self, db, api_client):
        plato_id = uuid.uuid4()
        RecetaPlatoFactory(
            plato_id=plato_id,
            nombre_ingrediente="Arroz",
            cantidad=Decimal("0.500"),
            costo_unitario=Decimal("4000.0000"))
        res = api_client.get(f"{RECETAS_URL}costo_plato/?plato_id={plato_id}")
        assert res.status_code == 200
        assert "costo_total" in res.data
        assert "ingredientes" in res.data
        assert "tiene_costos_vacios" in res.data

    def test_costo_plato_sin_plato_id_falla(self, db, api_client):
        res = api_client.get(f"{RECETAS_URL}costo_plato/")
        assert res.status_code == 400

    def test_costo_plato_sin_receta_retorna_404(self, db, api_client):
        res = api_client.get(
            f"{RECETAS_URL}costo_plato/?plato_id={uuid.uuid4()}")
        assert res.status_code == 404

    def test_costo_plato_detecta_costo_vacio(self, db, api_client):
        plato_id = uuid.uuid4()
        RecetaPlatoFactory(
            plato_id=plato_id,
            costo_unitario=Decimal("0.0000"))
        res = api_client.get(f"{RECETAS_URL}costo_plato/?plato_id={plato_id}")
        assert res.status_code == 200
        assert res.data["tiene_costos_vacios"] is True
        assert res.data["advertencia"] is not None

    def test_costo_plato_calcula_porciones(self, db, api_client):
        plato_id = uuid.uuid4()
        restaurante_id = uuid.uuid4()
        almacen = AlmacenFactory(restaurante_id=restaurante_id)
        ingr_id = uuid.uuid4()
        RecetaPlatoFactory(
            plato_id=plato_id,
            ingrediente_id=ingr_id,
            cantidad=Decimal("0.250"),
            costo_unitario=Decimal("2000.0000"))
        IngredienteInventarioFactory(
            ingrediente_id=ingr_id,
            almacen=almacen,
            cantidad_actual=Decimal("1.000"))
        res = api_client.get(
            f"{RECETAS_URL}costo_plato/?plato_id={plato_id}"
            f"&restaurante_id={restaurante_id}")
        assert res.status_code == 200
        assert res.data["porciones_disponibles"] == 4

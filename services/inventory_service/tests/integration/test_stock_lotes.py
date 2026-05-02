# tests/integration/test_stock_lotes.py
import uuid
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from app.inventory.models import (
    IngredienteInventario, LoteIngrediente, MovimientoInventario,
    AlertaStock, EstadoAlerta, EstadoLote,
)
from tests.conftest import (
    AlmacenFactory, ProveedorFactory, IngredienteInventarioFactory,
    LoteIngredienteFactory, AlertaStockFactory,
)

STOCK_URL = "/api/inventory/stock/"
LOTES_URL = "/api/inventory/lotes/"
ALERTAS_URL = "/api/inventory/alertas/"
MOVIMIENTOS_URL = "/api/inventory/movimientos/"


# ═══════════════════════════════════════════════════════════════════════════════
# IngredienteInventario
# ═══════════════════════════════════════════════════════════════════════════════

class TestIngredienteInventarioViewSet:

    def test_listar_stock(self, db, api_client):
        IngredienteInventarioFactory.create_batch(3)
        res = api_client.get(STOCK_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_crear_stock(self, db, api_client):
        almacen = AlmacenFactory()
        res = api_client.post(STOCK_URL, {
            "ingrediente_id": str(uuid.uuid4()),
            "nombre_ingrediente": "Arroz",
            "almacen": str(almacen.id),
            "unidad_medida": "kg",
            "cantidad_actual": "50.000",
            "nivel_minimo": "10.000",
            "nivel_maximo": "200.000",
        })
        assert res.status_code == 201

    def test_nivel_maximo_menor_minimo_falla(self, db, api_client):
        almacen = AlmacenFactory()
        res = api_client.post(STOCK_URL, {
            "ingrediente_id": str(uuid.uuid4()),
            "nombre_ingrediente": "Arroz",
            "almacen": str(almacen.id),
            "unidad_medida": "kg",
            "cantidad_actual": "50.000",
            "nivel_minimo": "200.000",
            "nivel_maximo": "10.000",
        })
        assert res.status_code == 400

    def test_detalle_stock(self, db, api_client, ingrediente_inv):
        res = api_client.get(f"{STOCK_URL}{ingrediente_inv.id}/")
        assert res.status_code == 200
        assert res.data["nombre_ingrediente"] == ingrediente_inv.nombre_ingrediente

    def test_detalle_incluye_propiedades(self, db, api_client, ingrediente_inv):
        res = api_client.get(f"{STOCK_URL}{ingrediente_inv.id}/")
        assert "necesita_reposicion" in res.data
        assert "esta_agotado" in res.data
        assert "porcentaje_stock" in res.data

    def test_actualizar_niveles(self, db, api_client, ingrediente_inv):
        res = api_client.patch(
            f"{STOCK_URL}{ingrediente_inv.id}/",
            {"nivel_minimo": "20.000", "nivel_maximo": "300.000"})
        assert res.status_code == 200

    def test_filtrar_por_almacen(self, db, api_client):
        almacen1 = AlmacenFactory()
        almacen2 = AlmacenFactory()
        IngredienteInventarioFactory(almacen=almacen1)
        IngredienteInventarioFactory(almacen=almacen2)
        res = api_client.get(f"{STOCK_URL}?almacen_id={almacen1.id}")
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_stock_inexistente_retorna_404(self, db, api_client):
        res = api_client.get(f"{STOCK_URL}{uuid.uuid4()}/")
        assert res.status_code == 404

    def test_ajustar_stock_positivo(self, db, api_client, ingrediente_inv):
        cantidad_antes = ingrediente_inv.cantidad_actual
        res = api_client.post(f"{STOCK_URL}{ingrediente_inv.id}/ajustar/", {
            "cantidad": "10.000",
            "descripcion": "Ajuste por inventario físico mensual",
        })
        assert res.status_code == 200
        ingrediente_inv.refresh_from_db()
        assert ingrediente_inv.cantidad_actual == cantidad_antes + \
            Decimal("10.000")

    def test_ajustar_stock_negativo(self, db, api_client, ingrediente_inv):
        cantidad_antes = ingrediente_inv.cantidad_actual
        res = api_client.post(f"{STOCK_URL}{ingrediente_inv.id}/ajustar/", {
            "cantidad": "-5.000",
            "descripcion": "Merma detectada en revisión semanal",
        })
        assert res.status_code == 200
        ingrediente_inv.refresh_from_db()
        assert ingrediente_inv.cantidad_actual == cantidad_antes - \
            Decimal("5.000")

    def test_ajustar_stock_negativo_falla_si_queda_negativo(
            self, db, api_client):
        inv = IngredienteInventarioFactory(cantidad_actual=Decimal("5.000"))
        res = api_client.post(f"{STOCK_URL}{inv.id}/ajustar/", {
            "cantidad": "-100.000",
            "descripcion": "Intento de dejar stock negativo en prueba",
        })
        assert res.status_code == 400

    def test_ajustar_crea_movimiento(self, db, api_client, ingrediente_inv):
        api_client.post(f"{STOCK_URL}{ingrediente_inv.id}/ajustar/", {
            "cantidad": "10.000",
            "descripcion": "Ajuste por inventario físico completo",
        })
        mov = MovimientoInventario.objects.filter(
            ingrediente_inventario=ingrediente_inv,
            tipo_movimiento="AJUSTE").first()
        assert mov is not None
        assert mov.cantidad == Decimal("10.000")

    def test_ajustar_descripcion_corta_falla(self, db, api_client, ingrediente_inv):
        res = api_client.post(f"{STOCK_URL}{ingrediente_inv.id}/ajustar/", {
            "cantidad": "5.000",
            "descripcion": "corta",
        })
        assert res.status_code == 400

    def test_ajustar_bajo_minimo_genera_alerta(self, db, api_client):
        inv = IngredienteInventarioFactory(
            cantidad_actual=Decimal("15.000"),
            nivel_minimo=Decimal("10.000"))
        api_client.post(f"{STOCK_URL}{inv.id}/ajustar/", {
            "cantidad": "-10.000",
            "descripcion": "Ajuste corrección inventario físico",
        })
        inv.refresh_from_db()
        assert AlertaStock.objects.filter(
            ingrediente_id=inv.ingrediente_id,
            estado=EstadoAlerta.PENDIENTE).exists()

    def test_movimientos_action(self, db, api_client, ingrediente_inv):
        api_client.post(f"{STOCK_URL}{ingrediente_inv.id}/ajustar/", {
            "cantidad": "5.000",
            "descripcion": "Primer ajuste de inventario físico",
        })
        res = api_client.get(f"{STOCK_URL}{ingrediente_inv.id}/movimientos/")
        assert res.status_code == 200
        assert len(res.data) >= 1

    def test_list_usa_serializer_ligero(self, db, api_client):
        IngredienteInventarioFactory()
        res = api_client.get(STOCK_URL)
        assert "movimientos" not in res.data[0]


# ═══════════════════════════════════════════════════════════════════════════════
# LoteIngrediente
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoteIngredienteViewSet:

    def test_listar_lotes(self, db, api_client):
        LoteIngredienteFactory.create_batch(3)
        res = api_client.get(LOTES_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_crear_lote_crea_stock_y_movimiento(self, db, api_client):
        almacen = AlmacenFactory()
        proveedor = ProveedorFactory()
        ingr_id = uuid.uuid4()
        res = api_client.post(LOTES_URL, {
            "ingrediente_id": str(ingr_id),
            "almacen": str(almacen.id),
            "proveedor": str(proveedor.id),
            "numero_lote": "LOTE-TEST-001",
            "fecha_vencimiento": (
                date.today() + timedelta(days=180)).isoformat(),
            "cantidad_recibida": "100.000",
            "unidad_medida": "kg",
        })
        assert res.status_code == 201
        # Stock creado
        inv = IngredienteInventario.objects.filter(
            ingrediente_id=ingr_id, almacen=almacen).first()
        assert inv is not None
        assert inv.cantidad_actual == Decimal("100.000")
        # Movimiento ENTRADA creado
        mov = MovimientoInventario.objects.filter(
            ingrediente_inventario=inv,
            tipo_movimiento="ENTRADA").first()
        assert mov is not None

    def test_crear_lote_acumula_stock_existente(self, db, api_client):
        almacen = AlmacenFactory()
        proveedor = ProveedorFactory()
        ingr_id = uuid.uuid4()
        inv = IngredienteInventarioFactory(
            ingrediente_id=ingr_id,
            almacen=almacen,
            cantidad_actual=Decimal("50.000"))
        api_client.post(LOTES_URL, {
            "ingrediente_id": str(ingr_id),
            "almacen": str(almacen.id),
            "proveedor": str(proveedor.id),
            "numero_lote": "LOTE-ACUM",
            "fecha_vencimiento": (
                date.today() + timedelta(days=90)).isoformat(),
            "cantidad_recibida": "30.000",
            "unidad_medida": "kg",
        })
        inv.refresh_from_db()
        assert inv.cantidad_actual == Decimal("80.000")

    def test_fecha_vencimiento_pasada_falla(self, db, api_client):
        almacen = AlmacenFactory()
        proveedor = ProveedorFactory()
        res = api_client.post(LOTES_URL, {
            "ingrediente_id": str(uuid.uuid4()),
            "almacen": str(almacen.id),
            "proveedor": str(proveedor.id),
            "numero_lote": "LOTE-PASADO",
            "fecha_vencimiento": (
                date.today() - timedelta(days=1)).isoformat(),
            "cantidad_recibida": "10.000",
            "unidad_medida": "kg",
        })
        assert res.status_code == 400

    def test_filtrar_por_estado(self, db, api_client):
        LoteIngredienteFactory(estado=EstadoLote.ACTIVO)
        LoteIngredienteFactory(estado=EstadoLote.AGOTADO)
        res = api_client.get(f"{LOTES_URL}?estado=ACTIVO")
        assert res.status_code == 200
        assert all(l["estado"] == "ACTIVO" for l in res.data)

    def test_filtrar_por_almacen(self, db, api_client):
        almacen1 = AlmacenFactory()
        almacen2 = AlmacenFactory()
        LoteIngredienteFactory(almacen=almacen1)
        LoteIngredienteFactory(almacen=almacen2)
        res = api_client.get(f"{LOTES_URL}?almacen_id={almacen1.id}")
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_filtrar_por_vencer(self, db, api_client):
        LoteIngredienteFactory(
            fecha_vencimiento=date.today() + timedelta(days=5),
            estado=EstadoLote.ACTIVO)
        LoteIngredienteFactory(
            fecha_vencimiento=date.today() + timedelta(days=60),
            estado=EstadoLote.ACTIVO)
        res = api_client.get(f"{LOTES_URL}?por_vencer=10")
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_retirar_lote(self, db, api_client):
        almacen = AlmacenFactory()
        proveedor = ProveedorFactory()
        ingr_id = uuid.uuid4()
        lote = LoteIngredienteFactory(
            almacen=almacen, proveedor=proveedor,
            ingrediente_id=ingr_id,
            cantidad_actual=Decimal("30.000"))
        inv = IngredienteInventarioFactory(
            ingrediente_id=ingr_id,
            almacen=almacen,
            cantidad_actual=Decimal("50.000"))
        res = api_client.post(f"{LOTES_URL}{lote.id}/retirar/")
        assert res.status_code == 200
        lote.refresh_from_db()
        assert lote.estado == "RETIRADO"
        inv.refresh_from_db()
        assert inv.cantidad_actual == Decimal("20.000")

    def test_retirar_lote_ya_retirado_falla(self, db, api_client):
        lote = LoteIngredienteFactory(estado=EstadoLote.RETIRADO)
        res = api_client.post(f"{LOTES_URL}{lote.id}/retirar/")
        assert res.status_code == 400

    def test_no_permite_delete(self, db, api_client, lote):
        res = api_client.delete(f"{LOTES_URL}{lote.id}/")
        assert res.status_code == 405


# ═══════════════════════════════════════════════════════════════════════════════
# AlertaStock
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertaStockViewSet:

    def test_listar_alertas(self, db, api_client):
        AlertaStockFactory.create_batch(3)
        res = api_client.get(ALERTAS_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_filtrar_por_restaurante(self, db, api_client):
        rid = uuid.uuid4()
        inv1 = IngredienteInventarioFactory()
        inv1.almacen.restaurante_id = rid
        inv1.almacen.save()
        alerta = AlertaStockFactory(
            ingrediente_inventario=inv1,
            almacen=inv1.almacen,
            restaurante_id=rid,
            ingrediente_id=inv1.ingrediente_id)
        AlertaStockFactory()  # otro restaurante
        res = api_client.get(f"{ALERTAS_URL}?restaurante_id={rid}")
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_filtrar_por_estado(self, db, api_client):
        AlertaStockFactory(estado=EstadoAlerta.PENDIENTE)
        AlertaStockFactory(estado=EstadoAlerta.RESUELTA)
        res = api_client.get(f"{ALERTAS_URL}?estado=PENDIENTE")
        assert res.status_code == 200
        assert all(a["estado"] == "PENDIENTE" for a in res.data)

    def test_resolver_alerta(self, db, api_client):
        alerta = AlertaStockFactory()
        res = api_client.post(f"{ALERTAS_URL}{alerta.id}/resolver/")
        assert res.status_code == 200
        alerta.refresh_from_db()
        assert alerta.estado == EstadoAlerta.RESUELTA
        assert alerta.fecha_resolucion is not None

    def test_ignorar_alerta_pendiente(self, db, api_client):
        alerta = AlertaStockFactory(estado=EstadoAlerta.PENDIENTE)
        res = api_client.post(f"{ALERTAS_URL}{alerta.id}/ignorar/")
        assert res.status_code == 200
        alerta.refresh_from_db()
        assert alerta.estado == EstadoAlerta.IGNORADA

    def test_ignorar_alerta_resuelta_falla(self, db, api_client):
        alerta = AlertaStockFactory(estado=EstadoAlerta.RESUELTA)
        res = api_client.post(f"{ALERTAS_URL}{alerta.id}/ignorar/")
        assert res.status_code == 400

    def test_no_permite_post(self, db, api_client):
        res = api_client.post(ALERTAS_URL, {})
        assert res.status_code == 405

    def test_no_permite_delete(self, db, api_client):
        alerta = AlertaStockFactory()
        res = api_client.delete(f"{ALERTAS_URL}{alerta.id}/")
        assert res.status_code == 405


# ═══════════════════════════════════════════════════════════════════════════════
# MovimientoInventario
# ═══════════════════════════════════════════════════════════════════════════════

class TestMovimientoInventarioViewSet:

    def test_listar_movimientos(self, db, api_client, ingrediente_inv):
        api_client.post(f"/api/inventory/stock/{ingrediente_inv.id}/ajustar/", {
            "cantidad": "5.000",
            "descripcion": "Ajuste de prueba para movimiento"
        })
        res = api_client.get(MOVIMIENTOS_URL)
        assert res.status_code == 200
        assert len(res.data) >= 1

    def test_filtrar_por_tipo(self, db, api_client, ingrediente_inv):
        api_client.post(f"/api/inventory/stock/{ingrediente_inv.id}/ajustar/", {
            "cantidad": "5.000",
            "descripcion": "Ajuste de prueba para filtrar tipo"
        })
        res = api_client.get(f"{MOVIMIENTOS_URL}?tipo=AJUSTE")
        assert res.status_code == 200
        assert all(m["tipo_movimiento"] == "AJUSTE" for m in res.data)

    def test_no_permite_post(self, db, api_client):
        res = api_client.post(MOVIMIENTOS_URL, {})
        assert res.status_code == 405

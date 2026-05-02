# tests/unit/test_serializers.py
import uuid
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from app.inventory.serializers import (
    ProveedorSerializer,
    AlmacenWriteSerializer,
    IngredienteInventarioWriteSerializer,
    IngredienteInventarioNivelesSerializer,
    AjusteStockSerializer,
    LoteIngredienteWriteSerializer,
    DetalleOrdenCompraWriteSerializer,
    OrdenCompraWriteSerializer,
    RecibirOrdenSerializer,
)
from tests.conftest import (
    AlmacenFactory, ProveedorFactory, IngredienteInventarioFactory,
    LoteIngredienteFactory, OrdenCompraFactory,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Proveedor
# ═══════════════════════════════════════════════════════════════════════════════

class TestProveedorSerializer:

    def test_datos_validos_global(self, db):
        data = {"nombre": "Dist. Nacional", "pais": "Colombia",
                "alcance": "GLOBAL", "moneda_preferida": "COP"}
        s = ProveedorSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_nombre_vacio_falla(self, db):
        data = {"nombre": "   ", "pais": "Colombia", "alcance": "GLOBAL"}
        s = ProveedorSerializer(data=data)
        assert not s.is_valid()
        assert "nombre" in s.errors

    def test_nombre_se_limpia(self, db):
        data = {"nombre": "  Dist. Sur  ",
                "pais": "Colombia", "alcance": "GLOBAL"}
        s = ProveedorSerializer(data=data)
        assert s.is_valid(), s.errors
        assert s.validated_data["nombre"] == "Dist. Sur"

    def test_alcance_pais_sin_pais_destino_falla(self, db):
        data = {"nombre": "Dist.", "pais": "Colombia",
                "alcance": "PAIS", "pais_destino": None}
        s = ProveedorSerializer(data=data)
        assert not s.is_valid()

    def test_alcance_ciudad_sin_ciudad_destino_falla(self, db):
        data = {"nombre": "Dist.", "pais": "Colombia",
                "alcance": "CIUDAD", "pais_destino": "Colombia",
                "ciudad_destino": None}
        s = ProveedorSerializer(data=data)
        assert not s.is_valid()

    def test_alcance_local_sin_restaurante_falla(self, db):
        data = {"nombre": "Dist.", "pais": "Colombia",
                "alcance": "LOCAL", "creado_por_restaurante_id": None}
        s = ProveedorSerializer(data=data)
        assert not s.is_valid()

    def test_alcance_local_valido(self, db):
        data = {"nombre": "Dist.", "pais": "Colombia",
                "alcance": "LOCAL",
                "creado_por_restaurante_id": str(uuid.uuid4())}
        s = ProveedorSerializer(data=data)
        assert s.is_valid(), s.errors


# ═══════════════════════════════════════════════════════════════════════════════
# AlmacenWriteSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlmacenWriteSerializer:

    def test_datos_validos(self, db):
        data = {"restaurante_id": str(uuid.uuid4()),
                "nombre": "Bodega Principal"}
        s = AlmacenWriteSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_nombre_vacio_falla(self, db):
        data = {"restaurante_id": str(uuid.uuid4()), "nombre": "  "}
        s = AlmacenWriteSerializer(data=data)
        assert not s.is_valid()
        assert "nombre" in s.errors


# ═══════════════════════════════════════════════════════════════════════════════
# IngredienteInventarioWriteSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestIngredienteInventarioWriteSerializer:

    def test_datos_validos(self, db):
        almacen = AlmacenFactory()
        data = {
            "ingrediente_id": str(uuid.uuid4()),
            "nombre_ingrediente": "Arroz",
            "almacen": almacen.id,
            "unidad_medida": "kg",
            "cantidad_actual": "50.000",
            "nivel_minimo": "10.000",
            "nivel_maximo": "200.000",
        }
        s = IngredienteInventarioWriteSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_nivel_maximo_menor_minimo_falla(self, db):
        almacen = AlmacenFactory()
        data = {
            "ingrediente_id": str(uuid.uuid4()),
            "nombre_ingrediente": "Arroz",
            "almacen": almacen.id,
            "unidad_medida": "kg",
            "cantidad_actual": "50.000",
            "nivel_minimo": "100.000",
            "nivel_maximo": "50.000",
        }
        s = IngredienteInventarioWriteSerializer(data=data)
        assert not s.is_valid()
        assert "nivel_maximo" in s.errors

    def test_cantidad_negativa_falla(self, db):
        almacen = AlmacenFactory()
        data = {
            "ingrediente_id": str(uuid.uuid4()),
            "nombre_ingrediente": "Arroz",
            "almacen": almacen.id,
            "unidad_medida": "kg",
            "cantidad_actual": "-1.000",
            "nivel_minimo": "10.000",
            "nivel_maximo": "200.000",
        }
        s = IngredienteInventarioWriteSerializer(data=data)
        assert not s.is_valid()


# ═══════════════════════════════════════════════════════════════════════════════
# AjusteStockSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestAjusteStockSerializer:

    def test_ajuste_positivo_valido(self):
        s = AjusteStockSerializer(
            data={"cantidad": "10.000", "descripcion": "Ajuste por inventario físico"})
        assert s.is_valid(), s.errors

    def test_ajuste_negativo_valido(self):
        s = AjusteStockSerializer(
            data={"cantidad": "-5.000",
                  "descripcion": "Ajuste por merma en producción"})
        assert s.is_valid(), s.errors

    def test_cantidad_cero_falla(self):
        s = AjusteStockSerializer(
            data={"cantidad": "0", "descripcion": "Descripción suficiente"})
        assert not s.is_valid()
        assert "cantidad" in s.errors

    def test_descripcion_corta_falla(self):
        s = AjusteStockSerializer(
            data={"cantidad": "5.000", "descripcion": "corta"})
        assert not s.is_valid()
        assert "descripcion" in s.errors


# ═══════════════════════════════════════════════════════════════════════════════
# LoteIngredienteWriteSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoteIngredienteWriteSerializer:

    def test_datos_validos(self, db):
        almacen = AlmacenFactory()
        proveedor = ProveedorFactory()
        data = {
            "ingrediente_id": str(uuid.uuid4()),
            "almacen": almacen.id,
            "proveedor": proveedor.id,
            "numero_lote": "LOTE-001",
            "fecha_vencimiento": (date.today() + timedelta(days=90)).isoformat(),
            "cantidad_recibida": "50.000",
            "unidad_medida": "kg",
        }
        s = LoteIngredienteWriteSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_fecha_vencimiento_pasada_falla(self, db):
        almacen = AlmacenFactory()
        proveedor = ProveedorFactory()
        data = {
            "ingrediente_id": str(uuid.uuid4()),
            "almacen": almacen.id,
            "proveedor": proveedor.id,
            "numero_lote": "LOTE-001",
            "fecha_vencimiento": (date.today() - timedelta(days=1)).isoformat(),
            "cantidad_recibida": "50.000",
            "unidad_medida": "kg",
        }
        s = LoteIngredienteWriteSerializer(data=data)
        assert not s.is_valid()
        assert "fecha_vencimiento" in s.errors

    def test_cantidad_cero_falla(self, db):
        almacen = AlmacenFactory()
        proveedor = ProveedorFactory()
        data = {
            "ingrediente_id": str(uuid.uuid4()),
            "almacen": almacen.id,
            "proveedor": proveedor.id,
            "numero_lote": "LOTE-001",
            "fecha_vencimiento": (date.today() + timedelta(days=90)).isoformat(),
            "cantidad_recibida": "0.000",
            "unidad_medida": "kg",
        }
        s = LoteIngredienteWriteSerializer(data=data)
        assert not s.is_valid()
        assert "cantidad_recibida" in s.errors

    def test_fecha_venc_anterior_produccion_falla(self, db):
        almacen = AlmacenFactory()
        proveedor = ProveedorFactory()
        hoy = date.today()
        data = {
            "ingrediente_id": str(uuid.uuid4()),
            "almacen": almacen.id,
            "proveedor": proveedor.id,
            "numero_lote": "LOTE-001",
            "fecha_produccion": (hoy + timedelta(days=10)).isoformat(),
            "fecha_vencimiento": (hoy + timedelta(days=5)).isoformat(),
            "cantidad_recibida": "10.000",
            "unidad_medida": "kg",
        }
        s = LoteIngredienteWriteSerializer(data=data)
        assert not s.is_valid()
        assert "fecha_vencimiento" in s.errors

    def test_create_setea_cantidad_actual(self, db):
        almacen = AlmacenFactory()
        proveedor = ProveedorFactory()
        data = {
            "ingrediente_id": str(uuid.uuid4()),
            "almacen": almacen.id,
            "proveedor": proveedor.id,
            "numero_lote": "LOTE-001",
            "fecha_vencimiento": (date.today() + timedelta(days=90)).isoformat(),
            "cantidad_recibida": "75.000",
            "unidad_medida": "kg",
        }
        s = LoteIngredienteWriteSerializer(data=data)
        assert s.is_valid(), s.errors
        lote = s.save()
        assert lote.cantidad_actual == Decimal("75.000")


# ═══════════════════════════════════════════════════════════════════════════════
# OrdenCompraWriteSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrdenCompraWriteSerializer:

    def _base_data(self, proveedor):
        return {
            "proveedor": proveedor.id,
            "restaurante_id": str(uuid.uuid4()),
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

    def test_datos_validos(self, db):
        proveedor = ProveedorFactory()
        s = OrdenCompraWriteSerializer(data=self._base_data(proveedor))
        assert s.is_valid(), s.errors

    def test_sin_detalles_falla(self, db):
        proveedor = ProveedorFactory()
        data = self._base_data(proveedor)
        data["detalles"] = []
        s = OrdenCompraWriteSerializer(data=data)
        assert not s.is_valid()
        assert "detalles" in s.errors

    def test_fecha_entrega_pasada_falla(self, db):
        proveedor = ProveedorFactory()
        data = self._base_data(proveedor)
        data["fecha_entrega_estimada"] = (
            timezone.now() - __import__('datetime').timedelta(hours=1)
        ).isoformat()
        s = OrdenCompraWriteSerializer(data=data)
        assert not s.is_valid()
        assert "fecha_entrega_estimada" in s.errors

    def test_create_calcula_total(self, db):
        proveedor = ProveedorFactory()
        data = self._base_data(proveedor)
        s = OrdenCompraWriteSerializer(data=data)
        assert s.is_valid(), s.errors
        orden = s.save()
        # 10 * 3000 = 30000
        assert orden.total_estimado == Decimal("30000.00")

    def test_detalle_precio_cero_falla(self, db):
        proveedor = ProveedorFactory()
        data = self._base_data(proveedor)
        data["detalles"][0]["precio_unitario"] = "0.00"
        s = OrdenCompraWriteSerializer(data=data)
        assert not s.is_valid()

    def test_detalle_cantidad_cero_falla(self, db):
        proveedor = ProveedorFactory()
        data = self._base_data(proveedor)
        data["detalles"][0]["cantidad"] = "0.000"
        s = OrdenCompraWriteSerializer(data=data)
        assert not s.is_valid()


# ═══════════════════════════════════════════════════════════════════════════════
# RecibirOrdenSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecibirOrdenSerializer:

    def test_datos_validos(self, db):
        detalle_id = str(uuid.uuid4())
        data = {
            "detalles": [
                {
                    "detalle_id": detalle_id,
                    "cantidad_recibida": "10.000",
                    "numero_lote": "LOTE-001",
                    "fecha_vencimiento": (
                        date.today() + timedelta(days=90)).isoformat(),
                }
            ]
        }
        s = RecibirOrdenSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_sin_detalles_falla(self):
        s = RecibirOrdenSerializer(data={"detalles": []})
        assert not s.is_valid()
        assert "detalles" in s.errors

    def test_fecha_vencimiento_pasada_falla(self):
        data = {
            "detalles": [
                {
                    "detalle_id": str(uuid.uuid4()),
                    "cantidad_recibida": "10.000",
                    "numero_lote": "LOTE-001",
                    "fecha_vencimiento": (
                        date.today() - timedelta(days=1)).isoformat(),
                }
            ]
        }
        s = RecibirOrdenSerializer(data=data)
        assert not s.is_valid()

    def test_cantidad_negativa_falla(self):
        data = {
            "detalles": [
                {
                    "detalle_id": str(uuid.uuid4()),
                    "cantidad_recibida": "-5.000",
                    "numero_lote": "LOTE-001",
                    "fecha_vencimiento": (
                        date.today() + timedelta(days=90)).isoformat(),
                }
            ]
        }
        s = RecibirOrdenSerializer(data=data)
        assert not s.is_valid()

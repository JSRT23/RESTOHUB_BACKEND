# tests/conftest.py
import uuid
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.utils import timezone
from rest_framework.test import APIClient

import factory
from factory.django import DjangoModelFactory

from app.inventory.models import (
    Proveedor, Almacen, IngredienteInventario, LoteIngrediente,
    MovimientoInventario, OrdenCompra, DetalleOrdenCompra,
    AlertaStock, RecetaPlato, Ingrediente,
    UnidadMedida, EstadoLote, EstadoOrdenCompra,
    TipoMovimiento, TipoAlerta, EstadoAlerta, Moneda, AlcanceProveedor,
)


# ── Factories ─────────────────────────────────────────────────────────────────

class ProveedorFactory(DjangoModelFactory):
    class Meta:
        model = Proveedor

    id = factory.LazyFunction(uuid.uuid4)
    nombre = factory.Sequence(lambda n: f"Proveedor {n}")
    pais = "Colombia"
    ciudad = "Bogotá"
    telefono = "3001234567"
    email = factory.Sequence(lambda n: f"proveedor{n}@test.com")
    moneda_preferida = Moneda.COP
    activo = True
    alcance = AlcanceProveedor.GLOBAL


class AlmacenFactory(DjangoModelFactory):
    class Meta:
        model = Almacen

    id = factory.LazyFunction(uuid.uuid4)
    restaurante_id = factory.LazyFunction(uuid.uuid4)
    nombre = factory.Sequence(lambda n: f"Almacén {n}")
    descripcion = "Almacén de prueba"
    activo = True


class IngredienteInventarioFactory(DjangoModelFactory):
    class Meta:
        model = IngredienteInventario

    id = factory.LazyFunction(uuid.uuid4)
    ingrediente_id = factory.LazyFunction(uuid.uuid4)
    almacen = factory.SubFactory(AlmacenFactory)
    nombre_ingrediente = factory.Sequence(lambda n: f"Ingrediente {n}")
    unidad_medida = UnidadMedida.KILOGRAMO
    cantidad_actual = Decimal("50.000")
    nivel_minimo = Decimal("10.000")
    nivel_maximo = Decimal("200.000")


class LoteIngredienteFactory(DjangoModelFactory):
    class Meta:
        model = LoteIngrediente

    id = factory.LazyFunction(uuid.uuid4)
    ingrediente_id = factory.LazyFunction(uuid.uuid4)
    almacen = factory.SubFactory(AlmacenFactory)
    proveedor = factory.SubFactory(ProveedorFactory)
    numero_lote = factory.Sequence(lambda n: f"LOTE-{n:04d}")
    fecha_produccion = factory.LazyFunction(
        lambda: timezone.now().date() - timedelta(days=30))
    fecha_vencimiento = factory.LazyFunction(
        lambda: timezone.now().date() + timedelta(days=180))
    cantidad_recibida = Decimal("100.000")
    cantidad_actual = Decimal("100.000")
    unidad_medida = UnidadMedida.KILOGRAMO
    estado = EstadoLote.ACTIVO


class OrdenCompraFactory(DjangoModelFactory):
    class Meta:
        model = OrdenCompra

    id = factory.LazyFunction(uuid.uuid4)
    proveedor = factory.SubFactory(ProveedorFactory)
    restaurante_id = factory.LazyFunction(uuid.uuid4)
    estado = EstadoOrdenCompra.BORRADOR
    moneda = Moneda.COP
    total_estimado = Decimal("0.00")


class DetalleOrdenCompraFactory(DjangoModelFactory):
    class Meta:
        model = DetalleOrdenCompra

    id = factory.LazyFunction(uuid.uuid4)
    orden = factory.SubFactory(OrdenCompraFactory)
    ingrediente_id = factory.LazyFunction(uuid.uuid4)
    nombre_ingrediente = factory.Sequence(lambda n: f"Ingrediente {n}")
    unidad_medida = UnidadMedida.KILOGRAMO
    cantidad = Decimal("10.000")
    cantidad_recibida = Decimal("0.000")
    precio_unitario = Decimal("5000.00")
    subtotal = Decimal("50000.00")


class AlertaStockFactory(DjangoModelFactory):
    class Meta:
        model = AlertaStock

    id = factory.LazyFunction(uuid.uuid4)
    ingrediente_inventario = factory.SubFactory(IngredienteInventarioFactory)
    almacen = factory.LazyAttribute(
        lambda o: o.ingrediente_inventario.almacen)
    restaurante_id = factory.LazyAttribute(
        lambda o: o.almacen.restaurante_id)
    ingrediente_id = factory.LazyAttribute(
        lambda o: o.ingrediente_inventario.ingrediente_id)
    tipo_alerta = TipoAlerta.STOCK_BAJO
    estado = EstadoAlerta.PENDIENTE
    nivel_actual = Decimal("5.000")
    nivel_minimo = Decimal("10.000")


class RecetaPlatoFactory(DjangoModelFactory):
    class Meta:
        model = RecetaPlato

    id = factory.LazyFunction(uuid.uuid4)
    plato_id = factory.LazyFunction(uuid.uuid4)
    ingrediente_id = factory.LazyFunction(uuid.uuid4)
    nombre_ingrediente = factory.Sequence(lambda n: f"Ingrediente receta {n}")
    cantidad = Decimal("0.500")
    unidad_medida = UnidadMedida.KILOGRAMO
    costo_unitario = Decimal("8000.0000")


class IngredienteCacheFactory(DjangoModelFactory):
    class Meta:
        model = Ingrediente

    id = factory.LazyFunction(uuid.uuid4)
    ingrediente_id = factory.LazyFunction(uuid.uuid4)
    nombre = factory.Sequence(lambda n: f"Ingrediente cache {n}")
    unidad_medida = UnidadMedida.KILOGRAMO
    activo = True


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def proveedor(db):
    return ProveedorFactory()


@pytest.fixture
def almacen(db):
    return AlmacenFactory()


@pytest.fixture
def ingrediente_inv(db, almacen):
    return IngredienteInventarioFactory(almacen=almacen)


@pytest.fixture
def lote(db, almacen, proveedor):
    return LoteIngredienteFactory(almacen=almacen, proveedor=proveedor)


@pytest.fixture
def orden(db, proveedor):
    return OrdenCompraFactory(proveedor=proveedor)


@pytest.fixture
def orden_enviada(db, proveedor):
    return OrdenCompraFactory(proveedor=proveedor, estado=EstadoOrdenCompra.ENVIADA)


# ── Mock publisher (evita conexión a RabbitMQ en todos los tests) ─────────────

@pytest.fixture(autouse=True)
def mock_publisher(mocker):
    mock = MagicMock()
    mock.publish = MagicMock(return_value=None)
    mocker.patch(
        "app.inventory.views.get_publisher",
        return_value=mock,
    )
    return mock

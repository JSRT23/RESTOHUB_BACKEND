# tests/conftest.py
import uuid
import pytest
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APIClient

import factory
from factory.django import DjangoModelFactory

from app.orders.models import (
    Pedido, DetallePedido, ComandaCocina,
    SeguimientoPedido, EntregaPedido,
    CanalPedido, EstadoPedido, EstadoComanda,
    EstacionCocina, TipoEntrega, EstadoEntrega,
    MetodoPago, PrioridadPedido,
)


# ── Factories ─────────────────────────────────────────────────────────────────

class PedidoFactory(DjangoModelFactory):
    class Meta:
        model = Pedido

    id = factory.LazyFunction(uuid.uuid4)
    restaurante_id = factory.LazyFunction(uuid.uuid4)
    cliente_id = None
    canal = CanalPedido.TPV
    estado = EstadoPedido.RECIBIDO
    prioridad = PrioridadPedido.NORMAL
    total = Decimal("15000.00")
    moneda = "COP"
    mesa_id = None
    metodo_pago = None
    numero_dia = 1

    @classmethod
    def en_preparacion(cls, **kwargs):
        return cls(estado=EstadoPedido.EN_PREPARACION, **kwargs)

    @classmethod
    def listo(cls, **kwargs):
        return cls(estado=EstadoPedido.LISTO, **kwargs)

    @classmethod
    def entregado(cls, **kwargs):
        return cls(estado=EstadoPedido.ENTREGADO, **kwargs)

    @classmethod
    def cancelado(cls, **kwargs):
        return cls(estado=EstadoPedido.CANCELADO, **kwargs)

    @classmethod
    def en_camino(cls, **kwargs):
        return cls(estado=EstadoPedido.EN_CAMINO, **kwargs)


class DetallePedidoFactory(DjangoModelFactory):
    class Meta:
        model = DetallePedido

    id = factory.LazyFunction(uuid.uuid4)
    pedido = factory.SubFactory(PedidoFactory)
    plato_id = factory.LazyFunction(uuid.uuid4)
    nombre_plato = factory.Sequence(lambda n: f"Plato {n}")
    precio_unitario = Decimal("5000.00")
    cantidad = 1
    subtotal = Decimal("5000.00")
    notas = None


class ComandaCocinaFactory(DjangoModelFactory):
    class Meta:
        model = ComandaCocina

    id = factory.LazyFunction(uuid.uuid4)
    pedido = factory.SubFactory(PedidoFactory)
    estacion = EstacionCocina.GENERAL
    estado = EstadoComanda.PENDIENTE
    hora_fin = None

    @classmethod
    def preparando(cls, **kwargs):
        return cls(estado=EstadoComanda.PREPARANDO, **kwargs)

    @classmethod
    def lista(cls, **kwargs):
        return cls(
            estado=EstadoComanda.LISTO,
            hora_fin=timezone.now(),
            **kwargs,
        )


class EntregaPedidoFactory(DjangoModelFactory):
    class Meta:
        model = EntregaPedido

    id = factory.LazyFunction(uuid.uuid4)
    pedido = factory.SubFactory(PedidoFactory)
    tipo_entrega = TipoEntrega.LOCAL
    direccion = None
    repartidor_id = None
    repartidor_nombre = None
    estado_entrega = EstadoEntrega.PENDIENTE
    fecha_salida = None
    fecha_entrega_real = None

    @classmethod
    def en_camino(cls, **kwargs):
        return cls(
            estado_entrega=EstadoEntrega.EN_CAMINO,
            fecha_salida=timezone.now(),
            **kwargs,
        )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def pedido(db):
    return PedidoFactory()


@pytest.fixture
def pedido_con_detalle(db):
    p = PedidoFactory()
    DetallePedidoFactory(pedido=p)
    return p


@pytest.fixture
def pedido_en_preparacion(db):
    return PedidoFactory.en_preparacion()


@pytest.fixture
def pedido_listo(db):
    return PedidoFactory.listo()


@pytest.fixture
def pedido_entregado(db):
    return PedidoFactory.entregado()


@pytest.fixture
def pedido_cancelado(db):
    return PedidoFactory.cancelado()


@pytest.fixture
def comanda(db, pedido_en_preparacion):
    return ComandaCocinaFactory(pedido=pedido_en_preparacion)


@pytest.fixture
def comanda_preparando(db, pedido_en_preparacion):
    return ComandaCocinaFactory.preparando(pedido=pedido_en_preparacion)


@pytest.fixture
def entrega(db, pedido_listo):
    return EntregaPedidoFactory(pedido=pedido_listo)


@pytest.fixture
def entrega_en_camino(db):
    pedido = PedidoFactory.en_camino()
    return EntregaPedidoFactory.en_camino(pedido=pedido)


@pytest.fixture
def make_pedido(db):
    """Fixture-factory para crear pedidos con parámetros custom."""
    def _make(**kwargs):
        return PedidoFactory(**kwargs)
    return _make


# ── Mock global de RabbitMQ ───────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_rabbitmq(mocker):
    """Evita conexiones reales a RabbitMQ en todos los tests."""
    mock_pub = mocker.MagicMock()
    mock_pub.publish = mocker.MagicMock(return_value=None)
    mocker.patch(
        "app.orders.signals.get_publisher",
        return_value=mock_pub,
    )
    # También parchear el publisher directamente
    try:
        mocker.patch(
            "app.orders.infrastructure.messaging.publisher.get_publisher",
            return_value=mock_pub,
        )
    except Exception:
        pass

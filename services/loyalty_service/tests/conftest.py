# tests/conftest.py
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

import factory
from factory.django import DjangoModelFactory

from app.loyalty.models import (
    CuentaPuntos, TransaccionPuntos, Promocion, ReglaPromocion,
    AplicacionPromocion, Cupon, CatalogoPlato, CatalogoCategoria,
    NivelCliente, TipoTransaccion, AlcancePromocion, TipoBeneficio,
    TipoDescuentoCupon,
)


# ── Factories ──────────────────────────────────────────────────────────────────

class CuentaPuntosFactory(DjangoModelFactory):
    class Meta:
        model = CuentaPuntos

    id = factory.LazyFunction(uuid.uuid4)
    cliente_id = factory.LazyFunction(uuid.uuid4)
    saldo = 500
    puntos_totales_historicos = 500
    nivel = NivelCliente.BRONCE

    @classmethod
    def con_saldo(cls, saldo, **kwargs):
        return cls(saldo=saldo, puntos_totales_historicos=saldo, **kwargs)

    @classmethod
    def plata(cls, **kwargs):
        return cls(saldo=1500, puntos_totales_historicos=1500,
                   nivel=NivelCliente.PLATA, **kwargs)

    @classmethod
    def oro(cls, **kwargs):
        return cls(saldo=6000, puntos_totales_historicos=6000,
                   nivel=NivelCliente.ORO, **kwargs)


class TransaccionPuntosFactory(DjangoModelFactory):
    class Meta:
        model = TransaccionPuntos

    id = factory.LazyFunction(uuid.uuid4)
    cuenta = factory.SubFactory(CuentaPuntosFactory)
    tipo = TipoTransaccion.ACUMULACION
    puntos = 100
    saldo_anterior = 0
    saldo_posterior = 100
    descripcion = "Test"


class PromocionFactory(DjangoModelFactory):
    class Meta:
        model = Promocion

    id = factory.LazyFunction(uuid.uuid4)
    nombre = factory.Sequence(lambda n: f"Promo {n}")
    alcance = AlcancePromocion.GLOBAL
    tipo_beneficio = TipoBeneficio.DESCUENTO_PORCENTAJE
    valor = Decimal("10.00")
    puntos_bonus = 0
    multiplicador_puntos = Decimal("1.0")
    fecha_inicio = factory.LazyFunction(
        lambda: timezone.now() - timedelta(days=1))
    fecha_fin = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=30))
    activa = True

    @classmethod
    def inactiva(cls, **kwargs):
        return cls(activa=False, **kwargs)

    @classmethod
    def expirada(cls, **kwargs):
        return cls(
            fecha_inicio=timezone.now() - timedelta(days=60),
            fecha_fin=timezone.now() - timedelta(days=1),
            **kwargs,
        )

    @classmethod
    def local(cls, restaurante_id=None, **kwargs):
        return cls(
            alcance=AlcancePromocion.LOCAL,
            restaurante_id=restaurante_id or uuid.uuid4(),
            **kwargs,
        )

    @classmethod
    def puntos_extra(cls, puntos=200, **kwargs):
        return cls(
            tipo_beneficio=TipoBeneficio.PUNTOS_EXTRA,
            puntos_bonus=puntos,
            valor=Decimal("0"),
            **kwargs,
        )


class ReglaPromocionFactory(DjangoModelFactory):
    class Meta:
        model = ReglaPromocion

    id = factory.LazyFunction(uuid.uuid4)
    promocion = factory.SubFactory(PromocionFactory)
    tipo_condicion = "monto_minimo"
    monto_minimo = Decimal("20000")
    moneda = "COP"


class AplicacionPromocionFactory(DjangoModelFactory):
    class Meta:
        model = AplicacionPromocion

    id = factory.LazyFunction(uuid.uuid4)
    promocion = factory.SubFactory(PromocionFactory)
    pedido_id = factory.LazyFunction(uuid.uuid4)
    cliente_id = factory.LazyFunction(uuid.uuid4)
    descuento_aplicado = Decimal("5000")
    puntos_bonus_otorgados = 0


class CuponFactory(DjangoModelFactory):
    class Meta:
        model = Cupon

    id = factory.LazyFunction(uuid.uuid4)
    codigo = factory.Sequence(lambda n: f"TEST{n:04d}")
    tipo_descuento = TipoDescuentoCupon.PORCENTAJE
    valor_descuento = Decimal("10.00")
    limite_uso = 1
    usos_actuales = 0
    fecha_inicio = factory.LazyFunction(lambda: date.today())
    fecha_fin = factory.LazyFunction(
        lambda: date.today() + timedelta(days=30))
    activo = True

    @classmethod
    def agotado(cls, **kwargs):
        return cls(usos_actuales=1, limite_uso=1, activo=False, **kwargs)

    @classmethod
    def expirado(cls, **kwargs):
        return cls(
            fecha_inicio=date.today() - timedelta(days=60),
            fecha_fin=date.today() - timedelta(days=1),
            **kwargs,
        )

    @classmethod
    def inactivo(cls, **kwargs):
        return cls(activo=False, **kwargs)


class CatalogoPlatoFactory(DjangoModelFactory):
    class Meta:
        model = CatalogoPlato

    id = factory.LazyFunction(uuid.uuid4)
    plato_id = factory.LazyFunction(uuid.uuid4)
    categoria_id = factory.LazyFunction(uuid.uuid4)
    nombre = factory.Sequence(lambda n: f"Plato {n}")
    activo = True


class CatalogoCategoriaFactory(DjangoModelFactory):
    class Meta:
        model = CatalogoCategoria

    id = factory.LazyFunction(uuid.uuid4)
    categoria_id = factory.LazyFunction(uuid.uuid4)
    nombre = factory.Sequence(lambda n: f"Categoría {n}")
    activo = True


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def cliente_id():
    return uuid.uuid4()


@pytest.fixture
def cuenta(db, cliente_id):
    return CuentaPuntosFactory(cliente_id=cliente_id)


@pytest.fixture
def cuenta_con_saldo(db, cliente_id):
    return CuentaPuntosFactory.con_saldo(1000, cliente_id=cliente_id)


@pytest.fixture
def promo_global(db):
    return PromocionFactory()


@pytest.fixture
def promo_inactiva(db):
    return PromocionFactory.inactiva()


@pytest.fixture
def cupon(db):
    return CuponFactory()


@pytest.fixture
def cupon_agotado(db):
    return CuponFactory.agotado()


@pytest.fixture
def cupon_expirado(db):
    return CuponFactory.expirado()


# ── Mock global RabbitMQ ───────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_rabbitmq(mocker):
    mock_pub = mocker.MagicMock()
    mock_pub.publish = mocker.MagicMock(return_value=None)
    mocker.patch(
        "app.loyalty.signals.get_publisher",
        return_value=mock_pub,
    )
    mocker.patch(
        "app.loyalty.infrastructure.messaging.publisher.get_publisher",
        return_value=mock_pub,
    )
    return mock_pub

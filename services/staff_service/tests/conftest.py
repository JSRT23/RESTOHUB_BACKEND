# tests/conftest.py
import uuid
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from django.utils import timezone
from rest_framework.test import APIClient

import factory
from factory.django import DjangoModelFactory

from app.staff.models import (
    RestauranteLocal,
    ConfiguracionLaboralPais,
    Empleado,
    Turno,
    RegistroAsistencia,
    EstacionCocina,
    AsignacionCocina,
    ServicioEntrega,
    AlertaOperacional,
    ResumenNomina,
    PrediccionPersonal,
    RolEmpleado,
    EstadoTurno,
    EstadoEntrega,
    TipoAlerta,
    NivelAlerta,
    FuentePrediccion,
)


# ── Factories ──────────────────────────────────────────────────────────────────

class RestauranteLocalFactory(DjangoModelFactory):
    class Meta:
        model = RestauranteLocal

    id = factory.LazyFunction(uuid.uuid4)
    restaurante_id = factory.LazyFunction(uuid.uuid4)
    nombre = factory.Sequence(lambda n: f"Restaurante {n}")
    pais = "CO"
    ciudad = "Bogotá"
    activo = True


class ConfiguracionLaboralPaisFactory(DjangoModelFactory):
    class Meta:
        model = ConfiguracionLaboralPais

    id = factory.LazyFunction(uuid.uuid4)
    pais = "CO"
    horas_max_diarias = 8
    horas_max_semanales = 48
    factor_hora_extra = Decimal("1.50")
    descanso_min_entre_turnos = 480
    horas_continuas_para_descanso = 6
    duracion_descanso_obligatorio = 30


class EmpleadoFactory(DjangoModelFactory):
    class Meta:
        model = Empleado

    id = factory.LazyFunction(uuid.uuid4)
    restaurante = factory.SubFactory(RestauranteLocalFactory)
    nombre = factory.Sequence(lambda n: f"Nombre{n}")
    apellido = factory.Sequence(lambda n: f"Apellido{n}")
    documento = factory.Sequence(lambda n: f"CC{n:08d}")
    email = factory.Sequence(lambda n: f"empleado{n}@test.com")
    telefono = "3001234567"
    rol = RolEmpleado.MESERO
    pais = "CO"
    fecha_contratacion = factory.LazyFunction(date.today)
    activo = True


class CocineroFactory(EmpleadoFactory):
    rol = RolEmpleado.COCINERO


class RepartidorFactory(EmpleadoFactory):
    rol = RolEmpleado.REPARTIDOR


class TurnoFactory(DjangoModelFactory):
    class Meta:
        model = Turno

    id = factory.LazyFunction(uuid.uuid4)
    empleado = factory.SubFactory(EmpleadoFactory)
    restaurante_id = factory.LazyFunction(uuid.uuid4)
    fecha_inicio = factory.LazyFunction(
        lambda: timezone.now() + timedelta(hours=1))
    fecha_fin = factory.LazyFunction(
        lambda: timezone.now() + timedelta(hours=9))
    estado = EstadoTurno.PROGRAMADO
    notas = ""


class RegistroAsistenciaFactory(DjangoModelFactory):
    class Meta:
        model = RegistroAsistencia

    id = factory.LazyFunction(uuid.uuid4)
    turno = factory.SubFactory(TurnoFactory, estado=EstadoTurno.ACTIVO)
    hora_entrada = factory.LazyFunction(timezone.now)
    hora_salida = None
    metodo_registro = "qr"
    horas_normales = Decimal("0.00")
    horas_extra = Decimal("0.00")


class EstacionCocinaFactory(DjangoModelFactory):
    class Meta:
        model = EstacionCocina

    id = factory.LazyFunction(uuid.uuid4)
    restaurante_id = factory.LazyFunction(uuid.uuid4)
    nombre = factory.Sequence(lambda n: f"Estacion {n}")
    capacidad_simultanea = 2
    activa = True


class AsignacionCocinaFactory(DjangoModelFactory):
    class Meta:
        model = AsignacionCocina

    id = factory.LazyFunction(uuid.uuid4)
    pedido_id = factory.LazyFunction(uuid.uuid4)
    comanda_id = factory.LazyFunction(uuid.uuid4)
    cocinero = factory.SubFactory(CocineroFactory)
    estacion = factory.SubFactory(EstacionCocinaFactory)
    completado_en = None
    sla_segundos = None


class ServicioEntregaFactory(DjangoModelFactory):
    class Meta:
        model = ServicioEntrega

    id = factory.LazyFunction(uuid.uuid4)
    pedido_id = factory.LazyFunction(uuid.uuid4)
    repartidor = factory.SubFactory(RepartidorFactory)
    estado = EstadoEntrega.ASIGNADA
    completado_en = None


class AlertaOperacionalFactory(DjangoModelFactory):
    class Meta:
        model = AlertaOperacional

    id = factory.LazyFunction(uuid.uuid4)
    restaurante_id = factory.LazyFunction(uuid.uuid4)
    tipo = TipoAlerta.STOCK_BAJO
    nivel = NivelAlerta.URGENTE
    mensaje = "Stock bajo de ingrediente"
    referencia_id = factory.LazyFunction(uuid.uuid4)
    resuelta = False


class ResumenNominaFactory(DjangoModelFactory):
    class Meta:
        model = ResumenNomina

    id = factory.LazyFunction(uuid.uuid4)
    empleado = factory.SubFactory(EmpleadoFactory)
    periodo_inicio = factory.LazyFunction(
        lambda: date.today().replace(day=1))
    periodo_fin = factory.LazyFunction(date.today)
    total_horas_normales = Decimal("40.00")
    total_horas_extra = Decimal("0.00")
    dias_trabajados = 5
    moneda = "COP"
    cerrado = False


class PrediccionPersonalFactory(DjangoModelFactory):
    class Meta:
        model = PrediccionPersonal

    id = factory.LazyFunction(uuid.uuid4)
    restaurante_id = factory.LazyFunction(uuid.uuid4)
    fecha = factory.LazyFunction(lambda: date.today() + timedelta(days=1))
    demanda_estimada = 100
    personal_recomendado = 5
    fuente = FuentePrediccion.HISTORIAL
    notas = ""


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def restaurante(db):
    return RestauranteLocalFactory()


@pytest.fixture
def config_laboral(db):
    return ConfiguracionLaboralPaisFactory()


@pytest.fixture
def empleado(db, restaurante):
    return EmpleadoFactory(restaurante=restaurante)


@pytest.fixture
def cocinero(db, restaurante):
    return CocineroFactory(restaurante=restaurante)


@pytest.fixture
def repartidor(db, restaurante):
    return RepartidorFactory(restaurante=restaurante)


@pytest.fixture
def turno(db, empleado):
    return TurnoFactory(empleado=empleado, restaurante_id=empleado.restaurante.restaurante_id)


@pytest.fixture
def turno_activo(db, empleado):
    return TurnoFactory(
        empleado=empleado,
        restaurante_id=empleado.restaurante.restaurante_id,
        estado=EstadoTurno.ACTIVO,
    )


@pytest.fixture
def estacion(db, restaurante):
    return EstacionCocinaFactory(restaurante_id=restaurante.restaurante_id)


# ── Mock global de RabbitMQ ───────────────────────────────────────────────────
# autouse=True → se aplica a TODOS los tests automáticamente.
# Evita que los signals de Django intenten conectar a RabbitMQ real,
# eliminando el spam de errores pika en la salida de tests.

@pytest.fixture(autouse=True)
def mock_rabbitmq(mocker):
    """
    Mockea get_publisher() para que los Django signals (publish_turno_event,
    publish_alerta_event, etc.) no intenten conectar a RabbitMQ en tests.
    """
    mocker.patch(
        "app.staff.infrastructure.messaging.publisher.get_publisher",
        return_value=None,
    )
    mocker.patch(
        "app.staff.signals.get_publisher",
        return_value=None,
    )
    # También parchear el publisher directamente por si el import es distinto
    mock_pub = mocker.MagicMock()
    mock_pub.publish = mocker.MagicMock(return_value=None)
    mocker.patch(
        "app.staff.infrastructure.messaging.publisher.EventPublisher",
        return_value=mock_pub,
    )

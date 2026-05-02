# tests/conftest.py
import pytest
from rest_framework.test import APIClient
from unittest.mock import MagicMock

from tests.factories import (
    RestauranteFactory, CategoriaFactory, IngredienteFactory,
    PlatoFactory, PrecioPlatoFactory, PlatoIngredienteFactory,
)


# ── Fixtures de modelos ───────────────────────────────────────────────────

@pytest.fixture
def restaurante(db):
    return RestauranteFactory()


@pytest.fixture
def restaurante2(db):
    return RestauranteFactory()


@pytest.fixture
def categoria(db):
    return CategoriaFactory()


@pytest.fixture
def ingrediente_global(db):
    return IngredienteFactory()


@pytest.fixture
def ingrediente_local(db, restaurante):
    return IngredienteFactory.local(restaurante=restaurante)


@pytest.fixture
def plato_global(db, categoria):
    return PlatoFactory(categoria=categoria)


@pytest.fixture
def plato_local(db, restaurante, categoria):
    return PlatoFactory.local(restaurante=restaurante, categoria=categoria)


@pytest.fixture
def precio(db, plato_global, restaurante):
    return PrecioPlatoFactory(plato=plato_global, restaurante=restaurante)


# ── APIClient ─────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


# ── Mock RabbitMQ ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_rabbitmq(mocker):
    """
    Mockea publicar_evento en todos los ViewSets automáticamente.
    Ningún test necesita RabbitMQ real.
    """
    return mocker.patch(
        "app.menu.infrastructure.messaging.mixins.publish_event."
        "PublicadorEventoMixin.publicar_evento",
        return_value=None,
    )

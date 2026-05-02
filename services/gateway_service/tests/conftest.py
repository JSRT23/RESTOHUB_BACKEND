# tests/conftest.py
import uuid
import pytest
import jwt
from graphene_django.views import GraphQLView
from django.test import RequestFactory

from app.gateway.graphql.schema import schema


# ── JWT helper ────────────────────────────────────────────────────────────

JWT_SECRET = "test-secret-key"
JWT_ALGO = "HS256"

ROLES = [
    "admin_central", "gerente_local", "supervisor",
    "cajero", "mesero", "cocinero", "repartidor",
]


def make_token(rol="admin_central", restaurante_id=None, **extra):
    """Genera un JWT válido firmado con la clave de tests."""
    payload = {
        "token_type":     "access",
        "user_id":        str(uuid.uuid4()),
        "email":          f"{rol}@test.com",
        "nombre":         f"Test {rol.title()}",
        "rol":            rol,
        "restaurante_id": str(restaurante_id) if restaurante_id else None,
        **extra,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def make_request(token=None, rol=None, restaurante_id=None):
    """
    Crea un Django Request con jwt_user inyectado directamente
    (simula lo que hace JWTMiddleware).
    """
    factory = RequestFactory()
    request = factory.post("/graphql/", content_type="application/json")
    if token:
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    if rol:
        request.jwt_user = {
            "token_type":     "access",
            "user_id":        str(uuid.uuid4()),
            "email":          f"{rol}@test.com",
            "nombre":         f"Test {rol.title()}",
            "rol":            rol,
            "restaurante_id": str(restaurante_id) if restaurante_id else None,
        }
    else:
        request.jwt_user = None
    return request


def gql(query, variables=None, rol=None, restaurante_id=None):
    """
    Ejecuta una operación GraphQL y retorna el resultado.
    Inyecta jwt_user según el rol pedido.
    """
    context = make_request(rol=rol, restaurante_id=restaurante_id)
    result = schema.execute(
        query, variable_values=variables or {}, context_value=context)
    return result


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def restaurante_id():
    return uuid.uuid4()


@pytest.fixture
def req_admin():
    return make_request(rol="admin_central")


@pytest.fixture
def req_gerente(restaurante_id):
    return make_request(rol="gerente_local", restaurante_id=restaurante_id)


@pytest.fixture
def req_supervisor(restaurante_id):
    return make_request(rol="supervisor", restaurante_id=restaurante_id)


@pytest.fixture
def req_cajero(restaurante_id):
    return make_request(rol="cajero", restaurante_id=restaurante_id)


@pytest.fixture
def req_cocinero(restaurante_id):
    return make_request(rol="cocinero", restaurante_id=restaurante_id)


@pytest.fixture
def req_anonimo():
    return make_request()

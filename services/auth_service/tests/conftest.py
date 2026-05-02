# tests/conftest.py
# Fixtures globales disponibles en TODOS los tests sin necesidad de importar.
# pytest los inyecta automáticamente por nombre de parámetro.

import pytest
from django.test import Client
from rest_framework.test import APIClient

from app.auth.tokens import generar_access_token, generar_refresh_token
from app.auth.models import RefreshToken

from .factories import (
    CodigoVerificacionFactory,
    RefreshTokenFactory,
    UsuarioFactory,
)


# ── Usuarios base ─────────────────────────────────────────────────────────────

@pytest.fixture
def usuario_admin(db):
    """Admin central — sin restaurante_id."""
    return UsuarioFactory.admin()


@pytest.fixture
def usuario_gerente(db):
    """Gerente local — con restaurante_id."""
    return UsuarioFactory.gerente()


@pytest.fixture
def usuario_mesero(db):
    """Mesero operativo — con restaurante_id."""
    return UsuarioFactory.mesero()


@pytest.fixture
def usuario_supervisor(db):
    return UsuarioFactory.supervisor()


@pytest.fixture
def usuario_no_verificado(db):
    """Usuario que no ha verificado su email."""
    return UsuarioFactory.no_verificado()


@pytest.fixture
def usuario_inactivo(db):
    """Usuario desactivado."""
    return UsuarioFactory.inactivo()


# ── APIClient autenticado ─────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    """APIClient sin autenticación — para endpoints públicos."""
    return APIClient()


@pytest.fixture
def client_admin(db, usuario_admin):
    """APIClient autenticado como admin_central."""
    client = APIClient()
    token = generar_access_token(usuario_admin)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def client_gerente(db, usuario_gerente):
    """APIClient autenticado como gerente_local."""
    client = APIClient()
    token = generar_access_token(usuario_gerente)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def client_mesero(db, usuario_mesero):
    """APIClient autenticado como mesero."""
    client = APIClient()
    token = generar_access_token(usuario_mesero)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


# ── Tokens ────────────────────────────────────────────────────────────────────

@pytest.fixture
def access_token_admin(db, usuario_admin):
    """JWT de acceso válido para admin."""
    return generar_access_token(usuario_admin)


@pytest.fixture
def access_token_gerente(db, usuario_gerente):
    return generar_access_token(usuario_gerente)


@pytest.fixture
def refresh_token_admin(db, usuario_admin):
    """RefreshToken en DB + string JWT para admin."""
    token_str, expira_at = generar_refresh_token(usuario_admin)
    rt = RefreshToken.objects.create(
        usuario=usuario_admin,
        token=token_str,
        expira_at=expira_at,
    )
    return token_str   # string del JWT — el objeto ORM lo encuentra la view


# ── Códigos de verificación ───────────────────────────────────────────────────

@pytest.fixture
def codigo_valido(db, usuario_no_verificado):
    """Código activo, no expirado, 0 intentos."""
    return CodigoVerificacionFactory(usuario=usuario_no_verificado)


@pytest.fixture
def codigo_expirado(db, usuario_no_verificado):
    return CodigoVerificacionFactory.expirado(usuario=usuario_no_verificado)


@pytest.fixture
def codigo_agotado(db, usuario_no_verificado):
    return CodigoVerificacionFactory.agotado(usuario=usuario_no_verificado)


# ── Helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture
def make_usuario(db):
    """
    Fixture-factory para crear usuarios con parámetros custom en el test.
    Uso: usuario = make_usuario(rol="cajero", activo=False)
    """
    def _make(**kwargs):
        return UsuarioFactory(**kwargs)
    return _make

# tests/factories.py
# factory_boy — crea objetos de prueba sin repetir código.
# Todos los factories usan la DB de tests (SQLite en memoria).

import uuid
from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from app.auth.models import (
    EmailVerificationCode,
    RefreshToken,
    Rol,
    Usuario,
)


class UsuarioFactory(DjangoModelFactory):
    """
    Crea un Usuario activo con email verificado por defecto.
    Uso:
        usuario = UsuarioFactory()
        admin   = UsuarioFactory(rol=Rol.ADMIN_CENTRAL)
        gerente = UsuarioFactory.gerente()
        mesero  = UsuarioFactory.mesero(restaurante_id=uuid.uuid4())
    """
    class Meta:
        model = Usuario

    id = factory.LazyFunction(uuid.uuid4)
    email = factory.Sequence(lambda n: f"usuario{n}@gmail.com")
    nombre = factory.Faker("name", locale="es_CO")
    rol = Rol.MESERO
    restaurante_id = factory.LazyFunction(uuid.uuid4)
    empleado_id = None
    activo = True
    email_verificado = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Asigna 'testpass123' por defecto o el valor pasado."""
        raw = extracted or "testpass123"
        obj.set_password(raw)
        if create:
            obj.save(update_fields=["password"])

    # ── Subfactories por rol ──────────────────────────────────────────────────

    @classmethod
    def admin(cls, **kwargs):
        return cls(
            rol=Rol.ADMIN_CENTRAL,
            restaurante_id=None,
            empleado_id=None,
            **kwargs,
        )

    @classmethod
    def gerente(cls, **kwargs):
        return cls(rol=Rol.GERENTE_LOCAL, **kwargs)

    @classmethod
    def supervisor(cls, **kwargs):
        return cls(rol=Rol.SUPERVISOR, **kwargs)

    @classmethod
    def cocinero(cls, **kwargs):
        return cls(rol=Rol.COCINERO, **kwargs)

    @classmethod
    def mesero(cls, **kwargs):
        return cls(rol=Rol.MESERO, **kwargs)

    @classmethod
    def cajero(cls, **kwargs):
        return cls(rol=Rol.CAJERO, **kwargs)

    @classmethod
    def no_verificado(cls, **kwargs):
        """Usuario que aún no ha verificado su email."""
        return cls(email_verificado=False, **kwargs)

    @classmethod
    def inactivo(cls, **kwargs):
        """Usuario desactivado."""
        return cls(activo=False, **kwargs)


class RefreshTokenFactory(DjangoModelFactory):
    """
    Crea un RefreshToken válido por defecto.
    Uso:
        rt         = RefreshTokenFactory(usuario=usuario)
        rt_exp     = RefreshTokenFactory.expirado(usuario=usuario)
        rt_rev     = RefreshTokenFactory.revocado(usuario=usuario)
    """
    class Meta:
        model = RefreshToken

    id = factory.LazyFunction(uuid.uuid4)
    usuario = factory.SubFactory(UsuarioFactory)
    token = factory.LazyFunction(lambda: str(uuid.uuid4()))
    revocado = False
    expira_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=7))

    @classmethod
    def expirado(cls, **kwargs):
        return cls(
            expira_at=timezone.now() - timedelta(seconds=1),
            **kwargs,
        )

    @classmethod
    def revocado(cls, **kwargs):
        return cls(revocado=True, **kwargs)


class UsuarioNoVerificadoFactory(UsuarioFactory):
    """Usuario que aún no ha verificado su email (para usar en SubFactory)."""
    email_verificado = False


class CodigoVerificacionFactory(DjangoModelFactory):
    """
    Crea un EmailVerificationCode válido por defecto.
    Uso:
        codigo       = CodigoVerificacionFactory(usuario=usuario)
        cod_expirado = CodigoVerificacionFactory.expirado(usuario=usuario)
        cod_agotado  = CodigoVerificacionFactory.agotado(usuario=usuario)
    """
    class Meta:
        model = EmailVerificationCode

    id = factory.LazyFunction(uuid.uuid4)
    usuario = factory.SubFactory(UsuarioNoVerificadoFactory)
    codigo = "123456"
    intentos = 0
    expira_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(minutes=10))

    @classmethod
    def expirado(cls, **kwargs):
        return cls(
            expira_at=timezone.now() - timedelta(seconds=1),
            **kwargs,
        )

    @classmethod
    def agotado(cls, **kwargs):
        """3 intentos fallidos → intentos_agotados = True."""
        return cls(intentos=3, **kwargs)

    @classmethod
    def un_intento(cls, **kwargs):
        return cls(intentos=1, **kwargs)

    @classmethod
    def dos_intentos(cls, **kwargs):
        return cls(intentos=2, **kwargs)

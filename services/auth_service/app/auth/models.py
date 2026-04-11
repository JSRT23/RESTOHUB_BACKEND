import random
import string
import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Rol(models.TextChoices):
    ADMIN_CENTRAL = "admin_central", "Admin Central"
    GERENTE_LOCAL = "gerente_local", "Gerente Local"
    SUPERVISOR = "supervisor",    "Supervisor"
    COCINERO = "cocinero",      "Cocinero"
    MESERO = "mesero",        "Mesero"
    CAJERO = "cajero",        "Cajero"
    REPARTIDOR = "repartidor",    "Repartidor"


ROLES_CON_RESTAURANTE = {
    Rol.GERENTE_LOCAL, Rol.SUPERVISOR, Rol.COCINERO,
    Rol.MESERO, Rol.CAJERO, Rol.REPARTIDOR,
}

ROLES_CON_EMPLEADO = {
    Rol.SUPERVISOR, Rol.COCINERO, Rol.MESERO,
    Rol.CAJERO, Rol.REPARTIDOR,
}


def _generar_codigo() -> str:
    """Genera un código numérico de 6 dígitos."""
    return "".join(random.choices(string.digits, k=6))


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("rol", Rol.ADMIN_CENTRAL)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("email_verificado", True)
        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Usuario del sistema RestoHub.

    Payload JWT según el rol:
    - admin_central  → {user_id, rol, email, nombre}
    - gerente_local  → + restaurante_id
    - operativos     → + restaurante_id + empleado_id
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=150)
    rol = models.CharField(
        max_length=20, choices=Rol.choices, default=Rol.MESERO)
    restaurante_id = models.UUIDField(null=True, blank=True)
    empleado_id = models.UUIDField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    email_verificado = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre", "rol"]

    class Meta:
        app_label = "auth_app"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.email} ({self.rol})"

    @property
    def is_active(self):
        return self.activo

    def get_jwt_payload(self) -> dict:
        payload = {
            "user_id": str(self.id),
            "rol":     self.rol,
            "nombre":  self.nombre,
            "email":   self.email,
        }
        if self.rol in ROLES_CON_RESTAURANTE and self.restaurante_id:
            payload["restaurante_id"] = str(self.restaurante_id)
        if self.rol in ROLES_CON_EMPLEADO and self.empleado_id:
            payload["empleado_id"] = str(self.empleado_id)
        return payload


class RefreshToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="refresh_tokens")
    token = models.TextField(unique=True)
    revocado = models.BooleanField(default=False)
    creado_at = models.DateTimeField(auto_now_add=True)
    expira_at = models.DateTimeField()

    class Meta:
        app_label = "auth_app"
        verbose_name = "Refresh Token"
        indexes = [models.Index(fields=["token"])]

    def __str__(self):
        return f"RT {self.usuario.email} — {'revocado' if self.revocado else 'activo'}"


class EmailVerificationCode(models.Model):
    """
    Código de 6 dígitos enviado al email del usuario para verificar su cuenta.

    Reglas:
    - Expira en 10 minutos
    - Máximo 3 intentos fallidos (para evitar fuerza bruta)
    - Se elimina al verificarse correctamente
    - Se puede reenviar (elimina el anterior y crea uno nuevo)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="verification_codes")
    codigo = models.CharField(max_length=6, default=_generar_codigo)
    intentos = models.PositiveSmallIntegerField(default=0)
    creado_at = models.DateTimeField(auto_now_add=True)
    expira_at = models.DateTimeField()

    class Meta:
        app_label = "auth_app"
        verbose_name = "Código de verificación de email"

    def save(self, *args, **kwargs):
        if not self.pk and not self.expira_at:
            self.expira_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    @property
    def ha_expirado(self) -> bool:
        return timezone.now() > self.expira_at

    @property
    def intentos_agotados(self) -> bool:
        return self.intentos >= 3

    def registrar_intento_fallido(self):
        self.intentos += 1
        self.save(update_fields=["intentos"])

    def __str__(self):
        estado = "expirado" if self.ha_expirado else f"intentos: {self.intentos}/3"
        return f"Código {self.usuario.email} — {estado}"

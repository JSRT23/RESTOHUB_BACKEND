# auth_service/app/auth_app/models.py
# FIX: get_jwt_payload ahora incluye cliente_id para rol=cliente
# Esto permite que el frontend use el cliente_id correcto en loyalty queries.
# Solo se cambia el método get_jwt_payload() — todo lo demás igual.

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
    CLIENTE = "cliente",       "Cliente App"


ROLES_CON_RESTAURANTE = {
    Rol.GERENTE_LOCAL, Rol.SUPERVISOR, Rol.COCINERO,
    Rol.MESERO, Rol.CAJERO, Rol.REPARTIDOR,
}

ROLES_CON_EMPLEADO = {
    Rol.SUPERVISOR, Rol.COCINERO, Rol.MESERO,
    Rol.CAJERO, Rol.REPARTIDOR,
}


def _generar_codigo() -> str:
    return "".join(random.choices(string.digits, k=6))


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio.")
        email = self.normalize_email(email).lower()
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

        # FIX: para clientes de la app, incluir el cliente_id en el JWT
        # Esto permite que el frontend use el ID correcto en loyalty queries.
        # El Cliente vinculado al usuario se busca por usuario_id.
        if self.rol == Rol.CLIENTE:
            try:
                cliente = Cliente.objects.filter(
                    usuario_id=self.id, activo=True
                ).first()
                if cliente:
                    payload["cliente_id"] = str(cliente.id)
            except Exception:
                pass

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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="verification_codes")
    codigo = models.CharField(max_length=6, default=_generar_codigo)
    intentos = models.PositiveSmallIntegerField(default=0)
    creado_at = models.DateTimeField(auto_now_add=True)
    expira_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "auth_app"
        verbose_name = "Código de verificación de email"

    def save(self, *args, **kwargs):
        if not self.expira_at:
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


class TipoDocumento(models.TextChoices):
    CEDULA_CIUDADANIA = "CC",  "Cédula de Ciudadanía"
    CEDULA_EXTRANJERIA = "CE",  "Cédula de Extranjería"
    PASAPORTE = "PA",  "Pasaporte"
    NIT = "NIT", "NIT"
    OTRO = "OT",  "Otro"


class Cliente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo_documento = models.CharField(
        max_length=5, choices=TipoDocumento.choices, default=TipoDocumento.CEDULA_CIUDADANIA)
    cedula = models.CharField(max_length=20, db_index=True)
    nombre = models.CharField(max_length=200)
    apellido = models.CharField(max_length=200, blank=True, default="")
    email = models.EmailField(blank=True, default="", db_index=True)
    telefono = models.CharField(max_length=20, blank=True, default="")
    usuario_id = models.UUIDField(null=True, blank=True, db_index=True)
    restaurante_id = models.UUIDField(null=True, blank=True, db_index=True)
    activo = models.BooleanField(default=True)
    notas = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "auth_app"
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nombre", "apellido"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_documento", "cedula", "restaurante_id"],
                name="unique_cliente_doc_restaurante",
            )
        ]
        indexes = [
            models.Index(fields=["cedula"],
                         name="cliente_cedula_idx"),
            models.Index(fields=["email"],
                         name="cliente_email_idx"),
            models.Index(fields=["restaurante_id", "cedula"],
                         name="cliente_rest_cedula_idx"),
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellido} · {self.tipo_documento} {self.cedula}"

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()

    @property
    def tiene_cuenta_app(self) -> bool:
        return self.usuario_id is not None

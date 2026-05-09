# auth_service/app/auth_app/serializers.py
# CAMBIO v3:
#   - RegistroSerializer: rol='cliente' no requiere restaurante_id
#     (los clientes de la app no pertenecen a un restaurante)
#   - Todo lo demás sin cambios respecto a v2.

from django.contrib.auth import authenticate
from rest_framework import serializers

from .email_validator import validar_email_completo
from .models import Cliente, Rol, TipoDocumento, Usuario, ROLES_CON_RESTAURANTE, ROLES_CON_EMPLEADO


def _check_email(email: str) -> str:
    ok, mensaje = validar_email_completo(email)
    if not ok:
        raise serializers.ValidationError(mensaje)
    return email.strip().lower()


# ── Serializers existentes ─────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Credenciales inválidas.")
        if not user.activo:
            raise serializers.ValidationError("Usuario desactivado.")
        data.pop("password")
        data["usuario"] = user
        return data


class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = [
            "email", "nombre", "password", "password_confirm",
            "rol", "restaurante_id", "empleado_id",
        ]

    def validate_email(self, value):
        return _check_email(value)

    def validate(self, data):
        if data["password"] != data.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )

        rol = data.get("rol")
        restaurante_id = data.get("restaurante_id")

        # rol='cliente' y 'admin_central' no requieren restaurante_id
        ROLES_SIN_RESTAURANTE = {Rol.CLIENTE, Rol.ADMIN_CENTRAL}

        if rol in ROLES_CON_RESTAURANTE and rol not in ROLES_SIN_RESTAURANTE:
            if not restaurante_id:
                raise serializers.ValidationError(
                    {"restaurante_id": f"El rol '{rol}' requiere restaurante_id."}
                )

        if rol in ROLES_SIN_RESTAURANTE and restaurante_id:
            raise serializers.ValidationError(
                {"restaurante_id": f"El rol '{rol}' no debe tener restaurante_id."}
            )

        return data

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            "id", "email", "nombre", "rol",
            "restaurante_id", "empleado_id", "activo",
            "email_verificado", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nuevo = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["password_nuevo"] != data["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        return data


# ── Cliente (sin cambios respecto a v2) ────────────────────────────────────

class ClienteSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    tiene_cuenta_app = serializers.BooleanField(read_only=True)
    tipo_documento_display = serializers.CharField(
        source="get_tipo_documento_display", read_only=True
    )

    class Meta:
        model = Cliente
        fields = (
            "id",
            "tipo_documento", "tipo_documento_display",
            "cedula",
            "nombre", "apellido", "nombre_completo",
            "email", "telefono",
            "restaurante_id", "usuario_id",
            "tiene_cuenta_app",
            "activo", "notas",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "nombre_completo", "tiene_cuenta_app",
            "tipo_documento_display", "created_at", "updated_at",
        )


class ClienteListSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    tiene_cuenta_app = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cliente
        fields = (
            "id", "tipo_documento", "cedula",
            "nombre", "apellido", "nombre_completo",
            "email", "telefono",
            "restaurante_id", "usuario_id",
            "tiene_cuenta_app", "activo",
            "created_at",
        )


class ClienteWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = (
            "tipo_documento", "cedula",
            "nombre", "apellido",
            "email", "telefono",
            "restaurante_id", "usuario_id",
            "activo", "notas",
        )

    def validate_cedula(self, value: str) -> str:
        return value.strip().upper()

    def validate_usuario_id(self, value):
        if value and not Usuario.objects.filter(id=value, activo=True).exists():
            raise serializers.ValidationError(
                "No existe un usuario activo con ese ID.")
        return value

    def validate(self, attrs):
        tipo_doc = attrs.get("tipo_documento",   getattr(
            self.instance, "tipo_documento",   None))
        cedula = attrs.get("cedula",            getattr(
            self.instance, "cedula",            None))
        restaurante_id = attrs.get("restaurante_id",    getattr(
            self.instance, "restaurante_id",    None))

        if tipo_doc and cedula:
            qs = Cliente.objects.filter(
                tipo_documento=tipo_doc,
                cedula=cedula,
                restaurante_id=restaurante_id,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"cedula": "Ya existe un cliente con ese documento en este restaurante."}
                )
        return attrs


class VincularUsuarioSerializer(serializers.Serializer):
    usuario_id = serializers.UUIDField()

    def validate_usuario_id(self, value):
        if not Usuario.objects.filter(id=value, activo=True).exists():
            raise serializers.ValidationError(
                "No existe un usuario activo con ese ID.")
        return value

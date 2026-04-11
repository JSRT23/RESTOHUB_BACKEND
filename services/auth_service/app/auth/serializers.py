# auth_service/app/auth/serializers.py
from django.contrib.auth import authenticate
from rest_framework import serializers

from .email_validator import validar_email_completo
from .models import Rol, Usuario, ROLES_CON_RESTAURANTE, ROLES_CON_EMPLEADO


def _check_email(email: str) -> str:
    """Valida formato + MX lookup. Lanza ValidationError si el correo no es real."""
    ok, mensaje = validar_email_completo(email)
    if not ok:
        raise serializers.ValidationError(mensaje)
    return email.strip().lower()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Credenciales inválidas.")
        if not user.activo:
            raise serializers.ValidationError("Usuario desactivado.")
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
        """MX lookup — verifica que el dominio tenga servidores de correo reales."""
        return _check_email(value)

    def validate(self, data):
        if data["password"] != data.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )

        rol = data.get("rol")
        restaurante_id = data.get("restaurante_id")
        empleado_id = data.get("empleado_id")

        if rol in ROLES_CON_RESTAURANTE and not restaurante_id:
            raise serializers.ValidationError(
                {"restaurante_id": f"El rol '{rol}' requiere restaurante_id."}
            )
        if rol in ROLES_CON_EMPLEADO and not empleado_id:
            raise serializers.ValidationError(
                {"empleado_id": f"El rol '{rol}' requiere empleado_id."}
            )
        if rol == Rol.ADMIN_CENTRAL and restaurante_id:
            raise serializers.ValidationError(
                {"restaurante_id": "admin_central no debe tener restaurante_id."}
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

import jwt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .email_service import enviar_bienvenida, enviar_codigo_verificacion
from .models import EmailVerificationCode, RefreshToken, Rol, Usuario
from .permissions import requiere_auth, requiere_rol
from .serializers import (
    CambiarPasswordSerializer,
    LoginSerializer,
    RegistroSerializer,
    UsuarioSerializer,
)
from .tokens import generar_access_token, generar_refresh_token, verificar_token


# ─────────────────────────────────────────────────────────────────────────────
# Auth básica
# ─────────────────────────────────────────────────────────────────────────────

class LoginView(APIView):
    """
    POST /api/auth/login/
    Bloquea el acceso si el email no fue verificado.
    """

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        usuario = serializer.validated_data["usuario"]

        if not usuario.email_verificado:
            return Response(
                {
                    "detail": "Debes verificar tu correo antes de iniciar sesión.",
                    "codigo": "EMAIL_NO_VERIFICADO",
                    "email": usuario.email,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        access_token = generar_access_token(usuario)
        refresh_token_str, expira_at = generar_refresh_token(usuario)
        RefreshToken.objects.create(
            usuario=usuario, token=refresh_token_str, expira_at=expira_at
        )

        return Response({
            "access_token":  access_token,
            "refresh_token": refresh_token_str,
            "token_type":    "Bearer",
            "expires_in":    3600,
            "usuario":       UsuarioSerializer(usuario).data,
        })


class RefreshView(APIView):
    """POST /api/auth/refresh/"""

    def post(self, request):
        refresh_token_str = request.data.get("refresh_token")
        if not refresh_token_str:
            return Response({"detail": "refresh_token requerido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            verificar_token(refresh_token_str, tipo="refresh")
        except jwt.ExpiredSignatureError:
            return Response(
                {"detail": "Sesión expirada. Inicia sesión nuevamente."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except jwt.InvalidTokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        rt = RefreshToken.objects.filter(
            token=refresh_token_str, revocado=False).first()
        if not rt or not rt.usuario.activo:
            return Response({"detail": "Token inválido o revocado."}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({
            "access_token": generar_access_token(rt.usuario),
            "token_type":   "Bearer",
        })


class LogoutView(APIView):
    """POST /api/auth/logout/"""
    @requiere_auth
    def post(self, request):
        refresh_token_str = request.data.get("refresh_token")
        if refresh_token_str:
            RefreshToken.objects.filter(
                token=refresh_token_str, usuario=request.usuario
            ).update(revocado=True)
        return Response({"detail": "Sesión cerrada."})


class MeView(APIView):
    """GET/PATCH /api/auth/me/"""
    @requiere_auth
    def get(self, request):
        return Response(UsuarioSerializer(request.usuario).data)

    @requiere_auth
    def patch(self, request):
        data = {k: v for k, v in request.data.items() if k in {"nombre"}}
        serializer = UsuarioSerializer(
            request.usuario, data=data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)


class CambiarPasswordView(APIView):
    """POST /api/auth/cambiar-password/"""
    @requiere_auth
    def post(self, request):
        serializer = CambiarPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        usuario = request.usuario
        if not usuario.check_password(serializer.validated_data["password_actual"]):
            return Response(
                {"password_actual": "Contraseña incorrecta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario.set_password(serializer.validated_data["password_nuevo"])
        usuario.save()
        RefreshToken.objects.filter(
            usuario=usuario, revocado=False).update(revocado=True)
        return Response({"detail": "Contraseña actualizada. Inicia sesión nuevamente."})


# ─────────────────────────────────────────────────────────────────────────────
# Registro + verificación por código
# ─────────────────────────────────────────────────────────────────────────────

class AutoRegistroView(APIView):
    """
    POST /api/auth/auto-registro/
    Registro público — solo para admin_central.
    Crea el usuario y envía el código de verificación por email.
    """

    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if serializer.validated_data.get("rol") != Rol.ADMIN_CENTRAL:
            return Response(
                {"detail": "El registro público solo está disponible para admin_central."},
                status=status.HTTP_403_FORBIDDEN,
            )

        usuario = serializer.save()  # email_verificado=False por defecto

        # Eliminar códigos anteriores y generar uno nuevo
        EmailVerificationCode.objects.filter(usuario=usuario).delete()
        codigo_obj = EmailVerificationCode.objects.create(usuario=usuario)

        enviado = enviar_codigo_verificacion(usuario, codigo_obj.codigo)

        return Response(
            {
                "detail": "Cuenta creada. Revisa tu correo e ingresa el código de 6 dígitos.",
                "email":        usuario.email,
                "email_enviado": enviado,
                # En desarrollo: mostrar código en la respuesta para no depender del email
                **({"codigo_dev": codigo_obj.codigo} if not enviado else {}),
            },
            status=status.HTTP_201_CREATED,
        )


class VerificarCodigoView(APIView):
    """
    POST /api/auth/verificar-codigo/
    Body: { email, codigo }

    Flujo:
    1. Busca el código activo para ese email
    2. Valida expiración y límite de intentos
    3. Si es correcto → activa la cuenta y envía bienvenida
    4. Si es incorrecto → suma intento fallido
    """

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        codigo = request.data.get("codigo", "").strip()

        if not email or not codigo:
            return Response(
                {"detail": "email y codigo son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario = Usuario.objects.filter(email=email, activo=True).first()
        if not usuario:
            return Response(
                {"detail": "No existe una cuenta con ese correo."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if usuario.email_verificado:
            return Response(
                {"detail": "Este correo ya está verificado. Puedes iniciar sesión."},
                status=status.HTTP_200_OK,
            )

        codigo_obj = EmailVerificationCode.objects.filter(
            usuario=usuario).first()

        if not codigo_obj:
            return Response(
                {
                    "detail": "No hay un código activo. Solicita uno nuevo.",
                    "codigo": "SIN_CODIGO",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if codigo_obj.ha_expirado:
            codigo_obj.delete()
            return Response(
                {
                    "detail": "El código expiró. Solicita uno nuevo.",
                    "codigo": "CODIGO_EXPIRADO",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if codigo_obj.intentos_agotados:
            codigo_obj.delete()
            return Response(
                {
                    "detail": "Demasiados intentos fallidos. Solicita un nuevo código.",
                    "codigo": "INTENTOS_AGOTADOS",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if codigo_obj.codigo != codigo:
            codigo_obj.registrar_intento_fallido()
            intentos_restantes = 3 - codigo_obj.intentos
            return Response(
                {
                    "detail": f"Código incorrecto. Te quedan {intentos_restantes} intento(s).",
                    "codigo": "CODIGO_INCORRECTO",
                    "intentos_restantes": intentos_restantes,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ✅ Código correcto
        usuario.email_verificado = True
        usuario.save(update_fields=["email_verificado"])
        codigo_obj.delete()

        enviar_bienvenida(usuario)

        return Response({
            "detail": "Email verificado correctamente. Ya puedes iniciar sesión.",
            "email":  usuario.email,
        })


class ReenviarCodigoView(APIView):
    """
    POST /api/auth/reenviar-codigo/
    Body: { email }
    Genera un código nuevo y lo envía — elimina el anterior.
    Respuesta genérica para no revelar si el email existe.
    """

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response({"detail": "email requerido."}, status=status.HTTP_400_BAD_REQUEST)

        respuesta_generica = Response({
            "detail": "Si el correo existe y no está verificado, recibirás un nuevo código."
        })

        usuario = Usuario.objects.filter(email=email, activo=True).first()
        if not usuario or usuario.email_verificado:
            return respuesta_generica

        # Eliminar código anterior y crear uno nuevo
        EmailVerificationCode.objects.filter(usuario=usuario).delete()
        codigo_obj = EmailVerificationCode.objects.create(usuario=usuario)
        enviar_codigo_verificacion(usuario, codigo_obj.codigo)

        return respuesta_generica


# ─────────────────────────────────────────────────────────────────────────────
# Registro interno (admin → operativos)
# ─────────────────────────────────────────────────────────────────────────────

class RegistroView(APIView):
    """
    POST /api/auth/registro/
    Solo admin_central y gerente_local pueden usar este endpoint.
    Los usuarios creados aquí tienen email_verificado=True por defecto
    (el gerente/admin los conoce personalmente).
    """
    @requiere_auth
    def post(self, request):
        creador = request.usuario

        if creador.rol not in (Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL):
            return Response(
                {"detail": "No tienes permiso para crear usuarios."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RegistroSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        rol_nuevo = serializer.validated_data.get("rol")

        if creador.rol == Rol.GERENTE_LOCAL:
            roles_permitidos = {
                Rol.SUPERVISOR, Rol.COCINERO, Rol.MESERO, Rol.CAJERO, Rol.REPARTIDOR
            }
            if rol_nuevo not in roles_permitidos:
                return Response(
                    {"detail": f"Gerente no puede crear usuarios con rol '{rol_nuevo}'."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            # Forzar restaurante del gerente
            serializer.validated_data["restaurante_id"] = creador.restaurante_id

        # Creados internamente → verificados por defecto
        serializer.validated_data["email_verificado"] = True
        usuario = serializer.save()

        return Response(UsuarioSerializer(usuario).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# Gestión de usuarios
# ─────────────────────────────────────────────────────────────────────────────

class UsuariosView(APIView):
    """GET /api/auth/usuarios/"""
    @requiere_rol(Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL)
    def get(self, request):
        if request.usuario.rol == Rol.ADMIN_CENTRAL:
            qs = Usuario.objects.all().order_by("rol", "email")
        else:
            qs = Usuario.objects.filter(
                restaurante_id=request.usuario.restaurante_id
            ).order_by("rol", "email")
        return Response(UsuarioSerializer(qs, many=True).data)


class UsuarioDetailView(APIView):
    """GET/PATCH/DELETE /api/auth/usuarios/<id>/"""

    def _get_usuario(self, pk, request_usuario):
        try:
            u = Usuario.objects.get(pk=pk)
        except Usuario.DoesNotExist:
            return None, Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if (request_usuario.rol == Rol.GERENTE_LOCAL
                and u.restaurante_id != request_usuario.restaurante_id):
            return None, Response({"detail": "Sin acceso."}, status=status.HTTP_403_FORBIDDEN)

        return u, None

    @requiere_rol(Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL)
    def get(self, request, pk):
        u, err = self._get_usuario(pk, request.usuario)
        if err:
            return err
        return Response(UsuarioSerializer(u).data)

    @requiere_rol(Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL)
    def patch(self, request, pk):
        u, err = self._get_usuario(pk, request.usuario)
        if err:
            return err

        allowed = (
            {"nombre", "rol", "restaurante_id", "empleado_id", "activo"}
            if request.usuario.rol == Rol.ADMIN_CENTRAL
            else {"nombre", "activo"}
        )
        data = {k: v for k, v in request.data.items() if k in allowed}
        serializer = UsuarioSerializer(u, data=data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    @requiere_rol(Rol.ADMIN_CENTRAL)
    def delete(self, request, pk):
        u, err = self._get_usuario(pk, request.usuario)
        if err:
            return err
        u.activo = False
        u.save()
        return Response({"detail": "Usuario desactivado."})


# ─────────────────────────────────────────────────────────────────────────────
# Verificación interna (gateway)
# ─────────────────────────────────────────────────────────────────────────────

class VerificarTokenView(APIView):
    """POST /api/auth/verificar/ — usado por el gateway."""

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "token requerido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = verificar_token(token, tipo="access")
            return Response({"valido": True, "payload": payload})
        except jwt.ExpiredSignatureError:
            return Response(
                {"valido": False, "detail": "Token expirado."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except jwt.InvalidTokenError as exc:
            return Response(
                {"valido": False, "detail": str(exc)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

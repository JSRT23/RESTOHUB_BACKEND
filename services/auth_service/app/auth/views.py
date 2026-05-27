# auth_service/app/auth_app/views.py
# FIX v2:
#   - LoginView incluye cliente_id en la respuesta
#   - ClienteListCreateView acepta filtro usuario_id
import jwt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .email_service import enviar_bienvenida, enviar_codigo_verificacion
from .models import Cliente, EmailVerificationCode, RefreshToken, Rol, Usuario
from .permissions import requiere_auth, requiere_rol
from .serializers import (
    CambiarPasswordSerializer, ClienteListSerializer, ClienteSerializer,
    ClienteWriteSerializer, LoginSerializer, RegistroSerializer,
    UsuarioSerializer, VincularUsuarioSerializer,
)
from .tokens import generar_access_token, generar_refresh_token, verificar_token

ROLES_AUTO_REGISTRO = {Rol.ADMIN_CENTRAL, "cliente"}


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        usuario = serializer.validated_data["usuario"]

        if not usuario.email_verificado:
            return Response({
                "detail": "Debes verificar tu correo antes de iniciar sesión.",
                "codigo": "EMAIL_NO_VERIFICADO",
                "email":  usuario.email,
            }, status=status.HTTP_403_FORBIDDEN)

        if usuario.rol == "cliente":
            tiene_cliente = Cliente.objects.filter(
                usuario_id=usuario.id, activo=True).exists()
            if not tiene_cliente:
                return Response({
                    "detail": "Tu cuenta no tiene perfil de cliente activo. Contacta con el restaurante o vuelve a registrarte.",
                    "codigo": "SIN_PERFIL_CLIENTE",
                }, status=status.HTTP_403_FORBIDDEN)

        access_token = generar_access_token(usuario)
        refresh_token_str, expira_at = generar_refresh_token(usuario)
        RefreshToken.objects.create(
            usuario=usuario, token=refresh_token_str, expira_at=expira_at)

        # FIX: incluir cliente_id para que el frontend lo use en loyalty queries
        usuario_data = UsuarioSerializer(usuario).data
        if usuario.rol == "cliente":
            cliente = Cliente.objects.filter(
                usuario_id=usuario.id, activo=True).first()
            if cliente:
                usuario_data["cliente_id"] = str(cliente.id)

        return Response({
            "access_token":  access_token,
            "refresh_token": refresh_token_str,
            "token_type":    "Bearer",
            "expires_in":    3600,
            "usuario":       usuario_data,
        })


class RefreshView(APIView):
    def post(self, request):
        refresh_token_str = request.data.get("refresh_token")
        if not refresh_token_str:
            return Response({"detail": "refresh_token requerido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            verificar_token(refresh_token_str, tipo="refresh")
        except jwt.ExpiredSignatureError:
            return Response({"detail": "Sesión expirada."}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
        rt = RefreshToken.objects.filter(
            token=refresh_token_str, revocado=False).first()
        if not rt or not rt.usuario.activo:
            return Response({"detail": "Token inválido o revocado."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"access_token": generar_access_token(rt.usuario), "token_type": "Bearer"})


class LogoutView(APIView):
    @requiere_auth
    def post(self, request):
        refresh_token_str = request.data.get("refresh_token")
        if refresh_token_str:
            RefreshToken.objects.filter(
                token=refresh_token_str, usuario=request.usuario).update(revocado=True)
        return Response({"detail": "Sesión cerrada."})


class MeView(APIView):
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
    @requiere_auth
    def post(self, request):
        serializer = CambiarPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        usuario = request.usuario
        if not usuario.check_password(serializer.validated_data["password_actual"]):
            return Response({"password_actual": "Contraseña incorrecta."}, status=status.HTTP_400_BAD_REQUEST)
        usuario.set_password(serializer.validated_data["password_nuevo"])
        usuario.save()
        RefreshToken.objects.filter(
            usuario=usuario, revocado=False).update(revocado=True)
        return Response({"detail": "Contraseña actualizada. Inicia sesión nuevamente."})


class BootstrapAdminView(APIView):
    def post(self, request):
        if Usuario.objects.filter(rol=Rol.ADMIN_CENTRAL).exists():
            return Response({"detail": "El sistema ya tiene un administrador central configurado."}, status=status.HTTP_400_BAD_REQUEST)
        email = request.data.get("email", "").strip().lower()
        nombre = request.data.get("nombre", "").strip()
        password = request.data.get("password", "")
        password_confirm = request.data.get("password_confirm", "")
        if not email or not nombre or not password:
            return Response({"detail": "email, nombre y password son requeridos."}, status=status.HTTP_400_BAD_REQUEST)
        if password != password_confirm:
            return Response({"detail": "Las contraseñas no coinciden."}, status=status.HTTP_400_BAD_REQUEST)
        if len(password) < 8:
            return Response({"detail": "La contraseña debe tener al menos 8 caracteres."}, status=status.HTTP_400_BAD_REQUEST)
        if Usuario.objects.filter(email=email).exists():
            return Response({"detail": "Ya existe una cuenta con ese email."}, status=status.HTTP_400_BAD_REQUEST)
        usuario = Usuario(email=email, nombre=nombre,
                          rol=Rol.ADMIN_CENTRAL, activo=True, email_verificado=True)
        usuario.set_password(password)
        usuario.save()
        return Response({"ok": True, "email": usuario.email, "nombre": usuario.nombre, "rol": usuario.rol, "detail": "Admin central creado."}, status=status.HTTP_201_CREATED)


class AutoRegistroView(APIView):
    def post(self, request):
        data = request.data.copy() if hasattr(
            request.data, 'copy') else dict(request.data)
        if not data.get("rol"):
            data["rol"] = "cliente"
        serializer = RegistroSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        rol = serializer.validated_data.get("rol")
        if rol not in ROLES_AUTO_REGISTRO:
            return Response({"detail": f"El rol '{rol}' debe ser creado por un administrador."}, status=status.HTTP_403_FORBIDDEN)
        usuario = serializer.save()
        cedula = data.get("cedula", "").strip().upper()
        tipo_documento = data.get("tipo_documento", "CC").strip().upper()
        telefono = data.get("telefono", "").strip()
        if cedula and rol == "cliente":
            try:
                existing = Cliente.objects.filter(
                    cedula=cedula, tipo_documento=tipo_documento, restaurante_id__isnull=True).first()
                if existing and not existing.usuario_id:
                    existing.usuario_id = usuario.id
                    existing.email = usuario.email
                    if not existing.nombre:
                        existing.nombre = usuario.nombre
                    if telefono:
                        existing.telefono = telefono
                    existing.save(
                        update_fields=["usuario_id", "email", "nombre", "telefono", "updated_at"])
                elif not existing:
                    nombre_parts = usuario.nombre.strip().split(" ", 1)
                    Cliente.objects.create(
                        tipo_documento=tipo_documento, cedula=cedula,
                        nombre=nombre_parts[0], apellido=nombre_parts[1] if len(
                            nombre_parts) > 1 else "",
                        email=usuario.email, telefono=telefono,
                        usuario_id=usuario.id, restaurante_id=None, activo=True,
                    )
            except Exception:
                pass
        EmailVerificationCode.objects.filter(usuario=usuario).delete()
        codigo_obj = EmailVerificationCode.objects.create(usuario=usuario)
        enviado = enviar_codigo_verificacion(usuario, codigo_obj.codigo)
        return Response({
            "detail": "Cuenta creada. Revisa tu correo e ingresa el código de 6 dígitos.",
            "email": usuario.email, "email_enviado": enviado,
            **({"codigo_dev": codigo_obj.codigo} if not enviado else {}),
        }, status=status.HTTP_201_CREATED)


class VerificarCodigoView(APIView):
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        codigo = request.data.get("codigo", "").strip()
        if not email or not codigo:
            return Response({"detail": "email y codigo son requeridos."}, status=status.HTTP_400_BAD_REQUEST)
        usuario = Usuario.objects.filter(email=email, activo=True).first()
        if not usuario:
            return Response({"detail": "No existe una cuenta con ese correo."}, status=status.HTTP_404_NOT_FOUND)
        if usuario.email_verificado:
            return Response({"detail": "Este correo ya está verificado. Puedes iniciar sesión."})
        codigo_obj = EmailVerificationCode.objects.filter(
            usuario=usuario).first()
        if not codigo_obj:
            return Response({"detail": "No hay un código activo.", "codigo": "SIN_CODIGO"}, status=status.HTTP_400_BAD_REQUEST)
        if codigo_obj.ha_expirado:
            codigo_obj.delete()
            return Response({"detail": "El código expiró.", "codigo": "CODIGO_EXPIRADO"}, status=status.HTTP_400_BAD_REQUEST)
        if codigo_obj.intentos_agotados:
            codigo_obj.delete()
            return Response({"detail": "Demasiados intentos.", "codigo": "INTENTOS_AGOTADOS"}, status=status.HTTP_400_BAD_REQUEST)
        if codigo_obj.codigo != codigo:
            codigo_obj.registrar_intento_fallido()
            return Response({"detail": f"Código incorrecto. Te quedan {3-codigo_obj.intentos} intento(s).", "codigo": "CODIGO_INCORRECTO", "intentos_restantes": 3-codigo_obj.intentos}, status=status.HTTP_400_BAD_REQUEST)
        usuario.email_verificado = True
        usuario.save(update_fields=["email_verificado"])
        codigo_obj.delete()
        enviar_bienvenida(usuario)
        return Response({"detail": "Email verificado correctamente.", "email": usuario.email})


class ReenviarCodigoView(APIView):
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response({"detail": "email requerido."}, status=status.HTTP_400_BAD_REQUEST)
        respuesta = Response(
            {"detail": "Si el correo existe y no está verificado, recibirás un nuevo código."})
        usuario = Usuario.objects.filter(email=email, activo=True).first()
        if not usuario or usuario.email_verificado:
            return respuesta
        EmailVerificationCode.objects.filter(usuario=usuario).delete()
        codigo_obj = EmailVerificationCode.objects.create(usuario=usuario)
        enviar_codigo_verificacion(usuario, codigo_obj.codigo)
        return respuesta


class RegistroView(APIView):
    @requiere_auth
    def post(self, request):
        creador = request.usuario
        if creador.rol not in (Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL):
            return Response({"detail": "No tienes permiso."}, status=status.HTTP_403_FORBIDDEN)
        serializer = RegistroSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        rol_nuevo = serializer.validated_data.get("rol")
        if creador.rol == Rol.GERENTE_LOCAL:
            roles_permitidos = {Rol.SUPERVISOR, Rol.COCINERO,
                                Rol.MESERO, Rol.CAJERO, Rol.REPARTIDOR}
            if rol_nuevo not in roles_permitidos:
                return Response({"detail": f"Gerente no puede crear rol '{rol_nuevo}'."}, status=status.HTTP_403_FORBIDDEN)
            serializer.validated_data["restaurante_id"] = creador.restaurante_id
        serializer.validated_data["email_verificado"] = True
        return Response(UsuarioSerializer(serializer.save()).data, status=status.HTTP_201_CREATED)


class UsuariosView(APIView):
    @requiere_rol(Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL)
    def get(self, request):
        if request.usuario.rol == Rol.ADMIN_CENTRAL:
            qs = Usuario.objects.all()
            rol = request.query_params.get("rol")
            activo = request.query_params.get("activo")
            restaurante_id = request.query_params.get("restaurante_id")
            if rol:
                qs = qs.filter(rol=rol)
            if activo is not None:
                qs = qs.filter(activo=activo.lower() == "true")
            if restaurante_id:
                qs = qs.filter(restaurante_id=restaurante_id)
        else:
            qs = Usuario.objects.filter(
                restaurante_id=request.usuario.restaurante_id)
        return Response(UsuarioSerializer(qs.order_by("rol", "email"), many=True).data)


class UsuarioDetailView(APIView):
    def _get(self, pk, req_user):
        try:
            u = Usuario.objects.get(pk=pk)
        except Usuario.DoesNotExist:
            return None, Response({"detail": "No encontrado."}, status=404)
        if req_user.rol == Rol.GERENTE_LOCAL and u.restaurante_id != req_user.restaurante_id:
            return None, Response({"detail": "Sin acceso."}, status=403)
        return u, None

    @requiere_rol(Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL)
    def get(self, request, pk):
        u, err = self._get(pk, request.usuario)
        return err or Response(UsuarioSerializer(u).data)

    @requiere_rol(Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL)
    def patch(self, request, pk):
        u, err = self._get(pk, request.usuario)
        if err:
            return err
        allowed = ({"nombre", "rol", "restaurante_id", "empleado_id", "activo"}
                   if request.usuario.rol == Rol.ADMIN_CENTRAL else {"nombre", "activo"})
        s = UsuarioSerializer(
            u, data={k: v for k, v in request.data.items() if k in allowed}, partial=True)
        if not s.is_valid():
            return Response(s.errors, status=400)
        return Response(UsuarioSerializer(s.save()).data)

    @requiere_rol(Rol.ADMIN_CENTRAL)
    def delete(self, request, pk):
        u, err = self._get(pk, request.usuario)
        if err:
            return err
        u.activo = False
        u.save()
        return Response({"detail": "Usuario desactivado."})


class DesactivarUsuarioView(APIView):
    @requiere_rol(Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL)
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response({"detail": "email requerido."}, status=400)
        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=404)
        if request.usuario.rol == Rol.GERENTE_LOCAL and usuario.restaurante_id != request.usuario.restaurante_id:
            return Response({"detail": "Sin acceso."}, status=403)
        if usuario.id == request.usuario.id:
            return Response({"detail": "No puedes desactivarte."}, status=403)
        if request.usuario.rol == Rol.GERENTE_LOCAL and usuario.rol in (Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL):
            return Response({"detail": "Sin permiso."}, status=403)
        if not usuario.activo:
            return Response({"ok": True, "detail": "Ya estaba inactivo."})
        usuario.activo = False
        usuario.save(update_fields=["activo"])
        RefreshToken.objects.filter(
            usuario=usuario, revocado=False).update(revocado=True)
        return Response({"ok": True})


class ActivarUsuarioView(APIView):
    @requiere_rol(Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL)
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response({"detail": "email requerido."}, status=400)
        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=404)
        if request.usuario.rol == Rol.GERENTE_LOCAL and usuario.restaurante_id != request.usuario.restaurante_id:
            return Response({"detail": "Sin acceso."}, status=403)
        if request.usuario.rol == Rol.GERENTE_LOCAL and usuario.rol in (Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL):
            return Response({"detail": "Sin permiso."}, status=403)
        if usuario.activo:
            return Response({"ok": True, "detail": "Ya estaba activo."})
        usuario.activo = True
        usuario.save(update_fields=["activo"])
        return Response({"ok": True})


class VincularEmpleadoView(APIView):
    @requiere_rol(Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL)
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        empleado_id = request.data.get("empleado_id", "").strip()
        if not email:
            return Response({"detail": "email requerido."}, status=400)
        if not empleado_id:
            return Response({"detail": "empleado_id requerido."}, status=400)
        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=404)
        if request.usuario.rol == Rol.GERENTE_LOCAL and usuario.restaurante_id != request.usuario.restaurante_id:
            return Response({"detail": "Sin acceso."}, status=403)
        import uuid as uuid_mod
        try:
            uuid_mod.UUID(empleado_id)
        except ValueError:
            return Response({"detail": "empleado_id inválido."}, status=400)
        usuario.empleado_id = empleado_id
        usuario.save(update_fields=["empleado_id"])
        return Response({"ok": True, "email": usuario.email, "empleado_id": str(usuario.empleado_id)})


class VerificarTokenView(APIView):
    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "token requerido."}, status=400)
        try:
            payload = verificar_token(token, tipo="access")
            return Response({"valido": True, "payload": payload})
        except jwt.ExpiredSignatureError:
            return Response({"valido": False, "detail": "Token expirado."}, status=401)
        except jwt.InvalidTokenError as exc:
            return Response({"valido": False, "detail": str(exc)}, status=401)


ROLES_CLIENTES = (Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL, Rol.CAJERO)


class ClienteListCreateView(APIView):
    @requiere_rol(*ROLES_CLIENTES)
    def get(self, request):
        qs = Cliente.objects.all()
        restaurante_id = request.query_params.get("restaurante_id")
        activo = request.query_params.get("activo")
        q = request.query_params.get("q")
        usuario_id = request.query_params.get(
            "usuario_id")  # FIX: filtro nuevo

        from django.db.models import Q as DQ

        scope = restaurante_id or (
            str(request.usuario.restaurante_id)
            if request.usuario.restaurante_id and request.usuario.rol != Rol.ADMIN_CENTRAL
            else None
        )
        # Si se filtra por usuario_id, no aplicar scope de restaurante
        # (el cliente puede estar en cualquier restaurante)
        if usuario_id:
            qs = qs.filter(usuario_id=usuario_id)
        elif scope:
            qs = qs.filter(DQ(restaurante_id=scope) |
                           DQ(restaurante_id__isnull=True))

        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")
        if q:
            qs = qs.filter(DQ(nombre__icontains=q) | DQ(apellido__icontains=q) | DQ(
                cedula__icontains=q) | DQ(email__icontains=q))

        return Response(ClienteListSerializer(qs.order_by("nombre", "apellido"), many=True).data)

    @requiere_rol(*ROLES_CLIENTES)
    def post(self, request):
        serializer = ClienteWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        data = serializer.validated_data
        if not data.get("restaurante_id") and request.usuario.restaurante_id:
            data["restaurante_id"] = request.usuario.restaurante_id
        return Response(ClienteSerializer(serializer.save()).data, status=201)


class ClienteDetailView(APIView):
    def _get(self, pk):
        try:
            return Cliente.objects.get(pk=pk), None
        except Cliente.DoesNotExist:
            return None, Response({"detail": "No encontrado."}, status=404)

    @requiere_rol(*ROLES_CLIENTES)
    def get(self, request, pk):
        c, err = self._get(pk)
        return err or Response(ClienteSerializer(c).data)

    @requiere_rol(*ROLES_CLIENTES)
    def patch(self, request, pk):
        c, err = self._get(pk)
        if err:
            return err
        s = ClienteWriteSerializer(c, data=request.data, partial=True)
        if not s.is_valid():
            return Response(s.errors, status=400)
        return Response(ClienteSerializer(s.save()).data)


class BuscarClienteView(APIView):
    @requiere_rol(*ROLES_CLIENTES)
    def get(self, request):
        cedula = request.query_params.get("cedula", "").strip().upper()
        restaurante_id = request.query_params.get("restaurante_id")
        if not cedula:
            return Response({"detail": "cedula requerida."}, status=400)
        if not restaurante_id and request.usuario.restaurante_id:
            restaurante_id = str(request.usuario.restaurante_id)
        from django.db.models import Q as DQ
        qs = Cliente.objects.filter(cedula=cedula, activo=True)
        if restaurante_id:
            qs = qs.filter(DQ(restaurante_id=restaurante_id)
                           | DQ(restaurante_id__isnull=True))
        clientes = list(qs.order_by("restaurante_id"))
        if not clientes:
            return Response({"detail": f"No se encontró cliente con cédula '{cedula}'."}, status=404)
        return Response(ClienteListSerializer(clientes, many=True).data)


class VincularUsuarioClienteView(APIView):
    @requiere_rol(*ROLES_CLIENTES)
    def post(self, request, pk):
        try:
            cliente = Cliente.objects.get(pk=pk)
        except Cliente.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=404)
        s = VincularUsuarioSerializer(data=request.data)
        if not s.is_valid():
            return Response(s.errors, status=400)
        cliente.usuario_id = s.validated_data["usuario_id"]
        cliente.save(update_fields=["usuario_id", "updated_at"])
        return Response({"ok": True, "cliente": ClienteSerializer(cliente).data, "message": "Vinculado correctamente."})


class DesvincularUsuarioClienteView(APIView):
    @requiere_rol(Rol.ADMIN_CENTRAL, Rol.GERENTE_LOCAL)
    def post(self, request, pk):
        try:
            cliente = Cliente.objects.get(pk=pk)
        except Cliente.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=404)
        if not cliente.usuario_id:
            return Response({"detail": "No está vinculado."}, status=400)
        cliente.usuario_id = None
        cliente.save(update_fields=["usuario_id", "updated_at"])
        return Response({"ok": True, "message": "Vinculación eliminada."})


class MiPerfilClienteView(APIView):
    """
    GET /api/auth/mi-perfil-cliente/
    Retorna el Cliente vinculado al usuario autenticado.
    Disponible para rol=cliente. No requiere rol de cajero/gerente.
    Usado por PerfilPage para obtener el cliente_id sin hacer logout/login.
    """
    @requiere_auth
    def get(self, request):
        usuario = request.usuario
        cliente = Cliente.objects.filter(
            usuario_id=usuario.id, activo=True).first()
        if not cliente:
            return Response({"detail": "No tienes un perfil de cliente activo."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ClienteListSerializer(cliente).data)

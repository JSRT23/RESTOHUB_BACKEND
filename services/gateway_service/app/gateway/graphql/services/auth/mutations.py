# gateway_service/app/gateway/graphql/services/auth/mutations.py
import graphene
from .types import AuthPayloadType, UsuarioType
from ....client import auth_client
from ....middleware.permissions import get_jwt_user


# ─────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────

class Login(graphene.Mutation):
    """
    Inicia sesión y retorna access_token + refresh_token.
    Si el email no está verificado retorna ok=False con codigo="EMAIL_NO_VERIFICADO".
    """
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    ok = graphene.Boolean()
    payload = graphene.Field(AuthPayloadType)
    error = graphene.String()
    codigo = graphene.String()

    def mutate(self, info, email, password):
        result = auth_client.login(email, password)

        if not result:
            return Login(ok=False, error="Error de conexión con el servicio de autenticación.", codigo="ERROR")

        if result.get("_error"):
            detail = result.get("detail", "Error al iniciar sesión.")
            codigo = result.get("codigo", "ERROR")

            if codigo == "EMAIL_NO_VERIFICADO":
                detail = "Debes verificar tu correo antes de iniciar sesión."

            return Login(ok=False, error=detail, codigo=codigo)

        return Login(ok=True, payload=result)


# ─────────────────────────────────────────
# REFRESH TOKEN
# ─────────────────────────────────────────

class RefreshToken(graphene.Mutation):
    """Renueva el access_token usando el refresh_token."""
    class Arguments:
        refresh_token = graphene.String(required=True)

    ok = graphene.Boolean()
    access_token = graphene.String()
    error = graphene.String()

    def mutate(self, info, refresh_token):
        result = auth_client.refresh_token(refresh_token)
        if not result or result.get("_error"):
            return RefreshToken(ok=False, error="Sesión expirada. Inicia sesión nuevamente.")
        return RefreshToken(ok=True, access_token=result.get("access_token"))


# ─────────────────────────────────────────
# AUTO-REGISTRO (público — solo admin_central)
# ─────────────────────────────────────────

class AutoRegistro(graphene.Mutation):
    """
    Registro público para crear el primer admin_central.
    Envía código de verificación al email.
    """
    class Arguments:
        email = graphene.String(required=True)
        nombre = graphene.String(required=True)
        password = graphene.String(required=True)
        password_confirm = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()
    email_enviado = graphene.Boolean()
    codigo_dev = graphene.String()

    def mutate(self, info, email, nombre, password, password_confirm):
        result = auth_client.auto_registro({
            "email":            email,
            "nombre":           nombre,
            "password":         password,
            "password_confirm": password_confirm,
            "rol":              "admin_central",
        })

        if not result:
            return AutoRegistro(ok=False, error="Error de conexión.")

        if result.get("_error"):
            detail = _extraer_error(result)
            return AutoRegistro(ok=False, error=detail)

        return AutoRegistro(
            ok=True,
            email_enviado=result.get("email_enviado", False),
            codigo_dev=result.get("codigo_dev"),
        )


# ─────────────────────────────────────────
# REGISTRO INTERNO (admin/gerente crean operativos)
# ─────────────────────────────────────────

class RegistrarUsuario(graphene.Mutation):
    """
    Crea un usuario operativo. Requiere token de admin_central o gerente_local.
    El email es validado con MX lookup. El usuario creado tiene email_verificado=True.

    NOTA: No se requiere empleado_id al momento del registro.
    El flujo correcto es:
      1. registrarUsuario en auth_service (sin empleado_id)
      2. crearEmpleado en staff_service
    Al hacer login, el JWT se construye vinculando ambos por email.
    """
    class Arguments:
        email = graphene.String(required=True)
        nombre = graphene.String(required=True)
        password = graphene.String(required=True)
        password_confirm = graphene.String(required=True)
        rol = graphene.String(required=True)
        restaurante_id = graphene.ID()
        empleado_id = graphene.ID()

    ok = graphene.Boolean()
    usuario = graphene.Field(UsuarioType)
    error = graphene.String()

    def mutate(self, info, email, nombre, password, password_confirm,
               rol, restaurante_id=None, empleado_id=None):

        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return RegistrarUsuario(ok=False, error="Debes iniciar sesión.")

        if jwt_user.get("rol") not in ("admin_central", "gerente_local"):
            return RegistrarUsuario(ok=False, error="No tienes permiso para crear usuarios.")

        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""

        payload = {
            "email":            email,
            "nombre":           nombre,
            "password":         password,
            "password_confirm": password_confirm,
            "rol":              rol,
        }
        if restaurante_id:
            payload["restaurante_id"] = restaurante_id
        if empleado_id:
            payload["empleado_id"] = empleado_id

        result = auth_client.registro(payload, token)

        if not result:
            return RegistrarUsuario(ok=False, error="Error de conexión.")

        if result.get("_error"):
            return RegistrarUsuario(ok=False, error=_extraer_error(result))

        return RegistrarUsuario(ok=True, usuario=result)


# ─────────────────────────────────────────
# DESACTIVAR USUARIO
# ─────────────────────────────────────────

class DesactivarUsuario(graphene.Mutation):
    """
    Desactiva la cuenta de un usuario en auth_service por email.
    Revoca el acceso al login de forma inmediata.
    Se llama en paralelo con desactivarEmpleado en staff_service.
    Solo permitido para admin_central y gerente_local.
    """
    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, email):
        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return DesactivarUsuario(ok=False, error="Debes iniciar sesión.")

        if jwt_user.get("rol") not in ("admin_central", "gerente_local"):
            return DesactivarUsuario(ok=False, error="No tienes permiso para desactivar usuarios.")

        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""

        result = auth_client.desactivar_usuario(email, token)

        if not result or result.get("_error"):
            return DesactivarUsuario(
                ok=False,
                error=result.get(
                    "detail", "Error al desactivar el usuario.") if result else "Error de conexión.",
            )

        return DesactivarUsuario(ok=True)


# ─────────────────────────────────────────
# ACTIVAR USUARIO
# ─────────────────────────────────────────

class ActivarUsuario(graphene.Mutation):
    """
    Reactiva la cuenta de un usuario en auth_service por email.
    Restaura el acceso al login.
    Se llama en paralelo con activarEmpleado en staff_service.
    Solo permitido para admin_central y gerente_local.
    """
    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, email):
        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return ActivarUsuario(ok=False, error="Debes iniciar sesión.")

        if jwt_user.get("rol") not in ("admin_central", "gerente_local"):
            return ActivarUsuario(ok=False, error="No tienes permiso para activar usuarios.")

        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""

        result = auth_client.activar_usuario(email, token)

        if not result or result.get("_error"):
            return ActivarUsuario(
                ok=False,
                error=result.get(
                    "detail", "Error al activar el usuario.") if result else "Error de conexión.",
            )

        return ActivarUsuario(ok=True)


# ─────────────────────────────────────────
# VERIFICAR CÓDIGO
# ─────────────────────────────────────────

class VerificarCodigo(graphene.Mutation):
    """
    Verifica el código de 6 dígitos enviado al email.
    Activa la cuenta si es correcto.
    """
    class Arguments:
        email = graphene.String(required=True)
        codigo = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()
    codigo_error = graphene.String()
    intentos_restantes = graphene.Int()

    def mutate(self, info, email, codigo):
        result = auth_client.verificar_codigo(email, codigo)

        if not result:
            return VerificarCodigo(ok=False, error="Error de conexión.", codigo_error="ERROR")

        if result.get("_error"):
            return VerificarCodigo(
                ok=False,
                error=result.get("detail", "Código inválido."),
                codigo_error=result.get("codigo", "ERROR"),
                intentos_restantes=result.get("intentos_restantes"),
            )

        return VerificarCodigo(ok=True)


# ─────────────────────────────────────────
# REENVIAR CÓDIGO
# ─────────────────────────────────────────

class ReenviarCodigo(graphene.Mutation):
    """Reenvía el código de verificación al email."""
    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, email):
        auth_client.reenviar_codigo(email)
        return ReenviarCodigo(ok=True)


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def _extraer_error(result: dict) -> str:
    """
    Extrae el mensaje de error más útil de la respuesta del auth_service.
    Maneja errores de validación del serializer (DRF) y errores simples.
    """
    if not result:
        return "Error desconocido."

    errores_campo = {
        k: v for k, v in result.items()
        if k not in ("_error", "status", "detail", "codigo")
        and isinstance(v, (list, str))
    }
    if errores_campo:
        partes = []
        for campo, msg in errores_campo.items():
            texto = msg[0] if isinstance(msg, list) else msg
            partes.append(f"{campo}: {texto}")
        return " | ".join(partes)

    return result.get("detail", "Error al procesar la solicitud.")


# ─────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────

class AuthMutation(graphene.ObjectType):
    login = Login.Field()
    refresh_token = RefreshToken.Field()
    auto_registro = AutoRegistro.Field()
    registrar_usuario = RegistrarUsuario.Field()
    verificar_codigo = VerificarCodigo.Field()
    reenviar_codigo = ReenviarCodigo.Field()
    desactivar_usuario = DesactivarUsuario.Field()
    activar_usuario = ActivarUsuario.Field()

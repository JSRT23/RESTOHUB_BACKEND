# gateway_service/app/gateway/graphql/services/auth/mutations.py
# CAMBIO v4:
#   - BootstrapAdmin: mutation pública para crear el primer admin_central.
#     Se bloquea automáticamente después del primer uso (el auth_service lo verifica).

import graphene
from .types import AuthPayloadType, ClientePayload, ClienteType, UsuarioType
from ....client import auth_client
from ....middleware.permissions import get_jwt_user
from .queries import _map_cliente


# ── Mutations existentes ───────────────────────────────────────────────────

class Login(graphene.Mutation):
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


class RefreshToken(graphene.Mutation):
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


class AutoRegistro(graphene.Mutation):
    """
    Registro público sin autenticación.
    Sin rol → auth_service defaultea a 'cliente'.
    """
    class Arguments:
        email = graphene.String(required=True)
        nombre = graphene.String(required=True)
        password = graphene.String(required=True)
        password_confirm = graphene.String(required=True)
        cedula = graphene.String()
        tipo_documento = graphene.String()
        telefono = graphene.String()

    ok = graphene.Boolean()
    error = graphene.String()
    email_enviado = graphene.Boolean()
    codigo_dev = graphene.String()

    def mutate(self, info, email, nombre, password, password_confirm,
               cedula=None, tipo_documento=None, telefono=None):
        payload = {
            "email":            email,
            "nombre":           nombre,
            "password":         password,
            "password_confirm": password_confirm,
        }
        if cedula:
            payload["cedula"] = cedula
        if tipo_documento:
            payload["tipo_documento"] = tipo_documento
        if telefono:
            payload["telefono"] = telefono

        result = auth_client.auto_registro(payload)
        if not result:
            return AutoRegistro(ok=False, error="Error de conexión.")
        if result.get("_error"):
            return AutoRegistro(ok=False, error=_extraer_error(result))
        return AutoRegistro(
            ok=True,
            email_enviado=result.get("email_enviado", False),
            codigo_dev=result.get("codigo_dev"),
        )


# ── NUEVO: Bootstrap Admin ─────────────────────────────────────────────────

class BootstrapAdmin(graphene.Mutation):
    """
    Crea el primer admin_central del sistema sin requerir autenticación.

    Solo funciona UNA VEZ. Si ya existe un admin_central, retorna error.
    Diseñado para el setup inicial en producción cuando no hay shell disponible.

    Uso:
        mutation {
          bootstrapAdmin(
            email: "admin@ejemplo.com"
            nombre: "Juan Ramos"
            password: "MiPassword123*"
            passwordConfirm: "MiPassword123*"
          ) {
            ok
            error
            email
          }
        }
    """
    class Arguments:
        email = graphene.String(required=True)
        nombre = graphene.String(required=True)
        password = graphene.String(required=True)
        password_confirm = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()
    email = graphene.String()

    def mutate(self, info, email, nombre, password, password_confirm):
        result = auth_client.bootstrap_admin({
            "email":            email,
            "nombre":           nombre,
            "password":         password,
            "password_confirm": password_confirm,
        })
        if not result:
            return BootstrapAdmin(ok=False, error="Error de conexión con auth_service.")
        if result.get("_error") or not result.get("ok"):
            detail = result.get("detail", "Error al crear el administrador.")
            return BootstrapAdmin(ok=False, error=detail)
        return BootstrapAdmin(ok=True, email=result.get("email"))


# ── Mutations existentes (sin cambios) ────────────────────────────────────

class RegistrarUsuario(graphene.Mutation):
    """Crea un usuario operativo. Requiere token de admin_central o gerente_local."""
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
            "email": email, "nombre": nombre,
            "password": password, "password_confirm": password_confirm,
            "rol": rol,
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


class VincularEmpleadoId(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        empleado_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, email, empleado_id):
        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return VincularEmpleadoId(ok=False, error="Debes iniciar sesión.")
        if jwt_user.get("rol") not in ("admin_central", "gerente_local"):
            return VincularEmpleadoId(ok=False, error="No tienes permiso.")

        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""

        result = auth_client.vincular_empleado(email, str(empleado_id), token)
        if not result or result.get("_error"):
            msg = result.get(
                "detail", "Error al vincular empleado_id.") if result else "Error de conexión."
            return VincularEmpleadoId(ok=False, error=msg)
        return VincularEmpleadoId(ok=True)


class DesactivarUsuario(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, email):
        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return DesactivarUsuario(ok=False, error="Debes iniciar sesión.")
        if jwt_user.get("rol") not in ("admin_central", "gerente_local"):
            return DesactivarUsuario(ok=False, error="No tienes permiso.")

        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""

        result = auth_client.desactivar_usuario(email, token)
        if not result or result.get("_error"):
            return DesactivarUsuario(
                ok=False,
                error=result.get(
                    "detail", "Error al desactivar.") if result else "Error de conexión.",
            )
        return DesactivarUsuario(ok=True)


class ActivarUsuario(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, email):
        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return ActivarUsuario(ok=False, error="Debes iniciar sesión.")
        if jwt_user.get("rol") not in ("admin_central", "gerente_local"):
            return ActivarUsuario(ok=False, error="No tienes permiso.")

        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""

        result = auth_client.activar_usuario(email, token)
        if not result or result.get("_error"):
            return ActivarUsuario(
                ok=False,
                error=result.get(
                    "detail", "Error al activar.") if result else "Error de conexión.",
            )
        return ActivarUsuario(ok=True)


class VerificarCodigo(graphene.Mutation):
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


class ReenviarCodigo(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, email):
        auth_client.reenviar_codigo(email)
        return ReenviarCodigo(ok=True)


# ── Cliente mutations ──────────────────────────────────────────────────────

class CrearCliente(graphene.Mutation):
    class Arguments:
        cedula = graphene.String(required=True)
        nombre = graphene.String(required=True)
        tipo_documento = graphene.String()
        apellido = graphene.String()
        email = graphene.String()
        telefono = graphene.String()
        restaurante_id = graphene.ID()
        notas = graphene.String()

    Output = ClientePayload

    def mutate(self, info, cedula, nombre,
               tipo_documento="CC", apellido="", email="",
               telefono="", restaurante_id=None, notas=""):
        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return ClientePayload(ok=False, error="Debes iniciar sesión.")
        if jwt_user.get("rol") not in ("admin_central", "gerente_local", "cajero"):
            return ClientePayload(ok=False, error="Sin permiso para crear clientes.")

        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""

        rid = restaurante_id or jwt_user.get("restaurante_id")

        result = auth_client.post(
            "/clientes/",
            {
                "tipo_documento": tipo_documento, "cedula": cedula,
                "nombre": nombre, "apellido": apellido,
                "email": email, "telefono": telefono,
                "restaurante_id": rid, "notas": notas, "activo": True,
            },
            token=token,
        )
        if not result or result.get("_error"):
            return ClientePayload(ok=False, error=_extraer_error(result) if result else "Error de conexión.")
        return ClientePayload(ok=True, cliente=_map_cliente(result))


class EditarCliente(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        nombre = graphene.String()
        apellido = graphene.String()
        email = graphene.String()
        telefono = graphene.String()
        activo = graphene.Boolean()
        notas = graphene.String()

    Output = ClientePayload

    def mutate(self, info, id, **kwargs):
        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return ClientePayload(ok=False, error="Debes iniciar sesión.")
        if jwt_user.get("rol") not in ("admin_central", "gerente_local", "cajero"):
            return ClientePayload(ok=False, error="Sin permiso.")

        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""

        payload = {k: v for k, v in kwargs.items() if v is not None}
        result = auth_client.patch(f"/clientes/{id}/", payload, token=token)
        if not result or result.get("_error"):
            return ClientePayload(ok=False, error=_extraer_error(result) if result else "Error de conexión.")
        return ClientePayload(ok=True, cliente=_map_cliente(result))


class VincularUsuarioCliente(graphene.Mutation):
    class Arguments:
        cliente_id = graphene.ID(required=True)
        usuario_id = graphene.ID(required=True)

    Output = ClientePayload

    def mutate(self, info, cliente_id, usuario_id):
        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return ClientePayload(ok=False, error="Debes iniciar sesión.")
        if jwt_user.get("rol") not in ("admin_central", "gerente_local", "cajero"):
            return ClientePayload(ok=False, error="Sin permiso.")

        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""

        result = auth_client.post(
            f"/clientes/{cliente_id}/vincular-usuario/",
            {"usuario_id": str(usuario_id)},
            token=token,
        )
        if not result or result.get("_error"):
            return ClientePayload(ok=False, error=_extraer_error(result) if result else "Error de conexión.")
        return ClientePayload(
            ok=result.get("ok", False),
            message=result.get("message"),
            cliente=_map_cliente(result.get("cliente", {})
                                 ) if result.get("ok") else None,
        )


class DesvincularUsuarioCliente(graphene.Mutation):
    class Arguments:
        cliente_id = graphene.ID(required=True)

    Output = ClientePayload

    def mutate(self, info, cliente_id):
        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return ClientePayload(ok=False, error="Debes iniciar sesión.")
        if jwt_user.get("rol") not in ("admin_central", "gerente_local"):
            return ClientePayload(ok=False, error="Sin permiso.")

        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""

        result = auth_client.post(
            f"/clientes/{cliente_id}/desvincular-usuario/", {}, token=token
        )
        if not result or result.get("_error"):
            return ClientePayload(ok=False, error=_extraer_error(result) if result else "Error de conexión.")
        return ClientePayload(ok=result.get("ok", False), message=result.get("message"))


# ── Helpers ────────────────────────────────────────────────────────────────

def _extraer_error(result: dict) -> str:
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


# ── Schema ─────────────────────────────────────────────────────────────────

class AuthMutation(graphene.ObjectType):
    # Setup inicial (una sola vez)
    bootstrap_admin = BootstrapAdmin.Field()

    # Auth
    login = Login.Field()
    refresh_token = RefreshToken.Field()
    auto_registro = AutoRegistro.Field()
    registrar_usuario = RegistrarUsuario.Field()
    verificar_codigo = VerificarCodigo.Field()
    reenviar_codigo = ReenviarCodigo.Field()
    desactivar_usuario = DesactivarUsuario.Field()
    activar_usuario = ActivarUsuario.Field()
    vincular_empleado_id = VincularEmpleadoId.Field()

    # Cliente TPV
    crear_cliente = CrearCliente.Field()
    editar_cliente = EditarCliente.Field()
    vincular_usuario_cliente = VincularUsuarioCliente.Field()
    desvincular_usuario_cliente = DesvincularUsuarioCliente.Field()

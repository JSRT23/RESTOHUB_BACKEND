# gateway_service/app/gateway/graphql/services/auth/mutations.py
# NUEVO: CrearSuperusuarioDjango — crea superusuario para el Django Admin
# Todo lo demás igual que el original.

import graphene
from .types import AuthPayloadType, ClientePayload, ClienteType, UsuarioType
from ....client import auth_client
from ....middleware.permissions import get_jwt_user
from .queries import _map_cliente


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
        payload = {"email": email, "nombre": nombre,
                   "password": password, "password_confirm": password_confirm}
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
        return AutoRegistro(ok=True, email_enviado=result.get("email_enviado", False), codigo_dev=result.get("codigo_dev"))


class BootstrapAdmin(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        nombre = graphene.String(required=True)
        password = graphene.String(required=True)
        password_confirm = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()
    email = graphene.String()

    def mutate(self, info, email, nombre, password, password_confirm):
        result = auth_client.bootstrap_admin(
            {"email": email, "nombre": nombre, "password": password, "password_confirm": password_confirm})
        if not result:
            return BootstrapAdmin(ok=False, error="Error de conexión con auth_service.")
        if result.get("_error") or not result.get("ok"):
            return BootstrapAdmin(ok=False, error=result.get("detail", "Error al crear el administrador."))
        return BootstrapAdmin(ok=True, email=result.get("email"))


# ── NUEVO: Crear superusuario Django Admin ─────────────────────────────────
class CrearSuperusuarioDjango(graphene.Mutation):
    """
    Crea un superusuario Django (is_staff=True, is_superuser=True) para acceder
    al Django Admin de cualquier microservicio.

    Solo puede ejecutarlo un admin_central.

    Uso:
        mutation {
          crearSuperusuarioDjango(
            servicio: "auth"   # "auth" | "loyalty" | "order" | "inventory" | "staff" | "menu"
            email: "dev@restohub.com"
            nombre: "Dev Admin"
            password: "DevPass123*"
          ) {
            ok
            error
            detalle
          }
        }

    El servicio debe tener el endpoint POST /api/admin/crear-superusuario/
    habilitado (agregar la view en cada microservicio).
    """
    class Arguments:
        servicio = graphene.String(
            required=True, description="Nombre del microservicio: auth | loyalty | order | inventory | staff | menu")
        email = graphene.String(required=True)
        nombre = graphene.String(required=True)
        password = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()
    detalle = graphene.String()

    def mutate(self, info, servicio, email, nombre, password):
        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return CrearSuperusuarioDjango(ok=False, error="Debes iniciar sesión.")
        if jwt_user.get("rol") != "admin_central":
            return CrearSuperusuarioDjango(ok=False, error="Solo admin_central puede crear superusuarios Django.")

        import os
        import httpx

        # Mapa de servicios → URLs internas
        SERVICE_URLS = {
            "auth":      os.getenv("AUTH_SERVICE_URL",      "http://auth_service:8000/api/auth"),
            "loyalty":   os.getenv("LOYALTY_SERVICE_URL",   "http://loyalty_service:8004/api/loyalty"),
            "order":     os.getenv("ORDER_SERVICE_URL",     "http://order_service:8002/api/orders"),
            "inventory": os.getenv("INVENTORY_SERVICE_URL", "http://inventory_service:8003/api/inventory"),
            "staff":     os.getenv("STAFF_SERVICE_URL",     "http://staff_service:8005/api/staff"),
            "menu":      os.getenv("MENU_SERVICE_URL",      "http://menu_service:8001/api/menu"),
        }

        base_url = SERVICE_URLS.get(servicio.lower())
        if not base_url:
            servicios_validos = ", ".join(SERVICE_URLS.keys())
            return CrearSuperusuarioDjango(ok=False, error=f"Servicio '{servicio}' no reconocido. Válidos: {servicios_validos}")

        # Normalizar URL base — quitar path /api/xxx y usar solo el host
        # El endpoint se expone en /api/admin/crear-superusuario/
        host = base_url.split("/api/")[0]
        endpoint = f"{host}/api/admin/crear-superusuario/"

        try:
            with httpx.Client(timeout=15, verify=False) as client:
                resp = client.post(endpoint, json={
                    "email":    email,
                    "nombre":   nombre,
                    "password": password,
                })
                resp.raise_for_status()
                data = resp.json()
                return CrearSuperusuarioDjango(
                    ok=data.get("ok", True),
                    detalle=data.get(
                        "detail", f"Superusuario creado en {servicio}.")
                )
        except httpx.HTTPStatusError as e:
            try:
                body = e.response.json()
                detail = body.get("detail", str(e))
            except Exception:
                detail = str(e)
            return CrearSuperusuarioDjango(ok=False, error=f"Error en {servicio}: {detail}")
        except Exception as e:
            return CrearSuperusuarioDjango(ok=False, error=f"No se pudo conectar con {servicio}: {str(e)}")


class RegistrarUsuario(graphene.Mutation):
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

    def mutate(self, info, email, nombre, password, password_confirm, rol, restaurante_id=None, empleado_id=None):
        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return RegistrarUsuario(ok=False, error="Debes iniciar sesión.")
        if jwt_user.get("rol") not in ("admin_central", "gerente_local"):
            return RegistrarUsuario(ok=False, error="No tienes permiso para crear usuarios.")
        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""
        payload = {"email": email, "nombre": nombre, "password": password,
                   "password_confirm": password_confirm, "rol": rol}
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
            return DesactivarUsuario(ok=False, error=result.get("detail", "Error al desactivar.") if result else "Error de conexión.")
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
            return ActivarUsuario(ok=False, error=result.get("detail", "Error al activar.") if result else "Error de conexión.")
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
            return VerificarCodigo(ok=False, error=result.get("detail", "Código inválido."), codigo_error=result.get("codigo", "ERROR"), intentos_restantes=result.get("intentos_restantes"))
        return VerificarCodigo(ok=True)


class ReenviarCodigo(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, email):
        auth_client.reenviar_codigo(email)
        return ReenviarCodigo(ok=True)


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

    def mutate(self, info, cedula, nombre, tipo_documento="CC", apellido="",
               email="", telefono="", restaurante_id=None, notas=""):
        jwt_user = get_jwt_user(info)
        if not jwt_user:
            return ClientePayload(ok=False, error="Debes iniciar sesión.")
        if jwt_user.get("rol") not in ("admin_central", "gerente_local", "cajero"):
            return ClientePayload(ok=False, error="Sin permiso para crear clientes.")
        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""
        rid = restaurante_id or jwt_user.get("restaurante_id")
        result = auth_client.post("/clientes/", {"tipo_documento": tipo_documento, "cedula": cedula, "nombre": nombre, "apellido": apellido,
                                  "email": email, "telefono": telefono, "restaurante_id": rid, "notas": notas, "activo": True}, token=token)
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
            f"/clientes/{cliente_id}/vincular-usuario/", {"usuario_id": str(usuario_id)}, token=token)
        if not result or result.get("_error"):
            return ClientePayload(ok=False, error=_extraer_error(result) if result else "Error de conexión.")
        return ClientePayload(ok=result.get("ok", False), message=result.get("message"), cliente=_map_cliente(result.get("cliente", {})) if result.get("ok") else None)


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
            f"/clientes/{cliente_id}/desvincular-usuario/", {}, token=token)
        if not result or result.get("_error"):
            return ClientePayload(ok=False, error=_extraer_error(result) if result else "Error de conexión.")
        return ClientePayload(ok=result.get("ok", False), message=result.get("message"))


def _extraer_error(result: dict) -> str:
    if not result:
        return "Error desconocido."
    errores_campo = {k: v for k, v in result.items() if k not in (
        "_error", "status", "detail", "codigo") and isinstance(v, (list, str))}
    if errores_campo:
        partes = []
        for campo, msg in errores_campo.items():
            texto = msg[0] if isinstance(msg, list) else msg
            partes.append(f"{campo}: {texto}")
        return " | ".join(partes)
    return result.get("detail", "Error al procesar la solicitud.")


class AuthMutation(graphene.ObjectType):
    bootstrap_admin = BootstrapAdmin.Field()
    crear_superusuario_django = CrearSuperusuarioDjango.Field()  # NUEVO
    login = Login.Field()
    refresh_token = RefreshToken.Field()
    auto_registro = AutoRegistro.Field()
    registrar_usuario = RegistrarUsuario.Field()
    verificar_codigo = VerificarCodigo.Field()
    reenviar_codigo = ReenviarCodigo.Field()
    desactivar_usuario = DesactivarUsuario.Field()
    activar_usuario = ActivarUsuario.Field()
    vincular_empleado_id = VincularEmpleadoId.Field()
    crear_cliente = CrearCliente.Field()
    editar_cliente = EditarCliente.Field()
    vincular_usuario_cliente = VincularUsuarioCliente.Field()
    desvincular_usuario_cliente = DesvincularUsuarioCliente.Field()

# gateway_service/app/gateway/graphql/services/auth/queries.py
# FIX: agrega resolver clientePorUsuarioId para que PerfilPage obtenga
#      el Cliente.id vinculado al usuario logueado (sin hacer logout/login).
# NUEVO: query crearSuperusuario movida a mutations, pero se agrega aquí
#        el resolver de clientePorUsuarioId.

import graphene
from .types import ClienteType, UsuarioType
from ....middleware.permissions import get_jwt_user, require_auth
from ....client import auth_client


class AuthQuery(graphene.ObjectType):

    me = graphene.Field(UsuarioType)
    usuarios = graphene.List(
        UsuarioType,
        rol=graphene.String(),
        activo=graphene.Boolean(),
        restaurante_id=graphene.ID(),
    )
    clientes = graphene.List(
        ClienteType,
        restaurante_id=graphene.ID(),
        activo=graphene.Boolean(),
        q=graphene.String(),
        search=graphene.String(),
    )
    cliente = graphene.Field(ClienteType, id=graphene.ID(required=True))
    buscar_cliente = graphene.List(
        ClienteType,
        cedula=graphene.String(required=True),
        restaurante_id=graphene.ID(),
    )
    # FIX: nuevo resolver para obtener el Cliente vinculado al usuario logueado
    cliente_por_usuario_id = graphene.Field(
        ClienteType,
        usuario_id=graphene.ID(required=True),
        description="Retorna el Cliente vinculado al usuario de la app. Usado por PerfilPage.",
    )

    @require_auth
    def resolve_me(self, info):
        user = get_jwt_user(info)
        return {
            "id":               user.get("user_id"),
            "email":            user.get("email"),
            "nombre":           user.get("nombre"),
            "rol":              user.get("rol"),
            "restaurante_id":   user.get("restaurante_id"),
            "empleado_id":      user.get("empleado_id"),
            "activo":           True,
            "email_verificado": True,
        }

    @require_auth
    def resolve_usuarios(self, info, rol=None, activo=None, restaurante_id=None):
        user = get_jwt_user(info)
        if user.get("rol") not in ("admin_central", "gerente_local"):
            raise PermissionError(
                "Solo admin_central y gerente_local pueden listar usuarios.")
        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""
        return auth_client.get_usuarios(rol=rol, activo=activo, restaurante_id=restaurante_id, token=token)

    @require_auth
    def resolve_clientes(self, info, restaurante_id=None, activo=None, q=None, search=None):
        user = get_jwt_user(info)
        if user.get("rol") not in ("admin_central", "gerente_local", "cajero", "supervisor"):
            raise PermissionError("Sin permiso para listar clientes.")
        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""
        texto = search or q
        params = {}
        if user.get("rol") == "admin_central":
            if restaurante_id:
                params["restaurante_id"] = restaurante_id
        else:
            jwt_restaurante = user.get("restaurante_id")
            if jwt_restaurante:
                params["restaurante_id"] = str(jwt_restaurante)
        if activo is not None:
            params["activo"] = str(activo).lower()
        if texto:
            params["q"] = texto
        data = auth_client.get_autenticado(
            "/clientes/", params=params, token=token)
        if not data or isinstance(data, dict):
            return []
        return [_map_cliente(c) for c in data]

    @require_auth
    def resolve_cliente(self, info, id):
        user = get_jwt_user(info)
        if user.get("rol") not in ("admin_central", "gerente_local", "cajero", "supervisor"):
            raise PermissionError("Sin permiso.")
        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""
        data = auth_client.get_autenticado(f"/clientes/{id}/", token=token)
        if not data or data.get("_error"):
            return None
        return _map_cliente(data)

    @require_auth
    def resolve_buscar_cliente(self, info, cedula, restaurante_id=None):
        user = get_jwt_user(info)
        if user.get("rol") not in ("admin_central", "gerente_local", "cajero"):
            raise PermissionError("Sin permiso para buscar clientes.")
        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""
        params = {"cedula": cedula}
        rid = restaurante_id or user.get("restaurante_id")
        if rid:
            params["restaurante_id"] = str(rid)
        data = auth_client.get_autenticado(
            "/clientes/buscar/", params=params, token=token)
        if not data or isinstance(data, dict):
            return []
        return [_map_cliente(c) for c in data]

    # FIX: resolver para obtener el Cliente del usuario logueado
    # Llama a /mi-perfil-cliente/ — endpoint que solo requiere estar logueado,
    # no requiere rol cajero/gerente. Usado por PerfilPage.
    def resolve_cliente_por_usuario_id(self, info, usuario_id):
        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""
        # Usar endpoint dedicado para clientes — no requiere rol especial
        data = auth_client.get_autenticado("/mi-perfil-cliente/", token=token)
        if not data or isinstance(data, dict) and data.get("_error"):
            return None
        if isinstance(data, dict) and data.get("id"):
            return _map_cliente(data)
        return None


def _map_cliente(d: dict) -> ClienteType:
    return ClienteType(
        id=d.get("id"),
        tipo_documento=d.get("tipo_documento"),
        tipo_documento_display=d.get("tipo_documento_display"),
        cedula=d.get("cedula"),
        nombre=d.get("nombre"),
        apellido=d.get("apellido", ""),
        nombre_completo=d.get("nombre_completo"),
        email=d.get("email", ""),
        telefono=d.get("telefono", ""),
        restaurante_id=d.get("restaurante_id"),
        usuario_id=d.get("usuario_id"),
        tiene_cuenta_app=d.get("tiene_cuenta_app", False),
        activo=d.get("activo"),
        notas=d.get("notas", ""),
        created_at=d.get("created_at"),
        updated_at=d.get("updated_at"),
    )

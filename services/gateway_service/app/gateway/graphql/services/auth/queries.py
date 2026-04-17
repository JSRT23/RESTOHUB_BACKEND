# gateway_service/app/gateway/graphql/services/auth/queries.py
import graphene
from .types import UsuarioType
from ....middleware.permissions import get_jwt_user, require_auth
from ....client import auth_client


class AuthQuery(graphene.ObjectType):

    me = graphene.Field(
        UsuarioType,
        description="Retorna el perfil del usuario autenticado.",
    )

    usuarios = graphene.List(
        UsuarioType,
        rol=graphene.String(),
        activo=graphene.Boolean(),
        restaurante_id=graphene.ID(),
        description="Lista todas las cuentas del sistema. Solo admin_central y gerente_local.",
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
        """
        Lista cuentas de auth_service.
        admin_central → ve todos con filtros opcionales.
        gerente_local → ve solo los de su restaurante (auth_service lo filtra).

        El token se pasa al auth_service para autenticar la llamada.
        """
        user = get_jwt_user(info)
        if user.get("rol") not in ("admin_central", "gerente_local"):
            raise PermissionError(
                "Solo admin_central y gerente_local pueden listar usuarios.")

        # Extraer el token del header para pasarlo al auth_service
        auth_header = info.context.META.get("HTTP_AUTHORIZATION", "")
        token = auth_header.split(
            " ", 1)[1] if auth_header.startswith("Bearer ") else ""

        return auth_client.get_usuarios(
            rol=rol,
            activo=activo,
            restaurante_id=restaurante_id,
            token=token,
        )

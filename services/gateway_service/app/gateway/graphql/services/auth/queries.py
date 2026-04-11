# gateway_service/app/gateway/graphql/services/auth/queries.py
import graphene
from .types import UsuarioType
from ....middleware.permissions import get_jwt_user, require_auth


class AuthQuery(graphene.ObjectType):

    me = graphene.Field(
        UsuarioType,
        description="Retorna el perfil del usuario autenticado.",
    )

    @require_auth
    def resolve_me(self, info):
        """Retorna los datos del usuario desde el JWT — sin llamar al auth_service."""
        user = get_jwt_user(info)
        return {
            "id":              user.get("user_id"),
            "email":           user.get("email"),
            "nombre":          user.get("nombre"),
            "rol":             user.get("rol"),
            "restaurante_id":  user.get("restaurante_id"),
            "empleado_id":     user.get("empleado_id"),
            "activo":          True,
            "email_verificado": True,
        }

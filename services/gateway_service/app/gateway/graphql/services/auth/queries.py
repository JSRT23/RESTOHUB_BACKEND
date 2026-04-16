# gateway_service/app/gateway/graphql/services/auth/queries.py
# ── Reemplaza el archivo completo ─────────────────────────────────────────
import graphene
from .types import UsuarioType
from ....middleware.permissions import get_jwt_user, require_auth
from ....client import auth_client


class AuthQuery(graphene.ObjectType):

    me = graphene.Field(
        UsuarioType,
        description="Retorna el perfil del usuario autenticado.",
    )

    # ── NUEVO ──────────────────────────────────────────────────────────────
    usuarios = graphene.List(
        UsuarioType,
        rol=graphene.String(),
        activo=graphene.Boolean(),
        restaurante_id=graphene.ID(),
        description="Lista todas las cuentas del sistema. Solo admin_central.",
    )

    @require_auth
    def resolve_me(self, info):
        """Retorna los datos del usuario desde el JWT — sin llamar al auth_service."""
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
        Acceso exclusivo para admin_central.
        """
        user = get_jwt_user(info)
        if user.get("rol") != "admin_central":
            raise PermissionError(
                "Solo el admin_central puede listar usuarios.")

        return auth_client.get_usuarios(
            rol=rol,
            activo=activo,
            restaurante_id=restaurante_id,
        )

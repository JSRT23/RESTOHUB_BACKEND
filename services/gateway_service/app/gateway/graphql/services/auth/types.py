# gateway_service/app/gateway/graphql/services/auth/types.py
import graphene


class UsuarioType(graphene.ObjectType):
    id = graphene.ID()
    email = graphene.String()
    nombre = graphene.String()
    rol = graphene.String()
    restaurante_id = graphene.ID()
    empleado_id = graphene.ID()
    activo = graphene.Boolean()
    email_verificado = graphene.Boolean()
    created_at = graphene.String()


class AuthPayloadType(graphene.ObjectType):
    """Respuesta del login exitoso."""
    access_token = graphene.String()
    refresh_token = graphene.String()
    token_type = graphene.String()
    expires_in = graphene.Int()
    usuario = graphene.Field(UsuarioType)

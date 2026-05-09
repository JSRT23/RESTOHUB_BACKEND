# gateway_service/app/gateway/graphql/services/auth/types.py
# CAMBIO v2: Agregado ClienteType y VincularUsuarioPayload.
# UsuarioType y AuthPayloadType sin cambios.

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


# ── NUEVO ──────────────────────────────────────────────────────────────────

class ClienteType(graphene.ObjectType):
    """
    Cliente identificado en el punto de venta físico (TPV/caja).
    El cajero lo busca por cédula para vincular ventas en tienda.
    """
    id = graphene.ID()
    tipo_documento = graphene.String()
    tipo_documento_display = graphene.String()
    cedula = graphene.String()
    nombre = graphene.String()
    apellido = graphene.String()
    nombre_completo = graphene.String()
    email = graphene.String()
    telefono = graphene.String()
    restaurante_id = graphene.ID()
    usuario_id = graphene.ID(
        description="UUID del Usuario de la app vinculado. Null si no tiene cuenta."
    )
    tiene_cuenta_app = graphene.Boolean()
    activo = graphene.Boolean()
    notas = graphene.String()
    created_at = graphene.String()
    updated_at = graphene.String()


class ClientePayload(graphene.ObjectType):
    ok = graphene.Boolean()
    error = graphene.String()
    message = graphene.String()
    cliente = graphene.Field(ClienteType)

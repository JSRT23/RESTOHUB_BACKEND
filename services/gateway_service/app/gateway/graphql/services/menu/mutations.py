# gateway_service/app/gateway/graphql/services/menu/mutations.py
import graphene
from .types import (
    RestauranteType, CategoriaType, PlatoType,
    IngredienteType, PrecioPlatoType,
)
from ....client import menu_client
from ....middleware.permissions import get_jwt_user


# ── Restaurante ────────────────────────────────────────────────────────────

class CrearRestaurante(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        pais = graphene.String(required=True)
        ciudad = graphene.String(required=True)
        direccion = graphene.String(required=True)
        moneda = graphene.String(required=True)

    ok = graphene.Boolean()
    restaurante = graphene.Field(RestauranteType)
    error = graphene.String()

    def mutate(self, info, **kwargs):
        data = menu_client.crear_restaurante(kwargs)
        if not data:
            return CrearRestaurante(ok=False, error="Error al crear restaurante.")
        return CrearRestaurante(ok=True, restaurante=data)


class ActualizarRestaurante(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        nombre = graphene.String()
        pais = graphene.String()
        ciudad = graphene.String()
        direccion = graphene.String()
        moneda = graphene.String()

    ok = graphene.Boolean()
    restaurante = graphene.Field(RestauranteType)
    error = graphene.String()

    def mutate(self, info, id, **kwargs):
        data = menu_client.actualizar_restaurante(id, kwargs)
        if not data:
            return ActualizarRestaurante(ok=False, error="Error al actualizar.")
        return ActualizarRestaurante(ok=True, restaurante=data)


class ActivarRestaurante(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()
    def mutate(self, info, id): return ActivarRestaurante(
        ok=bool(menu_client.activar_restaurante(id)))


class DesactivarRestaurante(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()
    def mutate(self, info, id): return DesactivarRestaurante(
        ok=bool(menu_client.desactivar_restaurante(id)))


# ── Categoría (solo admin_central) ────────────────────────────────────────

class CrearCategoria(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        descripcion = graphene.String()
        orden = graphene.Int()

    ok = graphene.Boolean()
    categoria = graphene.Field(CategoriaType)
    error = graphene.String()

    def mutate(self, info, nombre, descripcion=None, orden=None):
        jwt_user = get_jwt_user(info)
        if not jwt_user or jwt_user.get("rol") != "admin_central":
            return CrearCategoria(ok=False, error="Solo el admin central puede crear categorías.")
        data = menu_client.crear_categoria(
            {"nombre": nombre, "descripcion": descripcion, "orden": orden})
        if not data:
            return CrearCategoria(ok=False, error="Error al crear categoría.")
        return CrearCategoria(ok=True, categoria=data)


class ActualizarCategoria(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        nombre = graphene.String()
        descripcion = graphene.String()
        orden = graphene.Int()

    ok = graphene.Boolean()
    categoria = graphene.Field(CategoriaType)
    error = graphene.String()

    def mutate(self, info, id, **kwargs):
        jwt_user = get_jwt_user(info)
        if not jwt_user or jwt_user.get("rol") != "admin_central":
            return ActualizarCategoria(ok=False, error="Solo el admin central puede editar categorías.")
        payload = {k: v for k, v in kwargs.items() if v is not None}
        data = menu_client.actualizar_categoria(id, payload)
        if not data:
            return ActualizarCategoria(ok=False, error="Error al actualizar.")
        return ActualizarCategoria(ok=True, categoria=data)


class ActivarCategoria(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        jwt_user = get_jwt_user(info)
        if not jwt_user or jwt_user.get("rol") != "admin_central":
            return ActivarCategoria(ok=False, error="Sin permiso.")
        return ActivarCategoria(ok=bool(menu_client.activar_categoria(id)))


class DesactivarCategoria(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        jwt_user = get_jwt_user(info)
        if not jwt_user or jwt_user.get("rol") != "admin_central":
            return DesactivarCategoria(ok=False, error="Sin permiso.")
        return DesactivarCategoria(ok=bool(menu_client.desactivar_categoria(id)))


# ── Ingrediente ────────────────────────────────────────────────────────────

class CrearIngrediente(graphene.Mutation):
    """
    Crea un ingrediente.
    - Si restaurante_id es null → ingrediente global (solo admin_central debería hacerlo)
    - Si restaurante_id tiene valor → ingrediente del restaurante (gerente)
    """
    class Arguments:
        nombre = graphene.String(required=True)
        unidad_medida = graphene.String(required=True)
        descripcion = graphene.String()
        restaurante_id = graphene.ID(
            description="UUID del restaurante. null = ingrediente global.")

    ok = graphene.Boolean()
    ingrediente = graphene.Field(IngredienteType)
    error = graphene.String()

    def mutate(self, info, nombre, unidad_medida, descripcion=None, restaurante_id=None):
        payload = {"nombre": nombre, "unidad_medida": unidad_medida,
                   "descripcion": descripcion}
        if restaurante_id:
            payload["restaurante"] = restaurante_id
        data = menu_client.crear_ingrediente(payload)
        if not data:
            return CrearIngrediente(ok=False, error="Error al crear ingrediente.")
        return CrearIngrediente(ok=True, ingrediente=data)


class ActualizarIngrediente(graphene.Mutation):
    """Actualiza nombre y descripción (la unidad de medida no cambia)."""
    class Arguments:
        id = graphene.ID(required=True)
        nombre = graphene.String()
        descripcion = graphene.String()

    ok = graphene.Boolean()
    ingrediente = graphene.Field(IngredienteType)
    error = graphene.String()

    def mutate(self, info, id, nombre=None, descripcion=None):
        payload = {}
        if nombre is not None:
            payload["nombre"] = nombre
        if descripcion is not None:
            payload["descripcion"] = descripcion
        data = menu_client.actualizar_ingrediente(id, payload)
        if not data:
            return ActualizarIngrediente(ok=False, error="Error al actualizar ingrediente.")
        return ActualizarIngrediente(ok=True, ingrediente=data)


class ActivarIngrediente(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()
    def mutate(self, info, id): return ActivarIngrediente(
        ok=bool(menu_client.activar_ingrediente(id)))


class DesactivarIngrediente(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()
    def mutate(self, info, id): return DesactivarIngrediente(
        ok=bool(menu_client.desactivar_ingrediente(id)))


# ── Plato ──────────────────────────────────────────────────────────────────

class CrearPlato(graphene.Mutation):
    """
    restaurante_id = null → plato global (admin_central)
    restaurante_id = UUID → plato del restaurante (gerente)
    """
    class Arguments:
        nombre = graphene.String(required=True)
        descripcion = graphene.String(required=True)
        categoria_id = graphene.ID()
        imagen = graphene.String()
        restaurante_id = graphene.ID(
            description="UUID del restaurante. null = plato global.")

    ok = graphene.Boolean()
    plato = graphene.Field(PlatoType)
    error = graphene.String()

    def mutate(self, info, nombre, descripcion, categoria_id=None, imagen=None, restaurante_id=None):
        payload = {
            "nombre": nombre, "descripcion": descripcion,
            "categoria": categoria_id, "imagen": imagen,
        }
        if restaurante_id:
            payload["restaurante"] = restaurante_id
        data = menu_client.crear_plato(payload)
        if not data:
            return CrearPlato(ok=False, error="Error al crear plato.")
        return CrearPlato(ok=True, plato=data)


class ActualizarPlato(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        nombre = graphene.String()
        descripcion = graphene.String()
        categoria_id = graphene.ID()
        imagen = graphene.String()

    ok = graphene.Boolean()
    plato = graphene.Field(PlatoType)
    error = graphene.String()

    def mutate(self, info, id, categoria_id=None, **kwargs):
        payload = {k: v for k, v in kwargs.items() if v is not None}
        if categoria_id:
            payload["categoria"] = categoria_id
        data = menu_client.actualizar_plato(id, payload)
        if not data:
            return ActualizarPlato(ok=False, error="Error al actualizar plato.")
        return ActualizarPlato(ok=True, plato=data)


class ActivarPlato(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()
    def mutate(self, info, id): return ActivarPlato(
        ok=bool(menu_client.activar_plato(id)))


class DesactivarPlato(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()
    def mutate(self, info, id): return DesactivarPlato(
        ok=bool(menu_client.desactivar_plato(id)))


class AgregarIngredientePlato(graphene.Mutation):
    class Arguments:
        plato_id = graphene.ID(required=True)
        ingrediente_id = graphene.ID(required=True)
        cantidad = graphene.Float(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, plato_id, ingrediente_id, cantidad):
        result = menu_client.agregar_ingrediente_plato(
            plato_id, {"ingrediente": ingrediente_id,
                       "cantidad": str(cantidad)}
        )
        return AgregarIngredientePlato(
            ok=bool(result), error=None if result else "Error al agregar ingrediente."
        )


class QuitarIngredientePlato(graphene.Mutation):
    class Arguments:
        plato_id = graphene.ID(required=True)
        ingrediente_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, plato_id, ingrediente_id):
        result = menu_client.quitar_ingrediente_plato(plato_id, ingrediente_id)
        return QuitarIngredientePlato(
            ok=bool(result), error=None if result else "Error al quitar ingrediente."
        )


# ── Precio ─────────────────────────────────────────────────────────────────

class CrearPrecioPlato(graphene.Mutation):
    class Arguments:
        plato_id = graphene.ID(required=True)
        restaurante_id = graphene.ID(required=True)
        precio = graphene.Float(required=True)
        fecha_inicio = graphene.String(required=True)
        fecha_fin = graphene.String()

    ok = graphene.Boolean()
    precio_plato = graphene.Field(PrecioPlatoType)
    error = graphene.String()

    def mutate(self, info, plato_id, restaurante_id, precio, fecha_inicio, fecha_fin=None):
        data = menu_client.crear_precio({
            "plato": plato_id, "restaurante": restaurante_id,
            "precio": str(precio), "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin,
        })
        if not data:
            return CrearPrecioPlato(ok=False, error="Error al crear precio.")
        return CrearPrecioPlato(ok=True, precio_plato=data)


class ActivarPrecio(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()
    def mutate(self, info, id): return ActivarPrecio(
        ok=bool(menu_client.activar_precio(id)))


class DesactivarPrecio(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()
    def mutate(self, info, id): return DesactivarPrecio(
        ok=bool(menu_client.desactivar_precio(id)))


# ── Registro ───────────────────────────────────────────────────────────────

class MenuMutation(graphene.ObjectType):
    # Restaurante
    crear_restaurante = CrearRestaurante.Field()
    actualizar_restaurante = ActualizarRestaurante.Field()
    activar_restaurante = ActivarRestaurante.Field()
    desactivar_restaurante = DesactivarRestaurante.Field()

    # Categoría
    crear_categoria = CrearCategoria.Field()
    actualizar_categoria = ActualizarCategoria.Field()
    activar_categoria = ActivarCategoria.Field()
    desactivar_categoria = DesactivarCategoria.Field()

    # Ingrediente — ahora completo
    crear_ingrediente = CrearIngrediente.Field()
    actualizar_ingrediente = ActualizarIngrediente.Field()
    activar_ingrediente = ActivarIngrediente.Field()
    desactivar_ingrediente = DesactivarIngrediente.Field()

    # Plato
    crear_plato = CrearPlato.Field()
    actualizar_plato = ActualizarPlato.Field()
    activar_plato = ActivarPlato.Field()
    desactivar_plato = DesactivarPlato.Field()
    agregar_ingrediente_plato = AgregarIngredientePlato.Field()
    quitar_ingrediente_plato = QuitarIngredientePlato.Field()

    # Precio
    crear_precio_plato = CrearPrecioPlato.Field()
    activar_precio = ActivarPrecio.Field()
    desactivar_precio = DesactivarPrecio.Field()

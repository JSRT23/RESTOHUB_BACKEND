import graphene
from .types import (
    RestauranteType, CategoriaType, PlatoType,
    IngredienteType, PrecioPlatoType,
)
from ....client import menu_client


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
        return CrearRestaurante(ok=True, restaurante=RestauranteType(**data))


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
        return ActualizarRestaurante(ok=True, restaurante=RestauranteType(**data))


class ActivarRestaurante(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        return ActivarRestaurante(ok=bool(menu_client.activar_restaurante(id)))


class DesactivarRestaurante(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        return DesactivarRestaurante(ok=bool(menu_client.desactivar_restaurante(id)))


class CrearCategoria(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        orden = graphene.Int()
    ok = graphene.Boolean()
    categoria = graphene.Field(CategoriaType)
    error = graphene.String()

    def mutate(self, info, nombre, orden=0):
        data = menu_client.crear_categoria({"nombre": nombre, "orden": orden})
        if not data:
            return CrearCategoria(ok=False, error="Error al crear categoría.")
        return CrearCategoria(ok=True, categoria=CategoriaType(**data))


class CrearPlato(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        descripcion = graphene.String(required=True)
        categoria_id = graphene.ID()
        imagen = graphene.String()
    ok = graphene.Boolean()
    plato = graphene.Field(PlatoType)
    error = graphene.String()

    def mutate(self, info, nombre, descripcion, categoria_id=None, imagen=None):
        data = menu_client.crear_plato({
            "nombre": nombre, "descripcion": descripcion,
            "categoria": categoria_id, "imagen": imagen,
        })
        if not data:
            return CrearPlato(ok=False, error="Error al crear plato.")
        return CrearPlato(ok=True, plato=PlatoType(**data))


class ActivarPlato(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        return ActivarPlato(ok=bool(menu_client.activar_plato(id)))


class DesactivarPlato(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        return DesactivarPlato(ok=bool(menu_client.desactivar_plato(id)))


class AgregarIngredientePlato(graphene.Mutation):
    class Arguments:
        plato_id = graphene.ID(required=True)
        ingrediente_id = graphene.ID(required=True)
        cantidad = graphene.Float(required=True)
    ok = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, plato_id, ingrediente_id, cantidad):
        result = menu_client.agregar_ingrediente_plato(
            plato_id, {"ingrediente": ingrediente_id, "cantidad": cantidad}
        )
        return AgregarIngredientePlato(ok=bool(result))


class CrearIngrediente(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        unidad_medida = graphene.String(required=True)
        descripcion = graphene.String()
    ok = graphene.Boolean()
    ingrediente = graphene.Field(IngredienteType)
    error = graphene.String()

    def mutate(self, info, nombre, unidad_medida, descripcion=None):
        data = menu_client.crear_ingrediente({
            "nombre": nombre, "unidad_medida": unidad_medida, "descripcion": descripcion,
        })
        if not data:
            return CrearIngrediente(ok=False, error="Error al crear ingrediente.")
        return CrearIngrediente(ok=True, ingrediente=IngredienteType(**data))


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
            "precio": precio, "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin,
        })
        if not data:
            return CrearPrecioPlato(ok=False, error="Error al crear precio.")
        return CrearPrecioPlato(ok=True, precio_plato=PrecioPlatoType(**data))


class MenuMutation(graphene.ObjectType):
    crear_restaurante = CrearRestaurante.Field()
    actualizar_restaurante = ActualizarRestaurante.Field()
    activar_restaurante = ActivarRestaurante.Field()
    desactivar_restaurante = DesactivarRestaurante.Field()
    crear_categoria = CrearCategoria.Field()
    crear_plato = CrearPlato.Field()
    activar_plato = ActivarPlato.Field()
    desactivar_plato = DesactivarPlato.Field()
    agregar_ingrediente_plato = AgregarIngredientePlato.Field()
    crear_ingrediente = CrearIngrediente.Field()
    crear_precio_plato = CrearPrecioPlato.Field()

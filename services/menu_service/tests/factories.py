# tests/factories.py
import uuid
from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from app.menu.models import (
    Restaurante, Categoria, Ingrediente, Plato,
    PlatoIngrediente, PrecioPlato,
    Moneda, UnidadMedida,
)


class RestauranteFactory(DjangoModelFactory):
    class Meta:
        model = Restaurante

    id = factory.LazyFunction(uuid.uuid4)
    nombre = factory.Sequence(lambda n: f"Restaurante {n}")
    pais = "Colombia"
    ciudad = "Bogotá"
    direccion = factory.Sequence(lambda n: f"Calle {n} # 1-23")
    moneda = Moneda.COP
    activo = True


class CategoriaFactory(DjangoModelFactory):
    class Meta:
        model = Categoria

    id = factory.LazyFunction(uuid.uuid4)
    nombre = factory.Sequence(lambda n: f"Categoría {n}")
    orden = factory.Sequence(lambda n: n)
    activo = True


class IngredienteFactory(DjangoModelFactory):
    """Ingrediente global por defecto (restaurante=None)."""
    class Meta:
        model = Ingrediente

    id = factory.LazyFunction(uuid.uuid4)
    restaurante = None
    nombre = factory.Sequence(lambda n: f"Ingrediente {n}")
    unidad_medida = UnidadMedida.UNIDAD
    descripcion = "Descripción de prueba"
    activo = True

    @classmethod
    def local(cls, restaurante, **kwargs):
        return cls(restaurante=restaurante, **kwargs)


class PlatoFactory(DjangoModelFactory):
    """Plato global por defecto (restaurante=None)."""
    class Meta:
        model = Plato

    id = factory.LazyFunction(uuid.uuid4)
    restaurante = None
    nombre = factory.Sequence(lambda n: f"Plato {n}")
    descripcion = "Descripción del plato"
    categoria = factory.SubFactory(CategoriaFactory)
    imagen = None
    activo = True

    @classmethod
    def local(cls, restaurante, **kwargs):
        return cls(restaurante=restaurante, **kwargs)


class PlatoIngredienteFactory(DjangoModelFactory):
    class Meta:
        model = PlatoIngrediente

    id = factory.LazyFunction(uuid.uuid4)
    plato = factory.SubFactory(PlatoFactory)
    ingrediente = factory.SubFactory(IngredienteFactory)
    cantidad = "100.000"


class PrecioPlatoFactory(DjangoModelFactory):
    """Precio vigente por defecto."""
    class Meta:
        model = PrecioPlato
        exclude = ["skip_clean"]

    skip_clean = False

    id = factory.LazyFunction(uuid.uuid4)
    plato = factory.SubFactory(PlatoFactory)
    restaurante = factory.SubFactory(RestauranteFactory)
    precio = "15000.00"
    fecha_inicio = factory.LazyFunction(
        lambda: timezone.now() - timedelta(hours=1))
    fecha_fin = None
    activo = True

    class Params:
        vencido = factory.Trait(
            fecha_fin=factory.LazyFunction(
                lambda: timezone.now() - timedelta(minutes=1))
        )
        futuro = factory.Trait(
            fecha_inicio=factory.LazyFunction(
                lambda: timezone.now() + timedelta(hours=1))
        )

    @classmethod
    def vencido(cls, **kwargs):
        return cls(vencido=True, **kwargs)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Bypass full_clean para poder crear precios con fecha pasada en tests."""
        kwargs.pop("skip_clean", None)
        obj = model_class(**kwargs)
        obj.save_base(force_insert=True)
        return obj

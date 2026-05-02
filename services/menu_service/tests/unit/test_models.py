# tests/unit/test_models.py
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from app.menu.models import (
    Restaurante, Categoria, Ingrediente, Plato,
    PlatoIngrediente, PrecioPlato, Moneda, UnidadMedida,
)
from tests.factories import (
    RestauranteFactory, CategoriaFactory, IngredienteFactory,
    PlatoFactory, PlatoIngredienteFactory, PrecioPlatoFactory,
)


# ═══════════════════════════════════════════════════════════════════════════
# Restaurante
# ═══════════════════════════════════════════════════════════════════════════

class TestRestauranteModel:

    def test_crear_restaurante(self, db):
        r = RestauranteFactory()
        assert Restaurante.objects.filter(pk=r.pk).exists()

    def test_id_es_uuid(self, db):
        r = RestauranteFactory()
        assert isinstance(r.id, uuid.UUID)

    def test_str(self, db):
        r = RestauranteFactory(
            nombre="La Brasa", ciudad="Medellín", pais="Colombia")
        assert "La Brasa" in str(r)
        assert "Medellín" in str(r)

    def test_moneda_default_cop(self, db):
        r = RestauranteFactory()
        assert r.moneda == Moneda.COP

    def test_activo_por_defecto(self, db):
        r = RestauranteFactory()
        assert r.activo is True

    def test_ordering_por_pais_ciudad_nombre(self, db):
        r1 = RestauranteFactory(pais="Colombia", ciudad="Bogotá", nombre="A")
        r2 = RestauranteFactory(pais="Colombia", ciudad="Bogotá", nombre="B")
        qs = list(Restaurante.objects.all())
        assert qs.index(r1) < qs.index(r2)


# ═══════════════════════════════════════════════════════════════════════════
# Categoria
# ═══════════════════════════════════════════════════════════════════════════

class TestCategoriaModel:

    def test_crear_categoria(self, db):
        c = CategoriaFactory()
        assert Categoria.objects.filter(pk=c.pk).exists()

    def test_nombre_unico(self, db):
        CategoriaFactory(nombre="Entradas")
        with pytest.raises(Exception):
            CategoriaFactory(nombre="Entradas")

    def test_str(self, db):
        c = CategoriaFactory(nombre="Postres")
        assert str(c) == "Postres"

    def test_activo_default_true(self, db):
        c = CategoriaFactory()
        assert c.activo is True

    def test_orden_default_cero(self, db):
        c = Categoria.objects.create(nombre="Sin orden")
        assert c.orden == 0


# ═══════════════════════════════════════════════════════════════════════════
# Ingrediente
# ═══════════════════════════════════════════════════════════════════════════

class TestIngredienteModel:

    def test_ingrediente_global(self, db):
        i = IngredienteFactory()
        assert i.restaurante is None

    def test_ingrediente_local(self, db, restaurante):
        i = IngredienteFactory.local(restaurante=restaurante)
        assert i.restaurante == restaurante

    def test_str_global(self, db):
        i = IngredienteFactory(nombre="Sal")
        assert "Sal" in str(i)
        assert "Global" in str(i)

    def test_str_local(self, db, restaurante):
        i = IngredienteFactory.local(restaurante=restaurante, nombre="Ají")
        assert "Ají" in str(i)
        assert restaurante.nombre in str(i)

    def test_nombre_unico_por_restaurante(self, db, restaurante):
        IngredienteFactory.local(restaurante=restaurante, nombre="Tomate")
        with pytest.raises(Exception):
            IngredienteFactory.local(restaurante=restaurante, nombre="Tomate")

    def test_mismo_nombre_en_distintos_restaurantes(self, db, restaurante, restaurante2):
        i1 = IngredienteFactory.local(restaurante=restaurante, nombre="Tomate")
        i2 = IngredienteFactory.local(
            restaurante=restaurante2, nombre="Tomate")
        assert i1.pk != i2.pk

    def test_mismo_nombre_global_y_local(self, db, restaurante):
        """El nombre puede repetirse entre global y local."""
        ig = IngredienteFactory(nombre="Harina")
        il = IngredienteFactory.local(restaurante=restaurante, nombre="Harina")
        assert ig.pk != il.pk

    def test_cascade_delete_con_restaurante(self, db, restaurante):
        i = IngredienteFactory.local(restaurante=restaurante)
        restaurante.delete()
        assert not Ingrediente.objects.filter(pk=i.pk).exists()


# ═══════════════════════════════════════════════════════════════════════════
# Plato
# ═══════════════════════════════════════════════════════════════════════════

class TestPlatoModel:

    def test_plato_global(self, db):
        p = PlatoFactory()
        assert p.restaurante is None

    def test_plato_local(self, db, restaurante):
        p = PlatoFactory.local(restaurante=restaurante)
        assert p.restaurante == restaurante

    def test_str_global(self, db):
        p = PlatoFactory(nombre="Bandeja Paisa")
        assert "Bandeja Paisa" in str(p)
        assert "Global" in str(p)

    def test_str_local(self, db, restaurante):
        p = PlatoFactory.local(restaurante=restaurante, nombre="Ajiaco")
        assert "Ajiaco" in str(p)
        assert restaurante.nombre in str(p)

    def test_categoria_puede_ser_null(self, db):
        p = PlatoFactory(categoria=None)
        assert p.categoria is None

    def test_activo_default_true(self, db):
        p = PlatoFactory()
        assert p.activo is True


# ═══════════════════════════════════════════════════════════════════════════
# PlatoIngrediente
# ═══════════════════════════════════════════════════════════════════════════

class TestPlatoIngredienteModel:

    def test_crear_relacion(self, db):
        pi = PlatoIngredienteFactory(cantidad=Decimal("100"))
        assert pi.pk is not None

    def test_cantidad_positiva(self, db):
        pi = PlatoIngredienteFactory(cantidad=Decimal("0.5"))
        assert pi.cantidad == Decimal("0.5")

    def test_cantidad_cero_falla(self, db):
        plato = PlatoFactory()
        ing = IngredienteFactory()
        with pytest.raises(ValidationError):
            PlatoIngrediente(plato=plato, ingrediente=ing, cantidad=0).save()

    def test_cantidad_negativa_falla(self, db):
        plato = PlatoFactory()
        ing = IngredienteFactory()
        with pytest.raises(ValidationError):
            PlatoIngrediente(plato=plato, ingrediente=ing, cantidad=-5).save()

    def test_unicidad_plato_ingrediente(self, db):
        pi = PlatoIngredienteFactory()
        with pytest.raises(Exception):
            PlatoIngredienteFactory(plato=pi.plato, ingrediente=pi.ingrediente)

    def test_str(self, db):
        pi = PlatoIngredienteFactory()
        assert pi.plato.nombre in str(pi)
        assert pi.ingrediente.nombre in str(pi)

    def test_cascade_delete_plato(self, db):
        pi = PlatoIngredienteFactory()
        pk = pi.pk
        pi.plato.delete()
        assert not PlatoIngrediente.objects.filter(pk=pk).exists()


# ═══════════════════════════════════════════════════════════════════════════
# PrecioPlato
# ═══════════════════════════════════════════════════════════════════════════

class TestPrecioPlatoModel:

    def test_precio_positivo(self, db):
        pp = PrecioPlatoFactory(precio=Decimal("25000"))
        assert pp.precio == Decimal("25000")

    def test_precio_cero_falla(self, db):
        plato = PlatoFactory()
        rest = RestauranteFactory()
        pp = PrecioPlato(
            plato=plato, restaurante=rest, precio=0,
            fecha_inicio=timezone.now() + timedelta(hours=1),
        )
        with pytest.raises(ValidationError):
            pp.full_clean()

    def test_precio_negativo_falla(self, db):
        plato = PlatoFactory()
        rest = RestauranteFactory()
        pp = PrecioPlato(
            plato=plato, restaurante=rest, precio=-100,
            fecha_inicio=timezone.now() + timedelta(hours=1),
        )
        with pytest.raises(ValidationError):
            pp.full_clean()

    def test_fecha_fin_anterior_a_inicio_falla(self, db):
        plato = PlatoFactory()
        rest = RestauranteFactory()
        inicio = timezone.now() + timedelta(hours=1)
        fin = inicio - timedelta(minutes=1)
        pp = PrecioPlato(
            plato=plato, restaurante=rest, precio=1000,
            fecha_inicio=inicio, fecha_fin=fin,
        )
        with pytest.raises(ValidationError):
            pp.full_clean()

    def test_esta_vigente_true(self, db):
        pp = PrecioPlatoFactory()
        assert pp.esta_vigente is True

    def test_esta_vigente_false_inactivo(self, db):
        pp = PrecioPlatoFactory(activo=False)
        assert pp.esta_vigente is False

    def test_esta_vigente_false_vencido(self, db):
        pp = PrecioPlatoFactory.vencido()
        assert pp.esta_vigente is False

    def test_str(self, db):
        pp = PrecioPlatoFactory()
        assert pp.plato.nombre in str(pp)
        assert pp.restaurante.nombre in str(pp)

    def test_cascade_delete_plato(self, db):
        pp = PrecioPlatoFactory()
        pk = pp.pk
        pp.plato.delete()
        assert not PrecioPlato.objects.filter(pk=pk).exists()

    def test_cascade_delete_restaurante(self, db):
        pp = PrecioPlatoFactory()
        pk = pp.pk
        pp.restaurante.delete()
        assert not PrecioPlato.objects.filter(pk=pk).exists()

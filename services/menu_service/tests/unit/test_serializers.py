# tests/unit/test_serializers.py
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from app.menu.serializers import (
    RestauranteSerializer, CategoriaSerializer,
    IngredienteSerializer, IngredienteWriteSerializer,
    PlatoSerializer, PlatoListSerializer, PlatoWriteSerializer,
    PrecioPlatoSerializer, PrecioPlatoWriteSerializer,
    PlatoIngredienteSerializer, PlatoIngredienteWriteSerializer,
)
from tests.factories import (
    RestauranteFactory, CategoriaFactory, IngredienteFactory,
    PlatoFactory, PrecioPlatoFactory, PlatoIngredienteFactory,
)


# ═══════════════════════════════════════════════════════════════════════════
# RestauranteSerializer
# ═══════════════════════════════════════════════════════════════════════════

class TestRestauranteSerializer:

    def test_campos_presentes(self, db):
        r = RestauranteFactory()
        data = RestauranteSerializer(r).data
        for campo in ("id", "nombre", "pais", "ciudad", "moneda", "activo"):
            assert campo in data

    def test_id_read_only(self, db):
        r = RestauranteFactory()
        s = RestauranteSerializer(r, data={"id": "nuevo-id", "nombre": "X",
                                           "pais": "CO", "ciudad": "Cali",
                                           "direccion": "Cra 1"}, partial=True)
        s.is_valid()
        assert str(r.id) in str(RestauranteSerializer(r).data["id"])

    def test_datos_validos(self, db):
        data = {
            "nombre": "Nuevo Resto", "pais": "Colombia",
            "ciudad": "Cali", "direccion": "Cra 1 # 2-3",
            "moneda": "COP",
        }
        s = RestauranteSerializer(data=data)
        assert s.is_valid(), s.errors


# ═══════════════════════════════════════════════════════════════════════════
# CategoriaSerializer
# ═══════════════════════════════════════════════════════════════════════════

class TestCategoriaSerializer:

    def test_serializa_correctamente(self, db):
        c = CategoriaFactory(nombre="Bebidas", orden=2)
        data = CategoriaSerializer(c).data
        assert data["nombre"] == "Bebidas"
        assert data["orden"] == 2

    def test_datos_validos(self, db):
        s = CategoriaSerializer(
            data={"nombre": "Sopas", "orden": 1, "activo": True})
        assert s.is_valid(), s.errors

    def test_nombre_requerido(self, db):
        s = CategoriaSerializer(data={"orden": 1})
        assert not s.is_valid()
        assert "nombre" in s.errors


# ═══════════════════════════════════════════════════════════════════════════
# IngredienteWriteSerializer
# ═══════════════════════════════════════════════════════════════════════════

class TestIngredienteWriteSerializer:

    def test_nombre_vacio_falla(self, db):
        s = IngredienteWriteSerializer(
            data={"nombre": "   ", "unidad_medida": "g"})
        assert not s.is_valid()
        assert "nombre" in s.errors

    def test_nombre_se_limpia(self, db):
        s = IngredienteWriteSerializer(
            data={"nombre": "  Arroz  ", "unidad_medida": "kg"})
        assert s.is_valid(), s.errors
        assert s.validated_data["nombre"] == "Arroz"

    def test_restaurante_opcional(self, db):
        s = IngredienteWriteSerializer(
            data={"nombre": "Sal", "unidad_medida": "g"})
        assert s.is_valid(), s.errors
        assert s.validated_data.get("restaurante") is None

    def test_restaurante_valido(self, db, restaurante):
        s = IngredienteWriteSerializer(data={
            "nombre": "Pimienta", "unidad_medida": "g",
            "restaurante": str(restaurante.id),
        })
        assert s.is_valid(), s.errors


# ═══════════════════════════════════════════════════════════════════════════
# PlatoWriteSerializer
# ═══════════════════════════════════════════════════════════════════════════

class TestPlatoWriteSerializer:

    def test_nombre_vacio_falla(self, db, categoria):
        s = PlatoWriteSerializer(data={
            "nombre": "", "descripcion": "X", "categoria": str(categoria.id)
        })
        assert not s.is_valid()
        assert "nombre" in s.errors

    def test_nombre_se_limpia(self, db, categoria):
        s = PlatoWriteSerializer(data={
            "nombre": "  Bandeja  ", "descripcion": "Plato típico",
            "categoria": str(categoria.id),
        })
        assert s.is_valid(), s.errors
        assert s.validated_data["nombre"] == "Bandeja"

    def test_restaurante_opcional(self, db):
        s = PlatoWriteSerializer(
            data={"nombre": "Sopa", "descripcion": "Rica"})
        assert s.is_valid(), s.errors


# ═══════════════════════════════════════════════════════════════════════════
# PrecioPlatoWriteSerializer — validaciones
# ═══════════════════════════════════════════════════════════════════════════

class TestPrecioPlatoWriteSerializer:

    def _data(self, plato, restaurante, **kwargs):
        base = {
            "plato": str(plato.id),
            "restaurante": str(restaurante.id),
            "precio": "15000.00",
            "fecha_inicio": (timezone.now() + timedelta(hours=1)).isoformat(),
        }
        base.update(kwargs)
        return base

    def test_datos_validos(self, db, plato_global, restaurante):
        s = PrecioPlatoWriteSerializer(
            data=self._data(plato_global, restaurante))
        assert s.is_valid(), s.errors

    def test_precio_cero_falla(self, db, plato_global, restaurante):
        s = PrecioPlatoWriteSerializer(data=self._data(
            plato_global, restaurante, precio="0"))
        assert not s.is_valid()
        assert "precio" in s.errors

    def test_precio_negativo_falla(self, db, plato_global, restaurante):
        s = PrecioPlatoWriteSerializer(data=self._data(
            plato_global, restaurante, precio="-500"))
        assert not s.is_valid()
        assert "precio" in s.errors

    def test_fecha_inicio_pasada_falla(self, db, plato_global, restaurante):
        s = PrecioPlatoWriteSerializer(data=self._data(
            plato_global, restaurante,
            fecha_inicio=(timezone.now() - timedelta(hours=1)).isoformat()
        ))
        assert not s.is_valid()
        assert "fecha_inicio" in s.errors

    def test_fecha_fin_antes_de_inicio_falla(self, db, plato_global, restaurante):
        inicio = timezone.now() + timedelta(hours=2)
        fin = inicio - timedelta(hours=1)
        s = PrecioPlatoWriteSerializer(data=self._data(
            plato_global, restaurante,
            fecha_inicio=inicio.isoformat(),
            fecha_fin=fin.isoformat(),
        ))
        assert not s.is_valid()
        assert "fecha_fin" in s.errors

    def test_fecha_inicio_pasada_no_falla_en_update(self, db, plato_global, restaurante):
        """En updates (instance!=None) no se valida que fecha_inicio sea futura."""
        pp = PrecioPlatoFactory(plato=plato_global, restaurante=restaurante)
        s = PrecioPlatoWriteSerializer(
            instance=pp,
            data={"precio": "20000.00"},
            partial=True,
        )
        assert s.is_valid(), s.errors


# ═══════════════════════════════════════════════════════════════════════════
# PlatoIngredienteWriteSerializer
# ═══════════════════════════════════════════════════════════════════════════

class TestPlatoIngredienteWriteSerializer:

    def test_cantidad_cero_falla(self, db, ingrediente_global):
        s = PlatoIngredienteWriteSerializer(data={
            "ingrediente": str(ingrediente_global.id),
            "cantidad": "0",
        })
        assert not s.is_valid()
        assert "cantidad" in s.errors

    def test_cantidad_negativa_falla(self, db, ingrediente_global):
        s = PlatoIngredienteWriteSerializer(data={
            "ingrediente": str(ingrediente_global.id),
            "cantidad": "-10",
        })
        assert not s.is_valid()
        assert "cantidad" in s.errors

    def test_datos_validos(self, db, ingrediente_global):
        s = PlatoIngredienteWriteSerializer(data={
            "ingrediente": str(ingrediente_global.id),
            "cantidad": "200.500",
        })
        assert s.is_valid(), s.errors

# tests/integration/test_precios_menu.py
from datetime import timedelta

import pytest
from django.utils import timezone

from tests.factories import (
    RestauranteFactory, CategoriaFactory,
    PlatoFactory, PrecioPlatoFactory,
)

PRECIOS_URL = "/api/menu/precios/"
RESTAURANTES_URL = "/api/menu/restaurantes/"


# ═══════════════════════════════════════════════════════════════════════════
# PrecioPlato
# ═══════════════════════════════════════════════════════════════════════════

class TestPrecioPlatoViewSet:

    def _data(self, plato, restaurante, **kwargs):
        base = {
            "plato": str(plato.id),
            "restaurante": str(restaurante.id),
            "precio": "18000.00",
            "fecha_inicio": (timezone.now() + timedelta(hours=1)).isoformat(),
        }
        base.update(kwargs)
        return base

    def test_listar_precios(self, db, api_client):
        PrecioPlatoFactory.create_batch(2)
        res = api_client.get(PRECIOS_URL)
        assert res.status_code == 200
        assert len(res.data) == 2

    def test_crear_precio(self, db, api_client, plato_global, restaurante):
        res = api_client.post(
            PRECIOS_URL, self._data(plato_global, restaurante))
        assert res.status_code == 201
        assert "precio" in res.data

    def test_precio_cero_falla(self, db, api_client, plato_global, restaurante):
        res = api_client.post(PRECIOS_URL, self._data(
            plato_global, restaurante, precio="0"))
        assert res.status_code == 400

    def test_precio_negativo_falla(self, db, api_client, plato_global, restaurante):
        res = api_client.post(PRECIOS_URL, self._data(
            plato_global, restaurante, precio="-500"))
        assert res.status_code == 400

    def test_fecha_inicio_pasada_falla(self, db, api_client, plato_global, restaurante):
        res = api_client.post(PRECIOS_URL, self._data(
            plato_global, restaurante,
            fecha_inicio=(timezone.now() - timedelta(hours=1)).isoformat()
        ))
        assert res.status_code == 400

    def test_fecha_fin_antes_inicio_falla(self, db, api_client, plato_global, restaurante):
        inicio = timezone.now() + timedelta(hours=2)
        fin = inicio - timedelta(hours=1)
        res = api_client.post(PRECIOS_URL, self._data(
            plato_global, restaurante,
            fecha_inicio=inicio.isoformat(),
            fecha_fin=fin.isoformat(),
        ))
        assert res.status_code == 400

    def test_detalle_precio(self, db, api_client, precio):
        res = api_client.get(f"{PRECIOS_URL}{precio.id}/")
        assert res.status_code == 200
        assert "esta_vigente" in res.data
        assert "moneda" in res.data

    def test_precio_vigente_true(self, db, api_client, precio):
        res = api_client.get(f"{PRECIOS_URL}{precio.id}/")
        assert res.data["esta_vigente"] is True

    def test_precio_vencido_no_vigente(self, db, api_client):
        pp = PrecioPlatoFactory.vencido()
        res = api_client.get(f"{PRECIOS_URL}{pp.id}/")
        assert res.data["esta_vigente"] is False

    def test_actualizar_precio(self, db, api_client, precio):
        res = api_client.patch(
            f"{PRECIOS_URL}{precio.id}/",
            {"precio": "20000.00"},
        )
        assert res.status_code == 200
        assert res.data["precio"] == "20000.00"

    def test_eliminar_precio(self, db, api_client, precio):
        res = api_client.delete(f"{PRECIOS_URL}{precio.id}/")
        assert res.status_code == 204

    def test_activar_precio(self, db, api_client):
        pp = PrecioPlatoFactory(activo=False)
        res = api_client.post(f"{PRECIOS_URL}{pp.id}/activar/")
        assert res.status_code == 200
        pp.refresh_from_db()
        assert pp.activo is True

    def test_desactivar_precio(self, db, api_client, precio):
        res = api_client.post(f"{PRECIOS_URL}{precio.id}/desactivar/")
        assert res.status_code == 200
        precio.refresh_from_db()
        assert precio.activo is False

    def test_filtrar_por_plato(self, db, api_client, plato_global, restaurante):
        PrecioPlatoFactory(plato=plato_global, restaurante=restaurante)
        otro_plato = PlatoFactory()
        PrecioPlatoFactory(plato=otro_plato, restaurante=restaurante)
        res = api_client.get(f"{PRECIOS_URL}?plato={plato_global.id}")
        assert len(res.data) == 1

    def test_filtrar_por_restaurante(self, db, api_client, restaurante, restaurante2):
        PrecioPlatoFactory(restaurante=restaurante)
        PrecioPlatoFactory(restaurante=restaurante2)
        res = api_client.get(f"{PRECIOS_URL}?restaurante={restaurante.id}")
        assert len(res.data) == 1

    def test_filtrar_por_activo(self, db, api_client):
        PrecioPlatoFactory(activo=True)
        PrecioPlatoFactory(activo=False)
        res = api_client.get(f"{PRECIOS_URL}?activo=true")
        assert all(p["activo"] for p in res.data)

    def test_serializer_expone_plato_id_y_restaurante_id(self, db, api_client, precio):
        res = api_client.get(f"{PRECIOS_URL}{precio.id}/")
        assert "plato_id" in res.data
        assert "restaurante_id" in res.data
        assert "restaurante_nombre" in res.data

    def test_publicar_evento_al_crear(self, db, api_client, plato_global, restaurante, mock_rabbitmq):
        api_client.post(PRECIOS_URL, self._data(plato_global, restaurante))
        assert mock_rabbitmq.called

    def test_publicar_evento_al_actualizar(self, db, api_client, precio, mock_rabbitmq):
        api_client.patch(f"{PRECIOS_URL}{precio.id}/", {"precio": "99000.00"})
        assert mock_rabbitmq.called


# ═══════════════════════════════════════════════════════════════════════════
# Menú público del restaurante
# ═══════════════════════════════════════════════════════════════════════════

class TestMenuRestauranteAction:

    def test_menu_retorna_estructura(self, db, api_client, restaurante):
        res = api_client.get(f"{RESTAURANTES_URL}{restaurante.id}/menu/")
        assert res.status_code == 200
        assert "restaurante_id" in res.data
        assert "categorias" in res.data

    def test_menu_sin_platos_tiene_categorias_vacias(self, db, api_client, restaurante):
        res = api_client.get(f"{RESTAURANTES_URL}{restaurante.id}/menu/")
        assert res.data["categorias"] == []

    def test_menu_incluye_platos_con_precio_activo(self, db, api_client):
        restaurante = RestauranteFactory()
        categoria = CategoriaFactory()
        plato = PlatoFactory(categoria=categoria, activo=True)
        PrecioPlatoFactory(plato=plato, restaurante=restaurante, activo=True)

        res = api_client.get(f"{RESTAURANTES_URL}{restaurante.id}/menu/")
        assert res.status_code == 200
        categorias = res.data["categorias"]
        assert len(categorias) == 1
        assert len(categorias[0]["platos"]) == 1
        assert categorias[0]["platos"][0]["nombre"] == plato.nombre

    def test_menu_excluye_platos_sin_precio(self, db, api_client):
        restaurante = RestauranteFactory()
        categoria = CategoriaFactory()
        PlatoFactory(categoria=categoria, activo=True)  # sin precio

        res = api_client.get(f"{RESTAURANTES_URL}{restaurante.id}/menu/")
        assert res.data["categorias"] == []

    def test_menu_excluye_platos_con_precio_inactivo(self, db, api_client):
        restaurante = RestauranteFactory()
        categoria = CategoriaFactory()
        plato = PlatoFactory(categoria=categoria, activo=True)
        PrecioPlatoFactory(plato=plato, restaurante=restaurante, activo=False)

        res = api_client.get(f"{RESTAURANTES_URL}{restaurante.id}/menu/")
        assert res.data["categorias"] == []

    def test_menu_excluye_platos_inactivos(self, db, api_client):
        restaurante = RestauranteFactory()
        categoria = CategoriaFactory()
        plato = PlatoFactory(categoria=categoria, activo=False)
        PrecioPlatoFactory(plato=plato, restaurante=restaurante, activo=True)

        res = api_client.get(f"{RESTAURANTES_URL}{restaurante.id}/menu/")
        assert res.data["categorias"] == []

    def test_menu_precio_incluye_moneda(self, db, api_client):
        restaurante = RestauranteFactory(moneda="COP")
        categoria = CategoriaFactory()
        plato = PlatoFactory(categoria=categoria, activo=True)
        PrecioPlatoFactory(plato=plato, restaurante=restaurante, activo=True)

        res = api_client.get(f"{RESTAURANTES_URL}{restaurante.id}/menu/")
        plato_data = res.data["categorias"][0]["platos"][0]
        assert "precio" in plato_data
        assert "moneda" in plato_data
        assert plato_data["moneda"] == "COP"

    def test_menu_restaurante_inexistente_retorna_404(self, db, api_client):
        import uuid
        res = api_client.get(f"{RESTAURANTES_URL}{uuid.uuid4()}/menu/")
        assert res.status_code == 404

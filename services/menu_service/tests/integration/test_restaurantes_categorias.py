# tests/integration/test_restaurantes_categorias.py
import pytest
from tests.factories import RestauranteFactory, CategoriaFactory


RESTAURANTES_URL = "/api/menu/restaurantes/"
CATEGORIAS_URL = "/api/menu/categorias/"


# ═══════════════════════════════════════════════════════════════════════════
# Restaurante CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestRestauranteViewSet:

    def test_listar_restaurantes(self, db, api_client):
        RestauranteFactory.create_batch(3)
        res = api_client.get(RESTAURANTES_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_crear_restaurante(self, db, api_client):
        data = {
            "nombre": "El Fogón", "pais": "Colombia",
            "ciudad": "Medellín", "direccion": "Cra 70 # 1-10",
            "moneda": "COP",
        }
        res = api_client.post(RESTAURANTES_URL, data)
        assert res.status_code == 201
        assert res.data["nombre"] == "El Fogón"

    def test_crear_retorna_id_uuid(self, db, api_client):
        data = {
            "nombre": "La Pola", "pais": "Colombia",
            "ciudad": "Bogotá", "direccion": "Calle 85",
            "moneda": "COP",
        }
        res = api_client.post(RESTAURANTES_URL, data)
        assert res.status_code == 201
        assert "id" in res.data

    def test_detalle_restaurante(self, db, api_client, restaurante):
        res = api_client.get(f"{RESTAURANTES_URL}{restaurante.id}/")
        assert res.status_code == 200
        assert res.data["nombre"] == restaurante.nombre

    def test_restaurante_inexistente_retorna_404(self, db, api_client):
        import uuid
        res = api_client.get(f"{RESTAURANTES_URL}{uuid.uuid4()}/")
        assert res.status_code == 404

    def test_actualizar_restaurante(self, db, api_client, restaurante):
        res = api_client.patch(
            f"{RESTAURANTES_URL}{restaurante.id}/",
            {"nombre": "Nuevo Nombre"},
        )
        assert res.status_code == 200
        assert res.data["nombre"] == "Nuevo Nombre"

    def test_no_permite_delete(self, db, api_client, restaurante):
        res = api_client.delete(f"{RESTAURANTES_URL}{restaurante.id}/")
        assert res.status_code == 405

    def test_activar_restaurante(self, db, api_client):
        r = RestauranteFactory(activo=False)
        res = api_client.post(f"{RESTAURANTES_URL}{r.id}/activar/")
        assert res.status_code == 200
        r.refresh_from_db()
        assert r.activo is True

    def test_desactivar_restaurante(self, db, api_client, restaurante):
        res = api_client.post(
            f"{RESTAURANTES_URL}{restaurante.id}/desactivar/")
        assert res.status_code == 200
        restaurante.refresh_from_db()
        assert restaurante.activo is False

    def test_filtrar_por_activo(self, db, api_client):
        RestauranteFactory(activo=True)
        RestauranteFactory(activo=False)
        res = api_client.get(f"{RESTAURANTES_URL}?activo=true")
        assert res.status_code == 200
        assert all(r["activo"] for r in res.data)

    def test_filtrar_por_pais(self, db, api_client):
        RestauranteFactory(pais="Colombia")
        RestauranteFactory(pais="México")
        res = api_client.get(f"{RESTAURANTES_URL}?pais=Colombia")
        assert res.status_code == 200
        assert all(r["pais"] == "Colombia" for r in res.data)

    def test_publicar_evento_al_crear(self, db, api_client, mock_rabbitmq):
        data = {
            "nombre": "Evento Test", "pais": "Colombia",
            "ciudad": "Cali", "direccion": "Av 1",
            "moneda": "COP",
        }
        api_client.post(RESTAURANTES_URL, data)
        assert mock_rabbitmq.called

    def test_publicar_evento_al_actualizar(self, db, api_client, restaurante, mock_rabbitmq):
        api_client.patch(
            f"{RESTAURANTES_URL}{restaurante.id}/", {"nombre": "X"})
        assert mock_rabbitmq.called


# ═══════════════════════════════════════════════════════════════════════════
# Categoría CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestCategoriaViewSet:

    def test_listar_categorias(self, db, api_client):
        CategoriaFactory.create_batch(2)
        res = api_client.get(CATEGORIAS_URL)
        assert res.status_code == 200
        assert len(res.data) == 2

    def test_crear_categoria(self, db, api_client):
        res = api_client.post(
            CATEGORIAS_URL, {"nombre": "Ensaladas", "orden": 1})
        assert res.status_code == 201
        assert res.data["nombre"] == "Ensaladas"

    def test_nombre_duplicado_falla(self, db, api_client):
        CategoriaFactory(nombre="Bebidas")
        res = api_client.post(CATEGORIAS_URL, {"nombre": "Bebidas"})
        assert res.status_code == 400

    def test_detalle_categoria(self, db, api_client, categoria):
        res = api_client.get(f"{CATEGORIAS_URL}{categoria.id}/")
        assert res.status_code == 200

    def test_actualizar_categoria(self, db, api_client, categoria):
        res = api_client.patch(
            f"{CATEGORIAS_URL}{categoria.id}/", {"orden": 99})
        assert res.status_code == 200
        assert res.data["orden"] == 99

    def test_eliminar_categoria(self, db, api_client, categoria):
        res = api_client.delete(f"{CATEGORIAS_URL}{categoria.id}/")
        assert res.status_code == 204

    def test_activar_categoria(self, db, api_client):
        c = CategoriaFactory(activo=False)
        res = api_client.post(f"{CATEGORIAS_URL}{c.id}/activar/")
        assert res.status_code == 200
        c.refresh_from_db()
        assert c.activo is True

    def test_desactivar_categoria(self, db, api_client, categoria):
        res = api_client.post(f"{CATEGORIAS_URL}{categoria.id}/desactivar/")
        assert res.status_code == 200
        categoria.refresh_from_db()
        assert categoria.activo is False

    def test_filtrar_por_activo(self, db, api_client):
        CategoriaFactory(activo=True)
        CategoriaFactory(activo=False)
        res = api_client.get(f"{CATEGORIAS_URL}?activo=true")
        assert all(c["activo"] for c in res.data)

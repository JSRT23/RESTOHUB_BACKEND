# tests/integration/test_ingredientes_platos.py
import pytest
from tests.factories import (
    RestauranteFactory, CategoriaFactory, IngredienteFactory,
    PlatoFactory, PlatoIngredienteFactory,
)

INGREDIENTES_URL = "/api/menu/ingredientes/"
PLATOS_URL = "/api/menu/platos/"


# ═══════════════════════════════════════════════════════════════════════════
# Ingrediente
# ═══════════════════════════════════════════════════════════════════════════

class TestIngredienteViewSet:

    def test_listar_ingredientes(self, db, api_client):
        IngredienteFactory.create_batch(3)
        res = api_client.get(INGREDIENTES_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_crear_ingrediente_global(self, db, api_client):
        res = api_client.post(INGREDIENTES_URL, {
            "nombre": "Arroz", "unidad_medida": "kg"
        })
        assert res.status_code == 201
        assert res.data["nombre"] == "Arroz"

    def test_crear_ingrediente_local(self, db, api_client, restaurante):
        res = api_client.post(INGREDIENTES_URL, {
            "nombre": "Ají especial", "unidad_medida": "g",
            "restaurante": str(restaurante.id),
        })
        assert res.status_code == 201
        assert res.data["restaurante_id"] == str(restaurante.id)

    def test_nombre_vacio_falla(self, db, api_client):
        res = api_client.post(
            INGREDIENTES_URL, {"nombre": "  ", "unidad_medida": "g"})
        assert res.status_code == 400

    def test_detalle_ingrediente(self, db, api_client, ingrediente_global):
        res = api_client.get(f"{INGREDIENTES_URL}{ingrediente_global.id}/")
        assert res.status_code == 200

    def test_actualizar_ingrediente(self, db, api_client, ingrediente_global):
        res = api_client.patch(
            f"{INGREDIENTES_URL}{ingrediente_global.id}/",
            {"nombre": "Arroz Integral"},
        )
        assert res.status_code == 200
        assert res.data["nombre"] == "Arroz Integral"

    def test_eliminar_ingrediente(self, db, api_client, ingrediente_global):
        res = api_client.delete(f"{INGREDIENTES_URL}{ingrediente_global.id}/")
        assert res.status_code == 204

    def test_activar_ingrediente(self, db, api_client):
        i = IngredienteFactory(activo=False)
        res = api_client.post(f"{INGREDIENTES_URL}{i.id}/activar/")
        assert res.status_code == 200
        i.refresh_from_db()
        assert i.activo is True

    def test_desactivar_ingrediente(self, db, api_client, ingrediente_global):
        res = api_client.post(
            f"{INGREDIENTES_URL}{ingrediente_global.id}/desactivar/")
        assert res.status_code == 200
        ingrediente_global.refresh_from_db()
        assert ingrediente_global.activo is False

    def test_filtrar_por_activo(self, db, api_client):
        IngredienteFactory(activo=True)
        IngredienteFactory(activo=False)
        res = api_client.get(f"{INGREDIENTES_URL}?activo=true")
        assert all(i["activo"] for i in res.data)

    def test_filtrar_globales(self, db, api_client, restaurante):
        IngredienteFactory()  # global
        IngredienteFactory.local(restaurante=restaurante)  # local
        res = api_client.get(f"{INGREDIENTES_URL}?global=true")
        assert len(res.data) == 1
        assert res.data[0]["restaurante_id"] is None

    def test_filtrar_por_restaurante(self, db, api_client, restaurante, restaurante2):
        IngredienteFactory.local(restaurante=restaurante)
        IngredienteFactory.local(restaurante=restaurante2)
        res = api_client.get(
            f"{INGREDIENTES_URL}?restaurante_id={restaurante.id}")
        assert len(res.data) == 1

    def test_filtrar_disponibles_gerente(self, db, api_client, restaurante):
        """?disponibles=UUID → globales + locales del restaurante."""
        IngredienteFactory()  # global
        IngredienteFactory.local(restaurante=restaurante)  # local suyo
        otro = RestauranteFactory()
        IngredienteFactory.local(restaurante=otro)  # local de otro
        res = api_client.get(
            f"{INGREDIENTES_URL}?disponibles={restaurante.id}")
        assert len(res.data) == 2  # global + suyo

    def test_ingrediente_inexistente_retorna_404(self, db, api_client):
        import uuid
        res = api_client.get(f"{INGREDIENTES_URL}{uuid.uuid4()}/")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Plato
# ═══════════════════════════════════════════════════════════════════════════

class TestPlatoViewSet:

    def test_listar_platos(self, db, api_client):
        PlatoFactory.create_batch(3)
        res = api_client.get(PLATOS_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_crear_plato_global(self, db, api_client):
        res = api_client.post(PLATOS_URL, {
            "nombre": "Ajiaco", "descripcion": "Sopa bogotana",
        })
        assert res.status_code == 201
        assert res.data["nombre"] == "Ajiaco"

    def test_crear_plato_local(self, db, api_client, restaurante):
        res = api_client.post(PLATOS_URL, {
            "nombre": "Bandeja especial",
            "descripcion": "Exclusiva del restaurante",
            "restaurante": str(restaurante.id),
        })
        assert res.status_code == 201
        assert res.data["restaurante_id"] == str(restaurante.id)

    def test_nombre_vacio_falla(self, db, api_client):
        res = api_client.post(PLATOS_URL, {"nombre": "", "descripcion": "X"})
        assert res.status_code == 400

    def test_detalle_plato(self, db, api_client, plato_global):
        res = api_client.get(f"{PLATOS_URL}{plato_global.id}/")
        assert res.status_code == 200
        assert "ingredientes" in res.data
        assert "precios" in res.data

    def test_actualizar_plato(self, db, api_client, plato_global):
        res = api_client.patch(
            f"{PLATOS_URL}{plato_global.id}/",
            {"nombre": "Bandeja Paisa Nueva"},
        )
        assert res.status_code == 200

    def test_eliminar_plato(self, db, api_client, plato_global):
        res = api_client.delete(f"{PLATOS_URL}{plato_global.id}/")
        assert res.status_code == 204

    def test_activar_plato(self, db, api_client):
        p = PlatoFactory(activo=False)
        res = api_client.post(f"{PLATOS_URL}{p.id}/activar/")
        assert res.status_code == 200
        p.refresh_from_db()
        assert p.activo is True

    def test_desactivar_plato(self, db, api_client, plato_global):
        res = api_client.post(f"{PLATOS_URL}{plato_global.id}/desactivar/")
        assert res.status_code == 200
        plato_global.refresh_from_db()
        assert plato_global.activo is False

    def test_filtrar_por_activo(self, db, api_client):
        PlatoFactory(activo=True)
        PlatoFactory(activo=False)
        res = api_client.get(f"{PLATOS_URL}?activo=true")
        assert all(p["activo"] for p in res.data)

    def test_filtrar_por_categoria(self, db, api_client, categoria):
        PlatoFactory(categoria=categoria)
        PlatoFactory()
        res = api_client.get(f"{PLATOS_URL}?categoria={categoria.id}")
        assert len(res.data) == 1

    def test_filtrar_globales(self, db, api_client, restaurante):
        PlatoFactory()  # global
        PlatoFactory.local(restaurante=restaurante)  # local
        res = api_client.get(f"{PLATOS_URL}?global=true")
        assert len(res.data) == 1
        assert res.data[0]["restaurante_id"] is None

    def test_filtrar_disponibles(self, db, api_client, restaurante):
        PlatoFactory()  # global
        PlatoFactory.local(restaurante=restaurante)  # local suyo
        otro = RestauranteFactory()
        PlatoFactory.local(restaurante=otro)  # local de otro
        res = api_client.get(f"{PLATOS_URL}?disponibles={restaurante.id}")
        assert len(res.data) == 2

    def test_list_usa_serializer_ligero(self, db, api_client, plato_global):
        """La lista no debe incluir ingredientes ni precios anidados."""
        res = api_client.get(PLATOS_URL)
        assert "ingredientes" not in res.data[0]
        assert "precios" not in res.data[0]

    def test_plato_inexistente_retorna_404(self, db, api_client):
        import uuid
        res = api_client.get(f"{PLATOS_URL}{uuid.uuid4()}/")
        assert res.status_code == 404

    def test_publicar_evento_al_crear(self, db, api_client, mock_rabbitmq):
        api_client.post(
            PLATOS_URL, {"nombre": "Arroz con pollo", "descripcion": "Rico"})
        assert mock_rabbitmq.called

    def test_publicar_evento_al_eliminar(self, db, api_client, plato_global, mock_rabbitmq):
        api_client.delete(f"{PLATOS_URL}{plato_global.id}/")
        assert mock_rabbitmq.called


# ═══════════════════════════════════════════════════════════════════════════
# Ingredientes del plato (sub-recurso)
# ═══════════════════════════════════════════════════════════════════════════

class TestPlatoIngredientesSubrecurso:

    def test_listar_ingredientes_de_plato(self, db, api_client, plato_global, ingrediente_global):
        PlatoIngredienteFactory(
            plato=plato_global, ingrediente=ingrediente_global)
        res = api_client.get(f"{PLATOS_URL}{plato_global.id}/ingredientes/")
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_agregar_ingrediente(self, db, api_client, plato_global, ingrediente_global):
        res = api_client.post(
            f"{PLATOS_URL}{plato_global.id}/ingredientes/",
            {"ingrediente": str(ingrediente_global.id), "cantidad": "200.000"},
        )
        assert res.status_code == 201
        assert res.data["cantidad"] == "200.000"

    def test_cantidad_cero_falla(self, db, api_client, plato_global, ingrediente_global):
        res = api_client.post(
            f"{PLATOS_URL}{plato_global.id}/ingredientes/",
            {"ingrediente": str(ingrediente_global.id), "cantidad": "0"},
        )
        assert res.status_code == 400

    def test_ingrediente_duplicado_falla(self, db, api_client, plato_global, ingrediente_global):
        PlatoIngredienteFactory(
            plato=plato_global, ingrediente=ingrediente_global)
        res = api_client.post(
            f"{PLATOS_URL}{plato_global.id}/ingredientes/",
            {"ingrediente": str(ingrediente_global.id), "cantidad": "50"},
        )
        assert res.status_code == 400

    def test_quitar_ingrediente(self, db, api_client, plato_global, ingrediente_global):
        PlatoIngredienteFactory(
            plato=plato_global, ingrediente=ingrediente_global)
        res = api_client.delete(
            f"{PLATOS_URL}{plato_global.id}/ingredientes/{ingrediente_global.id}/"
        )
        assert res.status_code == 204

    def test_quitar_ingrediente_inexistente_retorna_404(self, db, api_client, plato_global):
        import uuid
        res = api_client.delete(
            f"{PLATOS_URL}{plato_global.id}/ingredientes/{uuid.uuid4()}/"
        )
        assert res.status_code == 404

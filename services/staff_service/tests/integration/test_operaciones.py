# tests/integration/test_operaciones.py
import uuid
import pytest
from datetime import date, timedelta

from django.utils import timezone

from app.staff.models import EstadoTurno
from tests.conftest import (
    RestauranteLocalFactory,
    EmpleadoFactory,
    CocineroFactory,
    RepartidorFactory,
    TurnoFactory,
    EstacionCocinaFactory,
    AsignacionCocinaFactory,
    ServicioEntregaFactory,
    AlertaOperacionalFactory,
    ResumenNominaFactory,
    PrediccionPersonalFactory,
    RegistroAsistenciaFactory,
    ConfiguracionLaboralPaisFactory,
)

ESTACIONES_URL = "/api/staff/estaciones/"
ASIGNACIONES_URL = "/api/staff/asignaciones-cocina/"
ENTREGAS_URL = "/api/staff/entregas/"
ALERTAS_URL = "/api/staff/alertas/"
NOMINA_URL = "/api/staff/nomina/"
PREDICCIONES_URL = "/api/staff/predicciones/"


# ═══════════════════════════════════════════════════════════
# EstacionCocina
# ═══════════════════════════════════════════════════════════

class TestEstacionCocinaViewSet:

    def test_listar_estaciones(self, db, api_client, estacion):
        res = api_client.get(ESTACIONES_URL)
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_crear_estacion(self, db, api_client, restaurante):
        res = api_client.post(ESTACIONES_URL, {
            "restaurante_id": str(restaurante.restaurante_id),
            "nombre": "Parrilla",
            "capacidad_simultanea": 2,
        }, format="json")
        assert res.status_code == 201

    def test_crear_estacion_restaurante_invalido_falla(self, db, api_client):
        res = api_client.post(ESTACIONES_URL, {
            "restaurante_id": str(uuid.uuid4()),
            "nombre": "Parrilla",
        }, format="json")
        assert res.status_code == 400

    def test_filtrar_por_restaurante(self, db, api_client, restaurante):
        EstacionCocinaFactory(restaurante_id=restaurante.restaurante_id)
        EstacionCocinaFactory()
        res = api_client.get(
            f"{ESTACIONES_URL}?restaurante_id={restaurante.restaurante_id}")
        assert len(res.data) == 1

    def test_filtrar_por_activa(self, db, api_client, restaurante):
        EstacionCocinaFactory(
            restaurante_id=restaurante.restaurante_id, activa=True)
        EstacionCocinaFactory(
            restaurante_id=restaurante.restaurante_id, activa=False)
        res = api_client.get(f"{ESTACIONES_URL}?activa=true")
        assert all(e["activa"] for e in res.data)

    def test_no_permite_delete(self, db, api_client, estacion):
        res = api_client.delete(f"{ESTACIONES_URL}{estacion.id}/")
        assert res.status_code == 405


# ═══════════════════════════════════════════════════════════
# AsignacionCocina
# ═══════════════════════════════════════════════════════════

class TestAsignacionCocinaViewSet:

    def test_listar_asignaciones(self, db, api_client):
        AsignacionCocinaFactory.create_batch(3)
        res = api_client.get(ASIGNACIONES_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_crear_asignacion(self, db, api_client, cocinero, estacion):
        res = api_client.post(ASIGNACIONES_URL, {
            "pedido_id": str(uuid.uuid4()),
            "comanda_id": str(uuid.uuid4()),
            "cocinero": str(cocinero.id),
            "estacion": str(estacion.id),
        }, format="json")
        assert res.status_code == 201

    def test_completar_asignacion(self, db, api_client):
        a = AsignacionCocinaFactory()
        res = api_client.post(f"{ASIGNACIONES_URL}{a.id}/completar/")
        assert res.status_code == 200
        assert res.data["completado_en"] is not None
        assert res.data["sla_segundos"] is not None

    def test_completar_ya_completada_falla(self, db, api_client):
        a = AsignacionCocinaFactory(completado_en=timezone.now())
        res = api_client.post(f"{ASIGNACIONES_URL}{a.id}/completar/")
        assert res.status_code == 400

    def test_filtrar_sin_completar(self, db, api_client):
        AsignacionCocinaFactory(completado_en=None)
        AsignacionCocinaFactory(completado_en=timezone.now())
        res = api_client.get(f"{ASIGNACIONES_URL}?sin_completar=true")
        assert len(res.data) == 1

    def test_list_usa_serializer_ligero(self, db, api_client):
        AsignacionCocinaFactory()
        res = api_client.get(ASIGNACIONES_URL)
        assert "created_at" not in res.data[0]


# ═══════════════════════════════════════════════════════════
# ServicioEntrega
# ═══════════════════════════════════════════════════════════

class TestServicioEntregaViewSet:

    def test_listar_entregas(self, db, api_client):
        ServicioEntregaFactory.create_batch(2)
        res = api_client.get(ENTREGAS_URL)
        assert res.status_code == 200
        assert len(res.data) == 2

    def test_no_permite_post(self, db, api_client):
        res = api_client.post(ENTREGAS_URL, {})
        assert res.status_code == 405

    def test_filtrar_por_estado(self, db, api_client):
        ServicioEntregaFactory(estado="asignada")
        ServicioEntregaFactory(estado="completada")
        res = api_client.get(f"{ENTREGAS_URL}?estado=asignada")
        assert all(e["estado"] == "asignada" for e in res.data)

    def test_filtrar_por_repartidor(self, db, api_client):
        r1 = RepartidorFactory()
        r2 = RepartidorFactory()
        ServicioEntregaFactory(repartidor=r1)
        ServicioEntregaFactory(repartidor=r2)
        res = api_client.get(f"{ENTREGAS_URL}?repartidor_id={r1.id}")
        assert len(res.data) == 1

    def test_disponibles_repartidores(self, db, api_client, restaurante):
        repartidor = RepartidorFactory(restaurante=restaurante)
        TurnoFactory(
            empleado=repartidor,
            restaurante_id=restaurante.restaurante_id,
            estado=EstadoTurno.ACTIVO,
        )
        res = api_client.get(
            f"{ENTREGAS_URL}disponibles/?restaurante_id={restaurante.restaurante_id}"
        )
        assert res.status_code == 200
        assert any(str(r["id"]) == str(repartidor.id) for r in res.data)


# ═══════════════════════════════════════════════════════════
# AlertaOperacional
# ═══════════════════════════════════════════════════════════

class TestAlertaOperacionalViewSet:

    def test_listar_alertas(self, db, api_client):
        AlertaOperacionalFactory.create_batch(3)
        res = api_client.get(ALERTAS_URL)
        assert res.status_code == 200
        assert len(res.data) == 3

    def test_detalle_alerta(self, db, api_client):
        a = AlertaOperacionalFactory()
        res = api_client.get(f"{ALERTAS_URL}{a.id}/")
        assert res.status_code == 200

    def test_no_permite_post(self, db, api_client):
        res = api_client.post(ALERTAS_URL, {})
        assert res.status_code == 405

    def test_resolver_alerta(self, db, api_client):
        a = AlertaOperacionalFactory()
        res = api_client.post(f"{ALERTAS_URL}{a.id}/resolver/")
        assert res.status_code == 200
        assert res.data["resuelta"] is True

    def test_resolver_ya_resuelta_falla(self, db, api_client):
        a = AlertaOperacionalFactory(resuelta=True)
        res = api_client.post(f"{ALERTAS_URL}{a.id}/resolver/")
        assert res.status_code == 400

    def test_filtrar_por_restaurante(self, db, api_client):
        rid = uuid.uuid4()
        AlertaOperacionalFactory(restaurante_id=rid)
        AlertaOperacionalFactory()
        res = api_client.get(f"{ALERTAS_URL}?restaurante_id={rid}")
        assert len(res.data) == 1

    def test_filtrar_por_resuelta(self, db, api_client):
        AlertaOperacionalFactory(resuelta=True)
        AlertaOperacionalFactory(resuelta=False)
        res = api_client.get(f"{ALERTAS_URL}?resuelta=false")
        assert all(not a["resuelta"] for a in res.data)


# ═══════════════════════════════════════════════════════════
# ResumenNomina
# ═══════════════════════════════════════════════════════════

class TestResumenNominaViewSet:

    def test_listar_nomina(self, db, api_client):
        ResumenNominaFactory.create_batch(2)
        res = api_client.get(NOMINA_URL)
        assert res.status_code == 200
        assert len(res.data) == 2

    def test_cerrar_nomina(self, db, api_client):
        r = ResumenNominaFactory()
        res = api_client.post(f"{NOMINA_URL}{r.id}/cerrar/")
        assert res.status_code == 200
        assert res.data["cerrado"] is True

    def test_cerrar_ya_cerrada_falla(self, db, api_client):
        r = ResumenNominaFactory(cerrado=True)
        res = api_client.post(f"{NOMINA_URL}{r.id}/cerrar/")
        assert res.status_code == 400

    def test_generar_nomina(self, db, api_client, restaurante, config_laboral):
        empleado = EmpleadoFactory(restaurante=restaurante, pais="CO")
        turno = TurnoFactory(empleado=empleado, estado=EstadoTurno.ACTIVO)
        RegistroAsistenciaFactory(
            turno=turno,
            hora_entrada=timezone.now() - timedelta(hours=8),
            hora_salida=timezone.now(),
            horas_normales=8,
        )
        res = api_client.post(f"{NOMINA_URL}generar/", {
            "periodo_inicio": date.today().replace(day=1).isoformat(),
            "periodo_fin": date.today().isoformat(),
            "restaurante_id": str(restaurante.restaurante_id),
        }, format="json")
        assert res.status_code == 201

    def test_generar_sin_empleados_falla(self, db, api_client):
        res = api_client.post(f"{NOMINA_URL}generar/", {
            "periodo_inicio": "2025-01-01",
            "periodo_fin": "2025-01-31",
            "restaurante_id": str(uuid.uuid4()),
        }, format="json")
        assert res.status_code == 404

    def test_filtrar_por_empleado(self, db, api_client):
        e1 = EmpleadoFactory()
        e2 = EmpleadoFactory()
        ResumenNominaFactory(empleado=e1)
        ResumenNominaFactory(empleado=e2)
        res = api_client.get(f"{NOMINA_URL}?empleado_id={e1.id}")
        assert len(res.data) == 1


# ═══════════════════════════════════════════════════════════
# PrediccionPersonal
# ═══════════════════════════════════════════════════════════

class TestPrediccionPersonalViewSet:

    def test_listar_predicciones(self, db, api_client):
        PrediccionPersonalFactory.create_batch(2)
        res = api_client.get(PREDICCIONES_URL)
        assert res.status_code == 200
        assert len(res.data) == 2

    def test_crear_prediccion(self, db, api_client, restaurante):
        res = api_client.post(PREDICCIONES_URL, {
            "restaurante_id": str(restaurante.restaurante_id),
            "fecha": (date.today() + timedelta(days=3)).isoformat(),
            "demanda_estimada": 120,
            "personal_recomendado": 6,
            "fuente": "historial",
        }, format="json")
        assert res.status_code == 201

    def test_crear_prediccion_restaurante_invalido_falla(self, db, api_client):
        res = api_client.post(PREDICCIONES_URL, {
            "restaurante_id": str(uuid.uuid4()),
            "fecha": (date.today() + timedelta(days=3)).isoformat(),
            "demanda_estimada": 100,
            "personal_recomendado": 5,
            "fuente": "historial",
        }, format="json")
        assert res.status_code == 400

    def test_filtrar_por_restaurante(self, db, api_client, restaurante):
        PrediccionPersonalFactory(restaurante_id=restaurante.restaurante_id)
        PrediccionPersonalFactory()
        res = api_client.get(
            f"{PREDICCIONES_URL}?restaurante_id={restaurante.restaurante_id}")
        assert len(res.data) == 1

    def test_no_permite_delete(self, db, api_client, restaurante):
        p = PrediccionPersonalFactory(
            restaurante_id=restaurante.restaurante_id)
        res = api_client.delete(f"{PREDICCIONES_URL}{p.id}/")
        assert res.status_code == 405

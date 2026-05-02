# tests/integration/test_turnos_asistencia.py
import uuid
import pytest
from datetime import timedelta

from django.utils import timezone

from app.staff.models import EstadoTurno, RegistroAsistencia
from tests.conftest import (
    TurnoFactory,
    RegistroAsistenciaFactory,
    ConfiguracionLaboralPaisFactory,
)

TURNOS_URL = "/api/staff/turnos/"
ASISTENCIA_URL = "/api/staff/asistencia/"


# ═══════════════════════════════════════════════════════════
# TurnoViewSet
# ═══════════════════════════════════════════════════════════

class TestTurnoViewSet:

    def _payload(self, empleado, inicio=None, fin=None):
        inicio = inicio or (timezone.now() + timedelta(hours=2))
        fin = fin or (inicio + timedelta(hours=8))
        return {
            "empleado": str(empleado.id),
            "restaurante_id": str(empleado.restaurante.restaurante_id),
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "notas": "",
        }

    def test_listar_turnos(self, db, api_client, turno):
        res = api_client.get(TURNOS_URL)
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_crear_turno(self, db, api_client, empleado):
        res = api_client.post(
            TURNOS_URL, self._payload(empleado), format="json")
        assert res.status_code == 201
        # TurnoWriteSerializer devuelve los campos de entrada (sin estado).
        # Verificamos que el turno quedó en DB con estado=programado.
        from app.staff.models import Turno, EstadoTurno
        turno = Turno.objects.filter(empleado=empleado).first()
        assert turno is not None
        assert turno.estado == EstadoTurno.PROGRAMADO

    def test_crear_turno_fin_antes_inicio_falla(self, db, api_client, empleado):
        inicio = timezone.now() + timedelta(hours=5)
        fin = inicio - timedelta(hours=1)
        res = api_client.post(TURNOS_URL, self._payload(
            empleado, inicio, fin), format="json")
        assert res.status_code == 400

    def test_crear_turno_solapado_falla(self, db, api_client, empleado):
        inicio = timezone.now() + timedelta(hours=2)
        fin = inicio + timedelta(hours=8)
        TurnoFactory(empleado=empleado, fecha_inicio=inicio, fecha_fin=fin)
        res = api_client.post(
            TURNOS_URL,
            self._payload(empleado, inicio + timedelta(hours=1),
                          fin + timedelta(hours=1)),
            format="json",
        )
        assert res.status_code == 400

    def test_detalle_turno(self, db, api_client, turno):
        res = api_client.get(f"{TURNOS_URL}{turno.id}/")
        assert res.status_code == 200
        assert "qr_token" in res.data

    def test_turno_inexistente_404(self, db, api_client):
        res = api_client.get(f"{TURNOS_URL}{uuid.uuid4()}/")
        assert res.status_code == 404

    def test_filtrar_por_estado(self, db, api_client, empleado):
        TurnoFactory(empleado=empleado, estado=EstadoTurno.PROGRAMADO)
        TurnoFactory(empleado=empleado,
                     fecha_inicio=timezone.now() + timedelta(hours=20),
                     fecha_fin=timezone.now() + timedelta(hours=28),
                     estado=EstadoTurno.CANCELADO)
        res = api_client.get(f"{TURNOS_URL}?estado=programado")
        assert all(t["estado"] == "programado" for t in res.data)

    def test_filtrar_por_empleado(self, db, api_client, empleado, turno):
        res = api_client.get(f"{TURNOS_URL}?empleado_id={empleado.id}")
        assert len(res.data) == 1

    def test_filtrar_por_restaurante(self, db, api_client, turno):
        res = api_client.get(
            f"{TURNOS_URL}?restaurante_id={turno.restaurante_id}")
        assert len(res.data) == 1

    def test_list_incluye_qr_token(self, db, api_client, turno):
        res = api_client.get(TURNOS_URL)
        assert "qr_token" in res.data[0]

    # ── Acciones ──────────────────────────────────────────────

    def test_iniciar_turno_programado(self, db, api_client, turno):
        res = api_client.post(f"{TURNOS_URL}{turno.id}/iniciar/")
        assert res.status_code == 200
        assert res.data["estado"] == "activo"

    def test_iniciar_turno_no_programado_falla(self, db, api_client, turno_activo):
        res = api_client.post(f"{TURNOS_URL}{turno_activo.id}/iniciar/")
        assert res.status_code == 400

    def test_iniciar_genera_qr_nuevo(self, db, api_client, turno):
        token_original = turno.qr_token
        api_client.post(f"{TURNOS_URL}{turno.id}/iniciar/")
        turno.refresh_from_db()
        assert turno.qr_token != token_original

    def test_iniciar_setea_qr_expira_en(self, db, api_client, turno):
        res = api_client.post(f"{TURNOS_URL}{turno.id}/iniciar/")
        assert res.data["qr_expira_en"] is not None

    def test_cancelar_turno_programado(self, db, api_client, turno):
        res = api_client.post(f"{TURNOS_URL}{turno.id}/cancelar/")
        assert res.status_code == 200
        assert res.data["estado"] == "cancelado"

    def test_cancelar_turno_activo(self, db, api_client, turno_activo):
        res = api_client.post(f"{TURNOS_URL}{turno_activo.id}/cancelar/")
        assert res.status_code == 200
        assert res.data["estado"] == "cancelado"

    def test_cancelar_turno_completado_falla(self, db, api_client, turno):
        turno.estado = EstadoTurno.COMPLETADO
        turno.save()
        res = api_client.post(f"{TURNOS_URL}{turno.id}/cancelar/")
        assert res.status_code == 400

    def test_completar_turno_activo(self, db, api_client, turno_activo):
        res = api_client.post(f"{TURNOS_URL}{turno_activo.id}/completar/")
        assert res.status_code == 200
        assert res.data["estado"] == "completado"

    def test_completar_turno_no_activo_falla(self, db, api_client, turno):
        res = api_client.post(f"{TURNOS_URL}{turno.id}/completar/")
        assert res.status_code == 400

    def test_completar_con_registro_abierto_lo_cierra(self, db, api_client, turno_activo):
        RegistroAsistenciaFactory(turno=turno_activo, hora_salida=None)
        api_client.post(f"{TURNOS_URL}{turno_activo.id}/completar/")
        registro = RegistroAsistencia.objects.get(turno=turno_activo)
        assert registro.hora_salida is not None


# ═══════════════════════════════════════════════════════════
# AsistenciaViewSet
# ═══════════════════════════════════════════════════════════

class TestAsistenciaViewSet:

    def test_listar_sin_filtro_falla(self, db, api_client):
        res = api_client.get(ASISTENCIA_URL)
        assert res.status_code == 400

    def test_listar_por_empleado(self, db, api_client, turno_activo):
        RegistroAsistenciaFactory(turno=turno_activo)
        res = api_client.get(
            f"{ASISTENCIA_URL}?empleado_id={turno_activo.empleado.id}"
        )
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_listar_por_fecha_desde(self, db, api_client, turno_activo):
        RegistroAsistenciaFactory(turno=turno_activo)
        from datetime import date
        res = api_client.get(
            f"{ASISTENCIA_URL}?fecha_desde={date.today().isoformat()}"
        )
        assert res.status_code == 200

    # ── Entrada ───────────────────────────────────────────────

    def test_entrada_qr_valida(self, db, api_client, turno_activo):
        turno_activo.qr_expira_en = timezone.now() + timezone.timedelta(hours=1)
        turno_activo.save()
        res = api_client.post(
            f"{ASISTENCIA_URL}entrada/",
            {"qr_token": str(turno_activo.qr_token), "metodo_registro": "qr"},
            format="json",
        )
        assert res.status_code == 201
        assert "hora_entrada" in res.data

    def test_entrada_qr_invalido_falla(self, db, api_client):
        res = api_client.post(
            f"{ASISTENCIA_URL}entrada/",
            {"qr_token": str(uuid.uuid4()), "metodo_registro": "qr"},
            format="json",
        )
        assert res.status_code == 400

    def test_entrada_manual_valida(self, db, api_client, turno_activo):
        res = api_client.post(
            f"{ASISTENCIA_URL}entrada/",
            {"turno_id": str(turno_activo.id), "metodo_registro": "manual"},
            format="json",
        )
        assert res.status_code == 201

    def test_entrada_duplicada_falla(self, db, api_client, turno_activo):
        RegistroAsistenciaFactory(turno=turno_activo)
        turno_activo.qr_expira_en = timezone.now() + timezone.timedelta(hours=1)
        turno_activo.save()
        res = api_client.post(
            f"{ASISTENCIA_URL}entrada/",
            {"qr_token": str(turno_activo.qr_token), "metodo_registro": "qr"},
            format="json",
        )
        assert res.status_code == 400

    # ── Salida ────────────────────────────────────────────────

    def test_salida_con_registro_de_entrada(self, db, api_client, turno_activo, config_laboral):
        RegistroAsistenciaFactory(turno=turno_activo)
        res = api_client.post(
            f"{ASISTENCIA_URL}salida/",
            {"turno_id": str(turno_activo.id)},
            format="json",
        )
        assert res.status_code == 200
        assert res.data["hora_salida"] is not None

    def test_salida_sin_registro_entrada_crea_registro(self, db, api_client, turno_activo, config_laboral):
        res = api_client.post(
            f"{ASISTENCIA_URL}salida/",
            {"turno_id": str(turno_activo.id)},
            format="json",
        )
        assert res.status_code == 200
        assert RegistroAsistencia.objects.filter(turno=turno_activo).exists()

    def test_salida_completa_el_turno(self, db, api_client, turno_activo, config_laboral):
        api_client.post(
            f"{ASISTENCIA_URL}salida/",
            {"turno_id": str(turno_activo.id)},
            format="json",
        )
        turno_activo.refresh_from_db()
        assert turno_activo.estado == EstadoTurno.COMPLETADO

    def test_salida_turno_no_activo_falla(self, db, api_client, turno):
        res = api_client.post(
            f"{ASISTENCIA_URL}salida/",
            {"turno_id": str(turno.id)},
            format="json",
        )
        assert res.status_code == 404

    def test_salida_calcula_horas_normales(self, db, api_client, turno_activo, config_laboral):
        # Entrada hace 6 horas (dentro del límite de 8h diarias)
        entrada = timezone.now() - timedelta(hours=6)
        RegistroAsistenciaFactory(turno=turno_activo, hora_entrada=entrada)
        res = api_client.post(
            f"{ASISTENCIA_URL}salida/",
            {"turno_id": str(turno_activo.id)},
            format="json",
        )
        assert res.status_code == 200
        from decimal import Decimal
        assert Decimal(str(res.data["horas_normales"])) > 0
        assert Decimal(str(res.data["horas_extra"])) == Decimal("0.00")

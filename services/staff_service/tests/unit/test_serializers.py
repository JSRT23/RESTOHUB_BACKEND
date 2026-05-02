# tests/unit/test_serializers.py
import uuid
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from app.staff.serializers import (
    EmpleadoWriteSerializer,
    TurnoWriteSerializer,
    EntradaSerializer,
    SalidaSerializer,
    GenerarNominaSerializer,
)
from tests.conftest import (
    RestauranteLocalFactory,
    EmpleadoFactory,
    TurnoFactory,
    ConfiguracionLaboralPaisFactory,
)


# ═══════════════════════════════════════════════════════════
# EmpleadoWriteSerializer
# ═══════════════════════════════════════════════════════════

class TestEmpleadoWriteSerializer:

    def _payload(self, restaurante_id, pais="CO"):
        return {
            "nombre": "Ana",
            "apellido": "Torres",
            "documento": "CC99887766",
            "email": "ana.torres@test.com",
            "telefono": "3001234567",
            "rol": "mesero",
            "pais": pais,
            "restaurante": str(restaurante_id),
        }

    def test_datos_validos(self, db):
        r = RestauranteLocalFactory(pais="CO")
        s = EmpleadoWriteSerializer(data=self._payload(r.restaurante_id))
        assert s.is_valid(), s.errors

    def test_restaurante_inexistente_falla(self, db):
        s = EmpleadoWriteSerializer(data=self._payload(uuid.uuid4()))
        assert not s.is_valid()
        assert "restaurante" in s.errors

    def test_restaurante_inactivo_falla(self, db):
        r = RestauranteLocalFactory(activo=False)
        s = EmpleadoWriteSerializer(data=self._payload(r.restaurante_id))
        assert not s.is_valid()
        assert "restaurante" in s.errors

    def test_pais_inconsistente_falla(self, db):
        r = RestauranteLocalFactory(pais="CO")
        payload = self._payload(r.restaurante_id, pais="MX")
        s = EmpleadoWriteSerializer(data=payload)
        assert not s.is_valid()

    def test_fecha_contratacion_default_hoy(self, db):
        r = RestauranteLocalFactory(pais="CO")
        payload = self._payload(r.restaurante_id)
        s = EmpleadoWriteSerializer(data=payload)
        assert s.is_valid()
        empleado = s.save()
        assert empleado.fecha_contratacion == date.today()

    def test_email_invalido_falla(self, db):
        r = RestauranteLocalFactory(pais="CO")
        payload = self._payload(r.restaurante_id)
        payload["email"] = "no-es-email"
        s = EmpleadoWriteSerializer(data=payload)
        assert not s.is_valid()
        assert "email" in s.errors


# ═══════════════════════════════════════════════════════════
# TurnoWriteSerializer
# ═══════════════════════════════════════════════════════════

class TestTurnoWriteSerializer:

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

    def test_datos_validos(self, db, empleado):
        s = TurnoWriteSerializer(data=self._payload(empleado))
        assert s.is_valid(), s.errors

    def test_fin_antes_que_inicio_falla(self, db, empleado):
        inicio = timezone.now() + timedelta(hours=5)
        fin = inicio - timedelta(hours=1)
        s = TurnoWriteSerializer(data=self._payload(empleado, inicio, fin))
        assert not s.is_valid()

    def test_solapamiento_falla(self, db, empleado):
        inicio = timezone.now() + timedelta(hours=2)
        fin = inicio + timedelta(hours=8)
        TurnoFactory(empleado=empleado, fecha_inicio=inicio, fecha_fin=fin)
        # Turno que solapa
        s = TurnoWriteSerializer(
            data=self._payload(empleado, inicio +
                               timedelta(hours=1), fin + timedelta(hours=1))
        )
        assert not s.is_valid()

    def test_descanso_minimo_falla(self, db, empleado):
        ConfiguracionLaboralPaisFactory(
            pais=empleado.pais, descanso_min_entre_turnos=480)
        inicio1 = timezone.now() + timedelta(hours=1)
        fin1 = inicio1 + timedelta(hours=8)
        TurnoFactory(empleado=empleado, fecha_inicio=inicio1, fecha_fin=fin1)
        # Segundo turno que empieza 1 hora después (falta descanso mínimo de 8h)
        inicio2 = fin1 + timedelta(hours=1)
        fin2 = inicio2 + timedelta(hours=8)
        s = TurnoWriteSerializer(data=self._payload(empleado, inicio2, fin2))
        assert not s.is_valid()


# ═══════════════════════════════════════════════════════════
# EntradaSerializer
# ═══════════════════════════════════════════════════════════

class TestEntradaSerializer:

    def test_qr_valido(self, db):
        s = EntradaSerializer(data={"qr_token": str(
            uuid.uuid4()), "metodo_registro": "qr"})
        assert s.is_valid(), s.errors

    def test_manual_con_turno_id(self, db):
        s = EntradaSerializer(data={"turno_id": str(
            uuid.uuid4()), "metodo_registro": "manual"})
        assert s.is_valid(), s.errors

    def test_sin_token_ni_turno_falla(self, db):
        s = EntradaSerializer(data={"metodo_registro": "qr"})
        assert not s.is_valid()

    def test_qr_sin_token_falla(self, db):
        s = EntradaSerializer(
            data={"metodo_registro": "qr", "turno_id": str(uuid.uuid4())})
        assert not s.is_valid()


# ═══════════════════════════════════════════════════════════
# SalidaSerializer
# ═══════════════════════════════════════════════════════════

class TestSalidaSerializer:

    def test_turno_id_valido(self, db):
        s = SalidaSerializer(data={"turno_id": str(uuid.uuid4())})
        assert s.is_valid(), s.errors

    def test_sin_turno_id_falla(self, db):
        s = SalidaSerializer(data={})
        assert not s.is_valid()


# ═══════════════════════════════════════════════════════════
# GenerarNominaSerializer
# ═══════════════════════════════════════════════════════════

class TestGenerarNominaSerializer:

    def test_con_empleado_id(self, db):
        s = GenerarNominaSerializer(data={
            "periodo_inicio": "2025-01-01",
            "periodo_fin": "2025-01-31",
            "empleado_id": str(uuid.uuid4()),
        })
        assert s.is_valid(), s.errors

    def test_con_restaurante_id(self, db):
        s = GenerarNominaSerializer(data={
            "periodo_inicio": "2025-01-01",
            "periodo_fin": "2025-01-31",
            "restaurante_id": str(uuid.uuid4()),
        })
        assert s.is_valid(), s.errors

    def test_sin_empleado_ni_restaurante_falla(self, db):
        s = GenerarNominaSerializer(data={
            "periodo_inicio": "2025-01-01",
            "periodo_fin": "2025-01-31",
        })
        assert not s.is_valid()

    def test_periodo_inicio_mayor_fin_falla(self, db):
        s = GenerarNominaSerializer(data={
            "periodo_inicio": "2025-02-01",
            "periodo_fin": "2025-01-01",
            "empleado_id": str(uuid.uuid4()),
        })
        assert not s.is_valid()

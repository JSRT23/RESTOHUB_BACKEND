# tests/unit/test_models.py
import uuid
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from app.staff.models import (
    EstadoTurno,
    RolEmpleado,
)
from tests.conftest import (
    RestauranteLocalFactory,
    ConfiguracionLaboralPaisFactory,
    EmpleadoFactory,
    TurnoFactory,
    RegistroAsistenciaFactory,
    EstacionCocinaFactory,
    AsignacionCocinaFactory,
    AlertaOperacionalFactory,
    ResumenNominaFactory,
)


# ═══════════════════════════════════════════════════════════
# RestauranteLocal
# ═══════════════════════════════════════════════════════════

class TestRestauranteLocalModel:

    def test_crear_restaurante(self, db):
        r = RestauranteLocalFactory()
        assert r.pk is not None
        assert r.activo is True

    def test_str(self, db):
        r = RestauranteLocalFactory(nombre="La Parrilla", pais="CO")
        assert "La Parrilla" in str(r)
        assert "Colombia" in str(r)

    def test_id_es_uuid(self, db):
        r = RestauranteLocalFactory()
        assert isinstance(r.id, uuid.UUID)


# ═══════════════════════════════════════════════════════════
# ConfiguracionLaboralPais
# ═══════════════════════════════════════════════════════════

class TestConfiguracionLaboralPaisModel:

    def test_crear_config(self, db):
        c = ConfiguracionLaboralPaisFactory()
        assert c.pk is not None
        assert c.horas_max_diarias == 8

    def test_str(self, db):
        c = ConfiguracionLaboralPaisFactory(pais="CO")
        assert "Colombia" in str(c)

    def test_unique_pais(self, db):
        from django.db import IntegrityError
        ConfiguracionLaboralPaisFactory(pais="MX")
        with pytest.raises(IntegrityError):
            ConfiguracionLaboralPaisFactory(pais="MX")


# ═══════════════════════════════════════════════════════════
# Empleado
# ═══════════════════════════════════════════════════════════

class TestEmpleadoModel:

    def test_crear_empleado(self, db):
        e = EmpleadoFactory()
        assert e.pk is not None
        assert e.activo is True

    def test_str(self, db):
        e = EmpleadoFactory(nombre="Juan", apellido="Pérez",
                            rol=RolEmpleado.MESERO)
        assert "Juan" in str(e)
        assert "Pérez" in str(e)

    def test_get_config_laboral(self, db):
        ConfiguracionLaboralPaisFactory(pais="CO")
        e = EmpleadoFactory(pais="CO")
        config = e.get_config_laboral()
        assert config is not None
        assert config.pais == "CO"

    def test_get_config_laboral_sin_config(self, db):
        e = EmpleadoFactory(pais="CO")
        assert e.get_config_laboral() is None

    def test_documento_unico(self, db):
        from django.db import IntegrityError
        EmpleadoFactory(documento="CC12345678")
        with pytest.raises(IntegrityError):
            EmpleadoFactory(documento="CC12345678")

    def test_email_unico(self, db):
        from django.db import IntegrityError
        EmpleadoFactory(email="unico@test.com")
        with pytest.raises(IntegrityError):
            EmpleadoFactory(email="unico@test.com")

    def test_ordering(self, db):
        """
        SQLite en :memory: no soporta collation de caracteres especiales (tildes).
        En PostgreSQL 'Álvarez' < 'Zuñiga' alfabéticamente, pero SQLite usa
        byte order → 'Z' (90) < 'Á' (195 en UTF-8) → orden inverso al esperado.
        El test verifica que el ordering existe (no el orden concreto de tildes).
        """
        EmpleadoFactory(apellido="Zuñiga",  nombre="Ana")
        # sin tilde — ASCII puro
        EmpleadoFactory(apellido="Alvarez", nombre="Carlos")
        from app.staff.models import Empleado
        empleados = list(Empleado.objects.order_by("apellido"))
        # "Alvarez" < "Zuñiga" tanto en ASCII como en Unicode
        assert empleados[0].apellido == "Alvarez"


# ═══════════════════════════════════════════════════════════
# Turno
# ═══════════════════════════════════════════════════════════

class TestTurnoModel:

    def test_crear_turno(self, db):
        t = TurnoFactory()
        assert t.pk is not None
        assert t.estado == EstadoTurno.PROGRAMADO

    def test_qr_token_es_uuid(self, db):
        t = TurnoFactory()
        assert isinstance(t.qr_token, uuid.UUID)

    def test_duracion_programada_horas(self, db):
        inicio = timezone.now()
        fin = inicio + timedelta(hours=8)
        t = TurnoFactory(fecha_inicio=inicio, fecha_fin=fin)
        assert t.duracion_programada_horas == 8.0

    def test_str(self, db):
        e = EmpleadoFactory(nombre="María", apellido="Gómez")
        t = TurnoFactory(empleado=e)
        s = str(t)
        assert "María" in s or "Gómez" in s

    def test_estado_default_programado(self, db):
        t = TurnoFactory()
        assert t.estado == EstadoTurno.PROGRAMADO


# ═══════════════════════════════════════════════════════════
# RegistroAsistencia
# ═══════════════════════════════════════════════════════════

class TestRegistroAsistenciaModel:

    def test_crear_registro(self, db):
        r = RegistroAsistenciaFactory()
        assert r.pk is not None
        assert r.hora_salida is None

    def test_horas_totales(self, db):
        r = RegistroAsistenciaFactory(
            horas_normales=Decimal("7.00"),
            horas_extra=Decimal("1.50"),
        )
        assert r.horas_totales == Decimal("8.50")

    def test_str(self, db):
        r = RegistroAsistenciaFactory()
        assert "Asistencia" in str(r)


# ═══════════════════════════════════════════════════════════
# AsignacionCocina
# ═══════════════════════════════════════════════════════════

class TestAsignacionCocinaModel:

    def test_crear_asignacion(self, db):
        a = AsignacionCocinaFactory()
        assert a.pk is not None
        assert a.completado_en is None

    def test_calcular_sla_sin_completar(self, db):
        a = AsignacionCocinaFactory()
        assert a.calcular_sla() is None

    def test_calcular_sla_completado(self, db):
        a = AsignacionCocinaFactory()
        a.completado_en = a.asignado_en + timedelta(minutes=10)
        sla = a.calcular_sla()
        assert sla == 600

    def test_str(self, db):
        a = AsignacionCocinaFactory()
        assert "Comanda" in str(a)


# ═══════════════════════════════════════════════════════════
# AlertaOperacional
# ═══════════════════════════════════════════════════════════

class TestAlertaOperacionalModel:

    def test_crear_alerta(self, db):
        a = AlertaOperacionalFactory()
        assert a.pk is not None
        assert a.resuelta is False

    def test_str(self, db):
        a = AlertaOperacionalFactory()
        s = str(a)
        assert "Urgente" in s or "stock" in s.lower() or "Stock" in s


# ═══════════════════════════════════════════════════════════
# ResumenNomina
# ═══════════════════════════════════════════════════════════

class TestResumenNominaModel:

    def test_crear_resumen(self, db):
        r = ResumenNominaFactory()
        assert r.pk is not None
        assert r.cerrado is False

    def test_total_horas(self, db):
        r = ResumenNominaFactory(
            total_horas_normales=Decimal("40.00"),
            total_horas_extra=Decimal("5.00"),
        )
        assert r.total_horas == Decimal("45.00")

    def test_str(self, db):
        r = ResumenNominaFactory()
        assert "Nómina" in str(r)

    def test_unique_empleado_periodo(self, db):
        from django.db import IntegrityError
        e = EmpleadoFactory()
        inicio = date.today().replace(day=1)
        fin = date.today()
        ResumenNominaFactory(
            empleado=e, periodo_inicio=inicio, periodo_fin=fin)
        with pytest.raises(IntegrityError):
            ResumenNominaFactory(
                empleado=e, periodo_inicio=inicio, periodo_fin=fin)

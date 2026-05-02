# tests/unit/test_models.py
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from app.inventory.models import (
    EstadoAlerta, EstadoLote, TipoAlerta,
)
from tests.conftest import (
    ProveedorFactory, AlmacenFactory, IngredienteInventarioFactory,
    LoteIngredienteFactory, OrdenCompraFactory, DetalleOrdenCompraFactory,
    AlertaStockFactory, RecetaPlatoFactory,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Proveedor
# ═══════════════════════════════════════════════════════════════════════════════

class TestProveedorModel:

    def test_crear_proveedor_global(self, db):
        p = ProveedorFactory(alcance="GLOBAL")
        assert p.pk is not None
        assert p.alcance == "GLOBAL"

    def test_id_es_uuid(self, db):
        import uuid
        p = ProveedorFactory()
        assert isinstance(p.id, uuid.UUID)

    def test_str(self, db):
        p = ProveedorFactory(nombre="Proveedor X",
                             pais="Colombia", alcance="GLOBAL")
        assert "Proveedor X" in str(p)
        assert "Colombia" in str(p)

    def test_alcance_pais_requiere_pais_destino(self, db):
        p = ProveedorFactory.build(alcance="PAIS", pais_destino=None)
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_alcance_pais_valido_con_pais_destino(self, db):
        p = ProveedorFactory(alcance="PAIS", pais_destino="Colombia")
        p.full_clean()  # no debe lanzar

    def test_alcance_ciudad_requiere_ciudad_destino(self, db):
        p = ProveedorFactory.build(
            alcance="CIUDAD", pais_destino="Colombia", ciudad_destino=None)
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_alcance_local_requiere_restaurante_id(self, db):
        p = ProveedorFactory.build(
            alcance="LOCAL", creado_por_restaurante_id=None)
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_activo_default_true(self, db):
        p = ProveedorFactory()
        assert p.activo is True


# ═══════════════════════════════════════════════════════════════════════════════
# Almacén
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlmacenModel:

    def test_crear_almacen(self, db):
        a = AlmacenFactory()
        assert a.pk is not None
        assert a.activo is True

    def test_str(self, db):
        a = AlmacenFactory(nombre="Bodega Central")
        assert "Bodega Central" in str(a)

    def test_ordering(self, db):
        import uuid
        rid = uuid.uuid4()
        AlmacenFactory(restaurante_id=rid, nombre="Z Almacen")
        AlmacenFactory(restaurante_id=rid, nombre="A Almacen")
        from app.inventory.models import Almacen
        nombres = list(Almacen.objects.filter(
            restaurante_id=rid).values_list("nombre", flat=True))
        assert nombres == sorted(nombres)


# ═══════════════════════════════════════════════════════════════════════════════
# IngredienteInventario
# ═══════════════════════════════════════════════════════════════════════════════

class TestIngredienteInventarioModel:

    def test_crear(self, db):
        inv = IngredienteInventarioFactory()
        assert inv.pk is not None

    def test_necesita_reposicion_true(self, db):
        inv = IngredienteInventarioFactory(
            cantidad_actual=Decimal("5.000"), nivel_minimo=Decimal("10.000"))
        assert inv.necesita_reposicion is True

    def test_necesita_reposicion_false(self, db):
        inv = IngredienteInventarioFactory(
            cantidad_actual=Decimal("50.000"), nivel_minimo=Decimal("10.000"))
        assert inv.necesita_reposicion is False

    def test_esta_agotado_true(self, db):
        inv = IngredienteInventarioFactory(cantidad_actual=Decimal("0.000"))
        assert inv.esta_agotado is True

    def test_esta_agotado_false(self, db):
        inv = IngredienteInventarioFactory(cantidad_actual=Decimal("1.000"))
        assert inv.esta_agotado is False

    def test_porcentaje_stock(self, db):
        inv = IngredienteInventarioFactory(
            cantidad_actual=Decimal("100.000"), nivel_maximo=Decimal("200.000"))
        assert inv.porcentaje_stock == 50.0

    def test_porcentaje_stock_nivel_maximo_cero(self, db):
        inv = IngredienteInventarioFactory(
            cantidad_actual=Decimal("50.000"),
            nivel_minimo=Decimal("0.000"),
            nivel_maximo=Decimal("0.000"))
        assert inv.porcentaje_stock == 0

    def test_nivel_maximo_menor_minimo_falla(self, db):
        inv = IngredienteInventarioFactory.build(
            nivel_minimo=Decimal("100.000"),
            nivel_maximo=Decimal("50.000"))
        with pytest.raises(ValidationError):
            inv.full_clean()

    def test_cantidad_negativa_falla(self, db):
        inv = IngredienteInventarioFactory.build(
            cantidad_actual=Decimal("-1.000"))
        with pytest.raises(ValidationError):
            inv.full_clean()

    def test_str(self, db):
        almacen = AlmacenFactory(nombre="Bodega Sur")
        inv = IngredienteInventarioFactory(
            almacen=almacen,
            nombre_ingrediente="Arroz",
            cantidad_actual=Decimal("50.000"),
            unidad_medida="kg")
        assert "Arroz" in str(inv)
        assert "Bodega Sur" in str(inv)

    def test_unique_ingrediente_almacen(self, db):
        from django.db import IntegrityError
        import uuid
        ingr_id = uuid.uuid4()
        almacen = AlmacenFactory()
        IngredienteInventarioFactory(ingrediente_id=ingr_id, almacen=almacen)
        with pytest.raises(IntegrityError):
            IngredienteInventarioFactory(
                ingrediente_id=ingr_id, almacen=almacen)


# ═══════════════════════════════════════════════════════════════════════════════
# LoteIngrediente
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoteIngredienteModel:

    def test_crear_lote(self, db):
        lote = LoteIngredienteFactory()
        assert lote.pk is not None
        assert lote.estado == EstadoLote.ACTIVO

    def test_esta_vencido_false(self, db):
        lote = LoteIngredienteFactory(
            fecha_vencimiento=timezone.now().date() + timedelta(days=30))
        assert lote.esta_vencido is False

    def test_esta_vencido_true(self, db):
        from app.inventory.models import LoteIngrediente, Almacen, Proveedor
        almacen = AlmacenFactory()
        proveedor = ProveedorFactory()
        # Save bypassing full_clean to test the property with past date
        obj = LoteIngrediente(
            ingrediente_id=__import__('uuid').uuid4(),
            almacen=almacen,
            proveedor=proveedor,
            numero_lote="TEST-VENCIDO",
            fecha_vencimiento=timezone.now().date() - timedelta(days=1),
            cantidad_recibida=Decimal("10.000"),
            cantidad_actual=Decimal("10.000"),
            unidad_medida="kg",
        )
        obj.save_base(force_insert=True)
        assert obj.esta_vencido is True

    def test_dias_para_vencer(self, db):
        lote = LoteIngredienteFactory(
            fecha_vencimiento=timezone.now().date() + timedelta(days=10))
        assert lote.dias_para_vencer == 10

    def test_cantidad_actual_mayor_recibida_falla(self, db):
        lote = LoteIngredienteFactory.build(
            cantidad_recibida=Decimal("50.000"),
            cantidad_actual=Decimal("100.000"))
        with pytest.raises(ValidationError):
            lote.full_clean()

    def test_fecha_vencimiento_anterior_produccion_falla(self, db):
        hoy = timezone.now().date()
        lote = LoteIngredienteFactory.build(
            fecha_produccion=hoy + timedelta(days=10),
            fecha_vencimiento=hoy + timedelta(days=5))
        with pytest.raises(ValidationError):
            lote.full_clean()

    def test_str(self, db):
        almacen = AlmacenFactory(nombre="Bodega Norte")
        lote = LoteIngredienteFactory(almacen=almacen, numero_lote="LOTE-001")
        assert "LOTE-001" in str(lote)
        assert "Bodega Norte" in str(lote)


# ═══════════════════════════════════════════════════════════════════════════════
# RecetaPlato
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecetaPlatoModel:

    def test_crear_receta(self, db):
        r = RecetaPlatoFactory()
        assert r.pk is not None

    def test_costo_ingrediente(self, db):
        r = RecetaPlatoFactory(
            cantidad=Decimal("2.000"),
            costo_unitario=Decimal("5000.0000"))
        assert r.costo_ingrediente == pytest.approx(10000.0)

    def test_unique_plato_ingrediente(self, db):
        from django.db import IntegrityError
        import uuid
        plato_id = uuid.uuid4()
        ingr_id = uuid.uuid4()
        RecetaPlatoFactory(plato_id=plato_id, ingrediente_id=ingr_id)
        with pytest.raises(IntegrityError):
            RecetaPlatoFactory(plato_id=plato_id, ingrediente_id=ingr_id)

    def test_str(self, db):
        import uuid
        pid = uuid.uuid4()
        r = RecetaPlatoFactory(plato_id=pid, nombre_ingrediente="Tomate")
        assert "Tomate" in str(r)


# ═══════════════════════════════════════════════════════════════════════════════
# DetalleOrdenCompra
# ═══════════════════════════════════════════════════════════════════════════════

class TestDetalleOrdenCompraModel:

    def test_subtotal_calculado_en_save(self, db):
        orden = OrdenCompraFactory()
        detalle = DetalleOrdenCompraFactory(
            orden=orden,
            cantidad=Decimal("5.000"),
            precio_unitario=Decimal("2000.00"))
        assert detalle.subtotal == Decimal("10000.00")

    def test_cantidad_cero_falla(self, db):
        orden = OrdenCompraFactory()
        detalle = DetalleOrdenCompraFactory.build(
            orden=orden,
            cantidad=Decimal("0.000"),
            precio_unitario=Decimal("1000.00"))
        with pytest.raises(ValidationError):
            detalle.full_clean()

    def test_precio_cero_falla(self, db):
        orden = OrdenCompraFactory()
        detalle = DetalleOrdenCompraFactory.build(
            orden=orden,
            cantidad=Decimal("5.000"),
            precio_unitario=Decimal("0.00"))
        with pytest.raises(ValidationError):
            detalle.full_clean()

    def test_cantidad_recibida_mayor_pedida_falla(self, db):
        orden = OrdenCompraFactory()
        detalle = DetalleOrdenCompraFactory.build(
            orden=orden,
            cantidad=Decimal("5.000"),
            cantidad_recibida=Decimal("10.000"),
            precio_unitario=Decimal("1000.00"))
        with pytest.raises(ValidationError):
            detalle.full_clean()


# ═══════════════════════════════════════════════════════════════════════════════
# OrdenCompra
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrdenCompraModel:

    def test_calcular_total(self, db):
        orden = OrdenCompraFactory()
        DetalleOrdenCompraFactory(
            orden=orden,
            cantidad=Decimal("2.000"),
            precio_unitario=Decimal("1000.00"),
            subtotal=Decimal("2000.00"))
        DetalleOrdenCompraFactory(
            orden=orden,
            cantidad=Decimal("3.000"),
            precio_unitario=Decimal("1000.00"),
            subtotal=Decimal("3000.00"))
        orden.calcular_total()
        orden.refresh_from_db()
        assert orden.total_estimado == Decimal("5000.00")

    def test_str(self, db):
        proveedor = ProveedorFactory(nombre="Dist. Central")
        orden = OrdenCompraFactory(proveedor=proveedor)
        assert "Dist. Central" in str(orden)


# ═══════════════════════════════════════════════════════════════════════════════
# AlertaStock
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertaStockModel:

    def test_crear_alerta(self, db):
        alerta = AlertaStockFactory()
        assert alerta.estado == EstadoAlerta.PENDIENTE

    def test_resolver(self, db):
        alerta = AlertaStockFactory()
        alerta.resolver()
        assert alerta.estado == EstadoAlerta.RESUELTA
        assert alerta.fecha_resolucion is not None

    def test_str(self, db):
        alerta = AlertaStockFactory(tipo_alerta=TipoAlerta.STOCK_BAJO)
        assert "STOCK_BAJO" in str(alerta)

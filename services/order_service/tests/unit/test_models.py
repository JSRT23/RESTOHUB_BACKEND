# tests/unit/test_models.py
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from app.orders.models import (
    CanalPedido, ComandaCocina, DetallePedido, EntregaPedido,
    EstadoComanda, EstadoEntrega, EstadoPedido, EstacionCocina,
    MetodoPago, Pedido, PrioridadPedido, SeguimientoPedido,
    TipoEntrega,
)
from tests.conftest import (
    ComandaCocinaFactory, DetallePedidoFactory,
    EntregaPedidoFactory, PedidoFactory,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Pedido
# ═══════════════════════════════════════════════════════════════════════════════

class TestPedidoModel:

    def test_crear_pedido(self, db):
        p = PedidoFactory()
        assert p.pk is not None
        assert p.estado == EstadoPedido.RECIBIDO
        assert p.canal == CanalPedido.TPV

    def test_id_es_uuid(self, db):
        p = PedidoFactory()
        assert isinstance(p.id, uuid.UUID)

    def test_estado_default_recibido(self, db):
        p = PedidoFactory()
        assert p.estado == EstadoPedido.RECIBIDO

    def test_prioridad_default_normal(self, db):
        p = PedidoFactory()
        assert p.prioridad == PrioridadPedido.NORMAL

    def test_metodo_pago_null_por_defecto(self, db):
        p = PedidoFactory()
        assert p.metodo_pago is None

    def test_numero_dia_asignado(self, db):
        p = PedidoFactory(numero_dia=3)
        assert p.numero_dia == 3

    def test_str(self, db):
        p = PedidoFactory(canal=CanalPedido.APP)
        s = str(p)
        assert "APP" in s
        assert str(p.id) in s

    def test_cliente_id_puede_ser_null(self, db):
        p = PedidoFactory(cliente_id=None)
        assert p.cliente_id is None

    def test_mesa_id_puede_ser_null(self, db):
        p = PedidoFactory(mesa_id=None)
        assert p.mesa_id is None

    def test_cascade_delete_detalles(self, db):
        p = PedidoFactory()
        d = DetallePedidoFactory(pedido=p)
        d_id = d.id
        p.delete()
        assert not DetallePedido.objects.filter(id=d_id).exists()

    def test_cascade_delete_seguimientos(self, db):
        p = PedidoFactory()
        s = SeguimientoPedido.objects.create(
            pedido=p, estado=EstadoPedido.RECIBIDO)
        s_id = s.id
        p.delete()
        assert not SeguimientoPedido.objects.filter(id=s_id).exists()

    @pytest.mark.parametrize("estado", [
        EstadoPedido.RECIBIDO, EstadoPedido.EN_PREPARACION,
        EstadoPedido.LISTO, EstadoPedido.ENTREGADO, EstadoPedido.CANCELADO,
    ])
    def test_estados_validos(self, db, estado):
        p = PedidoFactory(estado=estado)
        assert p.estado == estado

    @pytest.mark.parametrize("canal", [
        CanalPedido.TPV, CanalPedido.APP,
        CanalPedido.UBER_EATS, CanalPedido.RAPPI,
    ])
    def test_canales_validos(self, db, canal):
        p = PedidoFactory(canal=canal)
        assert p.canal == canal


# ═══════════════════════════════════════════════════════════════════════════════
# DetallePedido
# ═══════════════════════════════════════════════════════════════════════════════

class TestDetallePedidoModel:

    def test_crear_detalle(self, db):
        d = DetallePedidoFactory()
        assert d.pk is not None
        assert d.cantidad == 1

    def test_subtotal_calculado_en_save(self, db):
        d = DetallePedidoFactory(precio_unitario=Decimal("5000"), cantidad=3)
        assert d.subtotal == Decimal("15000")

    def test_subtotal_recalculado_al_actualizar(self, db):
        d = DetallePedidoFactory(precio_unitario=Decimal("2000"), cantidad=2)
        d.cantidad = 5
        d.save()
        assert d.subtotal == Decimal("10000")

    def test_str(self, db):
        d = DetallePedidoFactory(nombre_plato="Hamburguesa Angus", cantidad=2)
        assert "Hamburguesa Angus" in str(d)
        assert "2" in str(d)

    def test_notas_puede_ser_null(self, db):
        d = DetallePedidoFactory(notas=None)
        assert d.notas is None

    def test_fk_pedido(self, db):
        p = PedidoFactory()
        d = DetallePedidoFactory(pedido=p)
        assert d.pedido_id == p.id


# ═══════════════════════════════════════════════════════════════════════════════
# ComandaCocina
# ═══════════════════════════════════════════════════════════════════════════════

class TestComandaCocinaModel:

    def test_crear_comanda(self, db):
        c = ComandaCocinaFactory()
        assert c.pk is not None
        assert c.estado == EstadoComanda.PENDIENTE

    def test_hora_envio_auto(self, db):
        c = ComandaCocinaFactory()
        assert c.hora_envio is not None

    def test_hora_fin_null_por_defecto(self, db):
        c = ComandaCocinaFactory()
        assert c.hora_fin is None

    def test_tiempo_preparacion_none_sin_hora_fin(self, db):
        c = ComandaCocinaFactory()
        assert c.tiempo_preparacion_segundos is None

    def test_tiempo_preparacion_con_hora_fin(self, db):
        c = ComandaCocinaFactory()
        c.hora_fin = c.hora_envio + timedelta(minutes=10)
        assert c.tiempo_preparacion_segundos == pytest.approx(600, abs=1)

    def test_str(self, db):
        c = ComandaCocinaFactory(estacion=EstacionCocina.PARRILLA)
        assert "PARRILLA" in str(c)

    @pytest.mark.parametrize("estacion", [
        EstacionCocina.PARRILLA, EstacionCocina.BEBIDAS,
        EstacionCocina.POSTRES, EstacionCocina.FRIOS, EstacionCocina.GENERAL,
    ])
    def test_estaciones_validas(self, db, estacion):
        c = ComandaCocinaFactory(estacion=estacion)
        assert c.estacion == estacion


# ═══════════════════════════════════════════════════════════════════════════════
# SeguimientoPedido
# ═══════════════════════════════════════════════════════════════════════════════

class TestSeguimientoPedidoModel:

    def test_crear_seguimiento(self, db):
        p = PedidoFactory()
        s = SeguimientoPedido.objects.create(
            pedido=p, estado=EstadoPedido.RECIBIDO, descripcion="Pedido recibido."
        )
        assert s.pk is not None

    def test_fecha_auto(self, db):
        p = PedidoFactory()
        s = SeguimientoPedido.objects.create(
            pedido=p, estado=EstadoPedido.RECIBIDO)
        assert s.fecha is not None

    def test_ordering_por_fecha(self, db):
        p = PedidoFactory()
        s1 = SeguimientoPedido.objects.create(
            pedido=p, estado=EstadoPedido.RECIBIDO)
        s2 = SeguimientoPedido.objects.create(
            pedido=p, estado=EstadoPedido.EN_PREPARACION)
        seguimientos = list(p.seguimientos.all())
        assert seguimientos[0].id == s1.id
        assert seguimientos[1].id == s2.id

    def test_str(self, db):
        p = PedidoFactory()
        s = SeguimientoPedido.objects.create(
            pedido=p, estado=EstadoPedido.LISTO)
        assert "LISTO" in str(s)


# ═══════════════════════════════════════════════════════════════════════════════
# EntregaPedido
# ═══════════════════════════════════════════════════════════════════════════════

class TestEntregaPedidoModel:

    def test_crear_entrega(self, db):
        e = EntregaPedidoFactory()
        assert e.pk is not None
        assert e.estado_entrega == EstadoEntrega.PENDIENTE

    def test_one_to_one_con_pedido(self, db):
        p = PedidoFactory.listo()
        e = EntregaPedidoFactory(pedido=p)
        assert e.pedido_id == p.id

    def test_fecha_salida_null_por_defecto(self, db):
        e = EntregaPedidoFactory()
        assert e.fecha_salida is None

    def test_fecha_entrega_real_null_por_defecto(self, db):
        e = EntregaPedidoFactory()
        assert e.fecha_entrega_real is None

    def test_str_contiene_tipo_y_estado(self, db):
        e = EntregaPedidoFactory(tipo_entrega=TipoEntrega.DELIVERY,
                                 direccion="Calle 10 #5-20")
        assert "DELIVERY" in str(e)

    @pytest.mark.parametrize("tipo", [
        TipoEntrega.LOCAL, TipoEntrega.PICKUP, TipoEntrega.DELIVERY,
    ])
    def test_tipos_validos(self, db, tipo):
        e = EntregaPedidoFactory(tipo_entrega=tipo)
        assert e.tipo_entrega == tipo

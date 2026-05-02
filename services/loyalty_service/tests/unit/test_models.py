# tests/unit/test_models.py
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from app.loyalty.models import (
    CuentaPuntos, TransaccionPuntos, Promocion, ReglaPromocion,
    AplicacionPromocion, Cupon, CatalogoPlato, CatalogoCategoria,
    NivelCliente, TipoTransaccion,
)
from tests.conftest import (
    CuentaPuntosFactory, TransaccionPuntosFactory, PromocionFactory,
    ReglaPromocionFactory, CuponFactory, CatalogoPlatoFactory,
    CatalogoCategoriaFactory,
)


class TestCuentaPuntosModel:

    def test_crear_cuenta(self, db):
        c = CuentaPuntosFactory()
        assert c.pk is not None
        assert c.saldo == 500
        assert c.nivel == NivelCliente.BRONCE

    def test_id_es_uuid(self, db):
        c = CuentaPuntosFactory()
        assert isinstance(c.id, uuid.UUID)

    def test_cliente_id_unico(self, db):
        from django.db import IntegrityError
        cid = uuid.uuid4()
        CuentaPuntosFactory(cliente_id=cid)
        with pytest.raises(IntegrityError):
            CuentaPuntosFactory(cliente_id=cid)

    def test_str(self, db):
        c = CuentaPuntosFactory()
        s = str(c)
        assert str(c.cliente_id) in s
        assert str(c.saldo) in s

    def test_actualizar_nivel_bronce(self, db):
        c = CuentaPuntosFactory(puntos_totales_historicos=999)
        c.actualizar_nivel()
        assert c.nivel == NivelCliente.BRONCE

    def test_actualizar_nivel_plata(self, db):
        c = CuentaPuntosFactory(puntos_totales_historicos=1000)
        c.actualizar_nivel()
        assert c.nivel == NivelCliente.PLATA

    def test_actualizar_nivel_oro(self, db):
        c = CuentaPuntosFactory(puntos_totales_historicos=5000)
        c.actualizar_nivel()
        assert c.nivel == NivelCliente.ORO

    def test_actualizar_nivel_diamante(self, db):
        c = CuentaPuntosFactory(puntos_totales_historicos=10000)
        c.actualizar_nivel()
        assert c.nivel == NivelCliente.DIAMANTE

    def test_nivel_limite_inferior_plata(self, db):
        c = CuentaPuntosFactory(puntos_totales_historicos=1000)
        c.actualizar_nivel()
        assert c.nivel == NivelCliente.PLATA

    def test_nivel_limite_inferior_oro(self, db):
        c = CuentaPuntosFactory(puntos_totales_historicos=5000)
        c.actualizar_nivel()
        assert c.nivel == NivelCliente.ORO

    def test_nivel_limite_inferior_diamante(self, db):
        c = CuentaPuntosFactory(puntos_totales_historicos=10000)
        c.actualizar_nivel()
        assert c.nivel == NivelCliente.DIAMANTE


class TestTransaccionPuntosModel:

    def test_crear_transaccion(self, db):
        t = TransaccionPuntosFactory()
        assert t.pk is not None
        assert t.tipo == TipoTransaccion.ACUMULACION

    def test_str_positivo(self, db):
        t = TransaccionPuntosFactory(puntos=200, saldo_posterior=200)
        assert "+" in str(t)
        assert "200" in str(t)

    def test_str_negativo(self, db):
        cuenta = CuentaPuntosFactory(saldo=500)
        t = TransaccionPuntosFactory(
            cuenta=cuenta, tipo=TipoTransaccion.CANJE,
            puntos=-100, saldo_anterior=500, saldo_posterior=400,
        )
        assert "-100" in str(t)

    def test_ordering_por_fecha_desc(self, db):
        cuenta = CuentaPuntosFactory()
        t1 = TransaccionPuntosFactory(cuenta=cuenta)
        t2 = TransaccionPuntosFactory(cuenta=cuenta)
        qs = list(TransaccionPuntos.objects.filter(cuenta=cuenta))
        assert qs[0].created_at >= qs[1].created_at

    def test_pedido_id_puede_ser_null(self, db):
        t = TransaccionPuntosFactory(pedido_id=None)
        assert t.pedido_id is None


class TestPromocionModel:

    def test_crear_promocion(self, db):
        p = PromocionFactory()
        assert p.pk is not None
        assert p.activa is True

    def test_str(self, db):
        p = PromocionFactory(nombre="Black Friday")
        assert "Black Friday" in str(p)

    def test_clean_local_sin_restaurante_falla(self, db):
        from django.core.exceptions import ValidationError
        p = PromocionFactory.build(alcance="local", restaurante_id=None)
        with pytest.raises(ValidationError):
            p.clean()

    def test_clean_marca_sin_marca_falla(self, db):
        from django.core.exceptions import ValidationError
        p = PromocionFactory.build(alcance="marca", marca="")
        with pytest.raises(ValidationError):
            p.clean()

    def test_clean_global_sin_extras_ok(self, db):
        p = PromocionFactory.build(alcance="global")
        p.clean()  # no debe lanzar

    def test_cascade_delete_reglas(self, db):
        p = PromocionFactory()
        ReglaPromocionFactory(promocion=p)
        pid = p.id
        p.delete()
        assert not ReglaPromocion.objects.filter(promocion_id=pid).exists()


class TestCuponModel:

    def test_crear_cupon(self, db):
        c = CuponFactory()
        assert c.pk is not None
        assert c.activo is True

    def test_disponible_cupon_activo(self, db):
        c = CuponFactory()
        assert c.disponible is True

    def test_disponible_cupon_inactivo(self, db):
        c = CuponFactory.inactivo()
        assert c.disponible is False

    def test_disponible_cupon_agotado(self, db):
        c = CuponFactory.agotado()
        assert c.disponible is False

    def test_disponible_cupon_expirado(self, db):
        c = CuponFactory.expirado()
        assert c.disponible is False

    def test_disponible_futuro(self, db):
        c = CuponFactory(
            fecha_inicio=date.today() + timedelta(days=5),
            fecha_fin=date.today() + timedelta(days=10),
        )
        assert c.disponible is False

    def test_codigo_generado_automaticamente(self, db):
        c = Cupon(
            tipo_descuento="porcentaje",
            valor_descuento=Decimal("10"),
            limite_uso=1,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=30),
        )
        c.save()
        assert c.codigo
        assert len(c.codigo) == 8

    def test_codigo_unico(self, db):
        from django.db import IntegrityError
        CuponFactory(codigo="UNICO001")
        with pytest.raises(IntegrityError):
            CuponFactory(codigo="UNICO001")

    def test_str(self, db):
        c = CuponFactory(codigo="PROMO123")
        assert "PROMO123" in str(c)

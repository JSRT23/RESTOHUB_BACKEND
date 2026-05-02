# tests/unit/test_serializers.py
import uuid
from decimal import Decimal

import pytest

from app.orders.models import EstadoPedido, TipoEntrega
from app.orders.serializers import (
    DetallePedidoWriteSerializer,
    EntregaPedidoWriteSerializer,
    PedidoCambioEstadoSerializer,
    PedidoWriteSerializer,
    ComandaCocinaWriteSerializer,
)
from tests.conftest import PedidoFactory


# ═══════════════════════════════════════════════════════════════════════════════
# DetallePedidoWriteSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestDetallePedidoWriteSerializer:

    def _data(self, **kwargs):
        base = {
            "plato_id":        str(uuid.uuid4()),
            "nombre_plato":    "Hamburguesa Angus",
            "precio_unitario": "8500.00",
            "cantidad":        2,
        }
        base.update(kwargs)
        return base

    def test_datos_validos(self):
        s = DetallePedidoWriteSerializer(data=self._data())
        assert s.is_valid(), s.errors

    def test_cantidad_cero_falla(self):
        s = DetallePedidoWriteSerializer(data=self._data(cantidad=0))
        assert not s.is_valid()
        assert "cantidad" in s.errors

    def test_cantidad_negativa_falla(self):
        s = DetallePedidoWriteSerializer(data=self._data(cantidad=-1))
        assert not s.is_valid()
        assert "cantidad" in s.errors

    def test_precio_cero_falla(self):
        s = DetallePedidoWriteSerializer(data=self._data(precio_unitario="0"))
        assert not s.is_valid()
        assert "precio_unitario" in s.errors

    def test_precio_negativo_falla(self):
        s = DetallePedidoWriteSerializer(
            data=self._data(precio_unitario="-100"))
        assert not s.is_valid()
        assert "precio_unitario" in s.errors

    def test_nombre_plato_requerido(self):
        data = self._data()
        del data["nombre_plato"]
        s = DetallePedidoWriteSerializer(data=data)
        assert not s.is_valid()
        assert "nombre_plato" in s.errors

    def test_notas_opcional(self):
        s = DetallePedidoWriteSerializer(data=self._data(notas="Sin cebolla"))
        assert s.is_valid(), s.errors


# ═══════════════════════════════════════════════════════════════════════════════
# PedidoWriteSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestPedidoWriteSerializer:

    def _data(self, **kwargs):
        base = {
            "restaurante_id": str(uuid.uuid4()),
            "canal":          "TPV",
            "moneda":         "COP",
            "detalles": [{
                "plato_id":        str(uuid.uuid4()),
                "nombre_plato":    "Pizza",
                "precio_unitario": "25000",
                "cantidad":        1,
            }],
        }
        base.update(kwargs)
        return base

    def test_datos_validos(self, db):
        s = PedidoWriteSerializer(data=self._data())
        assert s.is_valid(), s.errors

    def test_sin_detalles_falla(self, db):
        s = PedidoWriteSerializer(data=self._data(detalles=[]))
        assert not s.is_valid()
        assert "detalles" in s.errors

    def test_create_calcula_total(self, db):
        data = self._data(detalles=[
            {"plato_id": str(uuid.uuid4()), "nombre_plato": "Plato A",
             "precio_unitario": "10000", "cantidad": 2},
            {"plato_id": str(uuid.uuid4()), "nombre_plato": "Plato B",
             "precio_unitario": "5000", "cantidad": 1},
        ])
        s = PedidoWriteSerializer(data=data)
        assert s.is_valid(), s.errors
        pedido = s.save()
        assert pedido.total == Decimal("25000")

    def test_create_estado_recibido(self, db):
        s = PedidoWriteSerializer(data=self._data())
        assert s.is_valid()
        pedido = s.save()
        assert pedido.estado == EstadoPedido.RECIBIDO

    def test_create_genera_seguimiento_inicial(self, db):
        s = PedidoWriteSerializer(data=self._data())
        assert s.is_valid()
        pedido = s.save()
        assert pedido.seguimientos.filter(
            estado=EstadoPedido.RECIBIDO).exists()

    def test_create_numero_dia_autoincremental(self, db):
        rid = uuid.uuid4()
        data = self._data(restaurante_id=str(rid))
        s1 = PedidoWriteSerializer(data=data)
        assert s1.is_valid()
        p1 = s1.save()

        s2 = PedidoWriteSerializer(data=self._data(restaurante_id=str(rid)))
        assert s2.is_valid()
        p2 = s2.save()

        assert p2.numero_dia == p1.numero_dia + 1

    def test_restaurante_id_requerido(self, db):
        data = self._data()
        del data["restaurante_id"]
        s = PedidoWriteSerializer(data=data)
        assert not s.is_valid()

    def test_cliente_id_opcional(self, db):
        s = PedidoWriteSerializer(
            data=self._data(cliente_id=str(uuid.uuid4())))
        assert s.is_valid(), s.errors


# ═══════════════════════════════════════════════════════════════════════════════
# PedidoCambioEstadoSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestPedidoCambioEstadoSerializer:

    def test_sin_campos_es_valido(self):
        s = PedidoCambioEstadoSerializer(data={})
        assert s.is_valid(), s.errors

    def test_descripcion_opcional(self):
        s = PedidoCambioEstadoSerializer(data={"descripcion": "Pedido listo"})
        assert s.is_valid()
        assert s.validated_data["descripcion"] == "Pedido listo"

    def test_metodo_pago_opcional(self):
        s = PedidoCambioEstadoSerializer(data={"metodo_pago": "efectivo"})
        assert s.is_valid()
        assert s.validated_data["metodo_pago"] == "efectivo"

    def test_ambos_campos(self):
        s = PedidoCambioEstadoSerializer(data={
            "descripcion": "Cobrado",
            "metodo_pago": "tarjeta",
        })
        assert s.is_valid()


# ═══════════════════════════════════════════════════════════════════════════════
# ComandaCocinaWriteSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestComandaCocinaWriteSerializer:

    def test_pedido_recibido_es_valido(self, db):
        p = PedidoFactory()  # RECIBIDO
        s = ComandaCocinaWriteSerializer(data={
            "pedido":   str(p.id),
            "estacion": "GENERAL",
        })
        assert s.is_valid(), s.errors

    def test_pedido_en_preparacion_es_valido(self, db):
        p = PedidoFactory.en_preparacion()
        s = ComandaCocinaWriteSerializer(data={
            "pedido":   str(p.id),
            "estacion": "PARRILLA",
        })
        assert s.is_valid(), s.errors

    def test_pedido_cancelado_falla(self, db):
        p = PedidoFactory.cancelado()
        s = ComandaCocinaWriteSerializer(data={
            "pedido":   str(p.id),
            "estacion": "GENERAL",
        })
        assert not s.is_valid()
        assert "pedido" in s.errors

    def test_pedido_entregado_falla(self, db):
        p = PedidoFactory.entregado()
        s = ComandaCocinaWriteSerializer(data={
            "pedido":   str(p.id),
            "estacion": "BEBIDAS",
        })
        assert not s.is_valid()


# ═══════════════════════════════════════════════════════════════════════════════
# EntregaPedidoWriteSerializer
# ═══════════════════════════════════════════════════════════════════════════════

class TestEntregaPedidoWriteSerializer:

    def test_entrega_local_valida(self, db):
        p = PedidoFactory.listo()
        s = EntregaPedidoWriteSerializer(data={
            "pedido":       str(p.id),
            "tipo_entrega": "LOCAL",
        })
        assert s.is_valid(), s.errors

    def test_delivery_sin_direccion_falla(self, db):
        p = PedidoFactory.listo()
        s = EntregaPedidoWriteSerializer(data={
            "pedido":       str(p.id),
            "tipo_entrega": "DELIVERY",
        })
        assert not s.is_valid()
        assert "direccion" in str(s.errors)

    def test_delivery_con_direccion_valida(self, db):
        p = PedidoFactory.listo()
        s = EntregaPedidoWriteSerializer(data={
            "pedido":       str(p.id),
            "tipo_entrega": "DELIVERY",
            "direccion":    "Calle 10 # 5-20",
        })
        assert s.is_valid(), s.errors

    def test_pedido_con_entrega_existente_falla(self, db):
        from tests.conftest import EntregaPedidoFactory
        e = EntregaPedidoFactory()
        s = EntregaPedidoWriteSerializer(data={
            "pedido":       str(e.pedido_id),
            "tipo_entrega": "LOCAL",
        })
        assert not s.is_valid()
        assert "pedido" in s.errors

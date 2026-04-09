# loyalty_service/app/loyalty/events/builders.py
"""
Builders de eventos de loyalty_service.

CRÍTICO: Este archivo estaba VACÍO — order_handlers.py importaba
LoyaltyEventBuilder y llamaba puntos_acumulados() y promocion_aplicada()
que no existían → AttributeError en runtime.
"""


class LoyaltyEventBuilder:

    @staticmethod
    def puntos_acumulados(
        cuenta,
        pedido_id: str,
        restaurante_id: str,
        puntos_ganados: int,
        saldo_anterior: int,
        nivel_anterior: str,
    ) -> dict:
        return {
            "cliente_id":      str(cuenta.cliente_id),
            "pedido_id":       str(pedido_id),
            "restaurante_id":  str(restaurante_id),
            "puntos_ganados":  puntos_ganados,
            "saldo_anterior":  saldo_anterior,
            "saldo_nuevo":     cuenta.saldo,
            # ✅ capturado ANTES de actualizar_nivel()
            "nivel_anterior":  nivel_anterior,
            "nivel_nuevo":     cuenta.nivel,
        }

    @staticmethod
    def promocion_aplicada(aplicacion) -> dict:
        return {
            "cliente_id":             str(aplicacion.cliente_id),
            "pedido_id":              str(aplicacion.pedido_id),
            "promocion_id":           str(aplicacion.promocion_id),
            "promocion_nombre":       aplicacion.promocion.nombre,
            "descuento_aplicado":     float(aplicacion.descuento_aplicado),
            "puntos_bonus_otorgados": aplicacion.puntos_bonus_otorgados,
        }

    @staticmethod
    def puntos_vencidos(cuenta, puntos_vencidos: int) -> dict:
        return {
            "cliente_id":      str(cuenta.cliente_id),
            "puntos_vencidos": puntos_vencidos,
            "saldo_nuevo":     cuenta.saldo,
        }

    @staticmethod
    def cupon_canjeado(cupon, pedido_id=None) -> dict:
        return {
            "cupon_id":   str(cupon.id),
            "codigo":     cupon.codigo,
            "cliente_id": str(cupon.cliente_id) if cupon.cliente_id else None,
            "pedido_id":  str(pedido_id) if pedido_id else None,
            "usos":       cupon.usos_actuales,
            "limite":     cupon.limite_uso,
        }

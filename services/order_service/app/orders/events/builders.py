# order_service/app/orders/events/builders.py
class OrderEventBuilder:
    """
    Construye los payloads de los eventos de order_service.
    """

    @staticmethod
    def pedido_confirmado(pedido) -> dict:
        return {
            "pedido_id":      str(pedido.id),
            "restaurante_id": str(pedido.restaurante_id),
            "cliente_id":     str(pedido.cliente_id) if pedido.cliente_id else None,
            "canal":          pedido.canal,
            "moneda":         pedido.moneda,
            "total":          float(pedido.total),
            "detalles": [
                {
                    "plato_id":       str(d.plato_id),
                    "nombre_plato":   d.nombre_plato,
                    "cantidad":       d.cantidad,
                    "precio_unitario": float(d.precio_unitario),
                    "subtotal":       float(d.subtotal),
                }
                for d in pedido.detalles.all()
            ],
        }

    @staticmethod
    def pedido_cancelado(pedido, motivo: str = "") -> dict:
        return {
            "pedido_id":      str(pedido.id),
            "restaurante_id": str(pedido.restaurante_id),
            "cliente_id":     str(pedido.cliente_id) if pedido.cliente_id else None,
            "motivo":         motivo,
            "detalles": [
                {
                    "plato_id": str(d.plato_id),
                    "cantidad": d.cantidad,
                }
                for d in pedido.detalles.all()
            ],
        }

    @staticmethod
    def pedido_entregado(pedido) -> dict:
        return {
            "pedido_id":      str(pedido.id),
            "restaurante_id": str(pedido.restaurante_id),
            "cliente_id":     str(pedido.cliente_id) if pedido.cliente_id else None,
            "canal":          pedido.canal,
            "total":          float(pedido.total),
            "moneda":         pedido.moneda,
            "detalles": [
                {
                    "plato_id":        str(d.plato_id),
                    "cantidad":        d.cantidad,
                    "precio_unitario": float(d.precio_unitario),
                }
                for d in pedido.detalles.all()
            ],
        }

    @staticmethod
    def entrega_asignada(pedido, repartidor_id: str, direccion: str = "") -> dict:
        return {
            "pedido_id":      str(pedido.id),
            "restaurante_id": str(pedido.restaurante_id),
            "repartidor_id":  repartidor_id,
            "direccion":      direccion,
        }

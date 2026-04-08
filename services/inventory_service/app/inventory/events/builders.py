class InventoryEventBuilder:
    """
    Construye los payloads (data) de los eventos de inventory_service.
    Mantiene consistencia con menu_service y staff_service.
    """

    # =========================================================
    # 📦 STOCK
    # =========================================================

    @staticmethod
    def stock_actualizado(
        ingrediente_id,
        almacen_id,
        restaurante_id,
        cantidad_anterior,
        cantidad_nueva,
        unidad_medida,
        tipo_movimiento
    ):
        return {
            "ingrediente_id": str(ingrediente_id),
            "almacen_id": str(almacen_id),
            "restaurante_id": str(restaurante_id),
            "cantidad_anterior": float(cantidad_anterior),
            "cantidad_nueva": float(cantidad_nueva),
            "unidad_medida": unidad_medida,
            "tipo_movimiento": tipo_movimiento
        }

    # =========================================================
    # 🚨 ALERTAS
    # =========================================================

    @staticmethod
    def alerta_stock_bajo(alerta):
        return {
            "alerta_id": str(alerta.id),
            "ingrediente_id": str(alerta.ingrediente_id),
            "restaurante_id": str(alerta.restaurante_id),
            "almacen_id": str(alerta.almacen_id),
            "nombre_ingrediente": alerta.ingrediente_inventario.nombre_ingrediente,
            "nivel_actual": float(alerta.nivel_actual),
            "nivel_minimo": float(alerta.nivel_minimo),
            "unidad_medida": alerta.ingrediente_inventario.unidad_medida,
        }

    @staticmethod
    def alerta_agotado(alerta):
        return {
            "alerta_id": str(alerta.id),
            "ingrediente_id": str(alerta.ingrediente_id),
            "restaurante_id": str(alerta.restaurante_id),
            "almacen_id": str(alerta.almacen_id),
            "nombre_ingrediente": alerta.ingrediente_inventario.nombre_ingrediente,
        }

    @staticmethod
    def alerta_vencimiento_proximo(alerta):
        return {
            "alerta_id": str(alerta.id),
            "lote_id": str(alerta.lote_id),
            "ingrediente_id": str(alerta.ingrediente_id),
            "restaurante_id": str(alerta.restaurante_id),
            "nombre_ingrediente": alerta.nombre_ingrediente,
            "fecha_vencimiento": alerta.fecha_vencimiento.isoformat(),
            "dias_para_vencer": alerta.dias_para_vencer
        }

    # =========================================================
    # 🧪 LOTES
    # =========================================================

    @staticmethod
    def lote_recibido(lote):
        return {
            "lote_id": str(lote.id),
            "ingrediente_id": str(lote.ingrediente_id),
            "almacen_id": str(lote.almacen_id),
            "restaurante_id": str(lote.restaurante_id),
            "proveedor_id": str(lote.proveedor_id),
            "numero_lote": lote.numero_lote,
            "cantidad_recibida": float(lote.cantidad_recibida),
            "unidad_medida": lote.unidad_medida,
            "fecha_vencimiento": lote.fecha_vencimiento.isoformat() if lote.fecha_vencimiento else None
        }

    @staticmethod
    def lote_vencido(lote):
        return {
            "lote_id": str(lote.id),
            "ingrediente_id": str(lote.ingrediente_id),
            "almacen_id": str(lote.almacen_id),
            "restaurante_id": str(lote.restaurante_id),
            "numero_lote": lote.numero_lote,
            "cantidad_actual": float(lote.cantidad_actual),
            "fecha_vencimiento": lote.fecha_vencimiento.isoformat() if lote.fecha_vencimiento else None
        }

    # =========================================================
    # 🛒 ÓRDENES DE COMPRA
    # =========================================================

    @staticmethod
    def orden_compra_creada(orden):
        return {
            "orden_id": str(orden.id),
            "proveedor_id": str(orden.proveedor_id),
            "restaurante_id": str(orden.restaurante_id),
            "total_estimado": float(orden.total_estimado),
            "moneda": orden.moneda,
            "fecha_entrega_estimada": orden.fecha_entrega_estimada.isoformat() if orden.fecha_entrega_estimada else None,
            "detalles": [
                {
                    "ingrediente_id": str(det.ingrediente_id),
                    "cantidad": float(det.cantidad),
                    "precio_unitario": float(det.precio_unitario)
                }
                for det in orden.detalles.all()
            ]
        }

    @staticmethod
    def orden_compra_enviada(orden):
        return {
            "orden_id": str(orden.id),
            "proveedor_id": str(orden.proveedor_id),
            "restaurante_id": str(orden.restaurante_id)
        }

    @staticmethod
    def orden_compra_recibida(orden):
        return {
            "orden_id": str(orden.id),
            "proveedor_id": str(orden.proveedor_id),
            "restaurante_id": str(orden.restaurante_id),
            "detalles": [
                {
                    "ingrediente_id": str(det.ingrediente_id),
                    "cantidad_recibida": float(det.cantidad_recibida)
                }
                for det in orden.detalles.all()
            ]
        }

    @staticmethod
    def orden_compra_cancelada(orden):
        return {
            "orden_id": str(orden.id),
            "proveedor_id": str(orden.proveedor_id),
            "restaurante_id": str(orden.restaurante_id)
        }

    # =========================================================
    # 💰 COSTO PLATO
    # =========================================================

    @staticmethod
    def costo_plato_actualizado(plato_id, costo_total, moneda, ingredientes):
        return {
            "plato_id": str(plato_id),
            "costo_total": float(costo_total),
            "moneda": moneda,
            "ingredientes": [
                {
                    "ingrediente_id": str(i["ingrediente_id"]),
                    "nombre": i["nombre"],
                    "cantidad": float(i["cantidad"]),
                    "unidad_medida": i["unidad_medida"],
                    "costo_unitario": float(i["costo_unitario"]),
                    "costo_ingrediente": float(i["costo_ingrediente"]),
                }
                for i in ingredientes
            ],
            "fecha_actualizacion": None  # lo puedes llenar desde el service si quieres
        }

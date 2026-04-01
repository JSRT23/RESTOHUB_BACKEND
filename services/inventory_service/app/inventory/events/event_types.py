# inventory_service/app/inventory/events/event_types.py
class InventoryEvents:
    """
    Eventos publicados por inventory_service hacia RabbitMQ.

    Convención: app.{servicio}.{entidad}.{accion}

    Eventos que PUBLICA:
    ┌─────────────────────────────────────┬──────────────────────────────────────┐
    │ Evento                              │ Consumidores                         │
    ├─────────────────────────────────────┼──────────────────────────────────────┤
    │ stock.actualizado                   │ gateway (dashboard tiempo real)      │
    │ alerta.stock_bajo                   │ staff_service, gateway               │
    │ alerta.agotado                      │ staff_service, order_service         │
    │ alerta.vencimiento_proximo          │ staff_service                        │
    │ lote.recibido                       │ gateway                              │
    │ lote.vencido                        │ staff_service                        │
    │ orden_compra.creada                 │ staff_service                        │
    │ orden_compra.recibida               │ gateway                              │
    └─────────────────────────────────────┴──────────────────────────────────────┘

    Eventos que CONSUME:
    ┌─────────────────────────────────────┬──────────────────────────────────────┐
    │ Origen                              │ Evento                               │
    ├─────────────────────────────────────┼──────────────────────────────────────┤
    │ menu_service                        │ restaurante.created                  │
    │ menu_service                        │ ingrediente.created/updated          │
    │ menu_service                        │ ingrediente.deactivated              │
    │ menu_service                        │ plato_ingrediente.added/removed      │
    │ menu_service                        │ plato_ingrediente.cantidad_updated   │
    │ order_service                       │ pedido.confirmado                    │
    │ order_service                       │ pedido.cancelado                     │
    └─────────────────────────────────────┴──────────────────────────────────────┘
    """

    """
    Eventos publicados por inventory_service.

    Convención: app.{servicio}.{entidad}.{accion}

    Este servicio es responsable de:
    - Gestión de stock
    - Control de lotes
    - Alertas operativas
    - Órdenes de compra

    Todos los eventos siguen el formato estándar:
    {
        "event_id": str (UUID),
        "event_type": str,
        "timestamp": str (ISO 8601),
        "service_origin": "inventory_service",
        "version": "1.0",
        "data": { ... }
    }
    """

    # =========================================================
    #  STOCK
    # =========================================================

    STOCK_ACTUALIZADO = "app.inventory.stock.actualizado"
    # data: {
    #   ingrediente_id,
    #   almacen_id,
    #   restaurante_id,
    #   cantidad_anterior,
    #   cantidad_nueva,
    #   unidad_medida,
    #   tipo_movimiento  # entrada | salida | ajuste
    # }

    # =========================================================
    #  ALERTAS
    # =========================================================

    ALERTA_STOCK_BAJO = "app.inventory.alerta.stock_bajo"
    # data: {
    #   alerta_id,
    #   ingrediente_id,
    #   restaurante_id,
    #   almacen_id,
    #   nombre_ingrediente,
    #   nivel_actual,
    #   nivel_minimo,
    #   unidad_medida
    # }

    ALERTA_AGOTADO = "app.inventory.alerta.agotado"
    # data: {
    #   alerta_id,
    #   ingrediente_id,
    #   restaurante_id,
    #   almacen_id,
    #   nombre_ingrediente
    # }

    ALERTA_VENCIMIENTO_PROXIMO = "app.inventory.alerta.vencimiento_proximo"
    # data: {
    #   alerta_id,
    #   lote_id,
    #   ingrediente_id,
    #   restaurante_id,
    #   nombre_ingrediente,
    #   fecha_vencimiento,
    #   dias_para_vencer
    # }

    # =========================================================
    #  LOTES
    # =========================================================

    LOTE_RECIBIDO = "app.inventory.lote.recibido"
    # data: {
    #   lote_id,
    #   ingrediente_id,
    #   almacen_id,
    #   restaurante_id,
    #   proveedor_id,
    #   numero_lote,
    #   cantidad_recibida,
    #   unidad_medida,
    #   fecha_vencimiento
    # }

    LOTE_VENCIDO = "app.inventory.lote.vencido"
    # data: {
    #   lote_id,
    #   ingrediente_id,
    #   almacen_id,
    #   restaurante_id,
    #   numero_lote,
    #   cantidad_actual,
    #   fecha_vencimiento
    # }

    # =========================================================
    # ÓRDENES DE COMPRA
    # =========================================================

    ORDEN_COMPRA_CREADA = "app.inventory.orden_compra.creada"
    # data: {
    #   orden_id,
    #   proveedor_id,
    #   restaurante_id,
    #   total_estimado,
    #   moneda,
    #   fecha_entrega_estimada,
    #   detalles: [
    #       { ingrediente_id, cantidad, precio_unitario }
    #   ]
    # }

    ORDEN_COMPRA_ENVIADA = "app.inventory.orden_compra.enviada"
    # data: {
    #   orden_id,
    #   proveedor_id,
    #   restaurante_id
    # }

    ORDEN_COMPRA_RECIBIDA = "app.inventory.orden_compra.recibida"
    # data: {
    #   orden_id,
    #   proveedor_id,
    #   restaurante_id,
    #   detalles: [
    #       { ingrediente_id, cantidad_recibida }
    #   ]
    # }

    ORDEN_COMPRA_CANCELADA = "app.inventory.orden_compra.cancelada"
    # data: {
    #   orden_id,
    #   proveedor_id,
    #   restaurante_id
    # }

    # =========================================================
    #  COSTOS
    # =========================================================

    COSTO_PLATO_ACTUALIZADO = "app.inventory.costo_plato.actualizado"
    # data: {
    #   plato_id,
    #   costo_total,
    #   moneda,
    #   ingredientes: [
    #       {
    #           ingrediente_id,
    #           nombre,
    #           cantidad,
    #           unidad_medida,
    #           costo_unitario,
    #           costo_ingrediente
    #       }
    #   ],
    #   fecha_actualizacion
    # }

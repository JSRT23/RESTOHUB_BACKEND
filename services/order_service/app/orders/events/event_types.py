# order_service/app/orders/events/event_types.py
class OrderEvents:
    """
    Eventos publicados por order_service.

    Convención: app.{servicio}.{entidad}.{accion}

    ┌──────────────────────────────────────┬──────────────────────────────────────┐
    │ Evento                               │ Consumidores                         │
    ├──────────────────────────────────────┼──────────────────────────────────────┤
    │ pedido.confirmado                    │ inventory, staff, loyalty            │
    │ pedido.cancelado                     │ inventory, loyalty                   │
    │ pedido.entregado                     │ loyalty                              │
    │ entrega.asignada                     │ staff                                │
    └──────────────────────────────────────┴──────────────────────────────────────┘

    Eventos que CONSUME:
    ┌──────────────────────────────────────┬──────────────────────────────────────┐
    │ Origen                               │ Evento                               │
    ├──────────────────────────────────────┼──────────────────────────────────────┤
    │ menu_service                         │ restaurante.creado                   │
    │ menu_service                         │ plato.creado/actualizado/desactivado │
    │ menu_service                         │ precio.creado/actualizado/desactivado│
    │ staff_service                        │ cocina.asignacion.creada             │
    │ staff_service                        │ cocina.asignacion.completada         │
    │ staff_service                        │ entrega.asignada                     │
    └──────────────────────────────────────┴──────────────────────────────────────┘
    """

    # ─────────────────────────────────────────
    # 🧾 PEDIDOS
    # ─────────────────────────────────────────

    PEDIDO_CONFIRMADO = "app.order.pedido.confirmado"
    # data: {
    #   pedido_id, restaurante_id, cliente_id,
    #   canal, moneda, total,
    #   detalles: [{ plato_id, nombre_plato, cantidad, precio_unitario, subtotal }]
    # }

    PEDIDO_CANCELADO = "app.order.pedido.cancelado"
    # data: {
    #   pedido_id, restaurante_id, cliente_id,
    #   motivo,
    #   detalles: [{ plato_id, cantidad }]
    # }

    PEDIDO_ENTREGADO = "app.order.pedido.entregado"
    # data: {
    #   pedido_id, restaurante_id, cliente_id,
    #   canal, total, moneda,
    #   detalles: [{ plato_id, cantidad, precio_unitario }]
    # }

    # ─────────────────────────────────────────
    # 🚚 ENTREGAS
    # ─────────────────────────────────────────

    ENTREGA_ASIGNADA = "app.order.entrega.asignada"
    # data: {
    #   pedido_id, restaurante_id,
    #   repartidor_id, direccion
    # }

class OrderEvents:
    """
    Eventos publicados por order_service hacia RabbitMQ.

    Convención de nombres: app.{servicio}.{entidad}.{accion}

    Consumidores por evento:
    ┌─────────────────────────────────────────┬──────────────────────────────────────────┐
    │ Evento                                  │ Consumidores                             │
    ├─────────────────────────────────────────┼──────────────────────────────────────────┤
    │ pedido.creado                           │ inventory_service, loyalty_service       │
    │ pedido.confirmado                       │ inventory_service, staff_service         │
    │ pedido.cancelado                        │ inventory_service, loyalty_service       │
    │ pedido.entregado                        │ loyalty_service, staff_service           │
    │ pedido.estado_actualizado               │ notificaciones (futuro)                  │
    │ comanda.creada                          │ staff_service                            │
    │ comanda.lista                           │ staff_service, notificaciones            │
    │ entrega.asignada                        │ staff_service, notificaciones            │
    │ entrega.completada                      │ loyalty_service, staff_service           │
    │ entrega.fallida                         │ notificaciones                           │
    └─────────────────────────────────────────┴──────────────────────────────────────────┘

    Eventos que order_service CONSUME (de otros servicios):
    ┌─────────────────────────────────────────┬──────────────────────────────────────────┐
    │ Origen                                  │ Evento                                   │
    ├─────────────────────────────────────────┼──────────────────────────────────────────┤
    │ menu_service                            │ precio.updated → invalidar caché         │
    │ menu_service                            │ precio.deactivated → invalidar caché     │
    │ menu_service                            │ plato.deactivated → rechazar pedidos     │
    │ menu_service                            │ restaurante.deactivated → bloquear local │
    │ loyalty_service                         │ promocion.aplicada → aplicar descuento   │
    └─────────────────────────────────────────┴──────────────────────────────────────────┘

    Todos los payloads incluyen:
    {
        "event_id":       str (UUID),
        "event_type":     str,
        "timestamp":      str (ISO 8601),
        "service_origin": "order_service",
        "version":        "1.0",
        "data":           { ... }
    }
    """

    # ─────────────────────────────────────────
    # PEDIDO
    # ─────────────────────────────────────────

    PEDIDO_CREADO = "app.order.pedido.creado"
    # data: { pedido_id, restaurante_id, cliente_id, canal, estado,
    #         prioridad, total, moneda, mesa_id, fecha_creacion,
    #         fecha_entrega_estimada, detalles: [...] }

    PEDIDO_CONFIRMADO = "app.order.pedido.confirmado"
    # data: { pedido_id, restaurante_id, cliente_id, total, moneda, detalles: [...] }
    # inventory_service descuenta stock. staff_service asigna cocina.

    PEDIDO_CANCELADO = "app.order.pedido.cancelado"
    # data: { pedido_id, restaurante_id, cliente_id, motivo, total, moneda }
    # inventory_service revierte stock. loyalty_service anula puntos pendientes.

    PEDIDO_ENTREGADO = "app.order.pedido.entregado"
    # data: { pedido_id, restaurante_id, cliente_id, total, moneda,
    #         fecha_entrega_real }
    # loyalty_service acumula puntos. staff_service cierra la operación.

    PEDIDO_ESTADO_ACTUALIZADO = "app.order.pedido.estado_actualizado"
    # data: { pedido_id, estado_anterior, estado_nuevo, timestamp }
    # Tracking en tiempo real. Futuro: notificaciones push al cliente.

    # ─────────────────────────────────────────
    # COMANDA COCINA
    # ─────────────────────────────────────────

    COMANDA_CREADA = "app.order.comanda.creada"
    # data: { comanda_id, pedido_id, restaurante_id, estacion, estado, hora_envio }
    # staff_service asigna cocinero disponible en esa estación.

    COMANDA_LISTA = "app.order.comanda.lista"
    # data: { comanda_id, pedido_id, restaurante_id, estacion,
    #         hora_envio, hora_fin, tiempo_preparacion_segundos }
    # staff_service mide SLA. Notificaciones avisa al cliente que su pedido está listo.

    # ─────────────────────────────────────────
    # ENTREGA
    # ─────────────────────────────────────────

    ENTREGA_ASIGNADA = "app.order.entrega.asignada"
    # data: { entrega_id, pedido_id, tipo_entrega, repartidor_id,
    #         repartidor_nombre, direccion }
    # staff_service registra al repartidor en servicio.
    # Notificaciones avisa al cliente quién trae su pedido.

    ENTREGA_COMPLETADA = "app.order.entrega.completada"
    # data: { entrega_id, pedido_id, restaurante_id, cliente_id,
    #         tipo_entrega, fecha_entrega_real }
    # loyalty_service acumula puntos definitivos.
    # staff_service libera al repartidor.

    ENTREGA_FALLIDA = "app.order.entrega.fallida"
    # data: { entrega_id, pedido_id, motivo }
    # Notificaciones avisa al cliente. Se puede reintentar asignación.

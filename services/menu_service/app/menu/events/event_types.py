class MenuEvents:
    """
    Eventos publicados por menu_service hacia RabbitMQ.

    Convención de nombres: app.{servicio}.{entidad}.{accion}

    Consumidores por evento:
    ┌──────────────────────────────────────┬─────────────────────────────────────────┐
    │ Evento                               │ Consumidores                            │
    ├──────────────────────────────────────┼─────────────────────────────────────────┤
    │ plato.*                              │ inventory_service, loyalty_service      │
    │ precio.*                             │ order_service, loyalty_service          │
    │ restaurante.*                        │ inventory_service, staff_service        │
    │ categoria.*                          │ loyalty_service                         │
    │ ingrediente.*                        │ inventory_service                       │
    │ plato_ingrediente.*                  │ inventory_service                       │
    └──────────────────────────────────────┴─────────────────────────────────────────┘

    Todos los payloads deben incluir:
    {
        "event_id":       str (UUID),
        "event_type":     str (el nombre del evento),
        "timestamp":      str (ISO 8601),
        "service_origin": "menu_service",
        "version":        "1.0",
        "data":           { ... payload específico del evento }
    }
    """

    # ─────────────────────────────────────────
    # PLATO
    # Consumidores: inventory_service, loyalty_service, order_service
    # ─────────────────────────────────────────

    PLATO_CREATED = "app.menu.plato.created"
    # data: { plato_id, nombre, descripcion, categoria_id, imagen, activo }

    PLATO_UPDATED = "app.menu.plato.updated"
    # data: { plato_id, campos_modificados: {...}, timestamp_anterior }

    PLATO_DELETED = "app.menu.plato.deleted"
    # data: { plato_id }
    # NOTA: usar con precaución — preferir PLATO_DEACTIVATED.
    # inventory_service debe limpiar stock asociado al recibir este evento.

    PLATO_ACTIVATED = "app.menu.plato.activated"
    # data: { plato_id }
    # order_service y loyalty_service habilitan el plato en sus cachés.

    PLATO_DEACTIVATED = "app.menu.plato.deactivated"
    # data: { plato_id }
    # order_service rechaza nuevos pedidos con ese plato_id.
    # loyalty_service suspende promociones asociadas.

    # ─────────────────────────────────────────
    # PRECIO PLATO
    # Consumidores: order_service, loyalty_service
    # ─────────────────────────────────────────

    PRECIO_CREATED = "app.menu.precio.created"
    # data: { precio_id, plato_id, restaurante_id, precio, moneda,
    #         fecha_inicio, fecha_fin, activo }

    PRECIO_UPDATED = "app.menu.precio.updated"
    # data: { precio_id, plato_id, restaurante_id, precio_anterior,
    #         precio_nuevo, fecha_inicio, fecha_fin }
    # order_service invalida su caché local del precio.

    PRECIO_ACTIVATED = "app.menu.precio.activated"
    # data: { precio_id, plato_id, restaurante_id, precio, moneda }
    # Evento separado de CREATED — reactiva un precio previamente desactivado.

    PRECIO_DEACTIVATED = "app.menu.precio.deactivated"
    # data: { precio_id, plato_id, restaurante_id }
    # El plato deja de estar disponible en ese restaurante.

    # ─────────────────────────────────────────
    # RESTAURANTE
    # Consumidores: inventory_service, staff_service, order_service
    # ─────────────────────────────────────────

    RESTAURANTE_CREATED = "app.menu.restaurante.created"
    # data: { restaurante_id, nombre, pais, ciudad, moneda }
    # inventory_service crea un registro de stock vacío para el local.
    # staff_service inicializa la configuración laboral por país.

    RESTAURANTE_UPDATED = "app.menu.restaurante.updated"
    # data: { restaurante_id, campos_modificados: {...} }

    RESTAURANTE_DEACTIVATED = "app.menu.restaurante.deactivated"
    # data: { restaurante_id }
    # Todos los servicios deben dejar de procesar operaciones de ese local.

    # ─────────────────────────────────────────
    # CATEGORIA
    # Consumidores: loyalty_service (filtrar promos por categoría)
    # ─────────────────────────────────────────

    CATEGORIA_CREATED = "app.menu.categoria.created"
    # data: { categoria_id, nombre, orden, activo }

    CATEGORIA_UPDATED = "app.menu.categoria.updated"
    # data: { categoria_id, campos_modificados: {...} }

    CATEGORIA_DEACTIVATED = "app.menu.categoria.deactivated"
    # data: { categoria_id }
    # loyalty_service suspende promos asociadas a esa categoría.

    # ─────────────────────────────────────────
    # INGREDIENTE
    # Consumidores: inventory_service (catálogo de ingredientes y stock)
    # ─────────────────────────────────────────

    INGREDIENTE_CREATED = "app.menu.ingrediente.created"
    # data: { ingrediente_id, nombre, unidad_medida }
    # inventory_service registra el ingrediente en su catálogo de stock.

    INGREDIENTE_UPDATED = "app.menu.ingrediente.updated"
    # data: { ingrediente_id, campos_modificados: {...} }

    INGREDIENTE_DEACTIVATED = "app.menu.ingrediente.deactivated"
    # data: { ingrediente_id }
    # inventory_service marca el ingrediente como descontinuado.

    # ─────────────────────────────────────────
    # PLATO INGREDIENTE
    # Consumidores: inventory_service
    # Permite recalcular con precisión el consumo de stock por pedido.
    # Más granular que un solo .updated para que inventory sepa exactamente qué cambió.
    # ─────────────────────────────────────────

    PLATO_INGREDIENTE_ADDED = "app.menu.plato_ingrediente.added"
    # data: { plato_id, ingrediente_id, cantidad, unidad_medida }
    # inventory_service actualiza la receta del plato sumando el nuevo ingrediente.

    PLATO_INGREDIENTE_REMOVED = "app.menu.plato_ingrediente.removed"
    # data: { plato_id, ingrediente_id }
    # inventory_service elimina el ingrediente de la receta del plato.

    PLATO_INGREDIENTE_CANTIDAD_UPDATED = "app.menu.plato_ingrediente.cantidad_updated"
    # data: { plato_id, ingrediente_id, cantidad_anterior, cantidad_nueva, unidad_medida }
    # inventory_service recalcula el descuento de stock por pedido.

# menu_service/app/menu/events/event_types.py
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
    # =========================================================
    # 🍽️ PLATOS
    # =========================================================

    PLATO_CREADO = "app.menu.plato.creado"
    # data: { plato_id, nombre, descripcion, categoria_id, activo }

    PLATO_ACTUALIZADO = "app.menu.plato.actualizado"
    # data: { plato_id, cambios: {...} }

    PLATO_ACTIVADO = "app.menu.plato.activado"
    # data: { plato_id }

    PLATO_DESACTIVADO = "app.menu.plato.desactivado"
    # data: { plato_id }

    PLATO_ELIMINADO = "app.menu.plato.eliminado"
    # data: { plato_id }
    # ⚠️ Usar solo si realmente se elimina físicamente

    # =========================================================
    # 💰 PRECIOS
    # =========================================================

    PRECIO_CREADO = "app.menu.precio.creado"
    # data: {
    #   precio_id,
    #   plato_id,
    #   restaurante_id,
    #   precio,
    #   moneda,
    #   activo
    # }

    PRECIO_ACTUALIZADO = "app.menu.precio.actualizado"
    # data: {
    #   precio_id,
    #   plato_id,
    #   restaurante_id,
    #   precio_anterior,
    #   precio_nuevo
    # }

    PRECIO_ACTIVADO = "app.menu.precio.activado"
    # data: { precio_id, plato_id, restaurante_id }

    PRECIO_DESACTIVADO = "app.menu.precio.desactivado"
    # data: { precio_id, plato_id, restaurante_id }

    # =========================================================
    # 🏪 RESTAURANTES
    # =========================================================

    RESTAURANTE_CREADO = "app.menu.restaurante.creado"
    # data: { restaurante_id, nombre, pais, ciudad, moneda }

    RESTAURANTE_ACTUALIZADO = "app.menu.restaurante.actualizado"
    # data: { restaurante_id, cambios: {...} }

    RESTAURANTE_DESACTIVADO = "app.menu.restaurante.desactivado"
    # data: { restaurante_id }

    # =========================================================
    # 🗂️ CATEGORÍAS
    # =========================================================

    CATEGORIA_CREADA = "app.menu.categoria.creada"
    # data: { categoria_id, nombre, activo }

    CATEGORIA_ACTUALIZADA = "app.menu.categoria.actualizada"
    # data: { categoria_id, cambios: {...} }

    CATEGORIA_DESACTIVADA = "app.menu.categoria.desactivada"
    # data: { categoria_id }

    # =========================================================
    # 🧪 INGREDIENTES
    # =========================================================

    INGREDIENTE_CREADO = "app.menu.ingrediente.creado"
    # data: { ingrediente_id, nombre, unidad_medida }

    INGREDIENTE_ACTUALIZADO = "app.menu.ingrediente.actualizado"
    # data: { ingrediente_id, cambios: {...} }

    INGREDIENTE_DESACTIVADO = "app.menu.ingrediente.desactivado"
    # data: { ingrediente_id }

    # =========================================================
    # 🍳 RELACIÓN PLATO - INGREDIENTE
    # =========================================================

    PLATO_INGREDIENTE_AGREGADO = "app.menu.plato_ingrediente.agregado"
    # data: { plato_id, ingrediente_id, cantidad, unidad_medida }

    PLATO_INGREDIENTE_ELIMINADO = "app.menu.plato_ingrediente.eliminado"
    # data: { plato_id, ingrediente_id }

    PLATO_INGREDIENTE_ACTUALIZADO = "app.menu.plato_ingrediente.actualizado"
    # data: {
    #   plato_id,
    #   ingrediente_id,
    #   cantidad_anterior,
    #   cantidad_nueva
    # }

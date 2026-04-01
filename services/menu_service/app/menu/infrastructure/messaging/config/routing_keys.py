# menu_service/app/menu/infrastructure/messaging/config/routing_keys.py

class RoutingKey:

    # PLATO
    PLATO_CREADO = "app.menu.plato.creado"
    PLATO_ACTUALIZADO = "app.menu.plato.actualizado"
    PLATO_DESACTIVADO = "app.menu.plato.desactivado"

    # PRECIO
    PRECIO_CREADO = "app.menu.precio.creado"
    PRECIO_ACTUALIZADO = "app.menu.precio.actualizado"
    PRECIO_DESACTIVADO = "app.menu.precio.desactivado"

    # CATEGORIA
    CATEGORIA_CREADA = "app.menu.categoria.creada"
    CATEGORIA_ACTUALIZADA = "app.menu.categoria.actualizada"
    CATEGORIA_DESACTIVADA = "app.menu.categoria.desactivada"

    # INGREDIENTE
    INGREDIENTE_CREADO = "app.menu.ingrediente.creado"
    INGREDIENTE_ACTUALIZADO = "app.menu.ingrediente.actualizado"
    INGREDIENTE_DESACTIVADO = "app.menu.ingrediente.desactivado"

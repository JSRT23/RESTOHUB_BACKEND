# menu_service/app/menu/infrastructure/messaging/config/routing_keys.py

class RoutingKey:

    # PLATO
    PLATO_CREADO = "app.menu.plato.creado"
    PLATO_ACTUALIZADO = "app.menu.plato.actualizado"
    PLATO_ACTIVADO = "app.menu.plato.activado"
    PLATO_DESACTIVADO = "app.menu.plato.desactivado"
    PLATO_ELIMINADO = "app.menu.plato.eliminado"

    # PRECIO
    PRECIO_CREADO = "app.menu.precio.creado"
    PRECIO_ACTUALIZADO = "app.menu.precio.actualizado"
    PRECIO_ACTIVADO = "app.menu.precio.activado"
    PRECIO_DESACTIVADO = "app.menu.precio.desactivado"

    # RESTAURANTE
    RESTAURANTE_CREADO = "app.menu.restaurante.creado"
    RESTAURANTE_ACTUALIZADO = "app.menu.restaurante.actualizado"
    RESTAURANTE_DESACTIVADO = "app.menu.restaurante.desactivado"

    # CATEGORIA
    CATEGORIA_CREADA = "app.menu.categoria.creada"
    CATEGORIA_ACTUALIZADA = "app.menu.categoria.actualizada"
    CATEGORIA_DESACTIVADA = "app.menu.categoria.desactivada"

    # INGREDIENTE
    INGREDIENTE_CREADO = "app.menu.ingrediente.creado"
    INGREDIENTE_ACTUALIZADO = "app.menu.ingrediente.actualizado"
    INGREDIENTE_DESACTIVADO = "app.menu.ingrediente.desactivado"

    # PLATO - INGREDIENTE
    PLATO_INGREDIENTE_AGREGADO = "app.menu.plato_ingrediente.agregado"
    PLATO_INGREDIENTE_ELIMINADO = "app.menu.plato_ingrediente.eliminado"
    PLATO_INGREDIENTE_ACTUALIZADO = "app.menu.plato_ingrediente.actualizado"

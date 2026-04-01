# menu_service/app/menu/infrastructure/messaging/consumer/handlers/menu_handler.py
def manejar_evento_menu(evento: dict):
    event_type = evento.get("event_type")
    data = evento.get("data", {})

    print(f"📥 Evento recibido: {event_type}")

    # =========================================================
    # 🏪 RESTAURANTES (IMPORTANTE PARA STAFF)
    # =========================================================

    if event_type == "app.menu.restaurante.creado":
        print("🏪 Restaurante creado:")
        print(f"   ID: {data.get('restaurante_id')}")
        print(f"   Nombre: {data.get('nombre')}")
        print(f"   Ubicación: {data.get('ciudad')}, {data.get('pais')}")
        print(f"   Moneda: {data.get('moneda')}")

        # 🔥 AQUÍ ES DONDE staff_service HARÍA:
        # - Guardar restaurante en su DB
        # - Crear relación con empleados
        # - Inicializar configuraciones

    elif event_type == "app.menu.restaurante.actualizado":
        print("✏️ Restaurante actualizado:")
        print(f"   ID: {data.get('restaurante_id')}")
        print(f"   Cambios: {data.get('cambios')}")

    elif event_type == "app.menu.restaurante.desactivado":
        print("⛔ Restaurante desactivado:")
        print(f"   ID: {data.get('restaurante_id')}")

    # =========================================================
    # 🍽️ PLATOS
    # =========================================================

    elif event_type == "app.menu.plato.creado":
        print(f"🍽️ Nuevo plato: {data}")

    elif event_type == "app.menu.plato.actualizado":
        print(f"✏️ Plato actualizado: {data}")

    elif event_type == "app.menu.plato.desactivado":
        print(f"⛔ Plato desactivado: {data}")

    # =========================================================
    # 💰 PRECIOS
    # =========================================================

    elif event_type == "app.menu.precio.creado":
        print(f"💰 Precio creado: {data}")

    elif event_type == "app.menu.precio.actualizado":
        print(f"💸 Precio actualizado: {data}")

    elif event_type == "app.menu.precio.desactivado":
        print(f"⛔ Precio desactivado: {data}")

    # =========================================================
    # 🗂️ CATEGORÍAS
    # =========================================================

    elif event_type == "app.menu.categoria.creada":
        print(f"📂 Categoría creada: {data}")

    elif event_type == "app.menu.categoria.actualizada":
        print(f"✏️ Categoría actualizada: {data}")

    elif event_type == "app.menu.categoria.desactivada":
        print(f"⛔ Categoría desactivada: {data}")

    # =========================================================
    # 🧪 INGREDIENTES
    # =========================================================

    elif event_type == "app.menu.ingrediente.creado":
        print(f"🧪 Ingrediente creado: {data}")

    elif event_type == "app.menu.ingrediente.actualizado":
        print(f"✏️ Ingrediente actualizado: {data}")

    elif event_type == "app.menu.ingrediente.desactivado":
        print(f"⛔ Ingrediente desactivado: {data}")

    # =========================================================
    # 🍳 RELACIONES
    # =========================================================

    elif event_type == "app.menu.plato_ingrediente.agregado":
        print(f"➕ Ingrediente agregado a plato: {data}")

    elif event_type == "app.menu.plato_ingrediente.eliminado":
        print(f"➖ Ingrediente eliminado de plato: {data}")

    elif event_type == "app.menu.plato_ingrediente.actualizado":
        print(f"🔄 Ingrediente actualizado en plato: {data}")

    else:
        print(f"⚠️ Evento no manejado: {event_type}")

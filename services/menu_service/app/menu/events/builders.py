# menu_service/app/menu/events/builders.py
class MenuEventBuilder:
    """
    Construye los payloads (data) de los eventos de menu_service.
    """

    # =========================================================
    # 🍽️ PLATOS
    # =========================================================

    @staticmethod
    def plato_creado(plato):
        return {
            "plato_id": str(plato.id),
            "nombre": plato.nombre,
            "descripcion": plato.descripcion,
            "categoria_id": str(plato.categoria_id) if plato.categoria_id else None,
            "activo": plato.activo
        }

    @staticmethod
    def plato_actualizado(plato, cambios: dict):
        return {
            "plato_id": str(plato.id),
            "cambios": cambios
        }

    @staticmethod
    def plato_estado(plato):
        return {
            "plato_id": str(plato.id)
        }

    @staticmethod
    def plato_eliminado(plato_id):
        return {
            "plato_id": str(plato_id)
        }

    # =========================================================
    # 💰 PRECIOS
    # =========================================================

    @staticmethod
    def precio_creado(precio):
        return {
            "precio_id": str(precio.id),
            "plato_id": str(precio.plato_id),
            "restaurante_id": str(precio.restaurante_id),
            "precio": float(precio.precio),
            "moneda": precio.restaurante.moneda,
            "activo": precio.activo
        }

    @staticmethod
    def precio_actualizado(precio, precio_anterior):
        return {
            "precio_id": str(precio.id),
            "plato_id": str(precio.plato_id),
            "restaurante_id": str(precio.restaurante_id),
            "precio_anterior": float(precio_anterior),
            "precio_nuevo": float(precio.precio)
        }

    @staticmethod
    def precio_estado(precio):
        return {
            "precio_id": str(precio.id),
            "plato_id": str(precio.plato_id),
            "restaurante_id": str(precio.restaurante_id)
        }

    # =========================================================
    # 🏪 RESTAURANTES
    # =========================================================

    @staticmethod
    def restaurante_creado(restaurante):
        return {
            "restaurante_id": str(restaurante.id),
            "nombre": restaurante.nombre,
            "pais": restaurante.pais,
            "ciudad": restaurante.ciudad,
            "moneda": restaurante.moneda
        }

    @staticmethod
    def restaurante_actualizado(restaurante, cambios: dict):
        return {
            "restaurante_id": str(restaurante.id),
            "cambios": cambios
        }

    @staticmethod
    def restaurante_desactivado(restaurante):
        return {
            "restaurante_id": str(restaurante.id)
        }

    # =========================================================
    # 🗂️ CATEGORÍAS
    # =========================================================

    @staticmethod
    def categoria_creada(categoria):
        return {
            "categoria_id": str(categoria.id),
            "nombre": categoria.nombre,
            "activo": categoria.activo
        }

    @staticmethod
    def categoria_actualizada(categoria, cambios: dict):
        return {
            "categoria_id": str(categoria.id),
            "cambios": cambios
        }

    @staticmethod
    def categoria_desactivada(categoria):
        return {
            "categoria_id": str(categoria.id)
        }

    # =========================================================
    # 🧪 INGREDIENTES
    # =========================================================

    @staticmethod
    def ingrediente_creado(ingrediente):
        return {
            "ingrediente_id": str(ingrediente.id),
            "nombre": ingrediente.nombre,
            "unidad_medida": ingrediente.unidad_medida
        }

    @staticmethod
    def ingrediente_actualizado(ingrediente, cambios: dict):
        return {
            "ingrediente_id": str(ingrediente.id),
            "cambios": cambios
        }

    @staticmethod
    def ingrediente_desactivado(ingrediente):
        return {
            "ingrediente_id": str(ingrediente.id)
        }

    # =========================================================
    # 🍳 PLATO - INGREDIENTE
    # =========================================================

    @staticmethod
    def plato_ingrediente_agregado(plato_id, ingrediente_id, cantidad, unidad_medida, nombre_ingrediente=""):
        """
        Agrega nombre_ingrediente al payload para que inventory_service
        pueda poblar RecetaPlato.nombre_ingrediente sin necesitar un
        caché local previo del ingrediente.
        """
        return {
            "plato_id":           str(plato_id),
            "ingrediente_id":     str(ingrediente_id),
            "cantidad":           float(cantidad),
            "unidad_medida":      unidad_medida,
            "nombre_ingrediente": nombre_ingrediente,
        }

    @staticmethod
    def plato_ingrediente_eliminado(plato_id, ingrediente_id):
        return {
            "plato_id": str(plato_id),
            "ingrediente_id": str(ingrediente_id)
        }

    @staticmethod
    def plato_ingrediente_actualizado(
        plato_id,
        ingrediente_id,
        cantidad_anterior,
        cantidad_nueva
    ):
        return {
            "plato_id": str(plato_id),
            "ingrediente_id": str(ingrediente_id),
            "cantidad_anterior": float(cantidad_anterior),
            "cantidad_nueva": float(cantidad_nueva)
        }

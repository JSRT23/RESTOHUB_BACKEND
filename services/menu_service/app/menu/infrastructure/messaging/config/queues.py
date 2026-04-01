# menu_service/app/menu/infrastructure/messaging/config/queues.py

"""
Cada servicio define sus propias colas.
Este archivo sirve como referencia estándar.
"""


class Queues:

    # Ejemplo para menu_service (si consume algo)
    MENU_QUEUE = "menu_service_queue"

    # Ejemplo global (otros servicios)
    LOYALTY_QUEUE = "loyalty_service_queue"
    INVENTORY_QUEUE = "inventory_service_queue"

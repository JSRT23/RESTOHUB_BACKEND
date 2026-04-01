# inventory_service/app/inventory/infrastructure/messaging/topology.py

MAX_RETRIES = 3

QUEUES = {
    "inventory": {
        "name":     "inventory_queue",
        "dlq":      "inventory_queue.dlq",
        "bindings": [
            "app.menu.restaurante.creado",
            "app.menu.ingrediente.creado",
            "app.menu.ingrediente.actualizado",
            "app.menu.ingrediente.desactivado",
            "app.menu.plato_ingrediente.agregado",
            "app.menu.plato_ingrediente.eliminado",
            "app.menu.plato_ingrediente.actualizado",
            "app.order.pedido.confirmado",
            "app.order.pedido.cancelado",
        ],
    },
}


def get_exchange() -> str:
    from django.conf import settings
    return settings.RABBITMQ["EXCHANGE"]


def get_dlx() -> str:
    return f"{get_exchange()}.dlx"


def get_queue(service: str) -> str:
    return QUEUES[service]["name"]


def get_dlq(service: str) -> str:
    return QUEUES[service]["dlq"]


def get_bindings(service: str) -> list[str]:
    return QUEUES[service]["bindings"]

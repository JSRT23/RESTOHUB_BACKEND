# loyalty_service/app/loyalty/infrastructure/messaging/topology.py

MAX_RETRIES = 3

QUEUES = {
    "loyalty": {
        "name":     "loyalty_queue",
        "dlq":      "loyalty_queue.dlq",
        "bindings": [
            # 🧾 order_service — core de loyalty
            "app.order.pedido.entregado",
            "app.order.pedido.cancelado",

            # 🍽️ menu_service — sync catálogo local
            "app.menu.plato.creado",
            "app.menu.plato.actualizado",
            "app.menu.plato.desactivado",
            "app.menu.categoria.creada",
            "app.menu.categoria.actualizada",
            "app.menu.categoria.desactivada",
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

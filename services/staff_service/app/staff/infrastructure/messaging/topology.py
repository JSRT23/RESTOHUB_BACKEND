# staff_service/app/staff/infrastructure/messaging/topology.py

MAX_RETRIES = 3

QUEUES = {
    "staff": {
        "name":     "staff_queue",
        "dlq":      "staff_queue.dlq",
        "bindings": [
            "app.menu.restaurante.creado",
            "app.menu.restaurante.actualizado",
            "app.menu.restaurante.desactivado",
            "app.inventory.alerta.stock_bajo",
            "app.inventory.alerta.agotado",
            "app.inventory.alerta.vencimiento_proximo",
            "app.inventory.lote.vencido",
            "app.inventory.orden_compra.creada",
            "app.order.pedido.confirmado",
            "app.order.entrega.asignada",
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

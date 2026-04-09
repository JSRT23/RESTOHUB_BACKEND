# order_service/app/orders/infrastructure/messaging/topology.py

MAX_RETRIES = 3

QUEUES = {
    "order": {
        "name": "order_queue",
        "dlq":  "order_queue.dlq",
        "bindings": [
            # ── staff_service — mueve el estado del pedido ────────────────
            "app.staff.cocina.asignacion.creada",
            "app.staff.cocina.asignacion.completada",
            "app.staff.entrega.asignada",
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

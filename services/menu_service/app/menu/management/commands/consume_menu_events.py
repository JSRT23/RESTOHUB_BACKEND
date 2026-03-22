"""
consume_menu_events.py — menu_service

menu_service NO consume eventos de otros servicios.
Este comando cumple dos propósitos:

1. DECLARAR QUEUES: crea en RabbitMQ todas las queues y bindings que los
   servicios consumidores (inventory, order, loyalty, staff) van a usar.
   Esto garantiza que los mensajes no se pierdan aunque esos consumers
   no estén corriendo todavía cuando menu_service empieza a publicar.

2. VERIFICAR PUBLICACIÓN: en modo debug escucha la queue de auditoría
   "menu.audit" que recibe una copia de TODOS los eventos de menu_service.
   Permite comprobar en desarrollo que los signals publican correctamente
   sin necesidad de levantar el resto de servicios.

Ejecutar:
    # Solo declarar queues y salir
    python manage.py consume_menu_events --solo-declarar

    # Declarar queues y escuchar en modo auditoría (desarrollo)
    python manage.py consume_menu_events
"""

import json
import logging

import pika
import pika.exceptions
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "restohub"

# ---------------------------------------------------------------------------
# Mapa completo de queues que deben existir para consumir eventos de menu.
# Cada entrada = (nombre_queue, [routing_keys]).
# Estas queues son propiedad de los servicios consumidores —
# se declaran aquí para que existan desde el arranque de menu_service.
# ---------------------------------------------------------------------------

QUEUES_CONSUMIDORES = {

    # inventory_service consume: platos, ingredientes, plato_ingrediente,
    # precios (para costo) y restaurantes (para inicializar stock)
    "inventory.menu": [
        "app.menu.plato.created",
        "app.menu.plato.updated",
        "app.menu.plato.activated",
        "app.menu.plato.deactivated",
        "app.menu.plato.deleted",
        "app.menu.ingrediente.created",
        "app.menu.ingrediente.updated",
        "app.menu.ingrediente.deactivated",
        "app.menu.plato_ingrediente.added",
        "app.menu.plato_ingrediente.removed",
        "app.menu.plato_ingrediente.cantidad_updated",
        "app.menu.restaurante.created",
        "app.menu.restaurante.updated",
        "app.menu.restaurante.deactivated",
    ],

    # order_service consume: precios (para calcular totales) y
    # platos (para saber si están activos al crear pedido)
    "order.menu": [
        "app.menu.precio.created",
        "app.menu.precio.updated",
        "app.menu.precio.activated",
        "app.menu.precio.deactivated",
        "app.menu.plato.activated",
        "app.menu.plato.deactivated",
        "app.menu.restaurante.deactivated",
    ],

    # loyalty_service consume: platos, precios, categorías y restaurantes
    # para evaluar promociones y filtrar por categoría
    "loyalty.menu": [
        "app.menu.plato.created",
        "app.menu.plato.updated",
        "app.menu.plato.activated",
        "app.menu.plato.deactivated",
        "app.menu.precio.created",
        "app.menu.precio.updated",
        "app.menu.precio.activated",
        "app.menu.precio.deactivated",
        "app.menu.categoria.created",
        "app.menu.categoria.updated",
        "app.menu.categoria.deactivated",
        "app.menu.restaurante.created",
        "app.menu.restaurante.updated",
        "app.menu.restaurante.deactivated",
    ],

    # staff_service consume: restaurantes (para inicializar config laboral)
    "staff.menu": [
        "app.menu.restaurante.created",
        "app.menu.restaurante.updated",
        "app.menu.restaurante.deactivated",
    ],

    # Queue de auditoría — solo para desarrollo/verificación.
    # Recibe TODOS los eventos de menu_service con wildcard.
    # No tiene consumidor en producción.
    "menu.audit": [
        "app.menu.#",
    ],
}


class Command(BaseCommand):
    help = (
        "Declara queues de consumidores de menu_service en RabbitMQ "
        "y opcionalmente escucha en modo auditoría para verificar publicación."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--solo-declarar",
            action="store_true",
            default=False,
            help="Solo declara queues y bindings, luego termina. No escucha mensajes.",
        )

    def handle(self, *args, **options):
        from django.conf import settings
        cfg = settings.RABBITMQ

        self.stdout.write("[menu_consumer] Conectando a RabbitMQ...")

        credentials = pika.PlainCredentials(cfg["USER"], cfg["PASSWORD"])
        params = pika.ConnectionParameters(
            host=cfg["HOST"],
            port=cfg["PORT"],
            virtual_host=cfg["VHOST"],
            credentials=credentials,
            heartbeat=120,
            blocked_connection_timeout=30,
        )

        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        # Declarar exchange
        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type="topic",
            durable=True,
        )

        # Declarar todas las queues y sus bindings
        total_bindings = 0
        for queue_name, routing_keys in QUEUES_CONSUMIDORES.items():
            channel.queue_declare(queue=queue_name, durable=True)
            for routing_key in routing_keys:
                channel.queue_bind(
                    exchange=EXCHANGE_NAME,
                    queue=queue_name,
                    routing_key=routing_key,
                )
                total_bindings += 1

            self.stdout.write(
                f"  [OK] Queue '{queue_name}' — {len(routing_keys)} binding(s)"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n[menu_consumer] {len(QUEUES_CONSUMIDORES)} queues declaradas, "
                f"{total_bindings} bindings registrados."
            )
        )

        # Modo --solo-declarar: terminar aquí
        if options["solo_declarar"]:
            connection.close()
            self.stdout.write(
                "[menu_consumer] Modo --solo-declarar. Finalizado.")
            return

        # Modo auditoría: escuchar menu.audit y loguear cada mensaje
        self.stdout.write(
            "\n[menu_consumer] Escuchando 'menu.audit' — "
            "Ctrl+C para detener.\n"
        )

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue="menu.audit",
            on_message_callback=self._audit_callback,
        )

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
        finally:
            connection.close()
            self.stdout.write("\n[menu_consumer] Conexión cerrada.")

    # -----------------------------------------------------------------------
    # Callback de auditoría
    # -----------------------------------------------------------------------

    def _audit_callback(self, channel, method, properties, body):
        try:
            message = json.loads(body)
            event_type = message.get("event_type", "desconocido")
            event_id = message.get("event_id", "—")
            data = message.get("data", {})

            self.stdout.write(
                f"\n{'─' * 60}\n"
                f"  evento  : {event_type}\n"
                f"  event_id: {event_id}\n"
                f"  data    : {json.dumps(data, indent=4, default=str, ensure_ascii=False)}\n"
            )

        except json.JSONDecodeError as exc:
            self.stderr.write(f"[menu_consumer] JSON inválido: {exc}")

        finally:
            # Siempre ackear en la queue de auditoría
            channel.basic_ack(delivery_tag=method.delivery_tag)

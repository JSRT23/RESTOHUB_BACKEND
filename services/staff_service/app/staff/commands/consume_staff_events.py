"""
Consumer de eventos RabbitMQ para staff_service.

Ejecutar con:
    python manage.py consume_staff_events

Queues declaradas y sus bindings:
    staff.menu      ← app.menu.restaurante.*
    staff.order     ← app.order.pedido.confirmado
                    ← app.order.comanda.creada
                    ← app.order.comanda.lista
                    ← app.order.entrega.asignada
                    ← app.order.entrega.completada
                    ← app.order.pedido.entregado
    staff.inventory ← app.inventory.alerta.stock_bajo
                    ← app.inventory.alerta.agotado
                    ← app.inventory.alerta.vencimiento_proximo
                    ← app.inventory.orden_compra.creada
"""

import json
import logging

import pika
import pika.exceptions
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "restohub"

# ---------------------------------------------------------------------------
# Definición de queues y sus routing keys
# ---------------------------------------------------------------------------

QUEUES = {
    "staff.menu": [
        "app.menu.restaurante.created",
        "app.menu.restaurante.updated",
        "app.menu.restaurante.deactivated",
    ],
    "staff.order": [
        "app.order.pedido.confirmado",
        "app.order.comanda.creada",
        "app.order.comanda.lista",
        "app.order.entrega.asignada",
        "app.order.entrega.completada",
        "app.order.pedido.entregado",
    ],
    "staff.inventory": [
        "app.inventory.alerta.stock_bajo",
        "app.inventory.alerta.agotado",
        "app.inventory.alerta.vencimiento_proximo",
        "app.inventory.orden_compra.creada",
    ],
}


class Command(BaseCommand):
    help = "Consume eventos RabbitMQ relevantes para staff_service"

    def handle(self, *args, **options):
        from django.conf import settings
        cfg = settings.RABBITMQ

        self.stdout.write("[staff_consumer] Iniciando...")

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

        # Declarar queues y bindings
        for queue_name, routing_keys in QUEUES.items():
            channel.queue_declare(queue=queue_name, durable=True)
            for routing_key in routing_keys:
                channel.queue_bind(
                    exchange=EXCHANGE_NAME,
                    queue=queue_name,
                    routing_key=routing_key,
                )
            self.stdout.write(
                f"[staff_consumer] Queue '{queue_name}' lista "
                f"({len(routing_keys)} bindings)"
            )

        # Un mensaje a la vez por consumer
        channel.basic_qos(prefetch_count=1)

        # Registrar el mismo callback para todas las queues
        for queue_name in QUEUES:
            channel.basic_consume(
                queue=queue_name,
                on_message_callback=self._callback,
            )

        self.stdout.write(
            "[staff_consumer] Esperando mensajes. Ctrl+C para detener.")
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
        finally:
            connection.close()
            self.stdout.write("[staff_consumer] Conexión cerrada.")

    # ---------------------------------------------------------------------------
    # Callback principal
    # ---------------------------------------------------------------------------

    def _callback(self, channel, method, properties, body):
        try:
            message = json.loads(body)
            event_type = message.get("event_type", "")
            data = message.get("data", {})

            logger.debug("[staff_consumer] Recibido: %s", event_type)
            self._procesar(event_type, data)

            # ACK solo si _procesar no lanzó excepción
            channel.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as exc:
            logger.error("[staff_consumer] JSON inválido: %s", exc)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as exc:
            logger.error("[staff_consumer] Error procesando mensaje: %s", exc)
            # requeue=True para reintentar ante errores transitorios (DB, etc.)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    # ---------------------------------------------------------------------------
    # Router de eventos
    # ---------------------------------------------------------------------------

    def _procesar(self, event_type: str, data: dict) -> None:
        handlers = {
            # ── Menu ──────────────────────────────────────────────────────────
            "app.menu.restaurante.created":     self._on_restaurante_created,
            "app.menu.restaurante.updated":     self._on_restaurante_updated,
            "app.menu.restaurante.deactivated": self._on_restaurante_deactivated,

            # ── Order ─────────────────────────────────────────────────────────
            "app.order.pedido.confirmado":      self._on_pedido_confirmado,
            "app.order.comanda.creada":         self._on_comanda_creada,
            "app.order.comanda.lista":          self._on_comanda_lista,
            "app.order.entrega.asignada":       self._on_entrega_asignada,
            "app.order.entrega.completada":     self._on_entrega_completada,
            "app.order.pedido.entregado":       self._on_pedido_entregado,

            # ── Inventory ─────────────────────────────────────────────────────
            "app.inventory.alerta.stock_bajo":           self._on_alerta_stock_bajo,
            "app.inventory.alerta.agotado":              self._on_alerta_agotado,
            "app.inventory.alerta.vencimiento_proximo":  self._on_alerta_vencimiento,
            "app.inventory.orden_compra.creada":         self._on_orden_compra_creada,
        }

        handler = handlers.get(event_type)
        if handler:
            handler(data)
        else:
            logger.warning(
                "[staff_consumer] Evento sin handler: %s", event_type)

    # ---------------------------------------------------------------------------
    # Handlers — menu_service
    # ---------------------------------------------------------------------------

    @transaction.atomic
    def _on_restaurante_created(self, data: dict) -> None:
        """
        Crea la copia local del restaurante y dispara la inicialización
        de la configuración laboral para el país correspondiente.
        """
        from app.staff.models import RestauranteLocal, ConfiguracionLaboralPais

        restaurante_id = data.get("id")
        pais = data.get("pais", "")

        if not restaurante_id:
            logger.warning("[staff_consumer] restaurante.created sin 'id'")
            return

        restaurante, created = RestauranteLocal.objects.update_or_create(
            restaurante_id=restaurante_id,
            defaults={
                "nombre": data.get("nombre", ""),
                "pais":   pais,
                "ciudad": data.get("ciudad", ""),
                "activo": True,
            },
        )

        # Asegurar que exista configuración laboral para este país
        if pais and not ConfiguracionLaboralPais.objects.filter(pais=pais).exists():
            ConfiguracionLaboralPais.objects.create(pais=pais)
            logger.info(
                "[staff_consumer] ConfiguracionLaboralPais creada para país '%s'", pais
            )

        action = "creado" if created else "actualizado (ya existía)"
        logger.info("[staff_consumer] RestauranteLocal %s — %s",
                    restaurante_id, action)

    @transaction.atomic
    def _on_restaurante_updated(self, data: dict) -> None:
        """Actualiza nombre y ciudad del restaurante local."""
        from app.staff.models import RestauranteLocal

        restaurante_id = data.get("id")
        if not restaurante_id:
            return

        updated = RestauranteLocal.objects.filter(
            restaurante_id=restaurante_id
        ).update(
            nombre=data.get("nombre", ""),
            ciudad=data.get("ciudad", ""),
        )

        if updated:
            logger.info(
                "[staff_consumer] RestauranteLocal actualizado: %s", restaurante_id)
        else:
            logger.warning(
                "[staff_consumer] restaurante.updated — no encontrado: %s", restaurante_id
            )

    @transaction.atomic
    def _on_restaurante_deactivated(self, data: dict) -> None:
        """
        Desactiva el restaurante local y cancela todos los turnos
        programados o activos del local.
        """
        from app.staff.models import RestauranteLocal, Turno, EstadoTurno

        restaurante_id = data.get("id")
        if not restaurante_id:
            return

        RestauranteLocal.objects.filter(
            restaurante_id=restaurante_id).update(activo=False)

        # Cancelar turnos activos/programados
        cancelados = Turno.objects.filter(
            restaurante_id=restaurante_id,
            estado__in=[EstadoTurno.PROGRAMADO, EstadoTurno.ACTIVO],
        ).update(estado=EstadoTurno.CANCELADO)

        logger.info(
            "[staff_consumer] Restaurante %s desactivado — %d turnos cancelados",
            restaurante_id, cancelados,
        )

    # ---------------------------------------------------------------------------
    # Handlers — order_service
    # ---------------------------------------------------------------------------

    @transaction.atomic
    def _on_pedido_confirmado(self, data: dict) -> None:
        """
        Un pedido confirmado puede implicar múltiples comandas.
        Aquí solo logueamos — la asignación real ocurre en comanda.creada
        cuando ya sabemos la estación específica.
        """
        pedido_id = data.get("pedido_id") or data.get("id")
        restaurante_id = data.get("restaurante_id")
        logger.info(
            "[staff_consumer] Pedido confirmado %s en restaurante %s — esperando comandas",
            pedido_id, restaurante_id,
        )

    @transaction.atomic
    def _on_comanda_creada(self, data: dict) -> None:
        """
        Asigna el cocinero disponible con menos carga en la estación
        correspondiente y crea la AsignacionCocina.
        """
        from app.staff.models import (
            AsignacionCocina, Empleado, EstacionCocina,
            RolEmpleado, EstadoTurno,
        )
        from django.utils import timezone

        comanda_id = data.get("comanda_id") or data.get("id")
        pedido_id = data.get("pedido_id")
        restaurante_id = data.get("restaurante_id")
        estacion_nombre = data.get("estacion", "")

        if not all([comanda_id, pedido_id, restaurante_id]):
            logger.warning(
                "[staff_consumer] comanda.creada — datos incompletos: %s", data)
            return

        # Buscar estación por nombre en el restaurante
        estacion = EstacionCocina.objects.filter(
            restaurante_id=restaurante_id,
            nombre__iexact=estacion_nombre,
            activa=True,
        ).first()

        if not estacion:
            # Si no existe la estación, crear una genérica para no perder el evento
            estacion, _ = EstacionCocina.objects.get_or_create(
                restaurante_id=restaurante_id,
                nombre=estacion_nombre or "General",
                defaults={"capacidad_simultanea": 3, "activa": True},
            )

        # Cocinero disponible: turno activo en el restaurante, menos asignaciones abiertas
        cocinero = (
            Empleado.objects
            .filter(
                restaurante__restaurante_id=restaurante_id,
                rol__in=[RolEmpleado.COCINERO, RolEmpleado.AUXILIAR],
                activo=True,
                turnos__estado=EstadoTurno.ACTIVO,
            )
            .annotate_open_assignments()   # ← ver nota abajo
            .order_by("open_assignments")
            .first()
        )

        if not cocinero:
            logger.warning(
                "[staff_consumer] Sin cocineros disponibles para comanda %s", comanda_id
            )
            return

        AsignacionCocina.objects.create(
            pedido_id=pedido_id,
            comanda_id=comanda_id,
            cocinero=cocinero,
            estacion=estacion,
        )

        logger.info(
            "[staff_consumer] Comanda %s asignada a cocinero %s en estación '%s'",
            comanda_id, cocinero, estacion.nombre,
        )

    @transaction.atomic
    def _on_comanda_lista(self, data: dict) -> None:
        """
        Marca la asignación como completada y calcula el SLA real.
        """
        from app.staff.models import AsignacionCocina
        from django.utils import timezone

        comanda_id = data.get("comanda_id") or data.get("id")
        if not comanda_id:
            return

        try:
            asignacion = AsignacionCocina.objects.get(comanda_id=comanda_id)
        except AsignacionCocina.DoesNotExist:
            logger.warning(
                "[staff_consumer] comanda.lista — AsignacionCocina no encontrada: %s",
                comanda_id,
            )
            return

        asignacion.completado_en = timezone.now()
        asignacion.sla_segundos = asignacion.calcular_sla()
        asignacion.save(update_fields=["completado_en", "sla_segundos"])

        logger.info(
            "[staff_consumer] Comanda %s completada — SLA: %ds",
            comanda_id, asignacion.sla_segundos,
        )

    @transaction.atomic
    def _on_entrega_asignada(self, data: dict) -> None:
        """
        Registra al repartidor en ServicioEntrega (estado: asignada).
        """
        from app.staff.models import ServicioEntrega, Empleado, RolEmpleado

        pedido_id = data.get("pedido_id")
        repartidor_id = data.get("repartidor_id")

        if not all([pedido_id, repartidor_id]):
            logger.warning(
                "[staff_consumer] entrega.asignada — datos incompletos: %s", data)
            return

        try:
            repartidor = Empleado.objects.get(
                id=repartidor_id, rol=RolEmpleado.REPARTIDOR)
        except Empleado.DoesNotExist:
            logger.warning(
                "[staff_consumer] Repartidor no encontrado en staff: %s", repartidor_id
            )
            return

        servicio, created = ServicioEntrega.objects.get_or_create(
            pedido_id=pedido_id,
            defaults={"repartidor": repartidor, "estado": "asignada"},
        )

        if not created:
            logger.warning(
                "[staff_consumer] ServicioEntrega ya existía para pedido %s", pedido_id
            )
            return

        logger.info(
            "[staff_consumer] Repartidor %s asignado al pedido %s",
            repartidor, pedido_id,
        )

    @transaction.atomic
    def _on_entrega_completada(self, data: dict) -> None:
        """
        Marca el servicio como completado y libera al repartidor.
        """
        from app.staff.models import ServicioEntrega
        from django.utils import timezone

        pedido_id = data.get("pedido_id")
        if not pedido_id:
            return

        updated = ServicioEntrega.objects.filter(pedido_id=pedido_id).update(
            estado="completada",
            completado_en=timezone.now(),
        )

        if updated:
            logger.info(
                "[staff_consumer] Entrega completada — repartidor liberado, pedido %s",
                pedido_id,
            )
        else:
            logger.warning(
                "[staff_consumer] entrega.completada — ServicioEntrega no encontrado: %s",
                pedido_id,
            )

    @transaction.atomic
    def _on_pedido_entregado(self, data: dict) -> None:
        """
        Cierre operacional del pedido en staff.
        En esta fase solo logueamos — en el futuro puede cerrar
        métricas de turno o actualizar KPIs del restaurante.
        """
        pedido_id = data.get("pedido_id") or data.get("id")
        logger.info(
            "[staff_consumer] Pedido entregado (cierre operacional): %s", pedido_id)

    # ---------------------------------------------------------------------------
    # Handlers — inventory_service
    # ---------------------------------------------------------------------------

    @transaction.atomic
    def _on_alerta_stock_bajo(self, data: dict) -> None:
        """
        Registra la alerta y genera una orden de compra urgente notificando
        al gerente del local.
        """
        from app.staff.models import AlertaOperacional, TipoAlerta, NivelAlerta

        restaurante_id = data.get("restaurante_id")
        ingrediente_id = data.get("ingrediente_id")
        nombre = data.get("nombre_ingrediente", "desconocido")

        alerta = AlertaOperacional.objects.create(
            restaurante_id=restaurante_id,
            tipo=TipoAlerta.STOCK_BAJO,
            nivel=NivelAlerta.URGENTE,
            mensaje=f"Stock bajo de '{nombre}'. Revisar y generar orden de compra.",
            referencia_id=ingrediente_id,
        )

        logger.warning(
            "[staff_consumer] Alerta stock bajo — restaurante %s, ingrediente '%s' [alerta %s]",
            restaurante_id, nombre, alerta.id,
        )

    @transaction.atomic
    def _on_alerta_agotado(self, data: dict) -> None:
        """
        Registra alerta crítica de ingrediente agotado.
        Nivel CRITICA para que el gerente del local reciba notificación inmediata.
        """
        from app.staff.models import AlertaOperacional, TipoAlerta, NivelAlerta

        restaurante_id = data.get("restaurante_id")
        ingrediente_id = data.get("ingrediente_id")
        nombre = data.get("nombre_ingrediente", "desconocido")

        alerta = AlertaOperacional.objects.create(
            restaurante_id=restaurante_id,
            tipo=TipoAlerta.AGOTADO,
            nivel=NivelAlerta.CRITICA,
            mensaje=f"INGREDIENTE AGOTADO: '{nombre}'. Acción inmediata requerida.",
            referencia_id=ingrediente_id,
        )

        logger.critical(
            "[staff_consumer] AGOTADO — restaurante %s, ingrediente '%s' [alerta %s]",
            restaurante_id, nombre, alerta.id,
        )

    @transaction.atomic
    def _on_alerta_vencimiento(self, data: dict) -> None:
        """
        Registra alerta de vencimiento próximo para coordinar
        el retiro físico del lote.
        """
        from app.staff.models import AlertaOperacional, TipoAlerta, NivelAlerta

        restaurante_id = data.get("restaurante_id")
        lote_id = data.get("lote_id")
        nombre = data.get("nombre_ingrediente", "desconocido")
        fecha_vence = data.get("fecha_vencimiento", "")

        alerta = AlertaOperacional.objects.create(
            restaurante_id=restaurante_id,
            tipo=TipoAlerta.VENCIMIENTO,
            nivel=NivelAlerta.URGENTE,
            mensaje=(
                f"Lote de '{nombre}' vence el {fecha_vence}. "
                f"Coordinar retiro físico del almacén."
            ),
            referencia_id=lote_id,
        )

        logger.warning(
            "[staff_consumer] Vencimiento próximo — '%s' vence %s [alerta %s]",
            nombre, fecha_vence, alerta.id,
        )

    @transaction.atomic
    def _on_orden_compra_creada(self, data: dict) -> None:
        """
        Registra la alerta para que el gerente gestione la aprobación
        y notifique al proveedor.
        """
        from app.staff.models import AlertaOperacional, TipoAlerta, NivelAlerta

        restaurante_id = data.get("restaurante_id")
        orden_id = data.get("orden_id") or data.get("id")
        proveedor = data.get("nombre_proveedor", "desconocido")
        total = data.get("total", "")
        moneda = data.get("moneda", "")

        alerta = AlertaOperacional.objects.create(
            restaurante_id=restaurante_id,
            tipo=TipoAlerta.ORDEN_COMPRA,
            nivel=NivelAlerta.INFO,
            mensaje=(
                f"Nueva orden de compra #{orden_id} con proveedor '{proveedor}'. "
                f"Total: {total} {moneda}. Pendiente de aprobación."
            ),
            referencia_id=orden_id,
        )

        logger.info(
            "[staff_consumer] Orden de compra creada %s — proveedor '%s' [alerta %s]",
            orden_id, proveedor, alerta.id,
        )

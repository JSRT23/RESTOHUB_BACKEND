"""
consume_loyalty_events.py — loyalty_service

Ubicacion: app/loyalty/management/commands/consume_loyalty_events.py

loyalty_service CONSUME eventos de:
  - order_service → pedido.creado, entregado, cancelado, entrega.completada
  - menu_service  → platos, categorias, precios (catalogo local)

loyalty_service PUBLICA eventos hacia:
  - order_service  → promocion.aplicada
  - gateway        → puntos.acumulados, puntos.canjeados, cupon.generado

Ejecutar:
    python manage.py consume_loyalty_events --solo-declarar
    python manage.py consume_loyalty_events
"""

import json
import logging
from decimal import Decimal

import pika
import pika.exceptions
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "restohub"

# ---------------------------------------------------------------------------
# Puntos base por compra — configurable en el futuro por restaurante/marca
# ---------------------------------------------------------------------------
PUNTOS_POR_PESO = Decimal("0.01")   # 1 punto por cada 100 unidades de moneda

# ---------------------------------------------------------------------------
# Queues que loyalty_service CONSUME
# ---------------------------------------------------------------------------

QUEUES_PROPIAS = {

    "loyalty.order": [
        "app.order.pedido.creado",
        "app.order.pedido.entregado",
        "app.order.pedido.cancelado",
        "app.order.entrega.completada",
    ],

    "loyalty.menu": [
        "app.menu.plato.created",
        "app.menu.plato.updated",
        "app.menu.plato.deactivated",
        "app.menu.categoria.created",
        "app.menu.categoria.updated",
        "app.menu.categoria.deactivated",
        "app.menu.precio.created",
        "app.menu.precio.updated",
    ],

    "loyalty.audit": [
        "app.loyalty.#",
    ],
}

# ---------------------------------------------------------------------------
# Queues de consumidores de loyalty_service
# Se declaran aquí para que existan aunque esos servicios no estén corriendo
# ---------------------------------------------------------------------------

QUEUES_CONSUMIDORES = {

    # order_service consume promocion.aplicada
    "order.loyalty": [
        "app.loyalty.promocion.aplicada",
    ],

    # gateway consume puntos y cupones
    "gateway.loyalty": [
        "app.loyalty.puntos.acumulados",
        "app.loyalty.puntos.canjeados",
        "app.loyalty.cupon.generado",
        "app.loyalty.cupon.canjeado",
    ],
}


class Command(BaseCommand):
    help = (
        "Declara queues de loyalty_service y consume eventos de "
        "order_service y menu_service."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--solo-declarar",
            action="store_true",
            default=False,
            help="Solo declara queues y bindings, luego termina.",
        )

    def handle(self, *args, **options):
        from django.conf import settings
        cfg = settings.RABBITMQ

        self.stdout.write("[loyalty_consumer] Conectando a RabbitMQ...")

        credentials = pika.PlainCredentials(cfg["USER"], cfg["PASSWORD"])
        params = pika.ConnectionParameters(
            host=cfg["HOST"],
            port=cfg["PORT"],
            virtual_host=cfg["VHOST"],
            credentials=credentials,
            heartbeat=120,
            blocked_connection_timeout=30,
        )

        # Retry loop — RabbitMQ puede tardar unos segundos en estar
        # completamente listo después de pasar el healthcheck
        import time
        max_retries = 10
        for intento in range(1, max_retries + 1):
            try:
                connection = pika.BlockingConnection(params)
                self.stdout.write(
                    f"[loyalty_consumer] Conectado (intento {intento})")
                break
            except Exception as exc:
                if intento == max_retries:
                    self.stderr.write(
                        f"[loyalty_consumer] No se pudo conectar tras {max_retries} intentos: {exc}")
                    raise
                self.stdout.write(
                    f"[loyalty_consumer] RabbitMQ no disponible, reintentando en 5s ({intento}/{max_retries})...")
                time.sleep(5)

        channel = connection.channel()

        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type="topic",
            durable=True,
        )

        # — Queues propias —
        self.stdout.write("\n  -- Queues propias (loyalty_service consume):")
        for queue_name, routing_keys in QUEUES_PROPIAS.items():
            channel.queue_declare(queue=queue_name, durable=True)
            for rk in routing_keys:
                channel.queue_bind(
                    exchange=EXCHANGE_NAME,
                    queue=queue_name,
                    routing_key=rk,
                )
            self.stdout.write(
                f"    [OK] '{queue_name}' -- {len(routing_keys)} binding(s)"
            )

        # — Queues consumidores —
        self.stdout.write("\n  -- Queues de consumidores (otros servicios):")
        for queue_name, routing_keys in QUEUES_CONSUMIDORES.items():
            channel.queue_declare(queue=queue_name, durable=True)
            for rk in routing_keys:
                channel.queue_bind(
                    exchange=EXCHANGE_NAME,
                    queue=queue_name,
                    routing_key=rk,
                )
            self.stdout.write(
                f"    [OK] '{queue_name}' -- {len(routing_keys)} binding(s)"
            )

        total_q = len(QUEUES_PROPIAS) + len(QUEUES_CONSUMIDORES)
        total_b = sum(
            len(v) for v in {**QUEUES_PROPIAS, **QUEUES_CONSUMIDORES}.values()
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"\n[loyalty_consumer] {total_q} queues declaradas, "
                f"{total_b} bindings registrados."
            )
        )

        if options["solo_declarar"]:
            connection.close()
            self.stdout.write(
                "[loyalty_consumer] Modo --solo-declarar. Finalizado.")
            return

        # — Modo escucha —
        self.stdout.write(
            "\n[loyalty_consumer] Escuchando eventos. Ctrl+C para detener.\n"
        )

        channel.basic_qos(prefetch_count=1)

        for queue_name in ["loyalty.order", "loyalty.menu"]:
            channel.basic_consume(
                queue=queue_name,
                on_message_callback=self._callback,
            )

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
        finally:
            connection.close()
            self.stdout.write("\n[loyalty_consumer] Conexion cerrada.")

    # -----------------------------------------------------------------------
    # Callback principal
    # -----------------------------------------------------------------------

    def _callback(self, channel, method, properties, body):
        event_type = "desconocido"
        try:
            message = json.loads(body)
            event_type = message.get("event_type", "")
            data = message.get("data", {})

            self.stdout.write(f"  [evento] {event_type}")
            self._procesar(event_type, data)

            channel.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as exc:
            logger.error("[loyalty_consumer] JSON invalido: %s", exc)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as exc:
            logger.error(
                "[loyalty_consumer] Error procesando '%s': %s", event_type, exc
            )
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    # -----------------------------------------------------------------------
    # Router
    # -----------------------------------------------------------------------

    def _procesar(self, event_type: str, data: dict) -> None:
        handlers = {
            # ── order_service ────────────────────────────────────────────
            "app.order.pedido.creado":        self._on_pedido_creado,
            "app.order.pedido.entregado":     self._on_pedido_entregado,
            "app.order.pedido.cancelado":     self._on_pedido_cancelado,
            "app.order.entrega.completada":   self._on_entrega_completada,

            # ── menu_service — catálogo local ─────────────────────────────
            "app.menu.plato.created":         self._on_plato_created,
            "app.menu.plato.updated":         self._on_plato_updated,
            "app.menu.plato.deactivated":     self._on_plato_deactivated,
            "app.menu.categoria.created":     self._on_categoria_created,
            "app.menu.categoria.updated":     self._on_categoria_updated,
            "app.menu.categoria.deactivated": self._on_categoria_deactivated,
            "app.menu.precio.created":        self._on_precio_sync,
            "app.menu.precio.updated":        self._on_precio_sync,
        }
        handler = handlers.get(event_type)
        if handler:
            handler(data)
        else:
            logger.debug(
                "[loyalty_consumer] Evento sin handler: %s", event_type)

    # -----------------------------------------------------------------------
    # Handlers — order_service
    # -----------------------------------------------------------------------

    @transaction.atomic
    def _on_pedido_creado(self, data: dict) -> None:
        """
        Pedido creado → evaluar si hay una promoción activa que aplique.
        Si aplica, crear AplicacionPromocion — el signal publica
        PROMOCION_APLICADA para que order_service aplique el descuento.
        """
        from app.loyalty.models import (
            AplicacionPromocion, Promocion, ReglaPromocion,
        )
        from django.utils import timezone

        pedido_id = data.get("pedido_id") or data.get("id")
        cliente_id = data.get("cliente_id")
        restaurante_id = data.get("restaurante_id")
        total = Decimal(str(data.get("total", "0")))
        detalles = data.get("detalles", [])

        if not pedido_id or not cliente_id:
            logger.warning(
                "[loyalty_consumer] pedido.creado sin pedido_id/cliente_id")
            return

        # Idempotencia — si ya se procesó este pedido, salir
        if AplicacionPromocion.objects.filter(pedido_id=pedido_id).exists():
            logger.info(
                "[loyalty_consumer] Pedido %s ya tiene promocion aplicada", pedido_id
            )
            return

        ahora = timezone.now()

        # Buscar promociones activas y vigentes que apliquen al restaurante
        promociones = Promocion.objects.filter(
            activa=True,
            fecha_inicio__lte=ahora,
            fecha_fin__gte=ahora,
        ).filter(
            # Alcance: global, o la marca del restaurante, o el restaurante exacto
            models_q_alcance(restaurante_id)
        ).prefetch_related("reglas")

        promo_aplicada = self._evaluar_promociones(
            promociones, total, detalles, restaurante_id, ahora
        )

        if not promo_aplicada:
            logger.info(
                "[loyalty_consumer] Sin promocion aplicable para pedido %s", pedido_id
            )
            return

        descuento, puntos_bonus = self._calcular_beneficio(
            promo_aplicada, total)

        AplicacionPromocion.objects.create(
            promocion=promo_aplicada,
            pedido_id=pedido_id,
            cliente_id=cliente_id,
            descuento_aplicado=descuento,
            puntos_bonus_otorgados=puntos_bonus,
        )

        logger.info(
            "[loyalty_consumer] Promocion '%s' aplicada al pedido %s — "
            "descuento: %s, bonus: %d pts",
            promo_aplicada.nombre, pedido_id, descuento, puntos_bonus,
        )

    @transaction.atomic
    def _on_pedido_entregado(self, data: dict) -> None:
        """
        Pedido entregado → acumular puntos al cliente.
        Crea la CuentaPuntos si es su primer pedido.
        Calcula puntos = total × PUNTOS_POR_PESO × multiplicador_nivel.
        """
        from app.loyalty.models import CuentaPuntos, TransaccionPuntos, AplicacionPromocion

        pedido_id = data.get("pedido_id") or data.get("id")
        cliente_id = data.get("cliente_id")
        restaurante_id = data.get("restaurante_id")
        total = Decimal(str(data.get("total", "0")))

        if not pedido_id or not cliente_id:
            return

        # Crear cuenta si no existe (primer pedido del cliente)
        cuenta, creada = CuentaPuntos.objects.get_or_create(
            cliente_id=cliente_id,
            defaults={"saldo": 0, "puntos_totales_historicos": 0},
        )

        if creada:
            logger.info(
                "[loyalty_consumer] Nueva CuentaPuntos creada para cliente %s",
                cliente_id,
            )

        # Verificar idempotencia — no acumular dos veces el mismo pedido
        if TransaccionPuntos.objects.filter(
            pedido_id=pedido_id,
            tipo="acumulacion",
        ).exists():
            logger.info(
                "[loyalty_consumer] Puntos ya acumulados para pedido %s", pedido_id
            )
            return

        # Calcular puntos base
        puntos_base = int(total * PUNTOS_POR_PESO)

        # Sumar puntos bonus de promoción si aplica
        puntos_bonus = 0
        aplicacion = AplicacionPromocion.objects.filter(
            pedido_id=pedido_id
        ).select_related("promocion").first()

        if aplicacion:
            puntos_bonus = aplicacion.puntos_bonus_otorgados

            # Si la promo es multiplicador de puntos
            if aplicacion.promocion.tipo_beneficio == "puntos_extra":
                multiplicador = aplicacion.promocion.multiplicador_puntos
                puntos_base = int(puntos_base * multiplicador)

        puntos_totales = puntos_base + puntos_bonus

        if puntos_totales <= 0:
            logger.info(
                "[loyalty_consumer] Sin puntos a acumular para pedido %s", pedido_id
            )
            return

        saldo_anterior = cuenta.saldo

        # Actualizar cuenta
        cuenta.saldo += puntos_totales
        cuenta.puntos_totales_historicos += puntos_totales
        cuenta.actualizar_nivel()
        cuenta.save(update_fields=[
                    "saldo", "puntos_totales_historicos", "nivel"])

        # Crear transacción (el signal la publica como PUNTOS_ACUMULADOS)
        TransaccionPuntos.objects.create(
            cuenta=cuenta,
            tipo="acumulacion",
            puntos=puntos_totales,
            saldo_anterior=saldo_anterior,
            saldo_posterior=cuenta.saldo,
            pedido_id=pedido_id,
            restaurante_id=restaurante_id,
            descripcion=f"Acumulacion por pedido {pedido_id}",
        )

        logger.info(
            "[loyalty_consumer] +%d pts para cliente %s | saldo: %d",
            puntos_totales, cliente_id, cuenta.saldo,
        )

    @transaction.atomic
    def _on_pedido_cancelado(self, data: dict) -> None:
        """
        Pedido cancelado → revertir puntos pendientes si el pedido
        tenía puntos acumulados que aún no fueron confirmados.
        Solo revierte si el pedido tiene transacción tipo ACUMULACION.
        """
        from app.loyalty.models import CuentaPuntos, TransaccionPuntos

        pedido_id = data.get("pedido_id") or data.get("id")
        if not pedido_id:
            return

        transacciones = TransaccionPuntos.objects.filter(
            pedido_id=pedido_id,
            tipo="acumulacion",
        ).select_related("cuenta")

        for tx in transacciones:
            cuenta = CuentaPuntos.objects.select_for_update().get(pk=tx.cuenta_id)
            puntos_a_revertir = tx.puntos
            saldo_anterior = cuenta.saldo

            cuenta.saldo = max(cuenta.saldo - puntos_a_revertir, 0)
            cuenta.save(update_fields=["saldo"])

            TransaccionPuntos.objects.create(
                cuenta=cuenta,
                tipo="ajuste",
                puntos=-puntos_a_revertir,
                saldo_anterior=saldo_anterior,
                saldo_posterior=cuenta.saldo,
                pedido_id=pedido_id,
                descripcion=f"Reversion por cancelacion de pedido {pedido_id}",
            )

            logger.info(
                "[loyalty_consumer] -%d pts revertidos para cliente %s por pedido cancelado %s",
                puntos_a_revertir, cuenta.cliente_id, pedido_id,
            )

    @transaction.atomic
    def _on_entrega_completada(self, data: dict) -> None:
        """
        Entrega completada → los puntos del pedido son definitivos.
        En esta fase solo logueamos — en el futuro puede activar
        beneficios por nivel (ej: subir a oro al completar cierto total).
        """
        pedido_id = data.get("pedido_id")
        cliente_id = data.get("cliente_id")
        logger.info(
            "[loyalty_consumer] Entrega completada — puntos confirmados "
            "para cliente %s, pedido %s",
            cliente_id, pedido_id,
        )

    # -----------------------------------------------------------------------
    # Handlers — menu_service (catálogo local)
    # -----------------------------------------------------------------------

    @transaction.atomic
    def _on_plato_created(self, data: dict) -> None:
        from app.loyalty.models import CatalogoPlato

        CatalogoPlato.objects.update_or_create(
            plato_id=data.get("plato_id"),
            defaults={
                "nombre":      data.get("nombre", ""),
                "categoria_id": data.get("categoria_id"),
                "activo":      data.get("activo", True),
            },
        )
        logger.info(
            "[loyalty_consumer] CatalogoPlato creado: %s", data.get("nombre")
        )

    @transaction.atomic
    def _on_plato_updated(self, data: dict) -> None:
        from app.loyalty.models import CatalogoPlato

        updated = CatalogoPlato.objects.filter(
            plato_id=data.get("plato_id")
        ).update(
            nombre=data.get("nombre", ""),
            categoria_id=data.get("categoria_id"),
        )
        logger.info(
            "[loyalty_consumer] CatalogoPlato actualizado: %d registro(s)", updated
        )

    @transaction.atomic
    def _on_plato_deactivated(self, data: dict) -> None:
        """
        Plato desactivado → suspender promociones que dependan
        de ese plato específico (ReglaPromocion tipo PLATO).
        """
        from app.loyalty.models import CatalogoPlato, Promocion

        plato_id = data.get("plato_id")
        if not plato_id:
            return

        CatalogoPlato.objects.filter(plato_id=plato_id).update(activo=False)

        # Desactivar promociones con regla de plato específico
        promos_afectadas = Promocion.objects.filter(
            activa=True,
            reglas__tipo_condicion="plato",
            reglas__plato_id=plato_id,
        ).distinct()

        count = promos_afectadas.count()
        if count:
            promos_afectadas.update(activa=False)
            logger.warning(
                "[loyalty_consumer] Plato %s desactivado — "
                "%d promocion(es) suspendidas.",
                plato_id, count,
            )

    @transaction.atomic
    def _on_categoria_created(self, data: dict) -> None:
        from app.loyalty.models import CatalogoCategoria

        CatalogoCategoria.objects.update_or_create(
            categoria_id=data.get("categoria_id"),
            defaults={
                "nombre": data.get("nombre", ""),
                "activo": data.get("activo", True),
            },
        )
        logger.info(
            "[loyalty_consumer] CatalogoCategoria creada: %s", data.get(
                "nombre")
        )

    @transaction.atomic
    def _on_categoria_updated(self, data: dict) -> None:
        from app.loyalty.models import CatalogoCategoria

        CatalogoCategoria.objects.filter(
            categoria_id=data.get("categoria_id")
        ).update(nombre=data.get("nombre", ""))

    @transaction.atomic
    def _on_categoria_deactivated(self, data: dict) -> None:
        """
        Categoría desactivada → suspender promociones que filtren
        por esa categoría (ReglaPromocion tipo CATEGORIA).
        """
        from app.loyalty.models import CatalogoCategoria, Promocion

        categoria_id = data.get("categoria_id")
        if not categoria_id:
            return

        CatalogoCategoria.objects.filter(
            categoria_id=categoria_id
        ).update(activo=False)

        promos_afectadas = Promocion.objects.filter(
            activa=True,
            reglas__tipo_condicion="categoria",
            reglas__categoria_id=categoria_id,
        ).distinct()

        count = promos_afectadas.count()
        if count:
            promos_afectadas.update(activa=False)
            logger.warning(
                "[loyalty_consumer] Categoria %s desactivada — "
                "%d promocion(es) suspendidas.",
                categoria_id, count,
            )

    @transaction.atomic
    def _on_precio_sync(self, data: dict) -> None:
        """
        Sincroniza el precio en CatalogoPlato si se guarda precio local.
        En esta fase solo logueamos — en el futuro se puede guardar
        el precio actual para calcular puntos sin consultar menu_service.
        """
        logger.info(
            "[loyalty_consumer] Precio sync — plato %s en restaurante %s: %s %s",
            data.get("plato_id"), data.get("restaurante_id"),
            data.get("precio"), data.get("moneda"),
        )

    # -----------------------------------------------------------------------
    # Helpers de evaluación de promociones
    # -----------------------------------------------------------------------

    def _evaluar_promociones(self, promociones, total, detalles,
                             restaurante_id, ahora) -> object:
        """
        Evalúa la lista de promociones contra el pedido y retorna
        la primera que cumpla TODAS sus reglas, o None.
        Prioriza las de alcance LOCAL > MARCA > GLOBAL.
        """
        orden = {"local": 0, "marca": 1, "global": 2}
        promociones_ordenadas = sorted(
            promociones, key=lambda p: orden.get(p.alcance, 99)
        )

        plato_ids = {str(d.get("plato_id")) for d in detalles}

        for promo in promociones_ordenadas:
            if self._cumple_reglas(promo, total, plato_ids, ahora):
                return promo

        return None

    def _cumple_reglas(self, promo, total, plato_ids, ahora) -> bool:
        """
        Verifica que el pedido cumpla TODAS las reglas de la promoción.
        Si no tiene reglas, la promoción aplica siempre (promo abierta).
        """
        from app.loyalty.models import CatalogoPlato

        reglas = list(promo.reglas.all())
        if not reglas:
            return True

        for regla in reglas:
            if regla.tipo_condicion == "monto_minimo":
                if total < (regla.monto_minimo or 0):
                    return False

            elif regla.tipo_condicion == "plato":
                if str(regla.plato_id) not in plato_ids:
                    return False

            elif regla.tipo_condicion == "categoria":
                # Verificar si algún plato del pedido pertenece a la categoría
                platos_en_categoria = CatalogoPlato.objects.filter(
                    plato_id__in=plato_ids,
                    categoria_id=regla.categoria_id,
                    activo=True,
                ).exists()
                if not platos_en_categoria:
                    return False

            elif regla.tipo_condicion == "hora":
                hora_actual = ahora.hour
                if not (regla.hora_inicio <= hora_actual < regla.hora_fin):
                    return False

        return True

    def _calcular_beneficio(self, promo, total) -> tuple:
        """
        Calcula (descuento_monto, puntos_bonus) según el tipo de beneficio.
        Retorna (Decimal, int).
        """
        descuento = Decimal("0")
        puntos_bonus = 0

        if promo.tipo_beneficio == "descuento_pct":
            descuento = (total * promo.valor / Decimal("100")).quantize(
                Decimal("0.01")
            )
        elif promo.tipo_beneficio == "descuento_monto":
            descuento = min(promo.valor, total)
        elif promo.tipo_beneficio == "puntos_extra":
            puntos_bonus = promo.puntos_bonus

        return descuento, puntos_bonus


# ---------------------------------------------------------------------------
# Helper Q para filtrar promociones por alcance
# Definido fuera de la clase para evitar importar Q dentro del método
# ---------------------------------------------------------------------------

def models_q_alcance(restaurante_id):
    from django.db.models import Q
    return (
        Q(alcance="global") |
        Q(alcance="local", restaurante_id=restaurante_id)
    )

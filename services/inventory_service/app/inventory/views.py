# inventory_service/app/inventory/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from django.db.models import F

from .models import (
    Proveedor, Almacen, IngredienteInventario,
    LoteIngrediente, MovimientoInventario,
    OrdenCompra, DetalleOrdenCompra, AlertaStock, RecetaPlato,
)
from .serializers import (
    ProveedorSerializer, ProveedorListSerializer,
    AlmacenSerializer, AlmacenWriteSerializer,
    IngredienteInventarioSerializer, IngredienteInventarioListSerializer,
    IngredienteInventarioWriteSerializer, IngredienteInventarioNivelesSerializer,
    AjusteStockSerializer,
    LoteIngredienteSerializer, LoteIngredienteWriteSerializer, LoteListSerializer,
    MovimientoInventarioSerializer,
    OrdenCompraSerializer, OrdenCompraListSerializer, OrdenCompraWriteSerializer,
    RecibirOrdenSerializer,
    AlertaStockSerializer,
    RecetaPlatoSerializer,
)
from .events.event_types import InventoryEvents
from .events.builders import InventoryEventBuilder
from app.inventory.infrastructure.messaging.publisher import get_publisher
import logging
import requests
from django.conf import settings
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────


def _crear_movimiento(inv, tipo, cantidad_signed, descripcion):
    """
    Registra un movimiento de stock y publica el evento correspondiente.

    cantidad_signed: valor con signo.
      - Positivo → suma al stock (ENTRADA, DEVOLUCION, AJUSTE positivo)
      - Negativo → resta del stock (SALIDA, VENCIMIENTO, AJUSTE negativo)

    Para SALIDA y VENCIMIENTO se aplica max(..., 0) para no dejar negativo.
    Para AJUSTE se permite negativos controlados (validado en el ViewSet).
    """
    cantidad_antes = float(inv.cantidad_actual)

    if tipo in ("SALIDA", "VENCIMIENTO"):
        inv.cantidad_actual = max(inv.cantidad_actual + cantidad_signed, 0)
    else:
        # ENTRADA, DEVOLUCION, AJUSTE (puede ser negativo si el ViewSet lo validó)
        inv.cantidad_actual = inv.cantidad_actual + cantidad_signed

    inv.save(update_fields=["cantidad_actual", "fecha_actualizacion"])

    MovimientoInventario.objects.create(
        ingrediente_inventario=inv,
        tipo_movimiento=tipo,
        cantidad=abs(cantidad_signed),
        cantidad_antes=cantidad_antes,
        cantidad_despues=float(inv.cantidad_actual),
        descripcion=descripcion,
    )

    get_publisher().publish(
        InventoryEvents.STOCK_ACTUALIZADO,
        InventoryEventBuilder.stock_actualizado(
            ingrediente_id=inv.ingrediente_id,
            almacen_id=inv.almacen_id,
            restaurante_id=inv.almacen.restaurante_id,
            cantidad_anterior=cantidad_antes,
            cantidad_nueva=float(inv.cantidad_actual),
            unidad_medida=inv.unidad_medida,
            tipo_movimiento=tipo,
        )
    )


def _verificar_alertas(inv):
    """
    Crea AlertaStock si aplica.
    Idempotente: no duplica si ya existe una PENDIENTE del mismo tipo.
    """
    from .models import TipoAlerta, EstadoAlerta

    if inv.esta_agotado:
        tipo = TipoAlerta.AGOTADO
    elif inv.necesita_reposicion:
        tipo = TipoAlerta.STOCK_BAJO
    else:
        return

    ya_existe = AlertaStock.objects.filter(
        ingrediente_id=inv.ingrediente_id,
        restaurante_id=inv.almacen.restaurante_id,
        tipo_alerta=tipo,
        estado=EstadoAlerta.PENDIENTE,
    ).exists()

    if ya_existe:
        return

    AlertaStock.objects.create(
        ingrediente_inventario=inv,
        almacen=inv.almacen,
        restaurante_id=inv.almacen.restaurante_id,
        ingrediente_id=inv.ingrediente_id,
        tipo_alerta=tipo,
        nivel_actual=inv.cantidad_actual,
        nivel_minimo=inv.nivel_minimo,
    )


# ─────────────────────────────────────────
# PROVEEDOR
# ─────────────────────────────────────────


class ProveedorViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        qs = Proveedor.objects.all()
        activo = self.request.query_params.get("activo")
        pais = self.request.query_params.get("pais")
        scope = self.request.query_params.get("scope")
        restaurante_id = self.request.query_params.get("restaurante_id")
        pais_destino = self.request.query_params.get("pais_destino")
        ciudad_destino = self.request.query_params.get("ciudad_destino")

        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")
        if pais:
            qs = qs.filter(pais__icontains=pais)

        # Filtro de visibilidad para gerente_local (Opción B)
        if scope == "gerente" and restaurante_id:
            from django.db.models import Q
            filtro = Q(alcance="GLOBAL")
            if pais_destino:
                filtro |= Q(alcance="PAIS", pais_destino=pais_destino)
            if ciudad_destino:
                filtro |= Q(alcance="CIUDAD", ciudad_destino=ciudad_destino)
            filtro |= Q(alcance="LOCAL",
                        creado_por_restaurante_id=restaurante_id)
            qs = qs.filter(filtro)

        return qs.order_by("nombre")

    def get_serializer_class(self):
        return ProveedorListSerializer if self.action == "list" else ProveedorSerializer


# ─────────────────────────────────────────
# ALMACÉN
# ─────────────────────────────────────────

class AlmacenViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        qs = Almacen.objects.prefetch_related("ingredientes")

        restaurante_id = self.request.query_params.get("restaurante_id")
        activo = self.request.query_params.get("activo")

        if restaurante_id:
            qs = qs.filter(restaurante_id=restaurante_id)
        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")

        return qs.order_by("nombre")

    def get_serializer_class(self):
        if self.action in ("create", "partial_update"):
            return AlmacenWriteSerializer
        return AlmacenSerializer

    @action(detail=True, methods=["get"])
    def stock(self, request, pk=None):
        almacen = self.get_object()
        qs = almacen.ingredientes.all()

        if request.query_params.get("bajo_minimo") == "true":
            qs = qs.filter(cantidad_actual__lte=F("nivel_minimo"))

        return Response(IngredienteInventarioListSerializer(qs, many=True).data)


# ─────────────────────────────────────────
# INGREDIENTE INVENTARIO
# ─────────────────────────────────────────

class IngredienteInventarioViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        qs = IngredienteInventario.objects.select_related(
            "almacen", "lote_actual"
        ).prefetch_related("movimientos")

        almacen_id = self.request.query_params.get("almacen_id")
        if almacen_id:
            qs = qs.filter(almacen_id=almacen_id)

        return qs.order_by("nombre_ingrediente")

    def get_serializer_class(self):
        if self.action == "list":
            return IngredienteInventarioListSerializer
        if self.action == "create":
            return IngredienteInventarioWriteSerializer
        if self.action == "partial_update":
            return IngredienteInventarioNivelesSerializer
        return IngredienteInventarioSerializer

    @action(detail=True, methods=["post"])
    def ajustar(self, request, pk=None):
        inv = self.get_object()

        serializer = AjusteStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cantidad = serializer.validated_data["cantidad"]
        descripcion = serializer.validated_data["descripcion"]

        if inv.cantidad_actual + cantidad < 0:
            return Response(
                {"detail": "El stock no puede quedar negativo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            _crear_movimiento(inv, "AJUSTE", cantidad, descripcion)
            _verificar_alertas(inv)

        inv.refresh_from_db()
        return Response(IngredienteInventarioSerializer(inv).data)

    @action(detail=True, methods=["get"])
    def movimientos(self, request, pk=None):
        inv = self.get_object()
        movs = inv.movimientos.order_by("-fecha")
        return Response(MovimientoInventarioSerializer(movs, many=True).data)


# ─────────────────────────────────────────
# LOTE
# ─────────────────────────────────────────

class LoteIngredienteViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post"]

    def get_queryset(self):
        qs = LoteIngrediente.objects.select_related("almacen", "proveedor")

        estado = self.request.query_params.get("estado")
        almacen_id = self.request.query_params.get("almacen_id")
        por_vencer = self.request.query_params.get("por_vencer")

        if estado:
            qs = qs.filter(estado=estado)
        if almacen_id:
            qs = qs.filter(almacen_id=almacen_id)
        if por_vencer:
            from datetime import timedelta
            fecha_limite = timezone.now().date() + timedelta(days=int(por_vencer))
            qs = qs.filter(fecha_vencimiento__lte=fecha_limite,
                           estado="ACTIVO")

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return LoteIngredienteWriteSerializer
        return LoteIngredienteSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        lote = serializer.save()

        inv, _ = IngredienteInventario.objects.get_or_create(
            ingrediente_id=lote.ingrediente_id,
            almacen=lote.almacen,
            defaults={
                "nombre_ingrediente": f"Ingrediente {lote.ingrediente_id}",
                "unidad_medida":      lote.unidad_medida,
            }
        )

        _crear_movimiento(
            inv, "ENTRADA", lote.cantidad_recibida, "Nuevo lote recibido")

    @action(detail=True, methods=["post"])
    def retirar(self, request, pk=None):
        lote = self.get_object()

        if lote.estado == "RETIRADO":
            return Response(
                {"detail": "El lote ya fue retirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lote.estado = "RETIRADO"
        lote.save(update_fields=["estado"])
        return Response(LoteIngredienteSerializer(lote).data)


# ─────────────────────────────────────────
# ORDEN COMPRA
# ─────────────────────────────────────────

class OrdenCompraViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        qs = OrdenCompra.objects.all()

        estado = self.request.query_params.get("estado")
        proveedor_id = self.request.query_params.get("proveedor_id")
        restaurante_id = self.request.query_params.get("restaurante_id")

        if estado:
            qs = qs.filter(estado=estado)
        if proveedor_id:
            qs = qs.filter(proveedor_id=proveedor_id)
        if restaurante_id:
            qs = qs.filter(restaurante_id=restaurante_id)

        return qs.order_by("-fecha_creacion")

    def get_serializer_class(self):
        if self.action == "list":
            return OrdenCompraListSerializer
        if self.action == "create":
            return OrdenCompraWriteSerializer
        if self.action == "recibir":
            return RecibirOrdenSerializer
        return OrdenCompraSerializer

    # ── ENVIAR ────────────────────────────────────────────────────────────
    @action(detail=True, methods=["post"])
    def enviar(self, request, pk=None):
        """
        POST /ordenes-compra/{id}/enviar/
        BORRADOR → ENVIADA (también acepta PENDIENTE → ENVIADA).
        """
        orden = self.get_object()

        if orden.estado not in ("BORRADOR", "PENDIENTE"):
            return Response(
                {"detail": f"No se puede enviar una orden en estado '{orden.estado}'. Solo se pueden enviar órdenes en estado BORRADOR o PENDIENTE."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orden.estado = "ENVIADA"
        orden.save(update_fields=["estado"])

        return Response(OrdenCompraSerializer(orden).data)

    # ── CANCELAR ──────────────────────────────────────────────────────────
    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        """
        POST /ordenes-compra/{id}/cancelar/
        Cancela una orden que no está ya RECIBIDA o CANCELADA.
        """
        orden = self.get_object()

        if orden.estado in ("RECIBIDA", "CANCELADA"):
            return Response(
                {"detail": f"No se puede cancelar una orden en estado '{orden.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orden.estado = "CANCELADA"
        orden.save(update_fields=["estado"])

        return Response(OrdenCompraSerializer(orden).data)

    # ── RECIBIR ───────────────────────────────────────────────────────────
    @action(detail=True, methods=["post"])
    def recibir(self, request, pk=None):
        """
        POST /ordenes-compra/{id}/recibir/
        Recibe una orden ENVIADA: crea lotes, actualiza stock y costos.
        """
        orden = self.get_object()

        if orden.estado != "ENVIADA":
            return Response(
                {"detail": f"Solo se pueden recibir órdenes en estado ENVIADA. Estado actual: '{orden.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RecibirOrdenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        detalles_recepcion = serializer.validated_data["detalles"]

        with transaction.atomic():
            for item in detalles_recepcion:
                detalle_id = item["detalle_id"]
                cantidad_recibida = item["cantidad_recibida"]
                numero_lote = item["numero_lote"]
                fecha_vencimiento = item["fecha_vencimiento"]
                fecha_produccion = item.get("fecha_produccion")

                try:
                    detalle = orden.detalles.get(id=detalle_id)
                except DetalleOrdenCompra.DoesNotExist:
                    return Response(
                        {"detail": f"Detalle {detalle_id} no pertenece a esta orden."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if cantidad_recibida == 0:
                    continue

                almacen = Almacen.objects.filter(
                    restaurante_id=orden.restaurante_id,
                    activo=True,
                ).first()

                if not almacen:
                    return Response(
                        {"detail": f"No hay almacén activo para el restaurante {orden.restaurante_id}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                lote = LoteIngrediente.objects.create(
                    ingrediente_id=detalle.ingrediente_id,
                    almacen=almacen,
                    proveedor=orden.proveedor,
                    numero_lote=numero_lote,
                    fecha_produccion=fecha_produccion,
                    fecha_vencimiento=fecha_vencimiento,
                    cantidad_recibida=cantidad_recibida,
                    cantidad_actual=cantidad_recibida,
                    unidad_medida=detalle.unidad_medida,
                )

                detalle.cantidad_recibida = cantidad_recibida
                detalle.save(update_fields=["cantidad_recibida"])

                inv, _ = IngredienteInventario.objects.get_or_create(
                    ingrediente_id=detalle.ingrediente_id,
                    almacen=almacen,
                    defaults={
                        "nombre_ingrediente": detalle.nombre_ingrediente,
                        "unidad_medida": detalle.unidad_medida,
                    }
                )
                inv.lote_actual = lote
                inv.save(update_fields=["lote_actual"])

                _crear_movimiento(
                    inv,
                    "ENTRADA",
                    cantidad_recibida,
                    f"Recepción orden de compra {orden.id} — lote {numero_lote}",
                )

                RecetaPlato.objects.filter(
                    ingrediente_id=detalle.ingrediente_id
                ).update(
                    costo_unitario=detalle.precio_unitario,
                    fecha_costo_actualizado=timezone.now(),
                )

            orden.estado = "RECIBIDA"
            orden.fecha_recepcion = timezone.now()
            orden.save(update_fields=["estado", "fecha_recepcion"])

        return Response(OrdenCompraSerializer(orden).data)


# ─────────────────────────────────────────
# ALERTAS
# ─────────────────────────────────────────

class AlertaStockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertaStockSerializer

    def get_queryset(self):
        qs = AlertaStock.objects.all()

        restaurante_id = self.request.query_params.get("restaurante_id")
        tipo = self.request.query_params.get("tipo")
        estado = self.request.query_params.get("estado")

        if restaurante_id:
            qs = qs.filter(restaurante_id=restaurante_id)
        if tipo:
            qs = qs.filter(tipo_alerta=tipo)
        if estado:
            qs = qs.filter(estado=estado)

        return qs.order_by("-fecha_alerta")

    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        alerta = self.get_object()
        alerta.resolver()
        return Response(AlertaStockSerializer(alerta).data)

    @action(detail=True, methods=["post"])
    def ignorar(self, request, pk=None):
        from .models import EstadoAlerta
        alerta = self.get_object()
        if alerta.estado != EstadoAlerta.PENDIENTE:
            return Response(
                {"detail": "Solo se pueden ignorar alertas en estado PENDIENTE."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        alerta.estado = EstadoAlerta.IGNORADA
        alerta.save(update_fields=["estado"])
        return Response(AlertaStockSerializer(alerta).data)


# ─────────────────────────────────────────
# MOVIMIENTOS (audit log — solo lectura)
# ─────────────────────────────────────────

class MovimientoInventarioViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MovimientoInventarioSerializer

    def get_queryset(self):
        qs = MovimientoInventario.objects.select_related(
            "ingrediente_inventario", "lote"
        )

        stock_id = self.request.query_params.get("stock_id")
        ingrediente_id = self.request.query_params.get("ingrediente_id")
        tipo = self.request.query_params.get("tipo")
        fecha_desde = self.request.query_params.get("fecha_desde")

        if stock_id:
            qs = qs.filter(ingrediente_inventario_id=stock_id)
        if ingrediente_id:
            qs = qs.filter(
                ingrediente_inventario__ingrediente_id=ingrediente_id)
        if tipo:
            qs = qs.filter(tipo_movimiento=tipo)
        if fecha_desde:
            qs = qs.filter(fecha__date__gte=fecha_desde)

        return qs.order_by("-fecha")


# ─────────────────────────────────────────
# RECETAS (solo lectura — se sincronizan vía RabbitMQ)
# ─────────────────────────────────────────

class RecetaPlatoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RecetaPlatoSerializer

    def get_queryset(self):
        qs = RecetaPlato.objects.all()
        plato_id = self.request.query_params.get("plato_id")
        if plato_id:
            qs = qs.filter(plato_id=plato_id)
        return qs.order_by("nombre_ingrediente")

    def get_serializer_context(self):
        context = super().get_serializer_context()

        qs = self.get_queryset()
        ingrediente_ids = set(qs.values_list("ingrediente_id", flat=True))

        registros = IngredienteInventario.objects.filter(
            ingrediente_id__in=ingrediente_ids
        ).values("ingrediente_id", "nombre_ingrediente")

        context["ingredientes_cache"] = {
            str(r["ingrediente_id"]): r["nombre_ingrediente"]
            for r in registros
            if r["nombre_ingrediente"]
        }

        return context

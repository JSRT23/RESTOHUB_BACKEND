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

        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")
        if pais:
            qs = qs.filter(pais__icontains=pais)

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

        # cantidad puede ser positiva o negativa — el serializer ya validó != 0
        cantidad = serializer.validated_data["cantidad"]
        descripcion = serializer.validated_data["descripcion"]

        if inv.cantidad_actual + cantidad < 0:
            return Response(
                {"detail": "El stock no puede quedar negativo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Pasamos cantidad con signo — _crear_movimiento lo maneja correctamente
            _crear_movimiento(inv, "AJUSTE", cantidad, descripcion)
            _verificar_alertas(inv)

        inv.refresh_from_db()
        return Response(IngredienteInventarioSerializer(inv).data)


# ─────────────────────────────────────────
# LOTE
# ─────────────────────────────────────────

class LoteIngredienteViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post"]

    def get_queryset(self):
        return LoteIngrediente.objects.select_related("almacen", "proveedor")

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


# ─────────────────────────────────────────
# ORDEN COMPRA
# ─────────────────────────────────────────

class OrdenCompraViewSet(viewsets.ModelViewSet):
    queryset = OrdenCompra.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return OrdenCompraListSerializer
        if self.action == "create":
            return OrdenCompraWriteSerializer
        if self.action == "recibir":
            return RecibirOrdenSerializer
        return OrdenCompraSerializer

    @action(detail=True, methods=["post"])
    def recibir(self, request, pk=None):
        """
        Recibe una orden de compra:
        1. Valida que esté en estado ENVIADA.
        2. Por cada detalle del payload crea un LoteIngrediente.
        3. Suma la cantidad recibida al stock del IngredienteInventario.
        4. Actualiza costo_unitario en RecetaPlato para análisis de márgenes.
        5. Marca la orden como RECIBIDA.
        Todo dentro de una transacción atómica.
        """
        orden = self.get_object()

        if orden.estado != "ENVIADA":
            return Response(
                {"detail": "Solo se pueden recibir órdenes en estado ENVIADA."},
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

                # Obtener el detalle de la orden
                try:
                    detalle = orden.detalles.get(id=detalle_id)
                except DetalleOrdenCompra.DoesNotExist:
                    return Response(
                        {"detail": f"Detalle {detalle_id} no pertenece a esta orden."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if cantidad_recibida == 0:
                    continue  # Ítem no entregado — saltar

                # Buscar el almacén del restaurante (primer almacén activo)
                almacen = Almacen.objects.filter(
                    restaurante_id=orden.restaurante_id,
                    activo=True,
                ).first()

                if not almacen:
                    return Response(
                        {"detail": f"No hay almacén activo para el restaurante {orden.restaurante_id}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Crear lote
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

                # Actualizar cantidad recibida en el detalle
                detalle.cantidad_recibida = cantidad_recibida
                detalle.save(update_fields=["cantidad_recibida"])

                # Actualizar o crear stock
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

                # Actualizar costo_unitario en RecetaPlato para análisis de márgenes
                RecetaPlato.objects.filter(
                    ingrediente_id=detalle.ingrediente_id
                ).update(
                    costo_unitario=detalle.precio_unitario,
                    fecha_costo_actualizado=timezone.now(),
                )

            # Marcar orden como recibida
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


# ─────────────────────────────────────────
# MOVIMIENTOS (audit log — solo lectura)
# ─────────────────────────────────────────

class MovimientoInventarioViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MovimientoInventarioSerializer

    def get_queryset(self):
        qs = MovimientoInventario.objects.select_related(
            "ingrediente_inventario", "lote"
        )

        ingrediente_id = self.request.query_params.get("ingrediente_id")
        tipo = self.request.query_params.get("tipo")
        fecha_desde = self.request.query_params.get("fecha_desde")

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
    """
    GET /api/inventory/recetas/
    GET /api/inventory/recetas/{id}/
    GET /api/inventory/recetas/?plato_id=uuid

    Retorna plato_id e ingrediente_id como referencias.
    La resolución de nombres (nombre_plato, nombre_ingrediente)
    se hace en el gateway_service que tiene acceso a todos los servicios.
    """
    serializer_class = RecetaPlatoSerializer

    def get_queryset(self):
        qs = RecetaPlato.objects.all()
        plato_id = self.request.query_params.get("plato_id")
        if plato_id:
            qs = qs.filter(plato_id=plato_id)
        return qs.order_by("nombre_ingrediente")

    def get_serializer_context(self):
        context = super().get_serializer_context()

        # Resolver nombre_ingrediente desde IngredienteInventario local
        # (sincronizado vía RabbitMQ — no requiere llamadas HTTP)
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

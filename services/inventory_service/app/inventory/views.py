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
from app.inventory.infrastructure.messaging.publisher import EventPublisher


# ─────────────────────────────────────────
# 🔧 Helper — crear movimiento
# ─────────────────────────────────────────

def _crear_movimiento(inv, tipo, cantidad, descripcion):
    cantidad_antes = inv.cantidad_actual

    if tipo in ["SALIDA", "VENCIMIENTO"]:
        inv.cantidad_actual = max(inv.cantidad_actual - cantidad, 0)
    else:
        inv.cantidad_actual += cantidad

    inv.save(update_fields=["cantidad_actual", "fecha_actualizacion"])

    MovimientoInventario.objects.create(
        ingrediente_inventario=inv,
        tipo_movimiento=tipo,
        cantidad=cantidad,
        cantidad_antes=cantidad_antes,
        cantidad_despues=inv.cantidad_actual,
        descripcion=descripcion,
    )

    # 🔥 EVENTO
    publisher = EventPublisher()
    publisher.publish(InventoryEvents.STOCK_ACTUALIZADO, {
        "ingrediente_id": str(inv.ingrediente_id),
        "almacen_id": str(inv.almacen_id),
        "restaurante_id": str(inv.almacen.restaurante_id),
        "cantidad_anterior": str(cantidad_antes),
        "cantidad_nueva": str(inv.cantidad_actual),
        "unidad_medida": inv.unidad_medida,
        "tipo_movimiento": tipo,
    })
    publisher.close()


def _verificar_alertas(inv):
    if inv.esta_agotado:
        AlertaStock.objects.create(
            ingrediente_inventario=inv,
            almacen=inv.almacen,
            restaurante_id=inv.almacen.restaurante_id,
            ingrediente_id=inv.ingrediente_id,
            tipo_alerta="AGOTADO",
            nivel_actual=inv.cantidad_actual,
            nivel_minimo=inv.nivel_minimo,
        )
    elif inv.necesita_reposicion:
        AlertaStock.objects.create(
            ingrediente_inventario=inv,
            almacen=inv.almacen,
            restaurante_id=inv.almacen.restaurante_id,
            ingrediente_id=inv.ingrediente_id,
            tipo_alerta="STOCK_BAJO",
            nivel_actual=inv.cantidad_actual,
            nivel_minimo=inv.nivel_minimo,
        )


# ─────────────────────────────────────────
# 🧑‍🌾 PROVEEDOR
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
# 🏪 ALMACÉN
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
# 📦 INGREDIENTE INVENTARIO
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
        if self.action == "ajustar":
            return AjusteStockSerializer
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
                {"detail": "Stock no puede quedar negativo"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            cantidad_antes = inv.cantidad_actual
            inv.cantidad_actual += cantidad
            inv.save(update_fields=["cantidad_actual", "fecha_actualizacion"])

            MovimientoInventario.objects.create(
                ingrediente_inventario=inv,
                tipo_movimiento="AJUSTE",
                cantidad=abs(cantidad),
                cantidad_antes=cantidad_antes,
                cantidad_despues=inv.cantidad_actual,
                descripcion=descripcion,
            )

            publish_event(InventoryEvents.STOCK_ACTUALIZADO, {
                "ingrediente_id": str(inv.ingrediente_id),
                "almacen_id": str(inv.almacen_id),
                "restaurante_id": str(inv.almacen.restaurante_id),
                "cantidad_anterior": str(cantidad_antes),
                "cantidad_nueva": str(inv.cantidad_actual),
                "unidad_medida": inv.unidad_medida,
                "tipo_movimiento": "AJUSTE",
            })

            _verificar_alertas(inv)

        return Response(IngredienteInventarioSerializer(inv).data)


# ─────────────────────────────────────────
# 📦 LOTE
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
                "unidad_medida": lote.unidad_medida,
            }
        )

        _crear_movimiento(inv, "ENTRADA", lote.cantidad_recibida, "Nuevo lote")


# ─────────────────────────────────────────
# 📑 ORDEN COMPRA
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
        orden = self.get_object()

        if orden.estado != "ENVIADA":
            return Response({"detail": "Orden no válida"}, status=400)

        orden.estado = "RECIBIDA"
        orden.fecha_recepcion = timezone.now()
        orden.save()

        return Response(OrdenCompraSerializer(orden).data)


# ─────────────────────────────────────────
# 🚨 ALERTAS
# ─────────────────────────────────────────

class AlertaStockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertaStockSerializer

    def get_queryset(self):
        return AlertaStock.objects.all().order_by("-fecha_alerta")

    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        alerta = self.get_object()
        alerta.resolver()
        return Response(AlertaStockSerializer(alerta).data)

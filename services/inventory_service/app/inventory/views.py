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
    EstadoLote, EstadoAlerta, EstadoOrdenCompra,
)
from .serializers import (
    ProveedorSerializer, ProveedorListSerializer,
    AlmacenSerializer, AlmacenWriteSerializer,
    IngredienteInventarioSerializer, IngredienteInventarioListSerializer,
    IngredienteInventarioWriteSerializer, IngredienteInventarioNivelesSerializer,
    AjusteStockSerializer, CostoPlatoSerializer,
    LoteIngredienteSerializer, LoteIngredienteWriteSerializer, LoteListSerializer,
    MovimientoInventarioSerializer,
    OrdenCompraSerializer, OrdenCompraListSerializer, OrdenCompraWriteSerializer,
    RecibirOrdenSerializer,
    AlertaStockSerializer,
    RecetaPlatoSerializer,
)
from .events.event_types import InventoryEvents
from .events.builders import InventoryEventBuilder
from app.inventory.infrastructure.messaging.publisher import get_publisher  # ✅ singleton


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def _crear_movimiento(inv, tipo, cantidad, descripcion):
    """
    cantidad debe ser positivo para ENTRADA/DEVOLUCION/VENCIMIENTO/SALIDA.
    Para AJUSTE, cantidad puede ser negativo (reducción) o positivo (aumento).
    El log de movimiento siempre almacena abs(cantidad).
    """
    cantidad_antes = inv.cantidad_actual

    if tipo in ["SALIDA", "VENCIMIENTO"]:
        inv.cantidad_actual = max(inv.cantidad_actual - abs(cantidad), 0)
    elif tipo == "AJUSTE":
        inv.cantidad_actual = max(inv.cantidad_actual + cantidad, 0)
    else:  # ENTRADA, DEVOLUCION
        inv.cantidad_actual += abs(cantidad)

    inv.save(update_fields=["cantidad_actual", "fecha_actualizacion"])

    MovimientoInventario.objects.create(
        ingrediente_inventario=inv,
        tipo_movimiento=tipo,
        cantidad=abs(cantidad),
        cantidad_antes=cantidad_antes,
        cantidad_despues=inv.cantidad_actual,
        descripcion=descripcion,
    )

    # ✅ get_publisher() — singleton, sin close()
    get_publisher().publish(
        InventoryEvents.STOCK_ACTUALIZADO,
        InventoryEventBuilder.stock_actualizado(
            ingrediente_id=inv.ingrediente_id,
            almacen_id=inv.almacen_id,
            restaurante_id=inv.almacen.restaurante_id,
            cantidad_anterior=cantidad_antes,
            cantidad_nueva=inv.cantidad_actual,
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

    # ✅ No duplicar alertas pendientes
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

    @action(detail=False, methods=["get"], url_path="costo-plato")
    def costo_plato(self, request):
        plato_id = request.query_params.get("plato_id")
        if not plato_id:
            return Response(
                {"detail": "plato_id es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recetas = RecetaPlato.objects.filter(plato_id=plato_id)
        if not recetas.exists():
            return Response(
                {"detail": "No se encontraron recetas para este plato."},
                status=status.HTTP_404_NOT_FOUND,
            )

        costo_total = sum(r.costo_ingrediente for r in recetas)
        tiene_costos_vacios = recetas.filter(costo_unitario=0).exists()

        data = {
            "plato_id": plato_id,
            "costo_total": round(costo_total, 4),
            "tiene_costos_vacios": tiene_costos_vacios,
            "ingredientes": recetas,
        }

        return Response(CostoPlatoSerializer(data).data)

    @action(detail=True, methods=["post"])
    def ajustar(self, request, pk=None):
        inv = self.get_object()

        serializer = AjusteStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cantidad = serializer.validated_data["cantidad"]
        descripcion = serializer.validated_data["descripcion"]

        if inv.cantidad_actual + cantidad < 0:
            return Response(
                {"detail": "Stock no puede quedar negativo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            _crear_movimiento(inv, "AJUSTE", cantidad, descripcion)
            _verificar_alertas(inv)

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

        inv.lote_actual = lote
        inv.save(update_fields=["lote_actual"])

    @action(detail=True, methods=["post"])
    def retirar(self, request, pk=None):
        lote = self.get_object()

        if lote.estado == EstadoLote.RETIRADO:
            return Response(
                {"detail": "Este lote ya está retirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            if lote.cantidad_actual > 0:
                inv = IngredienteInventario.objects.filter(
                    ingrediente_id=lote.ingrediente_id,
                    almacen=lote.almacen,
                ).first()
                if inv:
                    _crear_movimiento(
                        inv, "VENCIMIENTO", lote.cantidad_actual,
                        f"Retiro de lote {lote.numero_lote}",
                    )
                    _verificar_alertas(inv)

            lote.estado = EstadoLote.RETIRADO
            lote.cantidad_actual = 0
            lote.save(update_fields=["estado", "cantidad_actual"])

        return Response(LoteIngredienteSerializer(lote).data)


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
    def enviar(self, request, pk=None):
        orden = self.get_object()

        if orden.estado != "BORRADOR":
            return Response(
                {"detail": "Solo se pueden enviar órdenes en estado BORRADOR."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orden.estado = EstadoOrdenCompra.ENVIADA
        orden.save(update_fields=["estado"])

        get_publisher().publish(
            InventoryEvents.ORDEN_COMPRA_ENVIADA,
            InventoryEventBuilder.orden_compra_enviada(orden),
        )

        return Response(OrdenCompraSerializer(orden).data)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        orden = self.get_object()

        if orden.estado == EstadoOrdenCompra.RECIBIDA:
            return Response(
                {"detail": "No se puede cancelar una orden ya recibida."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if orden.estado == EstadoOrdenCompra.CANCELADA:
            return Response(
                {"detail": "Esta orden ya está cancelada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orden.estado = EstadoOrdenCompra.CANCELADA
        orden.save(update_fields=["estado"])

        get_publisher().publish(
            InventoryEvents.ORDEN_COMPRA_CANCELADA,
            InventoryEventBuilder.orden_compra_cancelada(orden),
        )

        return Response(OrdenCompraSerializer(orden).data)

    @action(detail=True, methods=["post"])
    def recibir(self, request, pk=None):
        orden = self.get_object()

        if orden.estado != EstadoOrdenCompra.ENVIADA:
            return Response(
                {"detail": "Solo se pueden recibir órdenes en estado ENVIADA."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RecibirOrdenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            for detalle_data in serializer.validated_data["detalles"]:
                try:
                    detalle = DetalleOrdenCompra.objects.get(
                        id=detalle_data["detalle_id"], orden=orden
                    )
                except DetalleOrdenCompra.DoesNotExist:
                    return Response(
                        {"detail": f"Detalle {detalle_data['detalle_id']} no pertenece a esta orden."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                cantidad_recibida = detalle_data["cantidad_recibida"]
                if cantidad_recibida > detalle.cantidad:
                    return Response(
                        {"detail": f"Cantidad recibida supera la pedida para '{detalle.nombre_ingrediente}'."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                detalle.cantidad_recibida = cantidad_recibida
                detalle.save(update_fields=["cantidad_recibida"])

                if cantidad_recibida == 0:
                    continue

                # Use first warehouse for this restaurant; skip if none exists
                almacen = Almacen.objects.filter(
                    restaurante_id=orden.restaurante_id, activo=True
                ).first()
                if not almacen:
                    continue

                lote = LoteIngrediente.objects.create(
                    ingrediente_id=detalle.ingrediente_id,
                    almacen=almacen,
                    proveedor=orden.proveedor,
                    numero_lote=detalle_data["numero_lote"],
                    fecha_vencimiento=detalle_data["fecha_vencimiento"],
                    fecha_produccion=detalle_data.get("fecha_produccion"),
                    cantidad_recibida=cantidad_recibida,
                    cantidad_actual=cantidad_recibida,
                    unidad_medida=detalle.unidad_medida,
                )

                inv, _ = IngredienteInventario.objects.get_or_create(
                    ingrediente_id=detalle.ingrediente_id,
                    almacen=almacen,
                    defaults={
                        "nombre_ingrediente": detalle.nombre_ingrediente,
                        "unidad_medida": detalle.unidad_medida,
                    },
                )

                _crear_movimiento(
                    inv, "ENTRADA", cantidad_recibida,
                    f"Recepción OC {str(orden.id)[:8]} — lote {lote.numero_lote}",
                )

                inv.lote_actual = lote
                inv.save(update_fields=["lote_actual"])

                # Update unit cost in recipe so margin analysis stays current
                RecetaPlato.objects.filter(
                    ingrediente_id=detalle.ingrediente_id
                ).update(
                    costo_unitario=detalle.precio_unitario,
                    fecha_costo_actualizado=timezone.now(),
                )

            orden.estado = EstadoOrdenCompra.RECIBIDA
            orden.fecha_recepcion = timezone.now()
            notas = serializer.validated_data.get("notas")
            if notas:
                orden.notas = notas
            orden.save(update_fields=["estado", "fecha_recepcion", "notas"])

        get_publisher().publish(
            InventoryEvents.ORDEN_COMPRA_RECIBIDA,
            InventoryEventBuilder.orden_compra_recibida(orden),
        )

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
        if alerta.estado != EstadoAlerta.PENDIENTE:
            return Response(
                {"detail": "Solo se pueden resolver alertas pendientes."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        alerta.resolver()
        return Response(AlertaStockSerializer(alerta).data)

    @action(detail=True, methods=["post"])
    def ignorar(self, request, pk=None):
        alerta = self.get_object()
        if alerta.estado != EstadoAlerta.PENDIENTE:
            return Response(
                {"detail": "Solo se pueden ignorar alertas pendientes."},
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

        ingrediente_id = self.request.query_params.get("ingrediente_id")
        tipo = self.request.query_params.get("tipo")
        fecha_desde = self.request.query_params.get("fecha_desde")

        if ingrediente_id:
            qs = qs.filter(
                ingrediente_inventario__ingrediente_id=ingrediente_id
            )
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

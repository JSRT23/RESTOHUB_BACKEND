# inventory_service/app/inventory/views.py
# PARCHES aplicados vs el original entregado:
#   1. LoteIngredienteViewSet.perform_create() → nivel_minimo=10, nivel_maximo=200
#   2. OrdenCompraViewSet.recibir() → nivel_minimo=10, nivel_maximo=200
#   3. LoteIngredienteViewSet.retirar() → descuenta stock + movimiento VENCIMIENTO
# Todo lo demás es idéntico al original.

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from decimal import Decimal

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
logger = logging.getLogger(__name__)


# ─── helpers ─────────────────────────────────────────────────────────────────

def _crear_movimiento(inv, tipo, cantidad_signed, descripcion):
    cantidad_antes = float(inv.cantidad_actual)
    if tipo in ("SALIDA", "VENCIMIENTO"):
        inv.cantidad_actual = max(inv.cantidad_actual + cantidad_signed, 0)
    else:
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


# ─── ViewSets ────────────────────────────────────────────────────────────────

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
        if scope == "gerente" and restaurante_id:
            from django.db.models import Q
            filtro = Q(alcance="GLOBAL")
            if pais_destino:
                filtro |= Q(alcance="PAIS", pais_destino__iexact=pais_destino)
                if ciudad_destino:
                    filtro |= Q(alcance="CIUDAD",
                                ciudad_destino__iexact=ciudad_destino)
            filtro |= Q(alcance="LOCAL",
                        creado_por_restaurante_id=restaurante_id)
            qs = qs.filter(filtro)
        return qs.order_by("nombre")

    def get_serializer_class(self):
        return ProveedorListSerializer if self.action == "list" else ProveedorSerializer


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
                "nivel_minimo":       10.0,   # ← FIX: mínimo operativo por defecto
                "nivel_maximo":       200.0,  # ← FIX: máximo por defecto
                "cantidad_actual":    0.0,
            }
        )
        _crear_movimiento(
            inv, "ENTRADA", lote.cantidad_recibida, "Nuevo lote recibido")

    @action(detail=True, methods=["post"])
    def retirar(self, request, pk=None):
        """
        Retira un lote del inventario (dañado, vencido, contaminado).

        Efectos:
          1. lote.estado = RETIRADO
          2. IngredienteInventario.cantidad_actual -= lote.cantidad_actual (lo que quede)
          3. MovimientoInventario tipo VENCIMIENTO (retiro de calidad)
          4. Publica stock.actualizado vía RabbitMQ
          5. Genera AlertaStock si el stock queda bajo mínimo o agotado
        """
        lote = self.get_object()

        if lote.estado == "RETIRADO":
            return Response(
                {"detail": "El lote ya fue retirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cantidad_a_descontar = lote.cantidad_actual

        with transaction.atomic():
            lote.estado = "RETIRADO"
            lote.save(update_fields=["estado"])

            if cantidad_a_descontar > 0:
                try:
                    inv = IngredienteInventario.objects.select_for_update().get(
                        ingrediente_id=lote.ingrediente_id,
                        almacen=lote.almacen,
                    )
                    _crear_movimiento(
                        inv,
                        tipo="VENCIMIENTO",
                        cantidad_signed=-cantidad_a_descontar,
                        descripcion=(
                            f"Retiro manual del lote {lote.numero_lote} — "
                            f"{float(cantidad_a_descontar):.3f} {lote.unidad_medida} retiradas"
                        ),
                    )
                    _verificar_alertas(inv)
                except IngredienteInventario.DoesNotExist:
                    pass

        return Response(LoteIngredienteSerializer(lote).data)


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

    @action(detail=True, methods=["post"])
    def enviar(self, request, pk=None):
        orden = self.get_object()
        if orden.estado not in ("BORRADOR", "PENDIENTE"):
            return Response(
                {"detail": f"No se puede enviar una orden en estado '{orden.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        orden.estado = "ENVIADA"
        orden.save(update_fields=["estado"])
        return Response(OrdenCompraSerializer(orden).data)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        orden = self.get_object()
        if orden.estado in ("RECIBIDA", "CANCELADA"):
            return Response(
                {"detail": f"No se puede cancelar una orden en estado '{orden.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        orden.estado = "CANCELADA"
        orden.save(update_fields=["estado"])
        return Response(OrdenCompraSerializer(orden).data)

    @action(detail=True, methods=["post"])
    def recibir(self, request, pk=None):
        orden = self.get_object()
        if orden.estado != "ENVIADA":
            return Response(
                {"detail": f"Solo se pueden recibir órdenes ENVIADAS. Estado actual: '{orden.estado}'."},
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
                    restaurante_id=orden.restaurante_id, activo=True).first()
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

                # ← FIX: nivel_minimo y nivel_maximo por defecto si el stock no existía
                inv, creado = IngredienteInventario.objects.get_or_create(
                    ingrediente_id=detalle.ingrediente_id,
                    almacen=almacen,
                    defaults={
                        "nombre_ingrediente": detalle.nombre_ingrediente,
                        "unidad_medida":      detalle.unidad_medida,
                        "nivel_minimo":       10.0,   # ← FIX
                        "nivel_maximo":       200.0,  # ← FIX
                        "cantidad_actual":    0.0,
                    }
                )
                inv.lote_actual = lote
                inv.save(update_fields=["lote_actual"])

                _crear_movimiento(
                    inv, "ENTRADA", cantidad_recibida,
                    f"Recepción orden de compra {orden.id} — lote {numero_lote}",
                )

                # Actualiza costo_unitario en RecetaPlato → cálculo de márgenes
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
                {"detail": "Solo se pueden ignorar alertas PENDIENTE."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        alerta.estado = EstadoAlerta.IGNORADA
        alerta.save(update_fields=["estado"])
        return Response(AlertaStockSerializer(alerta).data)


class MovimientoInventarioViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MovimientoInventarioSerializer

    def get_queryset(self):
        qs = MovimientoInventario.objects.select_related(
            "ingrediente_inventario", "lote")
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


# ─── RECETAS ─────────────────────────────────────────────────────────────────

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
            for r in registros if r["nombre_ingrediente"]
        }
        return context

    @action(detail=False, methods=["get"])
    def costo_plato(self, request):
        """
        GET /api/inventory/recetas/costo_plato/?plato_id=UUID&restaurante_id=UUID
        """
        plato_id = request.query_params.get("plato_id")
        restaurante_id = request.query_params.get("restaurante_id")

        if not plato_id:
            return Response({"detail": "plato_id es requerido."}, status=400)

        recetas = RecetaPlato.objects.filter(plato_id=plato_id)
        if not recetas.exists():
            return Response(
                {"detail": "No hay receta para este plato. Agrega ingredientes primero."},
                status=404,
            )

        stock_map = {}
        if restaurante_id:
            stock_qs = IngredienteInventario.objects.filter(
                ingrediente_id__in=recetas.values_list(
                    "ingrediente_id", flat=True),
                almacen__restaurante_id=restaurante_id,
            ).select_related("almacen")
            for s in stock_qs:
                stock_map[str(s.ingrediente_id)] = s

        costo_total = Decimal("0")
        tiene_costos_vacios = False
        porciones_minimas = None
        ingredientes_detalle = []

        for receta in recetas:
            if receta.costo_unitario == 0:
                tiene_costos_vacios = True

            costo_ing = receta.costo_ingrediente
            costo_total += Decimal(str(costo_ing))

            stock_obj = stock_map.get(str(receta.ingrediente_id))
            stock_actual = float(
                stock_obj.cantidad_actual) if stock_obj else None
            esta_agotado = stock_obj.esta_agotado if stock_obj else None
            necesita_reposicion = stock_obj.necesita_reposicion if stock_obj else None

            if stock_actual is not None and float(receta.cantidad) > 0:
                porciones_ing = int(stock_actual / float(receta.cantidad))
            else:
                porciones_ing = None

            if porciones_ing is not None:
                if porciones_minimas is None or porciones_ing < porciones_minimas:
                    porciones_minimas = porciones_ing

            ingredientes_detalle.append({
                "ingrediente_id":         str(receta.ingrediente_id),
                "nombre_ingrediente":     receta.nombre_ingrediente,
                "cantidad_receta":        float(receta.cantidad),
                "unidad_medida":          receta.unidad_medida,
                "costo_unitario":         float(receta.costo_unitario),
                "costo_ingrediente":      round(costo_ing, 4),
                "stock_actual":           stock_actual,
                "esta_agotado":           esta_agotado,
                "necesita_reposicion":    necesita_reposicion,
                "porciones_posibles":     porciones_ing,
                "fecha_costo_actualizado": (
                    receta.fecha_costo_actualizado.isoformat()
                    if receta.fecha_costo_actualizado else None
                ),
            })

        costo_total_float = float(costo_total.quantize(Decimal("0.01")))

        return Response({
            "plato_id":             plato_id,
            "costo_total":          costo_total_float,
            "tiene_costos_vacios":  tiene_costos_vacios,
            "porciones_disponibles": porciones_minimas,
            "ingredientes":         ingredientes_detalle,
            "advertencia": (
                "Algunos ingredientes tienen costo_unitario=0 — "
                "el costo total puede estar incompleto. "
                "Recibe una orden de compra para actualizarlos."
                if tiene_costos_vacios else None
            ),
        })

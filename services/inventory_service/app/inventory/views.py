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
    CostoPlatoSerializer,
)
from .events.event_types import InventoryEvents
from .services.rabbitmq import publish_event


# ─────────────────────────────────────────
# Helper — crear movimiento
# ─────────────────────────────────────────

def _crear_movimiento(inv, tipo, cantidad, descripcion, pedido_id=None, orden_id=None, lote=None):
    """Crea un MovimientoInventario y retorna la instancia."""
    cantidad_antes = inv.cantidad_actual

    if tipo in ["SALIDA", "VENCIMIENTO"]:
        inv.cantidad_actual = max(inv.cantidad_actual - cantidad, 0)
    else:
        inv.cantidad_actual += cantidad

    inv.save(update_fields=["cantidad_actual", "fecha_actualizacion"])

    movimiento = MovimientoInventario.objects.create(
        ingrediente_inventario=inv,
        lote=lote,
        tipo_movimiento=tipo,
        cantidad=cantidad,
        cantidad_antes=cantidad_antes,
        cantidad_despues=inv.cantidad_actual,
        pedido_id=pedido_id,
        orden_compra_id=orden_id,
        descripcion=descripcion,
    )

    # Publicar stock actualizado
    publish_event(InventoryEvents.STOCK_ACTUALIZADO, {
        "ingrediente_id":    str(inv.ingrediente_id),
        "almacen_id":        str(inv.almacen_id),
        "restaurante_id":    str(inv.almacen.restaurante_id),
        "cantidad_anterior": str(cantidad_antes),
        "cantidad_nueva":    str(inv.cantidad_actual),
        "unidad_medida":     inv.unidad_medida,
        "tipo_movimiento":   tipo,
    })

    # Generar alerta si es necesario
    _verificar_alertas(inv)

    return movimiento


def _verificar_alertas(inv):
    """Crea AlertaStock si el stock está bajo mínimo o agotado."""
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
# PROVEEDOR
# ─────────────────────────────────────────

class ProveedorViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

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
        if self.action == "list":
            return ProveedorListSerializer
        return ProveedorSerializer


# ─────────────────────────────────────────
# ALMACÉN
# ─────────────────────────────────────────

class AlmacenViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

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
        """
        GET /almacenes/{id}/stock/
        Retorna el stock completo del almacén con estado de cada ingrediente.
        Permite filtrar por bajo_minimo=true para ver solo los críticos.
        """
        almacen = self.get_object()
        qs = almacen.ingredientes.all()
        bajo_minimo = request.query_params.get("bajo_minimo")

        if bajo_minimo and bajo_minimo.lower() == "true":
            qs = qs.filter(cantidad_actual__lte=F("nivel_minimo"))

        return Response(
            IngredienteInventarioListSerializer(qs, many=True).data
        )


# ─────────────────────────────────────────
# INGREDIENTE INVENTARIO (STOCK)
# ─────────────────────────────────────────

class IngredienteInventarioViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = IngredienteInventario.objects.select_related(
            "almacen", "lote_actual"
        ).prefetch_related("movimientos")

        almacen_id = self.request.query_params.get("almacen_id")
        bajo_minimo = self.request.query_params.get("bajo_minimo")
        agotado = self.request.query_params.get("agotado")

        if almacen_id:
            qs = qs.filter(almacen_id=almacen_id)
        if bajo_minimo and bajo_minimo.lower() == "true":
            qs = qs.filter(cantidad_actual__lte=F("nivel_minimo"))
        if agotado and agotado.lower() == "true":
            qs = qs.filter(cantidad_actual=0)

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
        """
        POST /stock/{id}/ajustar/
        Ajuste manual de stock con justificación obligatoria.
        cantidad positiva = entrada, negativa = corrección a la baja.
        Crea MovimientoInventario tipo AJUSTE.
        """
        inv = self.get_object()
        serializer = AjusteStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cantidad = serializer.validated_data["cantidad"]
        descripcion = serializer.validated_data["descripcion"]

        # Validar que no quede negativo
        if inv.cantidad_actual + cantidad < 0:
            return Response(
                {"detail": f"El ajuste dejaría el stock en negativo. Stock actual: {inv.cantidad_actual}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            cantidad_antes = inv.cantidad_actual
            inv.cantidad_actual = inv.cantidad_actual + cantidad
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
                "ingrediente_id":    str(inv.ingrediente_id),
                "almacen_id":        str(inv.almacen_id),
                "restaurante_id":    str(inv.almacen.restaurante_id),
                "cantidad_anterior": str(cantidad_antes),
                "cantidad_nueva":    str(inv.cantidad_actual),
                "unidad_medida":     inv.unidad_medida,
                "tipo_movimiento":   "AJUSTE",
            })

            _verificar_alertas(inv)

        return Response(IngredienteInventarioSerializer(inv).data)

    @action(detail=True, methods=["get"])
    def movimientos(self, request, pk=None):
        """
        GET /stock/{id}/movimientos/
        Historial completo de entradas y salidas del ingrediente.
        """
        inv = self.get_object()
        qs = inv.movimientos.order_by("-fecha")
        return Response(
            MovimientoInventarioSerializer(qs, many=True).data
        )

    @action(detail=False, methods=["get"], url_path="costo-plato")
    def costo_plato(self, request):
        """
        GET /api/inventory/stock/costo-plato/?plato_id={uuid}

        Retorna el costo real de un plato sumando:
        costo_total = Σ (cantidad_ingrediente × costo_unitario)

        Usado para análisis de márgenes:
        margen = precio_venta (de menu_service) - costo_total

        Si algún ingrediente tiene costo_unitario=0 (nunca se ha
        recibido una orden de compra con ese ingrediente), retorna
        una advertencia para que el usuario lo tenga en cuenta.
        """
        from .models import RecetaPlato
        from .serializers import RecetaPlatoSerializer

        plato_id = request.query_params.get("plato_id")

        if not plato_id:
            return Response(
                {"detail": "El parámetro plato_id es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recetas = RecetaPlato.objects.filter(plato_id=plato_id)

        if not recetas.exists():
            return Response(
                {"detail": f"No se encontró receta para el plato {plato_id}."},
                status=status.HTTP_404_NOT_FOUND,
            )

        costo_total = sum(r.costo_ingrediente for r in recetas)
        tiene_costos_vacios = recetas.filter(costo_unitario=0).exists()

        data = {
            "plato_id":            plato_id,
            "costo_total":         round(costo_total, 4),
            "tiene_costos_vacios": tiene_costos_vacios,
            "ingredientes":        RecetaPlatoSerializer(recetas, many=True).data,
            "advertencia": (
                "Algunos ingredientes tienen costo_unitario=0. "
                "El costo total puede estar incompleto."
                if tiene_costos_vacios else None
            ),
        }

        return Response(data)

# ─────────────────────────────────────────
# LOTE INGREDIENTE
# ─────────────────────────────────────────


class LoteIngredienteViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = LoteIngrediente.objects.select_related("almacen", "proveedor")
        estado = self.request.query_params.get("estado")
        almacen_id = self.request.query_params.get("almacen_id")
        por_vencer = self.request.query_params.get("por_vencer")  # días

        if estado:
            qs = qs.filter(estado=estado)
        if almacen_id:
            qs = qs.filter(almacen_id=almacen_id)
        if por_vencer:
            try:
                dias = int(por_vencer)
                limite = timezone.now().date() + timezone.timedelta(days=dias)
                qs = qs.filter(
                    fecha_vencimiento__lte=limite,
                    estado="ACTIVO"
                )
            except ValueError:
                pass

        return qs.order_by("fecha_vencimiento")

    def get_serializer_class(self):
        if self.action == "list":
            return LoteListSerializer
        if self.action == "create":
            return LoteIngredienteWriteSerializer
        return LoteIngredienteSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Al crear un lote aumenta automáticamente el stock
        del IngredienteInventario correspondiente en el almacén.
        """
        lote = serializer.save()

        # Buscar o crear IngredienteInventario
        inv, created = IngredienteInventario.objects.get_or_create(
            ingrediente_id=lote.ingrediente_id,
            almacen=lote.almacen,
            defaults={
                "nombre_ingrediente": f"Ingrediente {lote.ingrediente_id}",
                "unidad_medida":      lote.unidad_medida,
                "cantidad_actual":    0,
                "nivel_minimo":       0,
                "nivel_maximo":       0,
            }
        )

        # Crear movimiento ENTRADA y actualizar stock
        _crear_movimiento(
            inv=inv,
            tipo="ENTRADA",
            cantidad=lote.cantidad_recibida,
            descripcion=f"Recepción lote {lote.numero_lote}.",
            lote=lote,
        )

        # Actualizar lote_actual si no tiene uno
        if not inv.lote_actual:
            inv.lote_actual = lote
            inv.save(update_fields=["lote_actual"])

    @action(detail=True, methods=["post"])
    def retirar(self, request, pk=None):
        """
        POST /lotes/{id}/retirar/
        Marca el lote como RETIRADO. Descuenta la cantidad
        restante del stock como movimiento VENCIMIENTO.
        """
        lote = self.get_object()

        if lote.estado in ["RETIRADO", "AGOTADO"]:
            return Response(
                {"detail": f"El lote ya está en estado '{lote.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Descontar cantidad restante del stock
            try:
                inv = IngredienteInventario.objects.select_for_update().get(
                    ingrediente_id=lote.ingrediente_id,
                    almacen=lote.almacen,
                )
                if lote.cantidad_actual > 0:
                    _crear_movimiento(
                        inv=inv,
                        tipo="VENCIMIENTO",
                        cantidad=lote.cantidad_actual,
                        descripcion=f"Retiro de lote {lote.numero_lote}.",
                        lote=lote,
                    )
            except IngredienteInventario.DoesNotExist:
                pass

            lote.estado = "RETIRADO"
            lote.cantidad_actual = 0
            lote.save(update_fields=["estado", "cantidad_actual"])

            publish_event(InventoryEvents.LOTE_VENCIDO, {
                "lote_id":           str(lote.id),
                "ingrediente_id":    str(lote.ingrediente_id),
                "almacen_id":        str(lote.almacen_id),
                "restaurante_id":    str(lote.almacen.restaurante_id),
                "numero_lote":       lote.numero_lote,
                "cantidad_actual":   "0",
                "fecha_vencimiento": str(lote.fecha_vencimiento),
            })

        return Response(LoteIngredienteSerializer(lote).data)


# ─────────────────────────────────────────
# ORDEN COMPRA
# ─────────────────────────────────────────

class OrdenCompraViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = OrdenCompra.objects.select_related(
            "proveedor").prefetch_related("detalles")
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
        """
        POST /ordenes-compra/{id}/enviar/
        BORRADOR → ENVIADA
        Dispara: orden_compra.enviada
        """
        orden = self.get_object()

        if orden.estado not in ["BORRADOR", "PENDIENTE"]:
            return Response(
                {"detail": f"No se puede enviar una orden en estado '{orden.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orden.estado = "ENVIADA"
        orden.save(update_fields=["estado"])    # dispara orden_compra.enviada

        return Response(OrdenCompraSerializer(orden).data)

    @action(detail=True, methods=["post"])
    def recibir(self, request, pk=None):
        """
        POST /ordenes-compra/{id}/recibir/
        ENVIADA → RECIBIDA
        Por cada detalle: crea LoteIngrediente + aumenta stock.
        Dispara: orden_compra.recibida + lote.recibido por cada lote.
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
            for recepcion in detalles_recepcion:
                try:
                    detalle = DetalleOrdenCompra.objects.get(
                        id=recepcion["detalle_id"],
                        orden=orden,
                    )
                except DetalleOrdenCompra.DoesNotExist:
                    return Response(
                        {"detail": f"Detalle {recepcion['detalle_id']} no pertenece a esta orden."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Actualizar cantidad recibida en el detalle
                detalle.cantidad_recibida = recepcion["cantidad_recibida"]
                detalle.save(update_fields=["cantidad_recibida"])

                if recepcion["cantidad_recibida"] == 0:
                    continue

                # Obtener almacén principal del restaurante
                almacen = Almacen.objects.filter(
                    restaurante_id=orden.restaurante_id,
                    activo=True,
                ).first()

                if not almacen:
                    return Response(
                        {"detail": f"No hay almacén activo para restaurante {orden.restaurante_id}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Crear lote para trazabilidad
                lote = LoteIngrediente.objects.create(
                    ingrediente_id=detalle.ingrediente_id,
                    almacen=almacen,
                    proveedor=orden.proveedor,
                    numero_lote=recepcion["numero_lote"],
                    fecha_produccion=recepcion.get("fecha_produccion"),
                    fecha_vencimiento=recepcion["fecha_vencimiento"],
                    cantidad_recibida=recepcion["cantidad_recibida"],
                    cantidad_actual=recepcion["cantidad_recibida"],
                    unidad_medida=detalle.unidad_medida,
                )

                # Aumentar stock
                inv, _ = IngredienteInventario.objects.get_or_create(
                    ingrediente_id=detalle.ingrediente_id,
                    almacen=almacen,
                    defaults={
                        "nombre_ingrediente": detalle.nombre_ingrediente,
                        "unidad_medida":      detalle.unidad_medida,
                        "cantidad_actual":    0,
                        "nivel_minimo":       0,
                        "nivel_maximo":       0,
                    }
                )

                _crear_movimiento(
                    inv=inv,
                    tipo="ENTRADA",
                    cantidad=lote.cantidad_recibida,
                    descripcion=f"Recepción orden {orden.id} — lote {lote.numero_lote}.",
                    orden_id=orden.id,
                    lote=lote,
                )

            # Marcar orden como recibida
            orden.estado = "RECIBIDA"
            orden.fecha_recepcion = timezone.now()
            # dispara orden_compra.recibida
            orden.save(update_fields=["estado", "fecha_recepcion"])

        return Response(OrdenCompraSerializer(orden).data)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        """
        POST /ordenes-compra/{id}/cancelar/
        → CANCELADA. No se puede cancelar si ya fue RECIBIDA.
        Dispara: orden_compra.cancelada
        """
        orden = self.get_object()

        if orden.estado in ["RECIBIDA", "CANCELADA"]:
            return Response(
                {"detail": f"No se puede cancelar una orden en estado '{orden.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orden.estado = "CANCELADA"
        # dispara orden_compra.cancelada
        orden.save(update_fields=["estado"])

        return Response(OrdenCompraSerializer(orden).data)


# ─────────────────────────────────────────
# ALERTA STOCK
# ─────────────────────────────────────────

class AlertaStockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo lectura — las alertas se crean automáticamente.
    Las acciones resolver e ignorar son las únicas escrituras permitidas.
    """
    serializer_class = AlertaStockSerializer

    def get_queryset(self):
        qs = AlertaStock.objects.select_related(
            "ingrediente_inventario", "almacen", "lote"
        )
        tipo = self.request.query_params.get("tipo")
        estado = self.request.query_params.get("estado")
        restaurante_id = self.request.query_params.get("restaurante_id")

        if tipo:
            qs = qs.filter(tipo_alerta=tipo)
        if estado:
            qs = qs.filter(estado=estado)
        if restaurante_id:
            qs = qs.filter(restaurante_id=restaurante_id)

        return qs.order_by("-fecha_alerta")

    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        """
        POST /alertas/{id}/resolver/
        Marca la alerta como RESUELTA y registra fecha_resolucion.
        """
        alerta = self.get_object()

        if alerta.estado != "PENDIENTE":
            return Response(
                {"detail": f"La alerta ya está en estado '{alerta.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        alerta.resolver()
        return Response(AlertaStockSerializer(alerta).data)

    @action(detail=True, methods=["post"])
    def ignorar(self, request, pk=None):
        """
        POST /alertas/{id}/ignorar/
        Marca la alerta como IGNORADA.
        """
        alerta = self.get_object()

        if alerta.estado != "PENDIENTE":
            return Response(
                {"detail": f"La alerta ya está en estado '{alerta.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        alerta.estado = "IGNORADA"
        alerta.save(update_fields=["estado"])
        return Response(AlertaStockSerializer(alerta).data)

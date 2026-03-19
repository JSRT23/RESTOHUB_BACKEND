from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Pedido,  ComandaCocina, SeguimientoPedido, EntregaPedido
from .serializers import (
    PedidoSerializer,
    PedidoListSerializer,
    PedidoWriteSerializer,
    PedidoCambioEstadoSerializer,
    DetallePedidoSerializer,
    DetallePedidoWriteSerializer,
    ComandaCocinaSerializer,
    ComandaCocinaWriteSerializer,
    SeguimientoPedidoSerializer,
    EntregaPedidoSerializer,
    EntregaPedidoWriteSerializer,
)


# ─────────────────────────────────────────
# Helper — registrar seguimiento
# ─────────────────────────────────────────

def _registrar_seguimiento(pedido, estado, descripcion=""):
    """
    Crea un registro de seguimiento append-only.
    Se llama en cada cambio de estado del pedido.
    """
    SeguimientoPedido.objects.create(
        pedido=pedido,
        estado=estado,
        descripcion=descripcion or f"Pedido pasado a {estado}.",
    )


# ─────────────────────────────────────────
# PEDIDO
# ─────────────────────────────────────────

class PedidoViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Pedido.objects.prefetch_related(
            "detalles",
            "comandas",
            "seguimientos",
            "entrega",
        )
        # Filtros opcionales por query params
        estado = self.request.query_params.get("estado")
        canal = self.request.query_params.get("canal")
        restaurante = self.request.query_params.get("restaurante_id")
        cliente = self.request.query_params.get("cliente_id")

        if estado:
            qs = qs.filter(estado=estado)
        if canal:
            qs = qs.filter(canal=canal)
        if restaurante:
            qs = qs.filter(restaurante_id=restaurante)
        if cliente:
            qs = qs.filter(cliente_id=cliente)

        return qs.order_by("-fecha_creacion")

    def get_serializer_class(self):
        if self.action == "list":
            return PedidoListSerializer
        if self.action == "create":
            return PedidoWriteSerializer
        if self.action in ("confirmar", "cancelar", "marcar_listo", "entregar"):
            return PedidoCambioEstadoSerializer
        return PedidoSerializer

    # ── Acción: confirmar ──
    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        """
        RECIBIDO → EN_PREPARACION
        Dispara: pedido.confirmado + pedido.estado_actualizado
        inventory_service descuenta stock al recibir pedido.confirmado.
        """
        pedido = self.get_object()

        if pedido.estado != "RECIBIDO":
            return Response(
                {"detail": f"No se puede confirmar un pedido en estado '{pedido.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PedidoCambioEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        descripcion = serializer.validated_data.get("descripcion", "")

        pedido.estado = "EN_PREPARACION"
        # dispara pedido.confirmado + estado_actualizado
        pedido.save(update_fields=["estado"])

        _registrar_seguimiento(pedido, "EN_PREPARACION", descripcion)

        return Response(PedidoSerializer(pedido).data)

    # ── Acción: cancelar ──
    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        """
        Cualquier estado cancelable → CANCELADO
        Dispara: pedido.cancelado
        inventory_service revierte stock. loyalty_service anula puntos.
        """
        pedido = self.get_object()

        if pedido.estado in ["ENTREGADO", "CANCELADO"]:
            return Response(
                {"detail": f"No se puede cancelar un pedido en estado '{pedido.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PedidoCambioEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        descripcion = serializer.validated_data.get(
            "descripcion", "Pedido cancelado.")

        pedido.estado = "CANCELADO"
        pedido.save(update_fields=["estado"])   # dispara pedido.cancelado

        _registrar_seguimiento(pedido, "CANCELADO", descripcion)

        return Response(PedidoSerializer(pedido).data)

    # ── Acción: marcar_listo ──
    @action(detail=True, methods=["post"])
    def marcar_listo(self, request, pk=None):
        """
        EN_PREPARACION → LISTO
        Se activa cuando todas las comandas de cocina están listas.
        Dispara: pedido.estado_actualizado
        """
        pedido = self.get_object()

        if pedido.estado != "EN_PREPARACION":
            return Response(
                {"detail": f"El pedido debe estar EN_PREPARACION para marcarlo como listo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PedidoCambioEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        descripcion = serializer.validated_data.get("descripcion", "")

        pedido.estado = "LISTO"
        # dispara pedido.estado_actualizado
        pedido.save(update_fields=["estado"])

        _registrar_seguimiento(pedido, "LISTO", descripcion)

        return Response(PedidoSerializer(pedido).data)

    # ── Acción: entregar ──
    @action(detail=True, methods=["post"])
    def entregar(self, request, pk=None):
        """
        LISTO | EN_CAMINO → ENTREGADO
        Dispara: pedido.entregado
        loyalty_service acumula puntos. staff_service cierra operación.
        """
        pedido = self.get_object()

        if pedido.estado not in ["LISTO", "EN_CAMINO"]:
            return Response(
                {"detail": f"El pedido debe estar LISTO o EN_CAMINO para entregarlo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PedidoCambioEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        descripcion = serializer.validated_data.get("descripcion", "")

        pedido.estado = "ENTREGADO"
        pedido.save(update_fields=["estado"])   # dispara pedido.entregado

        _registrar_seguimiento(pedido, "ENTREGADO", descripcion)

        return Response(PedidoSerializer(pedido).data)

    # ── Acción: seguimiento ──
    @action(detail=True, methods=["get"])
    def seguimiento(self, request, pk=None):
        """
        GET /pedidos/{id}/seguimiento/
        Retorna el historial completo de estados del pedido en orden cronológico.
        """
        pedido = self.get_object()
        qs = pedido.seguimientos.order_by("fecha")
        return Response(SeguimientoPedidoSerializer(qs, many=True).data)

    # ── Acción: detalles ──
    @action(detail=True, methods=["get", "post"])
    def detalles(self, request, pk=None):
        """
        GET  /pedidos/{id}/detalles/ — lista ítems del pedido
        POST /pedidos/{id}/detalles/ — agrega un ítem (solo si RECIBIDO)
        """
        pedido = self.get_object()

        if request.method == "GET":
            qs = pedido.detalles.all()
            return Response(DetallePedidoSerializer(qs, many=True).data)

        # POST — solo permitido si el pedido está en RECIBIDO
        if pedido.estado != "RECIBIDO":
            return Response(
                {"detail": "Solo se pueden agregar ítems a pedidos en estado RECIBIDO."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DetallePedidoWriteSerializer(data=request.data)
        if serializer.is_valid():
            detalle = serializer.save(pedido=pedido)

            # Recalcular total del pedido
            total = sum(d.subtotal for d in pedido.detalles.all())
            pedido.total = total
            pedido.save(update_fields=["total"])

            return Response(
                DetallePedidoSerializer(detalle).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────
# COMANDA COCINA
# ─────────────────────────────────────────

class ComandaCocinaViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = ComandaCocina.objects.select_related("pedido")
        estado = self.request.query_params.get("estado")
        estacion = self.request.query_params.get("estacion")
        pedido = self.request.query_params.get("pedido_id")

        if estado:
            qs = qs.filter(estado=estado)
        if estacion:
            qs = qs.filter(estacion=estacion)
        if pedido:
            qs = qs.filter(pedido_id=pedido)

        return qs.order_by("-hora_envio")

    def get_serializer_class(self):
        if self.action == "create":
            return ComandaCocinaWriteSerializer
        return ComandaCocinaSerializer

    @action(detail=True, methods=["post"])
    def iniciar(self, request, pk=None):
        """
        PENDIENTE → PREPARANDO
        El cocinero empieza a preparar la comanda.
        """
        comanda = self.get_object()

        if comanda.estado != "PENDIENTE":
            return Response(
                {"detail": "La comanda ya fue iniciada o completada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comanda.estado = "PREPARANDO"
        comanda.save(update_fields=["estado"])

        return Response(ComandaCocinaSerializer(comanda).data)

    @action(detail=True, methods=["post"])
    def lista(self, request, pk=None):
        """
        PREPARANDO → LISTO
        Registra hora_fin para calcular SLA de cocina.
        Dispara: comanda.lista → staff_service mide tiempos.
        """
        comanda = self.get_object()

        if comanda.estado != "PREPARANDO":
            return Response(
                {"detail": "La comanda debe estar en PREPARANDO para marcarla como lista."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comanda.estado = "LISTO"
        comanda.hora_fin = timezone.now()
        # dispara comanda.lista
        comanda.save(update_fields=["estado", "hora_fin"])

        return Response(ComandaCocinaSerializer(comanda).data)


# ─────────────────────────────────────────
# ENTREGA PEDIDO
# ─────────────────────────────────────────

class EntregaPedidoViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = EntregaPedido.objects.select_related("pedido")
        estado = self.request.query_params.get("estado_entrega")
        tipo = self.request.query_params.get("tipo_entrega")

        if estado:
            qs = qs.filter(estado_entrega=estado)
        if tipo:
            qs = qs.filter(tipo_entrega=tipo)

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return EntregaPedidoWriteSerializer
        return EntregaPedidoSerializer

    @action(detail=True, methods=["post"])
    def en_camino(self, request, pk=None):
        """
        PENDIENTE → EN_CAMINO
        Registra fecha_salida del repartidor.
        """
        entrega = self.get_object()

        if entrega.estado_entrega != "PENDIENTE":
            return Response(
                {"detail": "La entrega ya fue iniciada o completada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entrega.estado_entrega = "EN_CAMINO"
        entrega.fecha_salida = timezone.now()
        entrega.save(update_fields=["estado_entrega", "fecha_salida"])

        # Actualizar estado del pedido
        pedido = entrega.pedido
        if pedido.estado == "LISTO":
            pedido.estado = "EN_CAMINO"
            pedido.save(update_fields=["estado"])
            _registrar_seguimiento(pedido, "EN_CAMINO",
                                   "Repartidor en camino.")

        return Response(EntregaPedidoSerializer(entrega).data)

    @action(detail=True, methods=["post"])
    def completar(self, request, pk=None):
        """
        EN_CAMINO → ENTREGADO
        Registra fecha_entrega_real.
        Dispara: entrega.completada → loyalty acumula puntos.
        """
        entrega = self.get_object()

        if entrega.estado_entrega != "EN_CAMINO":
            return Response(
                {"detail": "La entrega debe estar EN_CAMINO para completarla."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entrega.estado_entrega = "ENTREGADO"
        entrega.fecha_entrega_real = timezone.now()
        # dispara entrega.completada
        entrega.save(update_fields=["estado_entrega", "fecha_entrega_real"])

        # Actualizar estado del pedido
        pedido = entrega.pedido
        pedido.estado = "ENTREGADO"
        pedido.save(update_fields=["estado"])
        _registrar_seguimiento(pedido, "ENTREGADO", "Entrega completada.")

        return Response(EntregaPedidoSerializer(entrega).data)

    @action(detail=True, methods=["post"])
    def fallo(self, request, pk=None):
        """
        EN_CAMINO → FALLIDO
        Dispara: entrega.fallida → notificaciones avisa al cliente.
        """
        entrega = self.get_object()

        if entrega.estado_entrega != "EN_CAMINO":
            return Response(
                {"detail": "La entrega debe estar EN_CAMINO para marcarla como fallida."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entrega.estado_entrega = "FALLIDO"
        # dispara entrega.fallida
        entrega.save(update_fields=["estado_entrega"])

        return Response(EntregaPedidoSerializer(entrega).data)

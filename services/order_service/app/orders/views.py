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


def _registrar_seguimiento(pedido, estado, descripcion=""):
    SeguimientoPedido.objects.create(
        pedido=pedido,
        estado=estado,
        descripcion=descripcion or f"Pedido pasado a {estado}.",
    )


class PedidoViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Pedido.objects.prefetch_related(
            "detalles", "comandas", "seguimientos", "entrega",
        )
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

    # ── FIX: create devuelve PedidoSerializer (con id, estado, detalles) ──
    def create(self, request, *args, **kwargs):
        serializer = PedidoWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pedido = serializer.save()
        return Response(
            PedidoSerializer(pedido).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
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
        pedido.save(update_fields=["estado"])
        _registrar_seguimiento(pedido, "EN_PREPARACION", descripcion)
        return Response(PedidoSerializer(pedido).data)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
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
        pedido.save(update_fields=["estado"])
        _registrar_seguimiento(pedido, "CANCELADO", descripcion)
        return Response(PedidoSerializer(pedido).data)

    @action(detail=True, methods=["post"])
    def marcar_listo(self, request, pk=None):
        pedido = self.get_object()
        if pedido.estado != "EN_PREPARACION":
            return Response(
                {"detail": "El pedido debe estar EN_PREPARACION para marcarlo como listo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = PedidoCambioEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        descripcion = serializer.validated_data.get("descripcion", "")
        pedido.estado = "LISTO"
        pedido.save(update_fields=["estado"])
        _registrar_seguimiento(pedido, "LISTO", descripcion)
        return Response(PedidoSerializer(pedido).data)

    @action(detail=True, methods=["post"])
    def entregar(self, request, pk=None):
        pedido = self.get_object()
        if pedido.estado not in ["LISTO", "EN_CAMINO"]:
            return Response(
                {"detail": "El pedido debe estar LISTO o EN_CAMINO para entregarlo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = PedidoCambioEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        descripcion = serializer.validated_data.get("descripcion", "")
        metodo_pago = serializer.validated_data.get("metodo_pago")
        pedido.estado = "ENTREGADO"
        update_fields = ["estado"]
        if metodo_pago:
            pedido.metodo_pago = metodo_pago
            update_fields.append("metodo_pago")
        pedido.save(update_fields=update_fields)
        _registrar_seguimiento(pedido, "ENTREGADO", descripcion)
        return Response(PedidoSerializer(pedido).data)

    @action(detail=True, methods=["get"])
    def seguimiento(self, request, pk=None):
        pedido = self.get_object()
        qs = pedido.seguimientos.order_by("fecha")
        return Response(SeguimientoPedidoSerializer(qs, many=True).data)

    @action(detail=True, methods=["get", "post"])
    def detalles(self, request, pk=None):
        pedido = self.get_object()
        if request.method == "GET":
            qs = pedido.detalles.all()
            return Response(DetallePedidoSerializer(qs, many=True).data)

        if pedido.estado != "RECIBIDO":
            return Response(
                {"detail": "Solo se pueden agregar ítems a pedidos en estado RECIBIDO."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = DetallePedidoWriteSerializer(data=request.data)
        if serializer.is_valid():
            detalle = serializer.save(pedido=pedido)
            total = sum(d.subtotal for d in pedido.detalles.all())
            pedido.total = total
            pedido.save(update_fields=["total"])
            return Response(
                DetallePedidoSerializer(detalle).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        comanda = self.get_object()
        if comanda.estado != "PREPARANDO":
            return Response(
                {"detail": "La comanda debe estar en PREPARANDO para marcarla como lista."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        comanda.estado = "LISTO"
        comanda.hora_fin = timezone.now()
        comanda.save(update_fields=["estado", "hora_fin"])
        return Response(ComandaCocinaSerializer(comanda).data)


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
        entrega = self.get_object()
        if entrega.estado_entrega != "PENDIENTE":
            return Response(
                {"detail": "La entrega ya fue iniciada o completada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entrega.estado_entrega = "EN_CAMINO"
        entrega.fecha_salida = timezone.now()
        entrega.save(update_fields=["estado_entrega", "fecha_salida"])
        pedido = entrega.pedido
        if pedido.estado == "LISTO":
            pedido.estado = "EN_CAMINO"
            pedido.save(update_fields=["estado"])
            _registrar_seguimiento(pedido, "EN_CAMINO",
                                   "Repartidor en camino.")
        return Response(EntregaPedidoSerializer(entrega).data)

    @action(detail=True, methods=["post"])
    def completar(self, request, pk=None):
        entrega = self.get_object()
        if entrega.estado_entrega != "EN_CAMINO":
            return Response(
                {"detail": "La entrega debe estar EN_CAMINO para completarla."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entrega.estado_entrega = "ENTREGADO"
        entrega.fecha_entrega_real = timezone.now()
        entrega.save(update_fields=["estado_entrega", "fecha_entrega_real"])
        pedido = entrega.pedido
        pedido.estado = "ENTREGADO"
        pedido.save(update_fields=["estado"])
        _registrar_seguimiento(pedido, "ENTREGADO", "Entrega completada.")
        return Response(EntregaPedidoSerializer(entrega).data)

    @action(detail=True, methods=["post"])
    def fallo(self, request, pk=None):
        entrega = self.get_object()
        if entrega.estado_entrega != "EN_CAMINO":
            return Response(
                {"detail": "La entrega debe estar EN_CAMINO para marcarla como fallida."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entrega.estado_entrega = "FALLIDO"
        entrega.save(update_fields=["estado_entrega"])
        return Response(EntregaPedidoSerializer(entrega).data)

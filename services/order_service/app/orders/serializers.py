from rest_framework import serializers
from django.utils import timezone
from .models import Pedido, DetallePedido, ComandaCocina, SeguimientoPedido, EntregaPedido


# ─────────────────────────────────────────
# DETALLE PEDIDO
# ─────────────────────────────────────────

class DetallePedidoSerializer(serializers.ModelSerializer):
    """Lectura — incluye todos los campos del snapshot."""
    class Meta:
        model = DetallePedido
        fields = (
            "id", "plato_id", "nombre_plato",
            "precio_unitario", "cantidad", "subtotal", "notas",
        )
        read_only_fields = ("id", "subtotal")


class DetallePedidoWriteSerializer(serializers.ModelSerializer):
    """
    Escritura — el frontend envía plato_id, nombre_plato y precio_unitario
    como snapshot. El subtotal se calcula automáticamente en el save().
    """
    class Meta:
        model = DetallePedido
        fields = ("plato_id", "nombre_plato",
                  "precio_unitario", "cantidad", "notas")

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "La cantidad debe ser mayor a 0.")
        return value

    def validate_precio_unitario(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0.")
        return value


# ─────────────────────────────────────────
# SEGUIMIENTO PEDIDO
# ─────────────────────────────────────────

class SeguimientoPedidoSerializer(serializers.ModelSerializer):
    """Solo lectura — el seguimiento es append-only generado por signals."""
    class Meta:
        model = SeguimientoPedido
        fields = ("id", "estado", "fecha", "descripcion")
        read_only_fields = ("id", "estado", "fecha")


# ─────────────────────────────────────────
# COMANDA COCINA
# ─────────────────────────────────────────

class ComandaCocinaSerializer(serializers.ModelSerializer):
    tiempo_preparacion_segundos = serializers.FloatField(read_only=True)

    class Meta:
        model = ComandaCocina
        fields = (
            "id", "pedido", "estacion", "estado",
            "hora_envio", "hora_fin", "tiempo_preparacion_segundos",
        )
        read_only_fields = ("id", "hora_envio", "tiempo_preparacion_segundos")


class ComandaCocinaWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComandaCocina
        fields = ("pedido", "estacion")

    def validate_pedido(self, value):
        if value.estado not in ["RECIBIDO", "EN_PREPARACION"]:
            raise serializers.ValidationError(
                "Solo se puede crear una comanda para pedidos en RECIBIDO o EN_PREPARACION."
            )
        return value


# ─────────────────────────────────────────
# ENTREGA PEDIDO
# ─────────────────────────────────────────

class EntregaPedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntregaPedido
        fields = (
            "id", "pedido", "tipo_entrega", "direccion",
            "repartidor_id", "repartidor_nombre",
            "estado_entrega", "fecha_salida", "fecha_entrega_real",
        )
        read_only_fields = ("id", "fecha_salida", "fecha_entrega_real")

    def validate(self, attrs):
        tipo = attrs.get("tipo_entrega")
        direccion = attrs.get("direccion")
        if tipo == "DELIVERY" and not direccion:
            raise serializers.ValidationError(
                {"direccion": "La dirección es obligatoria para entregas a domicilio."}
            )
        return attrs


class EntregaPedidoWriteSerializer(serializers.ModelSerializer):
    """Para crear una entrega asociada a un pedido."""
    class Meta:
        model = EntregaPedido
        fields = (
            "pedido", "tipo_entrega", "direccion",
            "repartidor_id", "repartidor_nombre",
        )

    def validate_pedido(self, value):
        if hasattr(value, "entrega"):
            raise serializers.ValidationError(
                "Este pedido ya tiene una entrega asignada."
            )
        return value

    def validate(self, attrs):
        tipo = attrs.get("tipo_entrega")
        direccion = attrs.get("direccion")
        if tipo == "DELIVERY" and not direccion:
            raise serializers.ValidationError(
                {"direccion": "La dirección es obligatoria para delivery."}
            )
        return attrs


# ─────────────────────────────────────────
# PEDIDO
# ─────────────────────────────────────────

class PedidoSerializer(serializers.ModelSerializer):
    """
    Lectura completa — incluye detalles, comandas, seguimientos y entrega.
    Usado en GET /pedidos/{id}/
    """
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    comandas = ComandaCocinaSerializer(many=True, read_only=True)
    seguimientos = SeguimientoPedidoSerializer(many=True, read_only=True)
    entrega = EntregaPedidoSerializer(read_only=True)

    class Meta:
        model = Pedido
        fields = (
            "id", "restaurante_id", "cliente_id",
            "canal", "estado", "prioridad",
            "total", "moneda", "mesa_id",
            "fecha_creacion", "fecha_entrega_estimada",
            "detalles", "comandas", "seguimientos", "entrega",
        )
        read_only_fields = ("id", "fecha_creacion")


class PedidoListSerializer(serializers.ModelSerializer):
    """
    Lectura ligera — para listar pedidos sin anidar relaciones.
    Usado en GET /pedidos/
    """
    class Meta:
        model = Pedido
        fields = (
            "id", "restaurante_id", "cliente_id",
            "canal", "estado", "prioridad",
            "total", "moneda", "fecha_creacion",
        )
        read_only_fields = ("id", "fecha_creacion")


class PedidoWriteSerializer(serializers.ModelSerializer):
    """
    Creación de pedido — recibe los detalles anidados.
    El total se calcula sumando los subtotales de los detalles.
    Crea el pedido y sus ítems en una sola llamada atómica.
    """
    detalles = DetallePedidoWriteSerializer(many=True)

    class Meta:
        model = Pedido
        fields = (
            "restaurante_id", "cliente_id", "canal",
            "prioridad", "moneda", "mesa_id",
            "fecha_entrega_estimada", "detalles",
        )

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError(
                "El pedido debe tener al menos un ítem.")
        return value

    def create(self, validated_data):
        detalles_data = validated_data.pop("detalles")

        # Calcular total sumando subtotales
        total = sum(
            d["precio_unitario"] * d["cantidad"]
            for d in detalles_data
        )

        # Crear el pedido
        pedido = Pedido.objects.create(
            **validated_data,
            total=total,
            estado="RECIBIDO",
        )

        # Crear detalles — cada uno dispara su signal
        for detalle_data in detalles_data:
            DetallePedido.objects.create(pedido=pedido, **detalle_data)

        # Crear seguimiento inicial
        SeguimientoPedido.objects.create(
            pedido=pedido,
            estado="RECIBIDO",
            descripcion="Pedido recibido.",
        )

        return pedido


class PedidoCambioEstadoSerializer(serializers.Serializer):
    """
    Serializer genérico para acciones de cambio de estado.
    Se usa en confirmar, cancelar, marcar_listo, entregar.
    """
    descripcion = serializers.CharField(required=False, allow_blank=True)

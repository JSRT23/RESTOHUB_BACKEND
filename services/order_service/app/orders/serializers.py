from rest_framework import serializers
from django.utils import timezone
from .models import Pedido, DetallePedido, ComandaCocina, SeguimientoPedido, EntregaPedido


class DetallePedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = ("id", "plato_id", "nombre_plato",
                  "precio_unitario", "cantidad", "subtotal", "notas")
        read_only_fields = ("id", "subtotal")


class DetallePedidoWriteSerializer(serializers.ModelSerializer):
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


class SeguimientoPedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeguimientoPedido
        fields = ("id", "estado", "fecha", "descripcion")
        read_only_fields = ("id", "estado", "fecha")


class ComandaCocinaSerializer(serializers.ModelSerializer):
    tiempo_preparacion_segundos = serializers.FloatField(read_only=True)
    numero_dia = serializers.SerializerMethodField()

    class Meta:
        model = ComandaCocina
        fields = ("id", "pedido", "estacion", "estado", "hora_envio", "hora_fin",
                  "tiempo_preparacion_segundos", "numero_dia")
        read_only_fields = ("id", "hora_envio", "tiempo_preparacion_segundos")

    def get_numero_dia(self, obj):
        return obj.pedido.numero_dia if obj.pedido_id else None


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


class EntregaPedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntregaPedido
        fields = ("id", "pedido", "tipo_entrega", "direccion", "repartidor_id", "repartidor_nombre",
                  "estado_entrega", "fecha_salida", "fecha_entrega_real")
        read_only_fields = ("id", "fecha_salida", "fecha_entrega_real")

    def validate(self, attrs):
        if attrs.get("tipo_entrega") == "DELIVERY" and not attrs.get("direccion"):
            raise serializers.ValidationError(
                {"direccion": "La dirección es obligatoria para entregas a domicilio."})
        return attrs


class EntregaPedidoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntregaPedido
        fields = ("pedido", "tipo_entrega", "direccion",
                  "repartidor_id", "repartidor_nombre")

    def validate_pedido(self, value):
        if hasattr(value, "entrega"):
            raise serializers.ValidationError(
                "Este pedido ya tiene una entrega asignada.")
        return value

    def validate(self, attrs):
        if attrs.get("tipo_entrega") == "DELIVERY" and not attrs.get("direccion"):
            raise serializers.ValidationError(
                {"direccion": "La dirección es obligatoria para delivery."})
        return attrs


class PedidoSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    comandas = ComandaCocinaSerializer(many=True, read_only=True)
    seguimientos = SeguimientoPedidoSerializer(many=True, read_only=True)
    entrega = EntregaPedidoSerializer(read_only=True)

    class Meta:
        model = Pedido
        fields = (
            "id", "restaurante_id", "cliente_id",
            "canal", "estado", "prioridad",
            "total", "moneda", "mesa_id", "metodo_pago", "numero_dia",
            "fecha_creacion", "fecha_entrega_estimada",
            "detalles", "comandas", "seguimientos", "entrega",
        )
        read_only_fields = ("id", "fecha_creacion")


class PedidoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedido
        fields = (
            "id", "restaurante_id", "cliente_id",
            "canal", "estado", "prioridad",
            "total", "moneda", "metodo_pago", "numero_dia", "fecha_creacion",
        )
        read_only_fields = ("id", "fecha_creacion")


class PedidoWriteSerializer(serializers.ModelSerializer):
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
        total = sum(d["precio_unitario"] * d["cantidad"]
                    for d in detalles_data)
        from django.utils import timezone
        from django.db.models import Max
        hoy = timezone.now().date()
        maximo = Pedido.objects.filter(
            restaurante_id=validated_data.get("restaurante_id"),
            fecha_creacion__date=hoy,
        ).aggregate(m=Max("numero_dia"))["m"]
        numero_dia = (maximo or 0) + 1

        pedido = Pedido.objects.create(
            **validated_data, total=total, estado="RECIBIDO", numero_dia=numero_dia)
        for detalle_data in detalles_data:
            DetallePedido.objects.create(pedido=pedido, **detalle_data)
        SeguimientoPedido.objects.create(
            pedido=pedido, estado="RECIBIDO", descripcion="Pedido recibido.")
        return pedido


class PedidoCambioEstadoSerializer(serializers.Serializer):
    descripcion = serializers.CharField(required=False, allow_blank=True)
    metodo_pago = serializers.CharField(
        required=False, allow_blank=True, allow_null=True)

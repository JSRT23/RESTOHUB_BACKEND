from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from .models import (
    Proveedor, Almacen, RecetaPlato,
    IngredienteInventario, LoteIngrediente,
    MovimientoInventario, OrdenCompra,
    DetalleOrdenCompra, AlertaStock,
)


# ─────────────────────────────────────────
# PROVEEDOR
# ─────────────────────────────────────────

class ProveedorSerializer(serializers.ModelSerializer):
    """
    Serializer completo — incluye todos los campos de alcance (Opción B).
    Usado para crear, editar y obtener detalle de un proveedor.
    """
    class Meta:
        model = Proveedor
        fields = (
            "id",
            "nombre",
            "pais",
            "ciudad",
            "telefono",
            "email",
            "moneda_preferida",
            "activo",
            # Campos de alcance (Opción B)
            "alcance",
            "pais_destino",
            "ciudad_destino",
            "creado_por_restaurante_id",
            "fecha_creacion",
            "fecha_actualizacion",
        )
        read_only_fields = ("id", "fecha_creacion", "fecha_actualizacion")

    def validate_nombre(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "El nombre no puede estar vacío.")
        return value.strip()

    def validate(self, attrs):
        alcance = attrs.get("alcance", getattr(
            self.instance, "alcance", "GLOBAL"))
        pais_destino = attrs.get("pais_destino", getattr(
            self.instance, "pais_destino", None))
        ciudad_destino = attrs.get("ciudad_destino", getattr(
            self.instance, "ciudad_destino", None))
        creado_por = attrs.get("creado_por_restaurante_id", getattr(
            self.instance, "creado_por_restaurante_id", None))

        if alcance == "PAIS" and not pais_destino:
            raise serializers.ValidationError(
                {"pais_destino": "Requerido para alcance PAIS."})
        if alcance == "CIUDAD" and not ciudad_destino:
            raise serializers.ValidationError(
                {"ciudad_destino": "Requerido para alcance CIUDAD."})
        if alcance == "LOCAL" and not creado_por:
            raise serializers.ValidationError(
                {"creado_por_restaurante_id": "Requerido para alcance LOCAL."})
        return attrs


class ProveedorListSerializer(serializers.ModelSerializer):
    """
    Serializer para listados — incluye campos de alcance y contacto completo.
    El GET /proveedores/ devuelve todos estos campos para que el frontend
    pueda mostrar teléfono, email, alcance, destinos, etc.
    """
    class Meta:
        model = Proveedor
        fields = (
            "id",
            "nombre",
            "pais",
            "ciudad",
            "telefono",
            "email",
            "moneda_preferida",
            "activo",
            # Campos de alcance
            "alcance",
            "pais_destino",
            "ciudad_destino",
            "creado_por_restaurante_id",
        )
        read_only_fields = ("id",)


# ─────────────────────────────────────────
# ALMACÉN
# ─────────────────────────────────────────

class AlmacenSerializer(serializers.ModelSerializer):
    total_ingredientes = serializers.SerializerMethodField()
    ingredientes_bajo_minimo = serializers.SerializerMethodField()

    class Meta:
        model = Almacen
        fields = (
            "id", "restaurante_id", "nombre", "descripcion",
            "activo", "fecha_creacion", "fecha_actualizacion",
            "total_ingredientes", "ingredientes_bajo_minimo",
        )
        read_only_fields = ("id", "fecha_creacion", "fecha_actualizacion")

    def get_total_ingredientes(self, obj):
        return obj.ingredientes.count()

    def get_ingredientes_bajo_minimo(self, obj):
        from django.db.models import F
        return obj.ingredientes.filter(
            cantidad_actual__lte=F("nivel_minimo")
        ).count()


class AlmacenWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Almacen
        fields = ("restaurante_id", "nombre", "descripcion", "activo")

    def validate_nombre(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "El nombre no puede estar vacío.")
        return value.strip()


# ─────────────────────────────────────────
# RECETA PLATO — solo lectura
# ─────────────────────────────────────────

class RecetaPlatoSerializer(serializers.ModelSerializer):
    nombre_ingrediente = serializers.SerializerMethodField()
    costo_ingrediente = serializers.SerializerMethodField()

    class Meta:
        model = RecetaPlato
        fields = (
            "id",
            "plato_id",
            "ingrediente_id",
            "nombre_ingrediente",
            "cantidad",
            "unidad_medida",
            "costo_unitario",
            "costo_ingrediente",
            "fecha_actualizacion",
            "fecha_costo_actualizado",
        )
        read_only_fields = fields

    def get_nombre_ingrediente(self, obj):
        if obj.nombre_ingrediente:
            return obj.nombre_ingrediente
        ingredientes_cache = self.context.get("ingredientes_cache", {})
        nombre = ingredientes_cache.get(str(obj.ingrediente_id))
        if nombre:
            RecetaPlato.objects.filter(pk=obj.pk).update(
                nombre_ingrediente=nombre)
            return nombre
        try:
            from app.inventory.models import Ingrediente
            ing = Ingrediente.objects.filter(
                ingrediente_id=obj.ingrediente_id).first()
            if ing:
                RecetaPlato.objects.filter(pk=obj.pk).update(
                    nombre_ingrediente=ing.nombre)
                return ing.nombre
        except Exception:
            pass
        return None

    def get_costo_ingrediente(self, obj):
        return round(obj.costo_ingrediente, 4)


class CostoPlatoSerializer(serializers.Serializer):
    plato_id = serializers.UUIDField()
    costo_total = serializers.DecimalField(max_digits=12, decimal_places=4)
    tiene_costos_vacios = serializers.BooleanField()
    ingredientes = RecetaPlatoSerializer(many=True)
    advertencia = serializers.SerializerMethodField()

    def get_advertencia(self, obj):
        if obj["tiene_costos_vacios"]:
            return (
                "Algunos ingredientes tienen costo_unitario=0. "
                "El costo total puede estar incompleto. "
                "Registra una orden de compra para actualizarlos."
            )
        return None


# ─────────────────────────────────────────
# MOVIMIENTO INVENTARIO — solo lectura
# ─────────────────────────────────────────

class MovimientoInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoInventario
        fields = (
            "id", "tipo_movimiento", "cantidad",
            "cantidad_antes", "cantidad_despues",
            "pedido_id", "orden_compra_id",
            "descripcion", "fecha",
        )
        read_only_fields = fields


# ─────────────────────────────────────────
# INGREDIENTE INVENTARIO
# ─────────────────────────────────────────

class IngredienteInventarioSerializer(serializers.ModelSerializer):
    necesita_reposicion = serializers.BooleanField(read_only=True)
    esta_agotado = serializers.BooleanField(read_only=True)
    porcentaje_stock = serializers.FloatField(read_only=True)
    almacen_nombre = serializers.CharField(
        source="almacen.nombre", read_only=True)
    movimientos = MovimientoInventarioSerializer(many=True, read_only=True)

    class Meta:
        model = IngredienteInventario
        fields = (
            "id", "ingrediente_id", "nombre_ingrediente",
            "almacen", "almacen_nombre", "unidad_medida",
            "cantidad_actual", "nivel_minimo", "nivel_maximo",
            "lote_actual", "necesita_reposicion", "esta_agotado",
            "porcentaje_stock", "fecha_creacion", "fecha_actualizacion",
            "movimientos",
        )
        read_only_fields = (
            "id", "fecha_creacion", "fecha_actualizacion",
            "necesita_reposicion", "esta_agotado", "porcentaje_stock",
        )


class IngredienteInventarioListSerializer(serializers.ModelSerializer):
    necesita_reposicion = serializers.BooleanField(read_only=True)
    esta_agotado = serializers.BooleanField(read_only=True)
    porcentaje_stock = serializers.FloatField(read_only=True)
    almacen_nombre = serializers.CharField(
        source="almacen.nombre", read_only=True)

    class Meta:
        model = IngredienteInventario
        fields = (
            "id", "ingrediente_id", "nombre_ingrediente",
            "almacen", "almacen_nombre", "unidad_medida",
            "cantidad_actual", "nivel_minimo", "nivel_maximo",
            "necesita_reposicion", "esta_agotado", "porcentaje_stock",
            "fecha_actualizacion",
        )
        read_only_fields = (
            "id", "fecha_actualizacion",
            "necesita_reposicion", "esta_agotado", "porcentaje_stock",
        )


class IngredienteInventarioWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngredienteInventario
        fields = (
            "ingrediente_id", "nombre_ingrediente", "almacen",
            "unidad_medida", "cantidad_actual",
            "nivel_minimo", "nivel_maximo",
        )

    def validate(self, attrs):
        nivel_min = attrs.get("nivel_minimo", 0)
        nivel_max = attrs.get("nivel_maximo", 0)
        cantidad = attrs.get("cantidad_actual", 0)
        if nivel_max < nivel_min:
            raise serializers.ValidationError(
                {"nivel_maximo": "El nivel máximo debe ser mayor o igual al mínimo."})
        if cantidad < 0:
            raise serializers.ValidationError(
                {"cantidad_actual": "La cantidad no puede ser negativa."})
        return attrs


class IngredienteInventarioNivelesSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngredienteInventario
        fields = ("nivel_minimo", "nivel_maximo")

    def validate(self, attrs):
        nivel_min = attrs.get("nivel_minimo", self.instance.nivel_minimo)
        nivel_max = attrs.get("nivel_maximo", self.instance.nivel_maximo)
        if nivel_max < nivel_min:
            raise serializers.ValidationError(
                {"nivel_maximo": "El nivel máximo debe ser mayor o igual al mínimo."})
        return attrs


class AjusteStockSerializer(serializers.Serializer):
    cantidad = serializers.DecimalField(max_digits=10, decimal_places=3)
    descripcion = serializers.CharField(
        min_length=10,
        error_messages={"min_length": "La justificación debe tener al menos 10 caracteres."})

    def validate_cantidad(self, value):
        if value == 0:
            raise serializers.ValidationError(
                "La cantidad del ajuste no puede ser cero.")
        return value


# ─────────────────────────────────────────
# LOTE INGREDIENTE
# ─────────────────────────────────────────

class LoteIngredienteSerializer(serializers.ModelSerializer):
    esta_vencido = serializers.BooleanField(read_only=True)
    dias_para_vencer = serializers.IntegerField(read_only=True)
    proveedor_nombre = serializers.CharField(
        source="proveedor.nombre", read_only=True)
    almacen_nombre = serializers.CharField(
        source="almacen.nombre", read_only=True)

    class Meta:
        model = LoteIngrediente
        fields = (
            "id", "ingrediente_id", "almacen", "almacen_nombre",
            "proveedor", "proveedor_nombre", "numero_lote",
            "fecha_produccion", "fecha_vencimiento",
            "cantidad_recibida", "cantidad_actual", "unidad_medida",
            "estado", "esta_vencido", "dias_para_vencer",
            "fecha_recepcion", "fecha_actualizacion",
        )
        read_only_fields = (
            "id", "esta_vencido", "dias_para_vencer",
            "fecha_recepcion", "fecha_actualizacion",
        )


class LoteIngredienteWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoteIngrediente
        fields = (
            "ingrediente_id", "almacen", "proveedor",
            "numero_lote", "fecha_produccion", "fecha_vencimiento",
            "cantidad_recibida", "unidad_medida",
        )

    def validate_fecha_vencimiento(self, value):
        if value <= timezone.now().date():
            raise serializers.ValidationError(
                "La fecha de vencimiento debe ser futura.")
        return value

    def validate_cantidad_recibida(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "La cantidad recibida debe ser mayor a 0.")
        return value

    def validate(self, attrs):
        fecha_prod = attrs.get("fecha_produccion")
        fecha_venc = attrs.get("fecha_vencimiento")
        if fecha_prod and fecha_venc and fecha_venc <= fecha_prod:
            raise serializers.ValidationError(
                {"fecha_vencimiento": "Debe ser posterior a la fecha de producción."})
        return attrs

    def create(self, validated_data):
        validated_data["cantidad_actual"] = validated_data["cantidad_recibida"]
        return super().create(validated_data)


class LoteListSerializer(serializers.ModelSerializer):
    esta_vencido = serializers.BooleanField(read_only=True)
    dias_para_vencer = serializers.IntegerField(read_only=True)
    almacen_nombre = serializers.CharField(
        source="almacen.nombre", read_only=True)

    class Meta:
        model = LoteIngrediente
        fields = (
            "id", "ingrediente_id", "numero_lote",
            "almacen", "almacen_nombre",
            "cantidad_actual", "unidad_medida",
            "fecha_vencimiento", "estado",
            "esta_vencido", "dias_para_vencer",
        )
        read_only_fields = ("id", "esta_vencido", "dias_para_vencer")


# ─────────────────────────────────────────
# DETALLE ORDEN COMPRA
# ─────────────────────────────────────────

class DetalleOrdenCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleOrdenCompra
        fields = (
            "id", "ingrediente_id", "nombre_ingrediente",
            "unidad_medida", "cantidad", "cantidad_recibida",
            "precio_unitario", "subtotal",
        )
        read_only_fields = ("id", "subtotal")


class DetalleOrdenCompraWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleOrdenCompra
        fields = (
            "ingrediente_id", "nombre_ingrediente",
            "unidad_medida", "cantidad", "precio_unitario",
        )

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
# ORDEN COMPRA
# ─────────────────────────────────────────

class OrdenCompraSerializer(serializers.ModelSerializer):
    detalles = DetalleOrdenCompraSerializer(many=True, read_only=True)
    proveedor_nombre = serializers.CharField(
        source="proveedor.nombre", read_only=True)

    class Meta:
        model = OrdenCompra
        fields = (
            "id", "proveedor", "proveedor_nombre", "restaurante_id",
            "estado", "moneda", "total_estimado",
            "fecha_creacion", "fecha_entrega_estimada", "fecha_recepcion",
            "notas", "detalles",
        )
        read_only_fields = ("id", "total_estimado",
                            "fecha_creacion", "fecha_recepcion")


class OrdenCompraListSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(
        source="proveedor.nombre", read_only=True)

    class Meta:
        model = OrdenCompra
        fields = (
            "id", "proveedor", "proveedor_nombre", "restaurante_id",
            "estado", "moneda", "total_estimado", "fecha_creacion",
        )
        read_only_fields = ("id", "total_estimado", "fecha_creacion")


class OrdenCompraWriteSerializer(serializers.ModelSerializer):
    detalles = DetalleOrdenCompraWriteSerializer(many=True)

    class Meta:
        model = OrdenCompra
        fields = (
            "proveedor", "restaurante_id", "moneda",
            "fecha_entrega_estimada", "notas", "detalles",
        )

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError(
                "La orden debe tener al menos un ítem.")
        return value

    def validate_fecha_entrega_estimada(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError(
                "La fecha de entrega estimada debe ser futura.")
        return value

    def create(self, validated_data):
        detalles_data = validated_data.pop("detalles")
        total = Decimal("0.00")

        orden = OrdenCompra.objects.create(
            **validated_data,
            total_estimado=total,
            estado="BORRADOR",
        )

        for detalle_data in detalles_data:
            precio = Decimal(detalle_data["precio_unitario"])
            cantidad = Decimal(detalle_data["cantidad"])
            subtotal = (precio * cantidad).quantize(Decimal("0.01"),
                                                    rounding=ROUND_HALF_UP)
            DetalleOrdenCompra.objects.create(
                orden=orden, subtotal=subtotal, **detalle_data)
            total += subtotal

        orden.total_estimado = total.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
        orden.save(update_fields=["total_estimado"])
        return orden


class RecibirOrdenSerializer(serializers.Serializer):
    class DetalleRecepcionSerializer(serializers.Serializer):
        detalle_id = serializers.UUIDField()
        cantidad_recibida = serializers.DecimalField(
            max_digits=10, decimal_places=3)
        numero_lote = serializers.CharField(max_length=100)
        fecha_vencimiento = serializers.DateField()
        fecha_produccion = serializers.DateField(
            required=False, allow_null=True)

        def validate_cantidad_recibida(self, value):
            if value < 0:
                raise serializers.ValidationError(
                    "La cantidad recibida no puede ser negativa.")
            return value

        def validate_fecha_vencimiento(self, value):
            if value <= timezone.now().date():
                raise serializers.ValidationError(
                    "La fecha de vencimiento debe ser futura.")
            return value

    detalles = DetalleRecepcionSerializer(many=True)
    notas = serializers.CharField(required=False, allow_blank=True)

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError(
                "Debes especificar al menos un detalle de recepción.")
        return value


# ─────────────────────────────────────────
# ALERTA STOCK
# ─────────────────────────────────────────

class AlertaStockSerializer(serializers.ModelSerializer):
    nombre_ingrediente = serializers.CharField(
        source="ingrediente_inventario.nombre_ingrediente", read_only=True)
    almacen_nombre = serializers.CharField(
        source="almacen.nombre", read_only=True)

    class Meta:
        model = AlertaStock
        fields = (
            "id", "tipo_alerta", "estado",
            "ingrediente_id", "nombre_ingrediente",
            "restaurante_id", "almacen", "almacen_nombre",
            "nivel_actual", "nivel_minimo",
            "lote", "fecha_alerta", "fecha_resolucion",
        )
        read_only_fields = fields

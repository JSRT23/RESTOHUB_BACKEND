from django.utils import timezone
from rest_framework import serializers

from app.loyalty.models import (
    AplicacionPromocion,
    CatalogoCategoria,
    CatalogoPlato,
    CuentaPuntos,
    Cupon,
    Promocion,
    ReglaPromocion,
    TransaccionPuntos,
)


# ---------------------------------------------------------------------------
# CuentaPuntos
# ---------------------------------------------------------------------------

class CuentaPuntosSerializer(serializers.ModelSerializer):
    nivel_display = serializers.CharField(
        source="get_nivel_display", read_only=True)

    class Meta:
        model = CuentaPuntos
        fields = [
            "id", "cliente_id",
            "saldo", "puntos_totales_historicos",
            "nivel", "nivel_display",
            "ultima_actualizacion",
        ]
        read_only_fields = [
            "id", "puntos_totales_historicos",
            "nivel", "ultima_actualizacion",
        ]


# ---------------------------------------------------------------------------
# TransaccionPuntos
# ---------------------------------------------------------------------------

class TransaccionPuntosSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(
        source="get_tipo_display", read_only=True)
    cliente_id = serializers.UUIDField(
        source="cuenta.cliente_id", read_only=True)
    puntos_display = serializers.SerializerMethodField()

    class Meta:
        model = TransaccionPuntos
        fields = [
            "id", "cuenta", "cliente_id",
            "tipo", "tipo_display",
            "puntos", "puntos_display",
            "saldo_anterior", "saldo_posterior",
            "pedido_id", "restaurante_id", "promocion_id",
            "descripcion", "created_at",
        ]
        read_only_fields = [
            "id", "saldo_anterior", "saldo_posterior", "created_at"
        ]

    def get_puntos_display(self, obj):
        return f"+{obj.puntos}" if obj.puntos >= 0 else str(obj.puntos)


# ---------------------------------------------------------------------------
# Acumular / Canjear puntos — serializers de acción
# ---------------------------------------------------------------------------

class AcumularPuntosSerializer(serializers.Serializer):
    """POST /puntos/acumular/ — acumulación manual de puntos."""
    cliente_id = serializers.UUIDField()
    puntos = serializers.IntegerField(min_value=1)
    pedido_id = serializers.UUIDField(required=False)
    restaurante_id = serializers.UUIDField(required=False)
    descripcion = serializers.CharField(
        max_length=255, required=False, default="Ajuste manual")


class CanjearPuntosSerializer(serializers.Serializer):
    """POST /puntos/canjear/ — canje de puntos como descuento."""
    cliente_id = serializers.UUIDField()
    puntos = serializers.IntegerField(min_value=1)
    pedido_id = serializers.UUIDField(required=False)
    descripcion = serializers.CharField(
        max_length=255, required=False, default="Canje de puntos")

    def validate(self, attrs):
        from app.loyalty.models import CuentaPuntos

        cliente_id = attrs["cliente_id"]
        puntos = attrs["puntos"]

        cuenta = CuentaPuntos.objects.filter(cliente_id=cliente_id).first()
        if not cuenta:
            raise serializers.ValidationError(
                {"cliente_id": "El cliente no tiene cuenta de puntos."}
            )
        if cuenta.saldo < puntos:
            raise serializers.ValidationError(
                {"puntos": f"Saldo insuficiente. Disponible: {cuenta.saldo} pts."}
            )
        attrs["_cuenta"] = cuenta
        return attrs


# ---------------------------------------------------------------------------
# ReglaPromocion
# ---------------------------------------------------------------------------

class ReglaPromocionSerializer(serializers.ModelSerializer):
    tipo_condicion_display = serializers.CharField(
        source="get_tipo_condicion_display", read_only=True
    )

    class Meta:
        model = ReglaPromocion
        fields = [
            "id", "tipo_condicion", "tipo_condicion_display",
            "monto_minimo", "moneda",
            "plato_id", "categoria_id",
            "hora_inicio", "hora_fin",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        tipo = attrs.get("tipo_condicion")

        if tipo == "monto_minimo" and not attrs.get("monto_minimo"):
            raise serializers.ValidationError(
                {"monto_minimo": "Requerido para condición MONTO_MINIMO."}
            )
        if tipo == "plato" and not attrs.get("plato_id"):
            raise serializers.ValidationError(
                {"plato_id": "Requerido para condición PLATO."}
            )
        if tipo == "categoria" and not attrs.get("categoria_id"):
            raise serializers.ValidationError(
                {"categoria_id": "Requerido para condición CATEGORIA."}
            )
        if tipo == "hora":
            if attrs.get("hora_inicio") is None or attrs.get("hora_fin") is None:
                raise serializers.ValidationError(
                    {"hora_inicio": "hora_inicio y hora_fin requeridos para condición HORA."}
                )
            if attrs["hora_inicio"] >= attrs["hora_fin"]:
                raise serializers.ValidationError(
                    {"hora_inicio": "hora_inicio debe ser menor que hora_fin."}
                )
        return attrs


# ---------------------------------------------------------------------------
# Promocion
# ---------------------------------------------------------------------------

class PromocionListSerializer(serializers.ModelSerializer):
    """Versión ligera para listados."""
    alcance_display = serializers.CharField(
        source="get_alcance_display", read_only=True)
    tipo_beneficio_display = serializers.CharField(
        source="get_tipo_beneficio_display", read_only=True
    )

    class Meta:
        model = Promocion
        fields = [
            "id", "nombre",
            "alcance", "alcance_display",
            "tipo_beneficio", "tipo_beneficio_display",
            "valor", "puntos_bonus",
            "fecha_inicio", "fecha_fin", "activa",
        ]


class PromocionSerializer(serializers.ModelSerializer):
    """Detalle completo — incluye reglas y conteo de aplicaciones."""
    alcance_display = serializers.CharField(
        source="get_alcance_display", read_only=True)
    tipo_beneficio_display = serializers.CharField(
        source="get_tipo_beneficio_display", read_only=True
    )
    reglas = ReglaPromocionSerializer(many=True, read_only=True)
    total_aplicaciones = serializers.IntegerField(
        source="aplicaciones.count", read_only=True
    )

    class Meta:
        model = Promocion
        fields = [
            "id", "nombre", "descripcion",
            "alcance", "alcance_display",
            "marca", "restaurante_id",
            "tipo_beneficio", "tipo_beneficio_display",
            "valor", "puntos_bonus", "multiplicador_puntos",
            "fecha_inicio", "fecha_fin", "activa",
            "reglas", "total_aplicaciones",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class FlexibleDateTimeField(serializers.DateTimeField):
    """
    DateTimeField que convierte string vacio a None antes de parsear.
    Necesario para Django 5.x + DRF BrowsableAPIRenderer:
    datetime.fromisoformat('') lanza ValueError en el template antes
    de que to_internal_value pueda interceptarlo.
    """

    def to_internal_value(self, value):
        if value == "" or value is None:
            if self.allow_null:
                return None
            self.fail("null")
        return super().to_internal_value(value)

    def run_validation(self, data=serializers.empty):
        if data == "":
            data = None
        return super().run_validation(data)


class PromocionWriteSerializer(serializers.ModelSerializer):
    """Para POST y PATCH -- incluye reglas anidadas."""
    reglas = ReglaPromocionSerializer(many=True, required=False)

    # Fix Django 5.x + DRF: datetime.fromisoformat('') lanza ValueError
    # que DRF no captura. Solucion: interceptar string vacio en
    # to_internal_value antes de que llegue al parser de fechas.
    fecha_inicio = FlexibleDateTimeField(required=False, allow_null=True)
    fecha_fin = FlexibleDateTimeField(required=False, allow_null=True)

    class Meta:
        model = Promocion
        fields = [
            "nombre", "descripcion",
            "alcance", "marca", "restaurante_id",
            "tipo_beneficio", "valor", "puntos_bonus", "multiplicador_puntos",
            "fecha_inicio", "fecha_fin",
            "reglas",
        ]

    def validate(self, attrs):
        alcance = attrs.get("alcance") or (
            self.instance.alcance if self.instance else None)
        marca = attrs.get("marca", "")
        restaurante_id = attrs.get("restaurante_id")

        # Fechas requeridas solo en creacion (no en PATCH parcial)
        if not self.instance:
            if not attrs.get("fecha_inicio"):
                raise serializers.ValidationError(
                    {"fecha_inicio": "Este campo es requerido."}
                )
            if not attrs.get("fecha_fin"):
                raise serializers.ValidationError(
                    {"fecha_fin": "Este campo es requerido."}
                )

        if alcance == "marca" and not marca:
            raise serializers.ValidationError(
                {"marca": "Requerido cuando alcance es MARCA."}
            )
        if alcance == "local" and not restaurante_id:
            raise serializers.ValidationError(
                {"restaurante_id": "Requerido cuando alcance es LOCAL."}
            )

        fecha_inicio = attrs.get("fecha_inicio")
        fecha_fin = attrs.get("fecha_fin")
        if fecha_inicio and fecha_fin and fecha_inicio >= fecha_fin:
            raise serializers.ValidationError(
                {"fecha_inicio": "fecha_inicio debe ser anterior a fecha_fin."}
            )
        return attrs

    def create(self, validated_data):
        reglas_data = validated_data.pop("reglas", [])
        promocion = Promocion.objects.create(**validated_data)
        for regla_data in reglas_data:
            ReglaPromocion.objects.create(promocion=promocion, **regla_data)
        return promocion

    def update(self, instance, validated_data):
        reglas_data = validated_data.pop("reglas", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Si se envían reglas en el PATCH, reemplazar completamente
        if reglas_data is not None:
            instance.reglas.all().delete()
            for regla_data in reglas_data:
                ReglaPromocion.objects.create(promocion=instance, **regla_data)

        return instance


class EvaluarPromocionSerializer(serializers.Serializer):
    """POST /promociones/evaluar/ — evaluar si aplica promo a un pedido."""
    pedido_id = serializers.UUIDField()
    cliente_id = serializers.UUIDField()
    restaurante_id = serializers.UUIDField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    detalles = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="Lista de {plato_id, cantidad} del pedido"
    )


# ---------------------------------------------------------------------------
# AplicacionPromocion
# ---------------------------------------------------------------------------

class AplicacionPromocionSerializer(serializers.ModelSerializer):
    promocion_nombre = serializers.CharField(
        source="promocion.nombre", read_only=True)

    class Meta:
        model = AplicacionPromocion
        fields = [
            "id", "promocion", "promocion_nombre",
            "pedido_id", "cliente_id",
            "descuento_aplicado", "puntos_bonus_otorgados",
            "applied_at",
        ]
        read_only_fields = ["id", "applied_at"]


# ---------------------------------------------------------------------------
# Cupon
# ---------------------------------------------------------------------------

class CuponListSerializer(serializers.ModelSerializer):
    """Versión ligera — sin exponer el código completo en listados."""
    tipo_descuento_display = serializers.CharField(
        source="get_tipo_descuento_display", read_only=True
    )
    disponible = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cupon
        fields = [
            "id", "codigo",
            "tipo_descuento", "tipo_descuento_display",
            "valor_descuento",
            "cliente_id",
            "usos_actuales", "limite_uso",
            "fecha_inicio", "fecha_fin",
            "activo", "disponible",
        ]


class CuponSerializer(CuponListSerializer):
    """Detalle completo."""
    promocion_nombre = serializers.SerializerMethodField()

    class Meta(CuponListSerializer.Meta):
        fields = CuponListSerializer.Meta.fields + [
            "promocion", "promocion_nombre",
            "created_at", "updated_at",
        ]

    def get_promocion_nombre(self, obj):
        return obj.promocion.nombre if obj.promocion else None


class CuponWriteSerializer(serializers.ModelSerializer):
    """Para POST — generación de cupón."""

    class Meta:
        model = Cupon
        fields = [
            "promocion", "cliente_id",
            "tipo_descuento", "valor_descuento",
            "limite_uso", "fecha_inicio", "fecha_fin",
            "codigo",
        ]
        extra_kwargs = {
            "codigo": {"required": False},
        }

    def validate(self, attrs):
        fecha_inicio = attrs.get("fecha_inicio")
        fecha_fin = attrs.get("fecha_fin")

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise serializers.ValidationError(
                {"fecha_inicio": "fecha_inicio debe ser anterior a fecha_fin."}
            )
        if fecha_fin and fecha_fin < timezone.now().date():
            raise serializers.ValidationError(
                {"fecha_fin": "fecha_fin no puede ser una fecha pasada."}
            )
        return attrs


class CanjearCuponSerializer(serializers.Serializer):
    """POST /cupones/{id}/canjear/"""
    pedido_id = serializers.UUIDField(required=False)


# ---------------------------------------------------------------------------
# Catálogo (solo lectura)
# ---------------------------------------------------------------------------

class CatalogoPlatoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogoPlato
        fields = [
            "id", "plato_id", "categoria_id",
            "nombre", "activo", "updated_at",
        ]
        read_only_fields = fields


class CatalogoCategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogoCategoria
        fields = [
            "id", "categoria_id",
            "nombre", "activo", "updated_at",
        ]
        read_only_fields = fields

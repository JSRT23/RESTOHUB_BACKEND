from rest_framework import serializers
from .models import Restaurante, Categoria, Plato, Ingrediente, PlatoIngrediente, PrecioPlato


# ─────────────────────────────────────────
# RESTAURANTE
# ─────────────────────────────────────────

class RestauranteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurante
        fields = (
            "id", "nombre", "pais", "ciudad", "direccion",
            "moneda", "activo", "fecha_creacion", "fecha_actualizacion",
        )
        read_only_fields = ("id", "fecha_creacion", "fecha_actualizacion")


# ─────────────────────────────────────────
# CATEGORIA
# ─────────────────────────────────────────

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ("id", "nombre", "orden", "activo")
        read_only_fields = ("id",)


# ─────────────────────────────────────────
# INGREDIENTE
# ─────────────────────────────────────────

class IngredienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingrediente
        fields = ("id", "nombre", "unidad_medida", "descripcion", "activo")
        read_only_fields = ("id",)


# ─────────────────────────────────────────
# PLATO INGREDIENTE
# ─────────────────────────────────────────

class PlatoIngredienteSerializer(serializers.ModelSerializer):
    ingrediente_nombre = serializers.CharField(
        source="ingrediente.nombre",
        read_only=True
    )
    unidad_medida = serializers.CharField(
        source="ingrediente.unidad_medida",
        read_only=True
    )

    class Meta:
        model = PlatoIngrediente
        fields = ("id", "ingrediente", "ingrediente_nombre",
                  "unidad_medida", "cantidad")
        read_only_fields = ("id",)


class PlatoIngredienteWriteSerializer(serializers.ModelSerializer):
    """Serializer para agregar/actualizar ingredientes en un plato."""
    class Meta:
        model = PlatoIngrediente
        fields = ("ingrediente", "cantidad")

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "La cantidad debe ser mayor a 0.")
        return value


# ─────────────────────────────────────────
# PRECIO PLATO
# ─────────────────────────────────────────

class PrecioPlatoSerializer(serializers.ModelSerializer):
    moneda = serializers.CharField(source="restaurante.moneda", read_only=True)
    restaurante_nombre = serializers.CharField(
        source="restaurante.nombre", read_only=True)
    esta_vigente = serializers.BooleanField(read_only=True)

    class Meta:
        model = PrecioPlato
        fields = (
            "id", "plato", "restaurante", "restaurante_nombre",
            "precio", "moneda", "fecha_inicio", "fecha_fin",
            "activo", "esta_vigente",
        )
        read_only_fields = (
            "id", "moneda", "restaurante_nombre", "esta_vigente")

    def validate(self, attrs):
        fecha_inicio = attrs.get("fecha_inicio")
        fecha_fin = attrs.get("fecha_fin")
        precio = attrs.get("precio")

        if precio is not None and precio <= 0:
            raise serializers.ValidationError(
                {"precio": "El precio debe ser mayor a 0."})

        if fecha_fin and fecha_inicio and fecha_fin <= fecha_inicio:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha de fin debe ser posterior a la fecha de inicio."}
            )
        return attrs


class PrecioPlatoWriteSerializer(serializers.ModelSerializer):
    """Serializer simplificado para crear/actualizar precios."""
    class Meta:
        model = PrecioPlato
        fields = ("plato", "restaurante", "precio",
                  "fecha_inicio", "fecha_fin", "activo")

    def validate(self, attrs):
        fecha_inicio = attrs.get("fecha_inicio")
        fecha_fin = attrs.get("fecha_fin")
        precio = attrs.get("precio")

        if precio is not None and precio <= 0:
            raise serializers.ValidationError(
                {"precio": "El precio debe ser mayor a 0."})

        if fecha_fin and fecha_inicio and fecha_fin <= fecha_inicio:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha de fin debe ser posterior a la fecha de inicio."}
            )
        return attrs


# ─────────────────────────────────────────
# PLATO
# ─────────────────────────────────────────

class PlatoSerializer(serializers.ModelSerializer):
    """Serializer completo — incluye ingredientes y precios (para GET detalle)."""
    categoria_nombre = serializers.CharField(
        source="categoria.nombre",
        read_only=True
    )
    ingredientes = PlatoIngredienteSerializer(many=True, read_only=True)
    precios = PrecioPlatoSerializer(many=True, read_only=True)

    class Meta:
        model = Plato
        fields = (
            "id", "nombre", "descripcion",
            "categoria", "categoria_nombre",
            "imagen", "activo",
            "fecha_creacion", "fecha_actualizacion",
            "ingredientes", "precios",
        )
        read_only_fields = ("id", "fecha_creacion", "fecha_actualizacion")


class PlatoListSerializer(serializers.ModelSerializer):
    """Serializer ligero — para listar platos sin anidar ingredientes ni precios."""
    categoria_nombre = serializers.CharField(
        source="categoria.nombre",
        read_only=True
    )

    class Meta:
        model = Plato
        fields = (
            "id", "nombre", "descripcion",
            "categoria", "categoria_nombre",
            "imagen", "activo",
            "fecha_creacion", "fecha_actualizacion",
        )
        read_only_fields = ("id", "fecha_creacion", "fecha_actualizacion")


class PlatoWriteSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar platos."""
    class Meta:
        model = Plato
        fields = ("nombre", "descripcion", "categoria", "imagen", "activo")

    def validate_nombre(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "El nombre no puede estar vacío.")
        return value.strip()


# ─────────────────────────────────────────
# MENU RESTAURANTE
# Serializer especial para GET /restaurantes/{id}/menu/
# Retorna platos activos con precio vigente agrupados por categoría.
# ─────────────────────────────────────────

class MenuPlatoSerializer(serializers.Serializer):
    """Plato dentro del menú de un restaurante — incluye precio vigente."""
    plato_id = serializers.UUIDField(source="id")
    nombre = serializers.CharField()
    descripcion = serializers.CharField()
    imagen = serializers.URLField()
    precio = serializers.SerializerMethodField()
    moneda = serializers.SerializerMethodField()

    def get_precio(self, obj):
        restaurante_id = self.context.get("restaurante_id")
        precio = obj.precios.filter(
            restaurante_id=restaurante_id,
            activo=True,
        ).order_by("-fecha_inicio").first()
        return str(precio.precio) if precio else None

    def get_moneda(self, obj):
        restaurante_id = self.context.get("restaurante_id")
        precio = obj.precios.filter(
            restaurante_id=restaurante_id,
            activo=True,
        ).order_by("-fecha_inicio").first()
        return precio.restaurante.moneda if precio else None


class MenuCategoriaSerializer(serializers.Serializer):
    """Categoría dentro del menú — agrupa sus platos activos."""
    categoria_id = serializers.UUIDField(source="id")
    nombre = serializers.CharField()
    orden = serializers.IntegerField()
    platos = serializers.SerializerMethodField()

    def get_platos(self, obj):
        restaurante_id = self.context.get("restaurante_id")
        platos = obj.platos.filter(
            activo=True,
            precios__restaurante_id=restaurante_id,
            precios__activo=True,
        ).distinct()
        return MenuPlatoSerializer(
            platos,
            many=True,
            context=self.context
        ).data


class MenuRestauranteSerializer(serializers.Serializer):
    """Menú completo de un restaurante agrupado por categoría."""
    restaurante_id = serializers.UUIDField(source="id")
    nombre = serializers.CharField()
    ciudad = serializers.CharField()
    pais = serializers.CharField()
    moneda = serializers.CharField()
    categorias = serializers.SerializerMethodField()

    def get_categorias(self, obj):
        categorias = Categoria.objects.filter(
            activo=True,
            platos__activo=True,
            platos__precios__restaurante=obj,
            platos__precios__activo=True,
        ).distinct().order_by("orden")

        return MenuCategoriaSerializer(
            categorias,
            many=True,
            context={"restaurante_id": obj.id}
        ).data

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from app.menu.events.event_types import MenuEvents
from app.menu.events.builders import MenuEventBuilder
from app.menu.infrastructure.messaging.mixins.publish_event import PublicadorEventoMixin  # noqa

from .models import Restaurante, Categoria, Plato, Ingrediente, PlatoIngrediente, PrecioPlato
from .serializers import (
    RestauranteSerializer,
    CategoriaSerializer,
    IngredienteSerializer,
    PlatoSerializer,
    PlatoListSerializer,
    PlatoWriteSerializer,
    PlatoIngredienteSerializer,
    PlatoIngredienteWriteSerializer,
    PrecioPlatoSerializer,
    PrecioPlatoWriteSerializer,
)

# ─────────────────────────────────────────
# RESTAURANTE
# ─────────────────────────────────────────


class RestauranteViewSet(PublicadorEventoMixin, viewsets.ModelViewSet):
    queryset = Restaurante.objects.all()
    serializer_class = RestauranteSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    # 🔥 FILTROS ACTIVADOS
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo", "pais"]

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publicar_evento(
            MenuEvents.RESTAURANTE_CREADO,
            MenuEventBuilder.restaurante_creado(instance)
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        cambios = {field: getattr(instance, field)
                   for field in serializer.validated_data}
        self.publicar_evento(
            MenuEvents.RESTAURANTE_ACTUALIZADO,
            MenuEventBuilder.restaurante_actualizado(instance, cambios)
        )

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = True
        obj.save()
        self.publicar_evento(
            MenuEvents.RESTAURANTE_ACTUALIZADO,
            MenuEventBuilder.restaurante_actualizado(obj, {"activo": True})
        )
        return Response({"detail": "Restaurante activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()
        self.publicar_evento(
            MenuEvents.RESTAURANTE_DESACTIVADO,
            MenuEventBuilder.restaurante_desactivado(obj)
        )
        return Response({"detail": "Restaurante desactivado."})


# ─────────────────────────────────────────
# CATEGORIA
# ─────────────────────────────────────────
class CategoriaViewSet(PublicadorEventoMixin, viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo"]

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publicar_evento(MenuEvents.CATEGORIA_CREADA,
                             MenuEventBuilder.categoria_creada(instance))

    def perform_update(self, serializer):
        instance = serializer.save()
        cambios = {field: getattr(instance, field)
                   for field in serializer.validated_data}
        self.publicar_evento(MenuEvents.CATEGORIA_ACTUALIZADA,
                             MenuEventBuilder.categoria_actualizada(instance, cambios))

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = True
        obj.save()
        self.publicar_evento(MenuEvents.CATEGORIA_ACTUALIZADA,
                             MenuEventBuilder.categoria_actualizada(obj, {"activo": True}))
        return Response({"detail": "Categoría activada."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()
        self.publicar_evento(MenuEvents.CATEGORIA_DESACTIVADA,
                             MenuEventBuilder.categoria_desactivada(obj))
        return Response({"detail": "Categoría desactivada."})


# ─────────────────────────────────────────
# INGREDIENTE
# ─────────────────────────────────────────
class IngredienteViewSet(PublicadorEventoMixin, viewsets.ModelViewSet):
    queryset = Ingrediente.objects.all()
    serializer_class = IngredienteSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo", "unidad_medida"]

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publicar_evento(MenuEvents.INGREDIENTE_CREADO,
                             MenuEventBuilder.ingrediente_creado(instance))

    def perform_update(self, serializer):
        instance = serializer.save()
        cambios = {field: getattr(instance, field)
                   for field in serializer.validated_data}
        self.publicar_evento(MenuEvents.INGREDIENTE_ACTUALIZADO,
                             MenuEventBuilder.ingrediente_actualizado(instance, cambios))

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()
        self.publicar_evento(MenuEvents.INGREDIENTE_DESACTIVADO,
                             MenuEventBuilder.ingrediente_desactivado(obj))
        return Response({"detail": "Ingrediente desactivado."})


# ─────────────────────────────────────────
# PLATO
# ─────────────────────────────────────────


class PlatoViewSet(PublicadorEventoMixin, viewsets.ModelViewSet):
    queryset = Plato.objects.all()

    # 🔥 FILTROS ACTIVADOS
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo", "categoria"]

    def get_serializer_class(self):
        if self.action == "list":
            return PlatoListSerializer
        if self.action in ("create", "partial_update"):
            return PlatoWriteSerializer
        return PlatoSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publicar_evento(
            MenuEvents.PLATO_CREADO,
            MenuEventBuilder.plato_creado(instance)
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        cambios = {field: getattr(instance, field)
                   for field in serializer.validated_data}
        self.publicar_evento(
            MenuEvents.PLATO_ACTUALIZADO,
            MenuEventBuilder.plato_actualizado(instance, cambios)
        )

    def perform_destroy(self, instance):
        plato_id = str(instance.id)
        instance.delete()
        self.publicar_evento(
            MenuEvents.PLATO_ELIMINADO,
            MenuEventBuilder.plato_eliminado(plato_id)
        )

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = True
        obj.save()
        self.publicar_evento(
            MenuEvents.PLATO_ACTIVADO,
            MenuEventBuilder.plato_estado(obj)
        )
        return Response({"detail": "Plato activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()
        self.publicar_evento(
            MenuEvents.PLATO_DESACTIVADO,
            MenuEventBuilder.plato_estado(obj)
        )
        return Response({"detail": "Plato desactivado."})

    @action(detail=True, methods=["get", "post"])
    def ingredientes(self, request, pk=None):
        plato = self.get_object()
        if request.method == "GET":
            qs = PlatoIngrediente.objects.filter(plato=plato)
            return Response(PlatoIngredienteSerializer(qs, many=True).data)

        serializer = PlatoIngredienteWriteSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save(plato=plato)
            self.publicar_evento(
                MenuEvents.PLATO_INGREDIENTE_AGREGADO,
                MenuEventBuilder.plato_ingrediente_agregado(
                    plato.id,
                    instance.ingrediente.id,
                    instance.cantidad,
                    instance.ingrediente.unidad_medida
                )
            )
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

    @action(detail=True, methods=["delete"], url_path="ingredientes/(?P<ingrediente_id>[^/.]+)")
    def quitar_ingrediente(self, request, pk=None, ingrediente_id=None):
        plato = self.get_object()
        rel = get_object_or_404(
            PlatoIngrediente,
            plato=plato,
            ingrediente_id=ingrediente_id
        )
        rel.delete()
        self.publicar_evento(
            MenuEvents.PLATO_INGREDIENTE_ELIMINADO,
            MenuEventBuilder.plato_ingrediente_eliminado(
                plato.id,
                ingrediente_id
            )
        )
        return Response(status=204)
# ─────────────────────────────────────────
# PRECIO
# ─────────────────────────────────────────


class PrecioPlatoViewSet(PublicadorEventoMixin, viewsets.ModelViewSet):
    queryset = PrecioPlato.objects.all()

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo", "plato", "restaurante"]

    def get_serializer_class(self):
        if self.action in ("create", "partial_update"):
            return PrecioPlatoWriteSerializer
        return PrecioPlatoSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publicar_evento(MenuEvents.PRECIO_CREADO,
                             MenuEventBuilder.precio_creado(instance))

    def perform_update(self, serializer):
        precio_anterior = serializer.instance.precio  # capture before save
        instance = serializer.save()
        self.publicar_evento(MenuEvents.PRECIO_ACTUALIZADO,
                             MenuEventBuilder.precio_actualizado(instance, precio_anterior))

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = True
        obj.save()
        self.publicar_evento(MenuEvents.PRECIO_ACTIVADO,
                             MenuEventBuilder.precio_estado(obj))
        return Response({"detail": "Precio activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()
        self.publicar_evento(MenuEvents.PRECIO_DESACTIVADO,
                             MenuEventBuilder.precio_estado(obj))
        return Response({"detail": "Precio desactivado."})

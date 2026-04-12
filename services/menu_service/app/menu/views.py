# menu_service/app/menu/views.py
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from app.menu.events.event_types import MenuEvents
from app.menu.events.builders import MenuEventBuilder
from app.menu.infrastructure.messaging.mixins.publish_event import PublicadorEventoMixin

from .models import Restaurante, Categoria, Plato, Ingrediente, PlatoIngrediente, PrecioPlato
from .serializers import (
    RestauranteSerializer,
    CategoriaSerializer,
    IngredienteSerializer,
    IngredienteWriteSerializer,
    PlatoSerializer,
    PlatoListSerializer,
    PlatoWriteSerializer,
    PlatoIngredienteSerializer,
    PlatoIngredienteWriteSerializer,
    PrecioPlatoSerializer,
    PrecioPlatoWriteSerializer,
)


# ── Restaurante ────────────────────────────────────────────────────────────

class RestauranteViewSet(PublicadorEventoMixin, viewsets.ModelViewSet):
    queryset = Restaurante.objects.all()
    serializer_class = RestauranteSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo", "pais"]

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publicar_evento(MenuEvents.RESTAURANTE_CREADO,
                             MenuEventBuilder.restaurante_creado(instance))

    def perform_update(self, serializer):
        instance = serializer.save()
        cambios = {f: getattr(instance, f) for f in serializer.validated_data}
        self.publicar_evento(MenuEvents.RESTAURANTE_ACTUALIZADO,
                             MenuEventBuilder.restaurante_actualizado(instance, cambios))

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = True
        obj.save()
        self.publicar_evento(MenuEvents.RESTAURANTE_ACTUALIZADO,
                             MenuEventBuilder.restaurante_actualizado(obj, {"activo": True}))
        return Response({"detail": "Restaurante activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()
        self.publicar_evento(MenuEvents.RESTAURANTE_DESACTIVADO,
                             MenuEventBuilder.restaurante_desactivado(obj))
        return Response({"detail": "Restaurante desactivado."})

    @action(detail=True, methods=["get"])
    def menu(self, request, pk=None):
        from .serializers import MenuRestauranteSerializer
        restaurante = self.get_object()
        return Response(MenuRestauranteSerializer(restaurante).data)


# ── Categoría ──────────────────────────────────────────────────────────────

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
        cambios = {f: getattr(instance, f) for f in serializer.validated_data}
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


# ── Ingrediente ────────────────────────────────────────────────────────────

class IngredienteViewSet(PublicadorEventoMixin, viewsets.ModelViewSet):
    """
    Filtros disponibles:
      ?activo=true/false
      ?restaurante_id=UUID   → ingredientes de ese restaurante
      ?global=true           → solo ingredientes globales (restaurante=null)
      ?disponibles=UUID      → globales + del restaurante X (para el gerente)
    """
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo", "unidad_medida"]

    def get_serializer_class(self):
        if self.action in ("create", "partial_update"):
            return IngredienteWriteSerializer
        return IngredienteSerializer

    def get_queryset(self):
        qs = Ingrediente.objects.all()

        activo = self.request.query_params.get("activo")
        restaurante_id = self.request.query_params.get("restaurante_id")
        global_only = self.request.query_params.get("global")
        disponibles = self.request.query_params.get(
            "disponibles")  # globales + restaurante X

        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")

        if disponibles:
            # El gerente ve sus propios + los globales
            qs = qs.filter(Q(restaurante_id=disponibles)
                           | Q(restaurante__isnull=True))
        elif restaurante_id:
            qs = qs.filter(restaurante_id=restaurante_id)
        elif global_only and global_only.lower() == "true":
            qs = qs.filter(restaurante__isnull=True)

        return qs.order_by("nombre")

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publicar_evento(MenuEvents.INGREDIENTE_CREADO,
                             MenuEventBuilder.ingrediente_creado(instance))

    def perform_update(self, serializer):
        instance = serializer.save()
        cambios = {f: getattr(instance, f) for f in serializer.validated_data}
        self.publicar_evento(MenuEvents.INGREDIENTE_ACTUALIZADO,
                             MenuEventBuilder.ingrediente_actualizado(instance, cambios))

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = True
        obj.save()
        self.publicar_evento(MenuEvents.INGREDIENTE_ACTUALIZADO,
                             MenuEventBuilder.ingrediente_actualizado(obj, {"activo": True}))
        return Response({"detail": "Ingrediente activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()
        self.publicar_evento(MenuEvents.INGREDIENTE_DESACTIVADO,
                             MenuEventBuilder.ingrediente_desactivado(obj))
        return Response({"detail": "Ingrediente desactivado."})


# ── Plato ──────────────────────────────────────────────────────────────────

class PlatoViewSet(PublicadorEventoMixin, viewsets.ModelViewSet):
    """
    Filtros disponibles:
      ?activo=true/false
      ?categoria=UUID
      ?restaurante_id=UUID   → platos de ese restaurante
      ?global=true           → solo platos globales
      ?disponibles=UUID      → globales + del restaurante X (para el gerente/menú)
    """
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo", "categoria"]

    def get_serializer_class(self):
        if self.action == "list":
            return PlatoListSerializer
        if self.action in ("create", "partial_update"):
            return PlatoWriteSerializer
        return PlatoSerializer

    def get_queryset(self):
        qs = Plato.objects.all()

        activo = self.request.query_params.get("activo")
        restaurante_id = self.request.query_params.get("restaurante_id")
        global_only = self.request.query_params.get("global")
        disponibles = self.request.query_params.get("disponibles")
        categoria = self.request.query_params.get("categoria")

        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")

        if categoria:
            qs = qs.filter(categoria_id=categoria)

        if disponibles:
            # Gerente ve sus platos + globales
            qs = qs.filter(Q(restaurante_id=disponibles)
                           | Q(restaurante__isnull=True))
        elif restaurante_id:
            qs = qs.filter(restaurante_id=restaurante_id)
        elif global_only and global_only.lower() == "true":
            qs = qs.filter(restaurante__isnull=True)

        return qs.select_related("categoria", "restaurante").order_by("nombre")

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publicar_evento(MenuEvents.PLATO_CREADO,
                             MenuEventBuilder.plato_creado(instance))

    def perform_update(self, serializer):
        instance = serializer.save()
        cambios = {f: getattr(instance, f) for f in serializer.validated_data}
        self.publicar_evento(MenuEvents.PLATO_ACTUALIZADO,
                             MenuEventBuilder.plato_actualizado(instance, cambios))

    def perform_destroy(self, instance):
        plato_id = str(instance.id)
        instance.delete()
        self.publicar_evento(MenuEvents.PLATO_ELIMINADO,
                             MenuEventBuilder.plato_eliminado(plato_id))

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = True
        obj.save()
        self.publicar_evento(MenuEvents.PLATO_ACTIVADO,
                             MenuEventBuilder.plato_estado(obj))
        return Response({"detail": "Plato activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()
        self.publicar_evento(MenuEvents.PLATO_DESACTIVADO,
                             MenuEventBuilder.plato_estado(obj))
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
                    plato.id, instance.ingrediente.id, instance.cantidad,
                    instance.ingrediente.unidad_medida, instance.ingrediente.nombre,
                )
            )
            return Response(PlatoIngredienteSerializer(instance).data, status=201)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=["delete"],
            url_path="ingredientes/(?P<ingrediente_id>[^/.]+)")
    def quitar_ingrediente(self, request, pk=None, ingrediente_id=None):
        plato = self.get_object()
        rel = get_object_or_404(
            PlatoIngrediente, plato=plato, ingrediente_id=ingrediente_id)
        rel.delete()
        self.publicar_evento(
            MenuEvents.PLATO_INGREDIENTE_ELIMINADO,
            MenuEventBuilder.plato_ingrediente_eliminado(
                plato.id, ingrediente_id)
        )
        return Response(status=204)


# ── Precio ─────────────────────────────────────────────────────────────────

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
        precio_anterior = serializer.instance.precio
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

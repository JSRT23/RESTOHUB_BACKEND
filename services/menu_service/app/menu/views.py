# menu_service/app/menu/views.py
# menu_service/app/menu/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from app.menu.events.event_types import MenuEvents
from app.menu.infrastructure.messaging.event_mixin import EventPublishingMixin
from app.menu.infrastructure.messaging.publisher import publish_event

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
    MenuRestauranteSerializer,
)

# ─────────────────────────────────────────
# RESTAURANTE
# ─────────────────────────────────────────


class RestauranteViewSet(EventPublishingMixin, viewsets.ModelViewSet):
    queryset = Restaurante.objects.all()
    serializer_class = RestauranteSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    event_created = MenuEvents.RESTAURANTE_CREATED
    event_updated = MenuEvents.RESTAURANTE_UPDATED

    def build_event_data(self, instance):
        return {
            "restaurante_id": str(instance.id),
            "nombre": instance.nombre,
            "pais": instance.pais,
            "ciudad": instance.ciudad,
            "moneda": instance.moneda,
            "activo": instance.activo,
        }

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publish_created_event(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self.publish_updated_event(instance)

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = True
        obj.save()
        self.publish_updated_event(obj)
        return Response({"detail": "Restaurante activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()

        publish_event(
            MenuEvents.RESTAURANTE_DEACTIVATED,
            {"restaurante_id": str(obj.id)}
        )
        return Response({"detail": "Restaurante desactivado."})


# ─────────────────────────────────────────
# CATEGORIA
# ─────────────────────────────────────────

class CategoriaViewSet(EventPublishingMixin, viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

    event_created = MenuEvents.CATEGORIA_CREATED
    event_updated = MenuEvents.CATEGORIA_UPDATED

    def build_event_data(self, instance):
        return {
            "categoria_id": str(instance.id),
            "nombre": instance.nombre,
            "orden": instance.orden,
            "activo": instance.activo,
        }

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publish_created_event(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self.publish_updated_event(instance)

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = True
        obj.save()
        self.publish_updated_event(obj)
        return Response({"detail": "Categoría activada."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()

        publish_event(
            MenuEvents.CATEGORIA_DEACTIVATED,
            {"categoria_id": str(obj.id)}
        )
        return Response({"detail": "Categoría desactivada."})


# ─────────────────────────────────────────
# INGREDIENTE
# ─────────────────────────────────────────

class IngredienteViewSet(EventPublishingMixin, viewsets.ModelViewSet):
    queryset = Ingrediente.objects.all()
    serializer_class = IngredienteSerializer

    event_created = MenuEvents.INGREDIENTE_CREATED
    event_updated = MenuEvents.INGREDIENTE_UPDATED

    def build_event_data(self, instance):
        return {
            "ingrediente_id": str(instance.id),
            "nombre": instance.nombre,
            "unidad_medida": instance.unidad_medida,
            "activo": instance.activo,
        }

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publish_created_event(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self.publish_updated_event(instance)

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()

        publish_event(
            MenuEvents.INGREDIENTE_DEACTIVATED,
            {"ingrediente_id": str(obj.id)}
        )
        return Response({"detail": "Ingrediente desactivado."})


# ─────────────────────────────────────────
# PLATO
# ─────────────────────────────────────────

class PlatoViewSet(EventPublishingMixin, viewsets.ModelViewSet):
    queryset = Plato.objects.all()

    event_created = MenuEvents.PLATO_CREATED
    event_updated = MenuEvents.PLATO_UPDATED

    def get_serializer_class(self):
        if self.action == "list":
            return PlatoListSerializer
        if self.action in ("create", "partial_update"):
            return PlatoWriteSerializer
        return PlatoSerializer

    def build_event_data(self, instance):
        return {
            "plato_id": str(instance.id),
            "nombre": instance.nombre,
            "descripcion": instance.descripcion,
            "categoria_id": str(instance.categoria_id) if instance.categoria_id else None,
            "imagen": instance.imagen,
            "activo": instance.activo,
        }

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publish_created_event(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self.publish_updated_event(instance)

    def perform_destroy(self, instance):
        plato_id = str(instance.id)
        instance.delete()

        publish_event(
            MenuEvents.PLATO_DELETED,
            {"plato_id": plato_id}
        )

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = True
        obj.save()

        publish_event(
            MenuEvents.PLATO_ACTIVATED,
            {"plato_id": str(obj.id)}
        )
        return Response({"detail": "Plato activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()

        publish_event(
            MenuEvents.PLATO_DEACTIVATED,
            {"plato_id": str(obj.id)}
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

            publish_event(
                MenuEvents.PLATO_INGREDIENTE_ADDED,
                {
                    "plato_id": str(plato.id),
                    "ingrediente_id": str(instance.ingrediente.id),
                    "cantidad": str(instance.cantidad),
                    "unidad_medida": instance.ingrediente.unidad_medida,
                }
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

        publish_event(
            MenuEvents.PLATO_INGREDIENTE_REMOVED,
            {
                "plato_id": str(plato.id),
                "ingrediente_id": str(ingrediente_id),
            }
        )

        return Response(status=204)


# ─────────────────────────────────────────
# PRECIO
# ─────────────────────────────────────────

class PrecioPlatoViewSet(EventPublishingMixin, viewsets.ModelViewSet):
    queryset = PrecioPlato.objects.all()

    event_created = MenuEvents.PRECIO_CREATED
    event_updated = MenuEvents.PRECIO_UPDATED

    def get_serializer_class(self):
        if self.action in ("create", "partial_update"):
            return PrecioPlatoWriteSerializer
        return PrecioPlatoSerializer

    def build_event_data(self, instance):
        return {
            "precio_id": str(instance.id),
            "plato_id": str(instance.plato_id),
            "restaurante_id": str(instance.restaurante_id),
            "precio": str(instance.precio),
            "fecha_inicio": instance.fecha_inicio.isoformat(),
            "fecha_fin": instance.fecha_fin.isoformat() if instance.fecha_fin else None,
            "activo": instance.activo,
        }

    def perform_create(self, serializer):
        instance = serializer.save()
        self.publish_created_event(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self.publish_updated_event(instance)

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = True
        obj.save()

        publish_event(
            MenuEvents.PRECIO_ACTIVATED,
            self.build_event_data(obj)
        )
        return Response({"detail": "Precio activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        obj.activo = False
        obj.save()

        publish_event(
            MenuEvents.PRECIO_DEACTIVATED,
            {
                "precio_id": str(obj.id),
                "plato_id": str(obj.plato_id),
                "restaurante_id": str(obj.restaurante_id),
            }
        )
        return Response({"detail": "Precio desactivado."})

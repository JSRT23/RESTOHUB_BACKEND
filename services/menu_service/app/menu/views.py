from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

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

class RestauranteViewSet(viewsets.ModelViewSet):
    queryset = Restaurante.objects.all()
    serializer_class = RestauranteSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Restaurante.objects.all()
        activo = self.request.query_params.get("activo")
        pais = self.request.query_params.get("pais")
        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")
        if pais:
            qs = qs.filter(pais__icontains=pais)
        return qs

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        restaurante = self.get_object()
        restaurante.activo = True
        # dispara restaurante.updated
        restaurante.save(update_fields=["activo"])
        return Response({"detail": "Restaurante activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        restaurante = self.get_object()
        restaurante.activo = False
        # dispara restaurante.deactivated
        restaurante.save(update_fields=["activo"])
        return Response({"detail": "Restaurante desactivado."})

    @action(detail=True, methods=["get"])
    def menu(self, request, pk=None):
        """
        GET /restaurantes/{id}/menu/
        Retorna el menú activo del restaurante agrupado por categoría.
        Solo incluye platos con precio activo y vigente en ese local.
        """
        restaurante = self.get_object()
        serializer = MenuRestauranteSerializer(restaurante)
        return Response(serializer.data)


# ─────────────────────────────────────────
# CATEGORIA
# ─────────────────────────────────────────

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Categoria.objects.all()
        activo = self.request.query_params.get("activo")
        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")
        return qs

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        categoria = self.get_object()
        categoria.activo = True
        categoria.save(update_fields=["activo"])
        return Response({"detail": "Categoría activada."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        categoria = self.get_object()
        categoria.activo = False
        # dispara categoria.deactivated
        categoria.save(update_fields=["activo"])
        return Response({"detail": "Categoría desactivada."})


# ─────────────────────────────────────────
# INGREDIENTE
# ─────────────────────────────────────────

class IngredienteViewSet(viewsets.ModelViewSet):
    queryset = Ingrediente.objects.all()
    serializer_class = IngredienteSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Ingrediente.objects.all()
        activo = self.request.query_params.get("activo")
        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")
        return qs

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        ingrediente = self.get_object()
        ingrediente.activo = True
        ingrediente.save(update_fields=["activo"])
        return Response({"detail": "Ingrediente activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        ingrediente = self.get_object()
        ingrediente.activo = False
        # dispara ingrediente.deactivated
        ingrediente.save(update_fields=["activo"])
        return Response({"detail": "Ingrediente desactivado."})


# ─────────────────────────────────────────
# PLATO
# ─────────────────────────────────────────

class PlatoViewSet(viewsets.ModelViewSet):
    queryset = Plato.objects.select_related("categoria").prefetch_related(
        "ingredientes__ingrediente",
        "precios__restaurante",
    )
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "list":
            return PlatoListSerializer
        if self.action in ("create", "partial_update"):
            return PlatoWriteSerializer
        return PlatoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        activo = self.request.query_params.get("activo")
        categoria = self.request.query_params.get("categoria")
        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")
        if categoria:
            qs = qs.filter(categoria_id=categoria)
        return qs

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        plato = self.get_object()
        plato.activo = True
        plato.save(update_fields=["activo"])   # dispara plato.activated
        return Response({"detail": "Plato activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        plato = self.get_object()
        plato.activo = False
        plato.save(update_fields=["activo"])   # dispara plato.deactivated
        return Response({"detail": "Plato desactivado."})

    @action(detail=True, methods=["get", "post"], url_path="ingredientes")
    def ingredientes(self, request, pk=None):
        """
        GET  /platos/{id}/ingredientes/ → lista ingredientes del plato
        POST /platos/{id}/ingredientes/ → agrega un ingrediente al plato
        """
        plato = self.get_object()

        if request.method == "GET":
            qs = PlatoIngrediente.objects.filter(
                plato=plato).select_related("ingrediente")
            serializer = PlatoIngredienteSerializer(qs, many=True)
            return Response(serializer.data)

        serializer = PlatoIngredienteWriteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(plato=plato)    # dispara plato_ingrediente.added
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=["delete"],
        url_path="ingredientes/(?P<ingrediente_id>[^/.]+)"
    )
    def quitar_ingrediente(self, request, pk=None, ingrediente_id=None):
        """
        DELETE /platos/{id}/ingredientes/{ingrediente_id}/
        Elimina un ingrediente del plato — dispara plato_ingrediente.removed
        """
        plato = self.get_object()
        ingrediente = get_object_or_404(
            PlatoIngrediente,
            plato=plato,
            ingrediente_id=ingrediente_id
        )
        ingrediente.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────
# PRECIO PLATO
# ─────────────────────────────────────────

class PrecioPlatoViewSet(viewsets.ModelViewSet):
    queryset = PrecioPlato.objects.select_related("plato", "restaurante")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action in ("create", "partial_update"):
            return PrecioPlatoWriteSerializer
        return PrecioPlatoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        plato = self.request.query_params.get("plato")
        restaurante = self.request.query_params.get("restaurante")
        activo = self.request.query_params.get("activo")

        if plato:
            qs = qs.filter(plato_id=plato)
        if restaurante:
            qs = qs.filter(restaurante_id=restaurante)
        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")
        return qs

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        precio = self.get_object()
        precio.activo = True
        precio.save(update_fields=["activo"])   # dispara precio.activated
        return Response({"detail": "Precio activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        precio = self.get_object()
        precio.activo = False
        precio.save(update_fields=["activo"])   # dispara precio.deactivated
        return Response({"detail": "Precio desactivado."})

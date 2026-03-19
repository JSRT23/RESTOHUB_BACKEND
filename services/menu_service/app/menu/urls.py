from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import (
    RestauranteViewSet,
    CategoriaViewSet,
    IngredienteViewSet,
    PlatoViewSet,
    PrecioPlatoViewSet,
)

router = DefaultRouter()
router.register("restaurantes", RestauranteViewSet,  basename="restaurante")
router.register("categorias",   CategoriaViewSet,    basename="categoria")
router.register("ingredientes", IngredienteViewSet,  basename="ingrediente")
router.register("platos",       PlatoViewSet,        basename="plato")
router.register("precios",      PrecioPlatoViewSet,  basename="precio")

urlpatterns = [
    path("", include(router.urls)),
]

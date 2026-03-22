# app/loyalty/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from app.loyalty.views import (
    CatalogoCategoriaViewSet,
    CatalogoPlatoViewSet,
    CuponViewSet,
    PromocionViewSet,
    PuntosViewSet,
    TransaccionPuntosViewSet,
)

router = DefaultRouter()
router.register("puntos",               PuntosViewSet,
                basename="puntos")
router.register("transacciones",
                TransaccionPuntosViewSet, basename="transaccion")
router.register("promociones",          PromocionViewSet,
                basename="promocion")
router.register("cupones",              CuponViewSet,
                basename="cupon")
router.register("catalogo/platos",      CatalogoPlatoViewSet,
                basename="catalogo-plato")
router.register("catalogo/categorias",  CatalogoCategoriaViewSet,
                basename="catalogo-categoria")

urlpatterns = [
    path("", include(router.urls)),
]

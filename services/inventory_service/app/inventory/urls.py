from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    ProveedorViewSet,
    AlmacenViewSet,
    IngredienteInventarioViewSet,
    LoteIngredienteViewSet,
    OrdenCompraViewSet,
    AlertaStockViewSet,
)

router = DefaultRouter()
router.register("proveedores",    ProveedorViewSet,
                basename="proveedor")
router.register("almacenes",      AlmacenViewSet,
                basename="almacen")
router.register("stock",          IngredienteInventarioViewSet,
                basename="stock")
router.register("lotes",          LoteIngredienteViewSet,      basename="lote")
router.register("ordenes-compra", OrdenCompraViewSet,
                basename="orden-compra")
router.register("alertas",        AlertaStockViewSet,
                basename="alerta")

urlpatterns = [
    path("", include(router.urls)),
]

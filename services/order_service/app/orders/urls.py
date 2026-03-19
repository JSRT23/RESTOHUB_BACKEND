from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import PedidoViewSet, ComandaCocinaViewSet, EntregaPedidoViewSet

router = DefaultRouter()
router.register("pedidos",  PedidoViewSet,        basename="pedido")
router.register("comandas", ComandaCocinaViewSet,  basename="comanda")
router.register("entregas", EntregaPedidoViewSet,  basename="entrega")

urlpatterns = [
    path("", include(router.urls)),
]

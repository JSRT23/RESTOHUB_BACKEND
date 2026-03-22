from django.urls import include, path
from rest_framework.routers import DefaultRouter

from app.staff.views import (
    AlertaOperacionalViewSet,
    AsignacionCocinaViewSet,
    AsistenciaViewSet,
    EmpleadoViewSet,
    EstacionCocinaViewSet,
    PrediccionPersonalViewSet,
    ResumenNominaViewSet,
    RestauranteLocalViewSet,
    ServicioEntregaViewSet,
    TurnoViewSet,
)

router = DefaultRouter()
router.register("restaurantes",       RestauranteLocalViewSet,
                basename="restaurante")
router.register("empleados",          EmpleadoViewSet,
                basename="empleado")
router.register("turnos",             TurnoViewSet,
                basename="turno")
router.register("asistencia",         AsistenciaViewSet,
                basename="asistencia")
router.register("estaciones",         EstacionCocinaViewSet,
                basename="estacion")
router.register("asignaciones-cocina", AsignacionCocinaViewSet,
                basename="asignacion-cocina")
router.register("entregas",           ServicioEntregaViewSet,
                basename="entrega")
router.register("alertas",            AlertaOperacionalViewSet,
                basename="alerta")
router.register("nomina",             ResumenNominaViewSet,
                basename="nomina")
router.register("predicciones",       PrediccionPersonalViewSet,
                basename="prediccion")

urlpatterns = [
    path("", include(router.urls)),
]

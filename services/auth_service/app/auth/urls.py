# auth_service/app/auth/urls.py

from django.urls import path
from .views import (
    AutoRegistroView,
    CambiarPasswordView,
    DesactivarUsuarioView,
    ActivarUsuarioView,
    LoginView,
    LogoutView,
    MeView,
    ReenviarCodigoView,
    RefreshView,
    RegistroView,
    UsuarioDetailView,
    UsuariosView,
    VerificarCodigoView,
    VerificarTokenView,
    VincularEmpleadoView,        # ← NUEVO
)

urlpatterns = [
    # Auth básica
    path("login/",             LoginView.as_view(),          name="login"),
    path("refresh/",           RefreshView.as_view(),         name="refresh"),
    path("logout/",            LogoutView.as_view(),          name="logout"),
    path("me/",                MeView.as_view(),              name="me"),
    path("cambiar-password/",  CambiarPasswordView.as_view(),
         name="cambiar-password"),

    # Registro y verificación
    path("auto-registro/",     AutoRegistroView.as_view(),    name="auto-registro"),
    path("registro/",          RegistroView.as_view(),        name="registro"),
    path("verificar-codigo/",  VerificarCodigoView.as_view(),
         name="verificar-codigo"),
    path("reenviar-codigo/",   ReenviarCodigoView.as_view(),
         name="reenviar-codigo"),

    # Gestión de usuarios
    path("usuarios/",                UsuariosView.as_view(),          name="usuarios"),
    path("usuarios/<uuid:pk>/",      UsuarioDetailView.as_view(),
         name="usuario-detail"),

    # Activar / desactivar por email (llamados desde el gateway)
    path("usuarios/desactivar/",     DesactivarUsuarioView.as_view(),
         name="usuario-desactivar"),
    path("usuarios/activar/",        ActivarUsuarioView.as_view(),
         name="usuario-activar"),

    # Vincular empleado_id (llamado desde el gateway al crear empleado) ← NUEVO
    path("usuarios/vincular-empleado/", VincularEmpleadoView.as_view(),
         name="usuario-vincular-empleado"),

    # Verificación interna
    path("verificar/",         VerificarTokenView.as_view(),
         name="verificar-token"),
]

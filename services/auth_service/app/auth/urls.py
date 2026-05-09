# auth_service/app/auth_app/urls.py
# CAMBIO v2: Agregadas URLs de Cliente al final.
# Las URLs existentes sin cambios.

from django.urls import path

from .views import (
    ActivarUsuarioView,
    AutoRegistroView,
    BuscarClienteView,
    CambiarPasswordView,
    ClienteDetailView,
    ClienteListCreateView,
    DesactivarUsuarioView,
    DesvincularUsuarioClienteView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    RegistroView,
    UsuarioDetailView,
    UsuariosView,
    VerificarCodigoView,
    VerificarTokenView,
    VincularEmpleadoView,
    VincularUsuarioClienteView,
    ReenviarCodigoView,
)

urlpatterns = [
    # ── Auth básica ────────────────────────────────────────────────────────
    path("login/",            LoginView.as_view()),
    path("refresh/",          RefreshView.as_view()),
    path("logout/",           LogoutView.as_view()),
    path("me/",               MeView.as_view()),
    path("cambiar-password/", CambiarPasswordView.as_view()),

    # ── Registro + verificación ────────────────────────────────────────────
    path("auto-registro/",    AutoRegistroView.as_view()),
    path("verificar-codigo/", VerificarCodigoView.as_view()),
    path("reenviar-codigo/",  ReenviarCodigoView.as_view()),
    path("registro/",         RegistroView.as_view()),

    # ── Gestión de usuarios ────────────────────────────────────────────────
    path("usuarios/",                   UsuariosView.as_view()),
    path("usuarios/<uuid:pk>/",         UsuarioDetailView.as_view()),
    path("usuarios/desactivar/",        DesactivarUsuarioView.as_view()),
    path("usuarios/activar/",           ActivarUsuarioView.as_view()),
    path("usuarios/vincular-empleado/", VincularEmpleadoView.as_view()),

    # ── Verificación interna (gateway) ─────────────────────────────────────
    path("verificar-token/",            VerificarTokenView.as_view()),

    # ── NUEVO: Clientes (TPV / ventas en tienda) ───────────────────────────
    path("clientes/",
         ClienteListCreateView.as_view()),
    path("clientes/buscar/",                        BuscarClienteView.as_view()),
    path("clientes/<uuid:pk>/",
         ClienteDetailView.as_view()),
    path("clientes/<uuid:pk>/vincular-usuario/",
         VincularUsuarioClienteView.as_view()),
    path("clientes/<uuid:pk>/desvincular-usuario/",
         DesvincularUsuarioClienteView.as_view()),
]

# Rutas completas (prefijo /api/auth/):
#
# Auth:
#   POST /api/auth/login/
#   POST /api/auth/refresh/
#   POST /api/auth/logout/
#   GET  /api/auth/me/
#   POST /api/auth/cambiar-password/
#   POST /api/auth/auto-registro/
#   POST /api/auth/verificar-codigo/
#   POST /api/auth/reenviar-codigo/
#   POST /api/auth/registro/
#
# Usuarios:
#   GET   /api/auth/usuarios/
#   GET   /api/auth/usuarios/{id}/
#   PATCH /api/auth/usuarios/{id}/
#   POST  /api/auth/usuarios/desactivar/
#   POST  /api/auth/usuarios/activar/
#   POST  /api/auth/usuarios/vincular-empleado/
#   POST  /api/auth/verificar-token/
#
# Clientes (NUEVO):
#   GET   /api/auth/clientes/
#   POST  /api/auth/clientes/
#   GET   /api/auth/clientes/buscar/?cedula=&restaurante_id=
#   GET   /api/auth/clientes/{id}/
#   PATCH /api/auth/clientes/{id}/
#   POST  /api/auth/clientes/{id}/vincular-usuario/
#   POST  /api/auth/clientes/{id}/desvincular-usuario/

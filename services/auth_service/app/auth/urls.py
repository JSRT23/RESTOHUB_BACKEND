from django.urls import path
from . import views

urlpatterns = [
    # Auth básica
    path("login/",              views.LoginView.as_view(),          name="login"),
    path("refresh/",            views.RefreshView.as_view(),         name="refresh"),
    path("logout/",             views.LogoutView.as_view(),          name="logout"),
    path("me/",                 views.MeView.as_view(),              name="me"),
    path("cambiar-password/",   views.CambiarPasswordView.as_view(),
         name="cambiar-password"),

    # Registro público + verificación por código
    path("auto-registro/",      views.AutoRegistroView.as_view(),
         name="auto-registro"),
    path("verificar-codigo/",   views.VerificarCodigoView.as_view(),
         name="verificar-codigo"),
    path("reenviar-codigo/",    views.ReenviarCodigoView.as_view(),
         name="reenviar-codigo"),

    # Registro interno (admin/gerente crean operativos)
    path("registro/",           views.RegistroView.as_view(),        name="registro"),

    # Gestión de usuarios
    path("usuarios/",           views.UsuariosView.as_view(),        name="usuarios"),
    path("usuarios/<uuid:pk>/", views.UsuarioDetailView.as_view(),
         name="usuario-detail"),

    # Verificación interna del gateway
    path("verificar/",          views.VerificarTokenView.as_view(),
         name="verificar-token"),
]

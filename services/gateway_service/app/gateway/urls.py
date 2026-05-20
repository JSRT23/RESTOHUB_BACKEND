# gateway_service/app/gateway/urls_pagos.py

from django.urls import path
from .views import CrearPreferenciaView, EmailConfirmacionView

urlpatterns = [
    path("crear-preferencia/",   CrearPreferenciaView.as_view(),
         name="crear_preferencia"),
    path("email-confirmacion/",  EmailConfirmacionView.as_view(),
         name="email_confirmacion"),
]

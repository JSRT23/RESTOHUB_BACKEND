# auth_service/app/auth_app/admin.py
# CAMBIO v2: Agregado ClienteAdmin para gestionar clientes del TPV.
# UsuarioAdmin y RefreshTokenAdmin sin cambios.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Cliente, EmailVerificationCode, RefreshToken, Usuario


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ("email", "nombre", "rol", "restaurante_id", "activo")
    list_filter = ("rol", "activo")
    search_fields = ("email", "nombre")
    ordering = ("email",)
    fieldsets = (
        (None,              {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("nombre",)}),
        ("Rol y acceso",    {
         "fields": ("rol", "restaurante_id", "empleado_id", "activo")}),
        ("Permisos",        {"fields": ("is_staff",
         "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "nombre", "rol", "restaurante_id", "empleado_id", "password1", "password2"),
        }),
    )


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("usuario", "revocado", "creado_at", "expira_at")
    list_filter = ("revocado",)
    search_fields = ("usuario__email",)
    readonly_fields = ("token", "creado_at")


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ("usuario", "codigo", "intentos", "creado_at", "expira_at")
    list_filter = ("intentos",)
    search_fields = ("usuario__email",)
    readonly_fields = ("codigo", "creado_at")


# ── NUEVO: Cliente ─────────────────────────────────────────────────────────

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        "cedula", "tipo_documento", "nombre_completo",
        "email", "telefono", "restaurante_id",
        "tiene_cuenta_app", "activo",
    )
    list_filter = ("tipo_documento", "activo")
    search_fields = ("cedula", "nombre", "apellido", "email", "telefono")
    ordering = ("nombre", "apellido")
    readonly_fields = ("id", "nombre_completo",
                       "tiene_cuenta_app", "created_at", "updated_at")
    fieldsets = (
        ("Identificación", {
            "fields": ("id", "tipo_documento", "cedula"),
        }),
        ("Datos personales", {
            "fields": ("nombre", "apellido", "email", "telefono"),
        }),
        ("Vinculaciones", {
            "fields": ("restaurante_id", "usuario_id"),
            "description": (
                "restaurante_id: restaurante que registró al cliente (null = global). "
                "usuario_id: cuenta de la app móvil vinculada para acumular puntos."
            ),
        }),
        ("Estado", {
            "fields": ("activo", "notas"),
        }),
        ("Auditoría", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def nombre_completo(self, obj):
        return obj.nombre_completo
    nombre_completo.short_description = "Nombre completo"

    def tiene_cuenta_app(self, obj):
        return obj.tiene_cuenta_app
    tiene_cuenta_app.boolean = True
    tiene_cuenta_app.short_description = "App vinculada"

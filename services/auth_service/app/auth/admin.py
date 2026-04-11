from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Usuario, RefreshToken


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ("email", "nombre", "rol", "restaurante_id", "activo")
    list_filter = ("rol", "activo")
    search_fields = ("email", "nombre")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("nombre",)}),
        ("Rol y acceso", {
         "fields": ("rol", "restaurante_id", "empleado_id", "activo")}),
        ("Permisos", {"fields": ("is_staff",
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

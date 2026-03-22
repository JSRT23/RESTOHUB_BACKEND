from django.contrib import admin
from django.utils.html import format_html

from app.loyalty.models import (
    AplicacionPromocion,
    CatalogoCategoria,
    CatalogoPlato,
    CuentaPuntos,
    Cupon,
    Promocion,
    ReglaPromocion,
    TransaccionPuntos,
)


# ---------------------------------------------------------------------------
# CuentaPuntos
# ---------------------------------------------------------------------------

class TransaccionPuntosInline(admin.TabularInline):
    model = TransaccionPuntos
    extra = 0
    max_num = 10
    ordering = ("-created_at",)
    readonly_fields = ("tipo", "puntos", "saldo_anterior", "saldo_posterior",
                       "pedido_id", "descripcion", "created_at")
    fields = ("tipo", "puntos", "saldo_anterior", "saldo_posterior",
              "descripcion", "created_at")
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CuentaPuntos)
class CuentaPuntosAdmin(admin.ModelAdmin):
    list_display = ("cliente_id", "saldo_display", "nivel_display",
                    "puntos_totales_historicos", "ultima_actualizacion")
    list_filter = ("nivel",)
    search_fields = ("cliente_id",)
    readonly_fields = ("id", "puntos_totales_historicos",
                       "created_at", "ultima_actualizacion")
    ordering = ("-ultima_actualizacion",)
    inlines = [TransaccionPuntosInline]

    fieldsets = (
        ("Cuenta", {
            "fields": ("id", "cliente_id", "nivel")
        }),
        ("Puntos", {
            "fields": ("saldo", "puntos_totales_historicos")
        }),
        ("Auditoría", {
            "fields": ("created_at", "ultima_actualizacion"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Saldo")
    def saldo_display(self, obj):
        color = "green" if obj.saldo > 0 else "gray"
        return format_html(
            '<span style="color:{}; font-weight:bold">{} pts</span>',
            color, obj.saldo,
        )

    @admin.display(description="Nivel")
    def nivel_display(self, obj):
        colores = {
            "bronce":   "#cd7f32",
            "plata":    "#aaa9ad",
            "oro":      "#d4af37",
            "diamante": "#b9f2ff",
        }
        color = colores.get(obj.nivel, "#000")
        return format_html(
            '<span style="color:{}; font-weight:bold">{}</span>',
            color, obj.get_nivel_display(),
        )


# ---------------------------------------------------------------------------
# TransaccionPuntos
# ---------------------------------------------------------------------------

@admin.register(TransaccionPuntos)
class TransaccionPuntosAdmin(admin.ModelAdmin):
    list_display = ("cuenta", "tipo_display", "puntos_display",
                    "saldo_posterior", "descripcion_corta", "created_at")
    list_filter = ("tipo",)
    search_fields = ("cuenta__cliente_id", "descripcion")
    readonly_fields = ("id", "saldo_anterior", "saldo_posterior", "created_at")
    ordering = ("-created_at",)

    @admin.display(description="Tipo")
    def tipo_display(self, obj):
        colores = {
            "acumulacion": "green",
            "bono":        "blue",
            "canje":       "orange",
            "vencimiento": "red",
            "ajuste":      "gray",
        }
        color = colores.get(obj.tipo, "black")
        return format_html(
            '<span style="color:{}; font-weight:bold">{}</span>',
            color, obj.get_tipo_display(),
        )

    @admin.display(description="Puntos")
    def puntos_display(self, obj):
        if obj.puntos >= 0:
            return format_html('<span style="color:green">+{}</span>', obj.puntos)
        return format_html('<span style="color:red">{}</span>', obj.puntos)

    @admin.display(description="Descripción")
    def descripcion_corta(self, obj):
        return obj.descripcion[:60] + "..." if len(obj.descripcion) > 60 else obj.descripcion


# ---------------------------------------------------------------------------
# Promocion + ReglaPromocion inline
# ---------------------------------------------------------------------------

class ReglaPromocionInline(admin.TabularInline):
    model = ReglaPromocion
    extra = 1
    fields = ("tipo_condicion", "monto_minimo", "moneda",
              "plato_id", "categoria_id", "hora_inicio", "hora_fin")


class AplicacionPromocionInline(admin.TabularInline):
    model = AplicacionPromocion
    extra = 0
    max_num = 10
    readonly_fields = ("pedido_id", "cliente_id", "descuento_aplicado",
                       "puntos_bonus_otorgados", "applied_at")
    fields = ("pedido_id", "cliente_id", "descuento_aplicado",
              "puntos_bonus_otorgados", "applied_at")
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "alcance_display", "tipo_beneficio_display",
                    "valor", "fecha_inicio", "fecha_fin", "activa_display")
    list_filter = ("activa", "alcance", "tipo_beneficio")
    search_fields = ("nombre", "marca")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    inlines = [ReglaPromocionInline, AplicacionPromocionInline]
    actions = ["activar_promociones", "desactivar_promociones"]

    fieldsets = (
        ("Identificación", {
            "fields": ("id", "nombre", "descripcion")
        }),
        ("Alcance", {
            "fields": ("alcance", "marca", "restaurante_id")
        }),
        ("Beneficio", {
            "fields": ("tipo_beneficio", "valor", "puntos_bonus", "multiplicador_puntos")
        }),
        ("Vigencia", {
            "fields": ("fecha_inicio", "fecha_fin", "activa")
        }),
        ("Auditoría", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Alcance")
    def alcance_display(self, obj):
        colores = {"global": "purple", "marca": "blue", "local": "teal"}
        color = colores.get(obj.alcance, "black")
        return format_html(
            '<span style="color:{}; font-weight:bold">{}</span>',
            color, obj.get_alcance_display(),
        )

    @admin.display(description="Beneficio")
    def tipo_beneficio_display(self, obj):
        return obj.get_tipo_beneficio_display()

    @admin.display(description="Activa")
    def activa_display(self, obj):
        if obj.activa:
            return format_html('<span style="color:green; font-weight:bold">Sí</span>')
        return format_html('<span style="color:red">No</span>')

    @admin.action(description="Activar seleccionadas")
    def activar_promociones(self, request, queryset):
        count = queryset.update(activa=True)
        self.message_user(request, f"{count} promoción(es) activada(s).")

    @admin.action(description="Desactivar seleccionadas")
    def desactivar_promociones(self, request, queryset):
        count = queryset.update(activa=False)
        self.message_user(request, f"{count} promoción(es) desactivada(s).")


# ---------------------------------------------------------------------------
# ReglaPromocion
# ---------------------------------------------------------------------------

@admin.register(ReglaPromocion)
class ReglaPromocionAdmin(admin.ModelAdmin):
    list_display = ("promocion", "tipo_condicion_display",
                    "monto_minimo", "plato_id", "categoria_id",
                    "hora_rango")
    list_filter = ("tipo_condicion",)
    search_fields = ("promocion__nombre",)
    readonly_fields = ("id", "created_at")

    @admin.display(description="Condición")
    def tipo_condicion_display(self, obj):
        return obj.get_tipo_condicion_display()

    @admin.display(description="Horario")
    def hora_rango(self, obj):
        if obj.hora_inicio is not None and obj.hora_fin is not None:
            return f"{obj.hora_inicio:02d}:00 – {obj.hora_fin:02d}:00"
        return "—"


# ---------------------------------------------------------------------------
# AplicacionPromocion
# ---------------------------------------------------------------------------

@admin.register(AplicacionPromocion)
class AplicacionPromocionAdmin(admin.ModelAdmin):
    list_display = ("promocion", "cliente_id", "pedido_id",
                    "descuento_aplicado", "puntos_bonus_otorgados", "applied_at")
    list_filter = ("promocion",)
    search_fields = ("cliente_id", "pedido_id")
    readonly_fields = ("id", "applied_at")
    ordering = ("-applied_at",)


# ---------------------------------------------------------------------------
# Cupon
# ---------------------------------------------------------------------------

@admin.register(Cupon)
class CuponAdmin(admin.ModelAdmin):
    list_display = ("codigo", "tipo_descuento_display", "valor_descuento",
                    "cliente_id", "usos_actuales", "limite_uso",
                    "fecha_fin", "disponible_display", "activo")
    list_filter = ("activo", "tipo_descuento")
    search_fields = ("codigo", "cliente_id")
    readonly_fields = ("id", "usos_actuales", "created_at", "updated_at")
    ordering = ("-created_at",)
    actions = ["desactivar_cupones"]

    fieldsets = (
        ("Cupón", {
            "fields": ("id", "codigo", "promocion", "cliente_id")
        }),
        ("Descuento", {
            "fields": ("tipo_descuento", "valor_descuento")
        }),
        ("Uso", {
            "fields": ("limite_uso", "usos_actuales", "activo")
        }),
        ("Vigencia", {
            "fields": ("fecha_inicio", "fecha_fin")
        }),
        ("Auditoría", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Tipo")
    def tipo_descuento_display(self, obj):
        return obj.get_tipo_descuento_display()

    @admin.display(description="Disponible")
    def disponible_display(self, obj):
        if obj.disponible:
            return format_html('<span style="color:green; font-weight:bold">Sí</span>')
        return format_html('<span style="color:red">No</span>')

    @admin.action(description="Desactivar cupones seleccionados")
    def desactivar_cupones(self, request, queryset):
        count = queryset.update(activo=False)
        self.message_user(request, f"{count} cupón(es) desactivado(s).")


# ---------------------------------------------------------------------------
# CatalogoPlato
# ---------------------------------------------------------------------------

@admin.register(CatalogoPlato)
class CatalogoPlatoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "plato_id", "categoria_id",
                    "activo", "updated_at")
    list_filter = ("activo",)
    search_fields = ("nombre", "plato_id")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("nombre",)


# ---------------------------------------------------------------------------
# CatalogoCategoria
# ---------------------------------------------------------------------------

@admin.register(CatalogoCategoria)
class CatalogoCategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria_id", "activo", "updated_at")
    list_filter = ("activo",)
    search_fields = ("nombre", "categoria_id")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("nombre",)

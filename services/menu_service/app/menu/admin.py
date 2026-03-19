from django.contrib import admin
from .models import Restaurante, Categoria, Plato, Ingrediente, PlatoIngrediente, PrecioPlato


# ─────────────────────────────────────────
# INLINE: PlatoIngrediente dentro de Plato
# ─────────────────────────────────────────

class PlatoIngredienteInline(admin.TabularInline):
    model = PlatoIngrediente
    extra = 1
    fields = ("ingrediente", "cantidad")
    autocomplete_fields = ("ingrediente",)


# ─────────────────────────────────────────
# INLINE: PrecioPlato dentro de Plato
# ─────────────────────────────────────────

class PrecioPlotoInline(admin.TabularInline):
    model = PrecioPlato
    extra = 1
    fields = ("restaurante", "precio", "fecha_inicio", "fecha_fin", "activo")
    autocomplete_fields = ("restaurante",)


# ─────────────────────────────────────────
# RESTAURANTE
# ─────────────────────────────────────────

@admin.register(Restaurante)
class RestauranteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ciudad", "pais",
                    "moneda", "activo", "fecha_creacion")
    list_filter = ("activo", "pais", "moneda")
    search_fields = ("nombre", "ciudad", "pais")
    ordering = ("pais", "ciudad", "nombre")
    readonly_fields = ("id", "fecha_creacion", "fecha_actualizacion")

    fieldsets = (
        ("Información general", {
            "fields": ("id", "nombre", "direccion")
        }),
        ("Ubicación", {
            "fields": ("pais", "ciudad")
        }),
        ("Configuración", {
            "fields": ("moneda", "activo")
        }),
        ("Auditoría", {
            "fields": ("fecha_creacion", "fecha_actualizacion"),
            "classes": ("collapse",),
        }),
    )

    # Activar/desactivar desde el listado
    actions = ("activar_restaurantes", "desactivar_restaurantes")

    @admin.action(description="Activar restaurantes seleccionados")
    def activar_restaurantes(self, request, queryset):
        for obj in queryset:
            obj.activo = True
            # dispara RESTAURANTE_UPDATED (no DEACTIVATED)
            obj.save(update_fields=["activo"])
        self.message_user(
            request, f"{queryset.count()} restaurante(s) activado(s).")

    @admin.action(description="Desactivar restaurantes seleccionados")
    def desactivar_restaurantes(self, request, queryset):
        for obj in queryset:
            obj.activo = False
            # dispara RESTAURANTE_DEACTIVATED
            obj.save(update_fields=["activo"])
        self.message_user(
            request, f"{queryset.count()} restaurante(s) desactivado(s).")


# ─────────────────────────────────────────
# CATEGORIA
# ─────────────────────────────────────────

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)
    ordering = ("orden", "nombre")
    readonly_fields = ("id",)

    actions = ("activar_categorias", "desactivar_categorias")

    @admin.action(description="Activar categorías seleccionadas")
    def activar_categorias(self, request, queryset):
        for obj in queryset:
            obj.activo = True
            obj.save(update_fields=["activo"])
        self.message_user(
            request, f"{queryset.count()} categoría(s) activada(s).")

    @admin.action(description="Desactivar categorías seleccionadas")
    def desactivar_categorias(self, request, queryset):
        for obj in queryset:
            obj.activo = False
            # dispara CATEGORIA_DEACTIVATED
            obj.save(update_fields=["activo"])
        self.message_user(
            request, f"{queryset.count()} categoría(s) desactivada(s).")


# ─────────────────────────────────────────
# INGREDIENTE
# ─────────────────────────────────────────

@admin.register(Ingrediente)
class IngredienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "unidad_medida", "activo")
    list_filter = ("activo", "unidad_medida")
    search_fields = ("nombre",)
    ordering = ("nombre",)
    readonly_fields = ("id",)

    actions = ("activar_ingredientes", "desactivar_ingredientes")

    @admin.action(description="Activar ingredientes seleccionados")
    def activar_ingredientes(self, request, queryset):
        for obj in queryset:
            obj.activo = True
            obj.save(update_fields=["activo"])
        self.message_user(
            request, f"{queryset.count()} ingrediente(s) activado(s).")

    @admin.action(description="Desactivar ingredientes seleccionados")
    def desactivar_ingredientes(self, request, queryset):
        for obj in queryset:
            obj.activo = False
            # dispara INGREDIENTE_DEACTIVATED
            obj.save(update_fields=["activo"])
        self.message_user(
            request, f"{queryset.count()} ingrediente(s) desactivado(s).")


# ─────────────────────────────────────────
# PLATO
# ─────────────────────────────────────────

@admin.register(Plato)
class PlatoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "activo",
                    "fecha_creacion", "fecha_actualizacion")
    list_filter = ("activo", "categoria")
    search_fields = ("nombre", "descripcion")
    ordering = ("nombre",)
    readonly_fields = ("id", "fecha_creacion", "fecha_actualizacion")
    autocomplete_fields = ("categoria",)

    fieldsets = (
        ("Información general", {
            "fields": ("id", "nombre", "descripcion", "imagen")
        }),
        ("Clasificación", {
            "fields": ("categoria", "activo")
        }),
        ("Auditoría", {
            "fields": ("fecha_creacion", "fecha_actualizacion"),
            "classes": ("collapse",),
        }),
    )

    inlines = (PlatoIngredienteInline, PrecioPlotoInline)

    actions = ("activar_platos", "desactivar_platos")

    @admin.action(description="Activar platos seleccionados")
    def activar_platos(self, request, queryset):
        for obj in queryset:
            obj.activo = True
            obj.save(update_fields=["activo"])   # dispara PLATO_ACTIVATED
        self.message_user(request, f"{queryset.count()} plato(s) activado(s).")

    @admin.action(description="Desactivar platos seleccionados")
    def desactivar_platos(self, request, queryset):
        for obj in queryset:
            obj.activo = False
            obj.save(update_fields=["activo"])   # dispara PLATO_DEACTIVATED
        self.message_user(
            request, f"{queryset.count()} plato(s) desactivado(s).")


# ─────────────────────────────────────────
# PRECIO PLATO
# ─────────────────────────────────────────

@admin.register(PrecioPlato)
class PrecioPlatoAdmin(admin.ModelAdmin):
    list_display = ("plato", "restaurante", "precio", "moneda_restaurante",
                    "esta_vigente", "activo", "fecha_inicio", "fecha_fin")
    list_filter = ("activo", "restaurante__pais", "restaurante")
    search_fields = ("plato__nombre", "restaurante__nombre")
    ordering = ("-fecha_inicio",)
    readonly_fields = ("id", "esta_vigente")
    autocomplete_fields = ("plato", "restaurante")

    fieldsets = (
        ("Relación", {
            "fields": ("id", "plato", "restaurante")
        }),
        ("Precio", {
            "fields": ("precio", "esta_vigente")
        }),
        ("Vigencia", {
            "fields": ("fecha_inicio", "fecha_fin", "activo")
        }),
    )

    actions = ("activar_precios", "desactivar_precios")

    @admin.display(description="Moneda")
    def moneda_restaurante(self, obj):
        return obj.restaurante.moneda

    @admin.display(description="Vigente", boolean=True)
    def esta_vigente(self, obj):
        return obj.esta_vigente

    @admin.action(description="Activar precios seleccionados")
    def activar_precios(self, request, queryset):
        for obj in queryset:
            obj.activo = True
            obj.save(update_fields=["activo"])   # dispara PRECIO_ACTIVATED
        self.message_user(
            request, f"{queryset.count()} precio(s) activado(s).")

    @admin.action(description="Desactivar precios seleccionados")
    def desactivar_precios(self, request, queryset):
        for obj in queryset:
            obj.activo = False
            obj.save(update_fields=["activo"])   # dispara PRECIO_DEACTIVATED
        self.message_user(
            request, f"{queryset.count()} precio(s) desactivado(s).")

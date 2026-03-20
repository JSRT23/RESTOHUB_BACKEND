from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import (
    Proveedor, Almacen, RecetaPlato,
    IngredienteInventario, LoteIngrediente,
    MovimientoInventario, OrdenCompra,
    DetalleOrdenCompra, AlertaStock,
)


# ─────────────────────────────────────────
# PROVEEDOR
# ─────────────────────────────────────────

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "pais", "ciudad",
                    "moneda_preferida", "email", "activo")
    list_filter = ("activo", "pais", "moneda_preferida")
    search_fields = ("nombre", "email", "pais", "ciudad")
    ordering = ("nombre",)
    readonly_fields = ("id", "fecha_creacion", "fecha_actualizacion")

    fieldsets = (
        ("Información general", {
            "fields": ("id", "nombre", "moneda_preferida", "activo")
        }),
        ("Ubicación", {
            "fields": ("pais", "ciudad")
        }),
        ("Contacto", {
            "fields": ("telefono", "email")
        }),
        ("Auditoría", {
            "fields": ("fecha_creacion", "fecha_actualizacion"),
            "classes": ("collapse",),
        }),
    )

    actions = ("activar_proveedores", "desactivar_proveedores")

    @admin.action(description="Activar proveedores seleccionados")
    def activar_proveedores(self, request, queryset):
        queryset.update(activo=True)
        self.message_user(
            request, f"{queryset.count()} proveedor(es) activado(s).")

    @admin.action(description="Desactivar proveedores seleccionados")
    def desactivar_proveedores(self, request, queryset):
        queryset.update(activo=False)
        self.message_user(
            request, f"{queryset.count()} proveedor(es) desactivado(s).")


# ─────────────────────────────────────────
# ALMACÉN
# ─────────────────────────────────────────

@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ("nombre", "restaurante_id", "activo", "fecha_creacion")
    list_filter = ("activo",)
    search_fields = ("nombre", "restaurante_id")
    ordering = ("restaurante_id", "nombre")
    readonly_fields = ("id", "fecha_creacion", "fecha_actualizacion")

    fieldsets = (
        ("Información", {
            "fields": ("id", "nombre", "descripcion", "activo")
        }),
        ("Restaurante", {
            "fields": ("restaurante_id",)
        }),
        ("Auditoría", {
            "fields": ("fecha_creacion", "fecha_actualizacion"),
            "classes": ("collapse",),
        }),
    )


# ─────────────────────────────────────────
# RECETA PLATO
# ─────────────────────────────────────────

@admin.register(RecetaPlato)
class RecetaPlatoAdmin(admin.ModelAdmin):
    list_display = ("plato_id", "nombre_ingrediente", "cantidad",
                    "unidad_medida", "fecha_actualizacion")
    search_fields = ("nombre_ingrediente", "plato_id", "ingrediente_id")
    ordering = ("plato_id", "nombre_ingrediente")
    readonly_fields = ("id", "fecha_actualizacion")

    def has_add_permission(self, request):
        return False     # se gestiona exclusivamente por eventos RabbitMQ

    def has_delete_permission(self, request, obj=None):
        return False     # se gestiona exclusivamente por eventos RabbitMQ


# ─────────────────────────────────────────
# INGREDIENTE INVENTARIO
# ─────────────────────────────────────────

@admin.register(IngredienteInventario)
class IngredienteInventarioAdmin(admin.ModelAdmin):
    list_display = (
        "nombre_ingrediente", "almacen", "cantidad_actual",
        "nivel_minimo", "unidad_medida", "estado_stock",
        "porcentaje_stock_display", "fecha_actualizacion",
    )
    list_filter = ("almacen", "unidad_medida")
    search_fields = ("nombre_ingrediente", "ingrediente_id")
    ordering = ("almacen", "nombre_ingrediente")
    readonly_fields = (
        "id", "fecha_creacion", "fecha_actualizacion",
        "necesita_reposicion", "esta_agotado", "porcentaje_stock",
    )
    autocomplete_fields = ("almacen",)

    fieldsets = (
        ("Referencia", {
            "fields": ("id", "ingrediente_id", "nombre_ingrediente", "unidad_medida")
        }),
        ("Stock", {
            "fields": ("almacen", "cantidad_actual", "nivel_minimo", "nivel_maximo", "lote_actual")
        }),
        ("Estado calculado", {
            "fields": ("necesita_reposicion", "esta_agotado", "porcentaje_stock"),
            "classes": ("collapse",),
        }),
        ("Auditoría", {
            "fields": ("fecha_creacion", "fecha_actualizacion"),
            "classes": ("collapse",),
        }),
    )

    actions = ("ajuste_stock",)

    @admin.display(description="Estado")
    def estado_stock(self, obj):
        if obj.esta_agotado:
            return format_html('<span style="color:#A32D2D;font-weight:500">Agotado</span>')
        if obj.necesita_reposicion:
            return format_html('<span style="color:#BA7517;font-weight:500">Stock bajo</span>')
        return format_html('<span style="color:#0F6E56;font-weight:500">OK</span>')

    @admin.display(description="% Stock")
    def porcentaje_stock_display(self, obj):
        pct = round(obj.porcentaje_stock, 1)
        color = "#A32D2D" if pct < 20 else "#BA7517" if pct < 50 else "#0F6E56"
        return format_html(
            '<span style="color:{}">{} %</span>', color, pct
        )


# ─────────────────────────────────────────
# LOTE INGREDIENTE
# ─────────────────────────────────────────

@admin.register(LoteIngrediente)
class LoteIngredienteAdmin(admin.ModelAdmin):
    list_display = (
        "numero_lote", "almacen", "proveedor",
        "cantidad_actual", "cantidad_recibida", "unidad_medida",
        "estado", "fecha_vencimiento", "dias_vencer_display",
    )
    list_filter = ("estado", "almacen", "proveedor")
    search_fields = ("numero_lote", "ingrediente_id")
    ordering = ("fecha_vencimiento",)
    readonly_fields = (
        "id", "fecha_recepcion", "fecha_actualizacion",
        "esta_vencido", "dias_para_vencer",
    )
    autocomplete_fields = ("almacen", "proveedor")

    fieldsets = (
        ("Identificación", {
            "fields": ("id", "ingrediente_id", "numero_lote", "proveedor", "almacen")
        }),
        ("Cantidades", {
            "fields": ("cantidad_recibida", "cantidad_actual", "unidad_medida")
        }),
        ("Fechas", {
            "fields": ("fecha_produccion", "fecha_vencimiento", "esta_vencido", "dias_para_vencer")
        }),
        ("Estado", {
            "fields": ("estado",)
        }),
        ("Auditoría", {
            "fields": ("fecha_recepcion", "fecha_actualizacion"),
            "classes": ("collapse",),
        }),
    )

    actions = ("marcar_vencido", "marcar_retirado")

    @admin.display(description="Días para vencer")
    def dias_vencer_display(self, obj):
        dias = obj.dias_para_vencer
        if dias < 0:
            return format_html('<span style="color:#A32D2D;font-weight:500">Vencido ({} días)</span>', abs(dias))
        if dias <= 3:
            return format_html('<span style="color:#BA7517;font-weight:500">{} días</span>', dias)
        return format_html('<span style="color:#0F6E56">{} días</span>', dias)

    @admin.action(description="Marcar lotes como VENCIDO")
    def marcar_vencido(self, request, queryset):
        for obj in queryset:
            obj.estado = "VENCIDO"
            obj.save(update_fields=["estado"])
        self.message_user(
            request, f"{queryset.count()} lote(s) marcado(s) como vencido.")

    @admin.action(description="Marcar lotes como RETIRADO")
    def marcar_retirado(self, request, queryset):
        for obj in queryset:
            obj.estado = "RETIRADO"
            obj.save(update_fields=["estado"])
        self.message_user(
            request, f"{queryset.count()} lote(s) marcado(s) como retirado.")


# ─────────────────────────────────────────
# MOVIMIENTO INVENTARIO — solo lectura
# ─────────────────────────────────────────

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = (
        "tipo_movimiento", "ingrediente_inventario",
        "cantidad", "cantidad_antes", "cantidad_despues",
        "pedido_id", "fecha",
    )
    list_filter = ("tipo_movimiento",)
    search_fields = ("pedido_id", "orden_compra_id",
                     "ingrediente_inventario__nombre_ingrediente")
    ordering = ("-fecha",)
    readonly_fields = (
        "id", "ingrediente_inventario", "lote", "tipo_movimiento",
        "cantidad", "cantidad_antes", "cantidad_despues",
        "pedido_id", "orden_compra_id", "descripcion", "fecha",
    )

    def has_add_permission(self, request):
        return False     # append-only — solo se crea por código

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ─────────────────────────────────────────
# DETALLE ORDEN COMPRA — inline
# ─────────────────────────────────────────

class DetalleOrdenCompraInline(admin.TabularInline):
    model = DetalleOrdenCompra
    extra = 1
    fields = (
        "ingrediente_id", "nombre_ingrediente", "unidad_medida",
        "cantidad", "cantidad_recibida", "precio_unitario", "subtotal",
    )
    readonly_fields = ("subtotal",)


# ─────────────────────────────────────────
# ORDEN COMPRA
# ─────────────────────────────────────────

@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = (
        "id_corto", "proveedor", "restaurante_id",
        "estado", "total_estimado", "moneda",
        "fecha_creacion", "fecha_entrega_estimada",
    )
    list_filter = ("estado", "moneda", "proveedor")
    search_fields = ("proveedor__nombre", "restaurante_id")
    ordering = ("-fecha_creacion",)
    readonly_fields = ("id", "fecha_creacion", "total_estimado")
    autocomplete_fields = ("proveedor",)

    fieldsets = (
        ("Identificación", {
            "fields": ("id", "proveedor", "restaurante_id")
        }),
        ("Estado", {
            "fields": ("estado", "moneda", "total_estimado")
        }),
        ("Fechas", {
            "fields": ("fecha_creacion", "fecha_entrega_estimada", "fecha_recepcion")
        }),
        ("Notas", {
            "fields": ("notas",),
            "classes": ("collapse",),
        }),
    )

    inlines = (DetalleOrdenCompraInline,)

    actions = ("enviar_orden", "marcar_recibida", "cancelar_orden")

    @admin.display(description="ID")
    def id_corto(self, obj):
        return f"OC-{str(obj.id)[:8]}"

    @admin.action(description="Enviar órdenes seleccionadas")
    def enviar_orden(self, request, queryset):
        for obj in queryset.filter(estado="PENDIENTE"):
            obj.estado = "ENVIADA"
            obj.save(update_fields=["estado"])   # dispara orden_compra.enviada
        self.message_user(request, "Órdenes enviadas.")

    @admin.action(description="Marcar como RECIBIDA")
    def marcar_recibida(self, request, queryset):
        for obj in queryset.filter(estado="ENVIADA"):
            obj.estado = "RECIBIDA"
            obj.fecha_recepcion = timezone.now()
            # dispara orden_compra.recibida
            obj.save(update_fields=["estado", "fecha_recepcion"])
        self.message_user(request, "Órdenes marcadas como recibidas.")

    @admin.action(description="Cancelar órdenes seleccionadas")
    def cancelar_orden(self, request, queryset):
        for obj in queryset.exclude(estado__in=["RECIBIDA", "CANCELADA"]):
            obj.estado = "CANCELADA"
            # dispara orden_compra.cancelada
            obj.save(update_fields=["estado"])
        self.message_user(request, "Órdenes canceladas.")


# ─────────────────────────────────────────
# ALERTA STOCK
# ─────────────────────────────────────────

@admin.register(AlertaStock)
class AlertaStockAdmin(admin.ModelAdmin):
    list_display = (
        "tipo_alerta", "ingrediente_inventario", "restaurante_id",
        "nivel_actual", "nivel_minimo", "estado",
        "fecha_alerta", "fecha_resolucion",
    )
    list_filter = ("tipo_alerta", "estado")
    search_fields = (
        "ingrediente_inventario__nombre_ingrediente", "restaurante_id")
    ordering = ("-fecha_alerta",)
    readonly_fields = (
        "id", "ingrediente_inventario", "almacen",
        "restaurante_id", "ingrediente_id", "tipo_alerta",
        "nivel_actual", "nivel_minimo", "lote",
        "fecha_alerta", "fecha_resolucion",
    )

    actions = ("resolver_alertas", "ignorar_alertas")

    @admin.action(description="Marcar alertas como RESUELTAS")
    def resolver_alertas(self, request, queryset):
        for obj in queryset.filter(estado="PENDIENTE"):
            obj.resolver()
        self.message_user(request, "Alertas resueltas.")

    @admin.action(description="Ignorar alertas seleccionadas")
    def ignorar_alertas(self, request, queryset):
        for obj in queryset.filter(estado="PENDIENTE"):
            obj.estado = "IGNORADA"
            obj.save(update_fields=["estado"])
        self.message_user(request, "Alertas ignoradas.")

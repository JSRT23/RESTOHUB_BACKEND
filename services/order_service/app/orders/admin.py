from django.contrib import admin
from django.utils import timezone
from .models import Pedido, DetallePedido, ComandaCocina, SeguimientoPedido, EntregaPedido


# ─────────────────────────────────────────
# INLINES
# ─────────────────────────────────────────

class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 1
    fields = ("plato_id", "nombre_plato", "precio_unitario",
              "cantidad", "subtotal", "notas")
    readonly_fields = ("subtotal",)


class ComandaCocinaInline(admin.TabularInline):
    model = ComandaCocina
    extra = 0
    fields = ("estacion", "estado", "hora_envio",
              "hora_fin", "tiempo_preparacion_segundos")
    readonly_fields = ("hora_envio", "tiempo_preparacion_segundos")


class SeguimientoPedidoInline(admin.TabularInline):
    model = SeguimientoPedido
    extra = 0
    fields = ("estado", "fecha", "descripcion")
    readonly_fields = ("estado", "fecha")

    def has_add_permission(self, request, obj=None):
        return False  # el seguimiento es append-only, no se crea manualmente


class EntregaPedidoInline(admin.StackedInline):
    model = EntregaPedido
    extra = 0
    fields = (
        "tipo_entrega", "direccion",
        "repartidor_id", "repartidor_nombre",
        "estado_entrega", "fecha_salida", "fecha_entrega_real",
    )


# ─────────────────────────────────────────
# PEDIDO
# ─────────────────────────────────────────

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id_corto", "restaurante_id", "canal", "estado",
        "prioridad", "total", "moneda", "fecha_creacion"
    )
    list_filter = ("estado", "canal", "prioridad", "moneda")
    search_fields = ("id", "restaurante_id", "cliente_id")
    ordering = ("-fecha_creacion",)
    readonly_fields = ("id", "fecha_creacion")

    fieldsets = (
        ("Identificación", {
            "fields": ("id", "restaurante_id", "cliente_id", "mesa_id")
        }),
        ("Pedido", {
            "fields": ("canal", "estado", "prioridad")
        }),
        ("Económico", {
            "fields": ("total", "moneda")
        }),
        ("Tiempos", {
            "fields": ("fecha_creacion", "fecha_entrega_estimada")
        }),
    )

    inlines = (
        DetallePedidoInline,
        ComandaCocinaInline,
        SeguimientoPedidoInline,
        EntregaPedidoInline,
    )

    actions = (
        "pasar_a_en_preparacion",
        "pasar_a_listo",
        "pasar_a_en_camino",
        "pasar_a_entregado",
        "cancelar_pedidos",
    )

    @admin.display(description="ID")
    def id_corto(self, obj):
        """Muestra solo los primeros 8 caracteres del UUID."""
        return str(obj.id)[:8] + "..."

    # ── Acciones de estado ──
    # Todas usan save(update_fields=["estado"]) para que el signal
    # detecte el cambio y publique el evento correcto en RabbitMQ.

    @admin.action(description="▶ Pasar a EN PREPARACIÓN")
    def pasar_a_en_preparacion(self, request, queryset):
        for obj in queryset.filter(estado="RECIBIDO"):
            obj.estado = "EN_PREPARACION"
            obj.save(update_fields=["estado"])
        self.message_user(request, "Pedidos pasados a EN PREPARACIÓN.")

    @admin.action(description="✓ Pasar a LISTO")
    def pasar_a_listo(self, request, queryset):
        for obj in queryset.filter(estado="EN_PREPARACION"):
            obj.estado = "LISTO"
            obj.save(update_fields=["estado"])
        self.message_user(request, "Pedidos pasados a LISTO.")

    @admin.action(description="🚚 Pasar a EN CAMINO")
    def pasar_a_en_camino(self, request, queryset):
        for obj in queryset.filter(estado="LISTO"):
            obj.estado = "EN_CAMINO"
            obj.save(update_fields=["estado"])
        self.message_user(request, "Pedidos pasados a EN CAMINO.")

    @admin.action(description="✅ Pasar a ENTREGADO")
    def pasar_a_entregado(self, request, queryset):
        for obj in queryset.filter(estado="EN_CAMINO"):
            obj.estado = "ENTREGADO"
            obj.save(update_fields=["estado"])
        self.message_user(request, "Pedidos marcados como ENTREGADO.")

    @admin.action(description="✗ Cancelar pedidos")
    def cancelar_pedidos(self, request, queryset):
        cancelables = queryset.exclude(estado__in=["ENTREGADO", "CANCELADO"])
        for obj in cancelables:
            obj.estado = "CANCELADO"
            obj.save(update_fields=["estado"])
        self.message_user(
            request, f"{cancelables.count()} pedido(s) cancelado(s).")


# ─────────────────────────────────────────
# COMANDA COCINA
# ─────────────────────────────────────────

@admin.register(ComandaCocina)
class ComandaCocinaAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "estacion", "estado",
                    "hora_envio", "hora_fin", "tiempo_preparacion_segundos")
    list_filter = ("estado", "estacion")
    search_fields = ("pedido__id",)
    ordering = ("-hora_envio",)
    readonly_fields = ("id", "hora_envio", "tiempo_preparacion_segundos")

    actions = ("marcar_preparando", "marcar_lista")

    @admin.action(description="▶ Marcar como PREPARANDO")
    def marcar_preparando(self, request, queryset):
        for obj in queryset.filter(estado="PENDIENTE"):
            obj.estado = "PREPARANDO"
            obj.save(update_fields=["estado"])
        self.message_user(request, "Comandas pasadas a PREPARANDO.")

    @admin.action(description="✓ Marcar como LISTA")
    def marcar_lista(self, request, queryset):
        for obj in queryset.filter(estado="PREPARANDO"):
            obj.estado = "LISTO"
            obj.hora_fin = timezone.now()
            # dispara COMANDA_LISTA
            obj.save(update_fields=["estado", "hora_fin"])
        self.message_user(request, "Comandas marcadas como LISTA.")


# ─────────────────────────────────────────
# ENTREGA PEDIDO
# ─────────────────────────────────────────

@admin.register(EntregaPedido)
class EntregaPedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "tipo_entrega", "estado_entrega",
                    "repartidor_nombre", "fecha_entrega_real")
    list_filter = ("tipo_entrega", "estado_entrega")
    search_fields = ("pedido__id", "repartidor_nombre")
    ordering = ("-id",)
    readonly_fields = ("id",)

    actions = ("marcar_en_camino", "marcar_entregada", "marcar_fallida")

    @admin.action(description="🚚 Marcar EN CAMINO")
    def marcar_en_camino(self, request, queryset):
        for obj in queryset.filter(estado_entrega="PENDIENTE"):
            obj.estado_entrega = "EN_CAMINO"
            obj.fecha_salida = timezone.now()
            obj.save(update_fields=["estado_entrega", "fecha_salida"])
        self.message_user(request, "Entregas marcadas EN CAMINO.")

    @admin.action(description="✅ Marcar ENTREGADA")
    def marcar_entregada(self, request, queryset):
        for obj in queryset.filter(estado_entrega="EN_CAMINO"):
            obj.estado_entrega = "ENTREGADO"
            obj.fecha_entrega_real = timezone.now()
            # dispara ENTREGA_COMPLETADA
            obj.save(update_fields=["estado_entrega", "fecha_entrega_real"])
        self.message_user(request, "Entregas marcadas como ENTREGADA.")

    @admin.action(description="✗ Marcar FALLIDA")
    def marcar_fallida(self, request, queryset):
        for obj in queryset.filter(estado_entrega="EN_CAMINO"):
            obj.estado_entrega = "FALLIDO"
            # dispara ENTREGA_FALLIDA
            obj.save(update_fields=["estado_entrega"])
        self.message_user(request, "Entregas marcadas como FALLIDA.")


# ─────────────────────────────────────────
# SEGUIMIENTO (solo lectura)
# ─────────────────────────────────────────

@admin.register(SeguimientoPedido)
class SeguimientoPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "descripcion")
    list_filter = ("estado",)
    search_fields = ("pedido__id",)
    ordering = ("-fecha",)
    readonly_fields = ("id", "pedido", "estado", "fecha")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

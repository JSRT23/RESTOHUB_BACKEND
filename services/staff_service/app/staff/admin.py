from django.contrib import admin
from django.utils.html import format_html

from app.staff.models import (
    AlertaOperacional,
    AsignacionCocina,
    ConfiguracionLaboralPais,
    Empleado,
    EstacionCocina,
    PrediccionPersonal,
    RegistroAsistencia,
    ResumenNomina,
    RestauranteLocal,
    ServicioEntrega,
    Turno,
)


# ---------------------------------------------------------------------------
# RestauranteLocal
# ---------------------------------------------------------------------------

@admin.register(RestauranteLocal)
class RestauranteLocalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "pais", "ciudad", "activo", "created_at")
    list_filter = ("pais", "activo")
    search_fields = ("nombre", "ciudad")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("nombre",)


# ---------------------------------------------------------------------------
# ConfiguracionLaboralPais
# ---------------------------------------------------------------------------

@admin.register(ConfiguracionLaboralPais)
class ConfiguracionLaboralPaisAdmin(admin.ModelAdmin):
    list_display = (
        "get_pais_display",
        "horas_max_diarias",
        "horas_max_semanales",
        "factor_hora_extra",
        "descanso_min_entre_turnos",
    )
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("pais",)


# ---------------------------------------------------------------------------
# Empleado
# ---------------------------------------------------------------------------

class TurnoInline(admin.TabularInline):
    model = Turno
    extra = 0
    fields = ("fecha_inicio", "fecha_fin", "estado")
    readonly_fields = ("fecha_inicio", "fecha_fin", "estado")
    show_change_link = True
    max_num = 5
    ordering = ("-fecha_inicio",)


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "apellido", "documento",
                    "rol", "restaurante", "pais", "activo")
    list_filter = ("rol", "pais", "activo", "restaurante")
    search_fields = ("nombre", "apellido", "documento", "email")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("apellido", "nombre")
    inlines = [TurnoInline]

    fieldsets = (
        ("Datos personales", {
            "fields": ("id", "nombre", "apellido", "documento", "email", "telefono")
        }),
        ("Datos laborales", {
            "fields": ("restaurante", "rol", "pais", "fecha_contratacion", "activo")
        }),
        ("Auditoría", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


# ---------------------------------------------------------------------------
# Turno
# ---------------------------------------------------------------------------

class RegistroAsistenciaInline(admin.StackedInline):
    model = RegistroAsistencia
    extra = 0
    max_num = 1
    readonly_fields = ("id", "horas_normales", "horas_extra", "created_at")
    fields = (
        "hora_entrada", "hora_salida", "metodo_registro",
        "horas_normales", "horas_extra",
    )


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = (
        "empleado", "restaurante_id", "fecha_inicio", "fecha_fin",
        "estado", "duracion_programada_horas",
    )
    list_filter = ("estado", "empleado__restaurante")
    search_fields = ("empleado__nombre", "empleado__apellido")
    readonly_fields = (
        "id", "qr_token", "duracion_programada_horas", "created_at", "updated_at")
    ordering = ("-fecha_inicio",)
    inlines = [RegistroAsistenciaInline]

    fieldsets = (
        ("Turno", {
            "fields": ("id", "empleado", "restaurante_id", "estado", "notas")
        }),
        ("Horario", {
            "fields": ("fecha_inicio", "fecha_fin", "duracion_programada_horas")
        }),
        ("QR dinámico", {
            "fields": ("qr_token", "qr_expira_en"),
            "classes": ("collapse",),
        }),
        ("Auditoría", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Duración (h)")
    def duracion_programada_horas(self, obj):
        return obj.duracion_programada_horas


# ---------------------------------------------------------------------------
# RegistroAsistencia
# ---------------------------------------------------------------------------

@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = (
        "turno", "hora_entrada", "hora_salida",
        "metodo_registro", "horas_normales", "horas_extra",
    )
    list_filter = ("metodo_registro",)
    search_fields = ("turno__empleado__nombre", "turno__empleado__apellido")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-hora_entrada",)


# ---------------------------------------------------------------------------
# EstacionCocina
# ---------------------------------------------------------------------------

class AsignacionCocinaInline(admin.TabularInline):
    model = AsignacionCocina
    extra = 0
    fields = ("pedido_id", "cocinero", "asignado_en",
              "completado_en", "sla_segundos")
    readonly_fields = ("asignado_en", "sla_segundos")
    show_change_link = True
    ordering = ("-asignado_en",)
    max_num = 10


@admin.register(EstacionCocina)
class EstacionCocinaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "restaurante_id",
                    "capacidad_simultanea", "activa")
    list_filter = ("activa",)
    search_fields = ("nombre",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [AsignacionCocinaInline]


# ---------------------------------------------------------------------------
# AsignacionCocina
# ---------------------------------------------------------------------------

@admin.register(AsignacionCocina)
class AsignacionCocinaAdmin(admin.ModelAdmin):
    list_display = (
        "comanda_id", "cocinero", "estacion",
        "asignado_en", "completado_en", "sla_display",
    )
    list_filter = ("estacion",)
    search_fields = ("cocinero__nombre", "cocinero__apellido")
    readonly_fields = ("id", "asignado_en", "created_at", "updated_at")
    ordering = ("-asignado_en",)

    @admin.display(description="SLA")
    def sla_display(self, obj):
        if obj.sla_segundos is None:
            return "—"
        minutos = obj.sla_segundos // 60
        segundos = obj.sla_segundos % 60
        color = "red" if obj.sla_segundos > 900 else "green"
        return format_html(
            '<span style="color:{}">{:02d}:{:02d}</span>',
            color, minutos, segundos,
        )


# ---------------------------------------------------------------------------
# ServicioEntrega
# ---------------------------------------------------------------------------

@admin.register(ServicioEntrega)
class ServicioEntregaAdmin(admin.ModelAdmin):
    list_display = ("pedido_id", "repartidor", "estado",
                    "asignado_en", "completado_en")
    list_filter = ("estado",)
    search_fields = ("repartidor__nombre", "repartidor__apellido")
    readonly_fields = ("id", "asignado_en", "created_at", "updated_at")
    ordering = ("-asignado_en",)


# ---------------------------------------------------------------------------
# AlertaOperacional
# ---------------------------------------------------------------------------

@admin.register(AlertaOperacional)
class AlertaOperacionalAdmin(admin.ModelAdmin):
    list_display = (
        "tipo", "nivel_display", "restaurante_id",
        "mensaje_corto", "resuelta", "created_at",
    )
    list_filter = ("tipo", "nivel", "resuelta")
    search_fields = ("mensaje",)
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    actions = ["marcar_resueltas"]

    @admin.display(description="Nivel")
    def nivel_display(self, obj):
        colores = {"info": "blue", "urgente": "orange", "critica": "red"}
        color = colores.get(obj.nivel, "black")
        return format_html(
            '<span style="color:{}; font-weight:bold">{}</span>',
            color, obj.get_nivel_display(),
        )

    @admin.display(description="Mensaje")
    def mensaje_corto(self, obj):
        return obj.mensaje[:80] + "..." if len(obj.mensaje) > 80 else obj.mensaje

    @admin.action(description="Marcar seleccionadas como resueltas")
    def marcar_resueltas(self, request, queryset):
        actualizadas = queryset.filter(resuelta=False).update(resuelta=True)
        self.message_user(
            request, f"{actualizadas} alerta(s) marcada(s) como resueltas.")


# ---------------------------------------------------------------------------
# ResumenNomina
# ---------------------------------------------------------------------------

@admin.register(ResumenNomina)
class ResumenNominaAdmin(admin.ModelAdmin):
    list_display = (
        "empleado", "periodo_inicio", "periodo_fin",
        "total_horas_normales", "total_horas_extra",
        "dias_trabajados", "moneda", "cerrado",
    )
    list_filter = ("cerrado", "moneda")
    search_fields = ("empleado__nombre", "empleado__apellido")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-periodo_inicio",)


# ---------------------------------------------------------------------------
# PrediccionPersonal
# ---------------------------------------------------------------------------

@admin.register(PrediccionPersonal)
class PrediccionPersonalAdmin(admin.ModelAdmin):
    list_display = (
        "restaurante_id", "fecha", "demanda_estimada",
        "personal_recomendado", "fuente",
    )
    list_filter = ("fuente",)
    search_fields = ("restaurante_id",)
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-fecha",)

# staff_service/app/staff/models.py
import uuid
from django.db import models


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class Pais(models.TextChoices):
    COLOMBIA = "CO", "Colombia"
    MEXICO = "MX", "México"
    ARGENTINA = "AR", "Argentina"
    CHILE = "CL", "Chile"
    BRASIL = "BR", "Brasil"
    PERU = "PE", "Perú"
    PANAMA = "PA", "Panamá"


class Moneda(models.TextChoices):
    COP = "COP", "Peso colombiano"
    USD = "USD", "Dólar estadounidense"
    EUR = "EUR", "Euro"
    MXN = "MXN", "Peso mexicano"
    ARS = "ARS", "Peso argentino"
    BRL = "BRL", "Real brasileño"
    CLP = "CLP", "Peso chileno"


class RolEmpleado(models.TextChoices):
    COCINERO = "cocinero",   "Cocinero"
    REPARTIDOR = "repartidor", "Repartidor"
    CAJERO = "cajero",     "Cajero"
    MESERO = "mesero",     "Mesero"
    GERENTE = "gerente",    "Gerente"
    SUPERVISOR = "supervisor", "Supervisor"
    AUXILIAR = "auxiliar",   "Auxiliar de cocina"


class EstadoTurno(models.TextChoices):
    PROGRAMADO = "programado", "Programado"
    ACTIVO = "activo",     "Activo"
    COMPLETADO = "completado", "Completado"
    CANCELADO = "cancelado",  "Cancelado"


class MetodoAsistencia(models.TextChoices):
    QR = "qr",     "QR dinámico"
    MANUAL = "manual", "Registro manual"


class EstadoEntrega(models.TextChoices):
    ASIGNADA = "asignada",   "Asignada"
    EN_CAMINO = "en_camino",  "En camino"
    COMPLETADA = "completada", "Completada"
    FALLIDA = "fallida",    "Fallida"


class TipoAlerta(models.TextChoices):
    STOCK_BAJO = "stock_bajo",  "Stock bajo"
    AGOTADO = "agotado",     "Ingrediente agotado"
    VENCIMIENTO = "vencimiento", "Vencimiento próximo"
    ORDEN_COMPRA = "orden_compra", "Orden de compra"


class NivelAlerta(models.TextChoices):
    INFO = "info",    "Informativa"
    URGENTE = "urgente", "Urgente"
    CRITICA = "critica", "Crítica"


class FuentePrediccion(models.TextChoices):
    HISTORIAL = "historial",    "Historial de pedidos"
    ESTACIONAL = "estacional",   "Estacionalidad"
    EVENTO = "evento",       "Evento programado"
    COMBINADO = "combinado",    "Combinado"


# ---------------------------------------------------------------------------
# RestauranteLocal
# Copia local sincronizada vía RabbitMQ (eventos app.menu.restaurante.*)
# No hay FK real al menu_service — todo es UUID externo.
# ---------------------------------------------------------------------------

class RestauranteLocal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurante_id = models.UUIDField(
        unique=True,
        db_index=True,
        help_text="UUID del restaurante en menu_service"
    )
    nombre = models.CharField(max_length=200)
    pais = models.CharField(max_length=2, choices=Pais.choices)
    ciudad = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Restaurante local"
        verbose_name_plural = "Restaurantes locales"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.get_pais_display()})"


# ---------------------------------------------------------------------------
# ConfiguracionLaboralPais
# Regulaciones laborales por país.
# Un registro por país; se consulta siempre por Empleado.pais.
# ---------------------------------------------------------------------------

class ConfiguracionLaboralPais(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pais = models.CharField(max_length=2, choices=Pais.choices, unique=True)

    # Límites de jornada
    horas_max_diarias = models.PositiveSmallIntegerField(
        default=8,
        help_text="Horas máximas de trabajo por día"
    )
    horas_max_semanales = models.PositiveSmallIntegerField(
        default=48,
        help_text="Horas máximas de trabajo por semana"
    )

    # Hora extra
    factor_hora_extra = models.DecimalField(
        max_digits=4, decimal_places=2, default=1.50,
        help_text="Multiplicador sobre el valor hora base (1.50 = 50% extra)"
    )

    # Descansos obligatorios
    descanso_min_entre_turnos = models.PositiveSmallIntegerField(
        default=480,
        help_text="Minutos mínimos de descanso entre dos turnos consecutivos"
    )
    horas_continuas_para_descanso = models.PositiveSmallIntegerField(
        default=6,
        help_text="Horas continuas de trabajo que obligan una pausa"
    )
    duracion_descanso_obligatorio = models.PositiveSmallIntegerField(
        default=30,
        help_text="Duración en minutos de la pausa obligatoria"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración laboral por país"
        verbose_name_plural = "Configuraciones laborales por país"

    def __str__(self):
        return f"Config laboral — {self.get_pais_display()}"


# ---------------------------------------------------------------------------
# Empleado
# FK interna a RestauranteLocal.
# pais se desnormaliza para consultar ConfiguracionLaboralPais sin join extra.
# documento permite validar identidad en check-in manual.
# ---------------------------------------------------------------------------

class Empleado(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurante = models.ForeignKey(
        RestauranteLocal,
        on_delete=models.PROTECT,
        related_name="empleados"
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    documento = models.CharField(
        max_length=30, unique=True,
        help_text="Cédula o documento de identidad"
    )
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    rol = models.CharField(max_length=20, choices=RolEmpleado.choices)
    pais = models.CharField(
        max_length=2, choices=Pais.choices,
        help_text="Define qué ConfiguracionLaboralPais aplica"
    )
    fecha_contratacion = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.nombre} {self.apellido} — {self.get_rol_display()}"

    def get_config_laboral(self):
        """Retorna la configuración laboral del país del empleado."""
        return ConfiguracionLaboralPais.objects.filter(pais=self.pais).first()


# ---------------------------------------------------------------------------
# Turno
# Programación de turnos. Usa DateTimeField (no date + time separados)
# para facilitar cálculos de duración y validaciones de solapamiento.
#
# qr_token: UUID único generado al crear el turno.
# qr_expira_en: ventana válida para marcar entrada (ej: ±15 min del inicio).
# restaurante_id: snapshot UUID — el empleado puede rotar entre locales.
# ---------------------------------------------------------------------------

class Turno(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name="turnos"
    )
    restaurante_id = models.UUIDField(
        db_index=True,
        help_text="UUID snapshot del restaurante — no FK externa"
    )
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    estado = models.CharField(
        max_length=20,
        choices=EstadoTurno.choices,
        default=EstadoTurno.PROGRAMADO
    )

    # QR dinámico — se genera al crear, expira cerca del inicio del turno
    qr_token = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True)
    qr_expira_en = models.DateTimeField(
        null=True, blank=True,
        help_text="Hasta cuándo el QR es válido para registrar entrada"
    )

    notas = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Turno"
        verbose_name_plural = "Turnos"
        ordering = ["-fecha_inicio"]
        indexes = [
            models.Index(fields=["restaurante_id", "fecha_inicio"]),
            models.Index(fields=["empleado", "estado"]),
        ]

    def __str__(self):
        return (
            f"Turno {self.empleado} | "
            f"{self.fecha_inicio:%Y-%m-%d %H:%M} → {self.fecha_fin:%H:%M} "
            f"[{self.get_estado_display()}]"
        )

    @property
    def duracion_programada_horas(self):
        if not self.fecha_inicio or not self.fecha_fin:
            return None

        return round((self.fecha_fin - self.fecha_inicio).total_seconds() / 3600, 2)

# ---------------------------------------------------------------------------
# RegistroAsistencia
# OneToOne con Turno — un turno genera exactamente un registro.
# Fusiona lo que sería HorasTrabajadas: horas_normales y horas_extra
# se calculan al cerrar (hora_salida) según ConfiguracionLaboralPais.
# ---------------------------------------------------------------------------


class RegistroAsistencia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    turno = models.OneToOneField(
        Turno,
        on_delete=models.PROTECT,
        related_name="registro_asistencia"
    )

    hora_entrada = models.DateTimeField()
    hora_salida = models.DateTimeField(null=True, blank=True)
    metodo_registro = models.CharField(
        max_length=10,
        choices=MetodoAsistencia.choices,
        default=MetodoAsistencia.QR
    )

    # Calculados al cerrar el registro (hora_salida set)
    horas_normales = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Horas dentro del límite diario del país"
    )
    horas_extra = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Horas por encima del límite diario"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Registro de asistencia"
        verbose_name_plural = "Registros de asistencia"

    def __str__(self):
        return f"Asistencia {self.turno.empleado} — {self.hora_entrada:%Y-%m-%d}"

    @property
    def horas_totales(self):
        return self.horas_normales + self.horas_extra


# ---------------------------------------------------------------------------
# ResumenNomina
# Agrega horas por período (semanal o mensual) por empleado.
# Separado de RegistroAsistencia porque tiene lógica propia:
# cierre de período, moneda, aprobación de gerente.
# ---------------------------------------------------------------------------

class ResumenNomina(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name="resumenes_nomina"
    )
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()

    total_horas_normales = models.DecimalField(
        max_digits=7, decimal_places=2, default=0)
    total_horas_extra = models.DecimalField(
        max_digits=7, decimal_places=2, default=0)
    dias_trabajados = models.PositiveSmallIntegerField(default=0)
    moneda = models.CharField(max_length=3, choices=Moneda.choices)

    # cerrado = True impide modificaciones (período liquidado)
    cerrado = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resumen de nómina"
        verbose_name_plural = "Resúmenes de nómina"
        unique_together = [["empleado", "periodo_inicio", "periodo_fin"]]
        ordering = ["-periodo_inicio"]

    def __str__(self):
        return (
            f"Nómina {self.empleado} | "
            f"{self.periodo_inicio} → {self.periodo_fin}"
        )

    @property
    def total_horas(self):
        return self.total_horas_normales + self.total_horas_extra


# ---------------------------------------------------------------------------
# EstacionCocina
# Cada local tiene estaciones (parrilla, fría, postres, etc.).
# Sincronizada manualmente o por evento de creación de restaurante.
# restaurante_id es UUID externo (sin FK).
# ---------------------------------------------------------------------------

class EstacionCocina(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurante_id = models.UUIDField(db_index=True)
    nombre = models.CharField(max_length=100)
    capacidad_simultanea = models.PositiveSmallIntegerField(
        default=1,
        help_text="Máximo de cocineros asignados en paralelo a esta estación"
    )
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estación de cocina"
        verbose_name_plural = "Estaciones de cocina"
        unique_together = [["restaurante_id", "nombre"]]

    def __str__(self):
        return f"{self.nombre} (cap. {self.capacidad_simultanea})"


# ---------------------------------------------------------------------------
# AsignacionCocina
# Creada al consumir app.order.comanda.creada.
# Guarda qué cocinero trabajó qué comanda en qué estación.
# sla_segundos: tiempo real desde asignación hasta completado_en.
# ---------------------------------------------------------------------------

class AsignacionCocina(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido_id = models.UUIDField(db_index=True)
    comanda_id = models.UUIDField(db_index=True, unique=True)
    cocinero = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name="asignaciones_cocina",
        limit_choices_to={"rol__in": [
            RolEmpleado.COCINERO, RolEmpleado.AUXILIAR]}
    )
    estacion = models.ForeignKey(
        EstacionCocina,
        on_delete=models.PROTECT,
        related_name="asignaciones"
    )
    asignado_en = models.DateTimeField(auto_now_add=True)
    completado_en = models.DateTimeField(null=True, blank=True)
    sla_segundos = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Segundos reales desde asignación hasta completado. Calculado al cerrar."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Asignación de cocina"
        verbose_name_plural = "Asignaciones de cocina"
        ordering = ["-asignado_en"]

    def __str__(self):
        return f"Comanda {self.comanda_id} → {self.cocinero} [{self.estacion}]"

    def calcular_sla(self):
        if self.completado_en:
            delta = self.completado_en - self.asignado_en
            return int(delta.total_seconds())
        return None


# ---------------------------------------------------------------------------
# ServicioEntrega
# Creado al consumir app.order.entrega.asignada.
# Controla qué repartidor está en servicio activo y cuándo termina.
# pedido_id es unique: un pedido tiene exactamente un servicio de entrega.
# ---------------------------------------------------------------------------

class ServicioEntrega(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido_id = models.UUIDField(unique=True, db_index=True)
    repartidor = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name="servicios_entrega",
        limit_choices_to={"rol": RolEmpleado.REPARTIDOR}
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoEntrega.choices,
        default=EstadoEntrega.ASIGNADA
    )
    asignado_en = models.DateTimeField(auto_now_add=True)
    completado_en = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Servicio de entrega"
        verbose_name_plural = "Servicios de entrega"
        ordering = ["-asignado_en"]

    def __str__(self):
        return f"Entrega pedido {self.pedido_id} → {self.repartidor} [{self.get_estado_display()}]"


# ---------------------------------------------------------------------------
# AlertaOperacional
# Log de alertas que llegan de inventory_service vía RabbitMQ.
# referencia_id: UUID del lote, ingrediente u orden de compra que generó la alerta.
# No se borra — se marca como resuelta.
# ---------------------------------------------------------------------------

class AlertaOperacional(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurante_id = models.UUIDField(db_index=True)
    tipo = models.CharField(max_length=20, choices=TipoAlerta.choices)
    nivel = models.CharField(max_length=10, choices=NivelAlerta.choices)
    mensaje = models.TextField()
    referencia_id = models.UUIDField(
        null=True, blank=True,
        help_text="UUID del recurso que disparó la alerta (lote, ingrediente, orden)"
    )
    resuelta = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Alerta operacional"
        verbose_name_plural = "Alertas operacionales"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurante_id", "resuelta"]),
            models.Index(fields=["nivel", "resuelta"]),
        ]

    def __str__(self):
        return f"[{self.get_nivel_display()}] {self.get_tipo_display()} — {self.created_at:%Y-%m-%d %H:%M}"


# ---------------------------------------------------------------------------
# PrediccionPersonal
# Modelo predictivo de necesidades de personal por restaurante y fecha.
# fuente indica si la predicción viene de historial, estacionalidad o evento.
# En fases futuras puede alimentarse de un modelo ML externo.
# ---------------------------------------------------------------------------

class PrediccionPersonal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurante_id = models.UUIDField(db_index=True)
    fecha = models.DateField()
    demanda_estimada = models.PositiveIntegerField(
        help_text="Número de pedidos estimados para ese día"
    )
    personal_recomendado = models.PositiveSmallIntegerField(
        help_text="Cantidad de empleados sugeridos para cubrir la demanda"
    )
    fuente = models.CharField(
        max_length=20,
        choices=FuentePrediccion.choices,
        default=FuentePrediccion.HISTORIAL
    )
    notas = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Predicción de personal"
        verbose_name_plural = "Predicciones de personal"
        unique_together = [["restaurante_id", "fecha"]]
        ordering = ["-fecha"]

    def __str__(self):
        return (
            f"Predicción {self.restaurante_id} | {self.fecha} → "
            f"{self.personal_recomendado} empleados ({self.get_fuente_display()})"
        )

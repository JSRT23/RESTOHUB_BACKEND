from decimal import Decimal

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.renderers import JSONRenderer
from rest_framework.decorators import action
from rest_framework.response import Response

from app.loyalty.models import (
    AplicacionPromocion,
    CatalogoCategoria,
    CatalogoPlato,
    CuentaPuntos,
    Cupon,
    Promocion,
    TransaccionPuntos,
)
from app.loyalty.serializers import (
    AcumularPuntosSerializer,
    AplicacionPromocionSerializer,
    CanjearCuponSerializer,
    CanjearPuntosSerializer,
    CatalogoCategoriaSerializer,
    CatalogoPlatoSerializer,
    CuentaPuntosSerializer,
    CuponListSerializer,
    CuponSerializer,
    CuponWriteSerializer,
    EvaluarPromocionSerializer,
    PromocionListSerializer,
    PromocionSerializer,
    PromocionWriteSerializer,
    TransaccionPuntosSerializer,
)


# ---------------------------------------------------------------------------
# Helpers de caché Redis
# ---------------------------------------------------------------------------

def _cache_key(cliente_id: str) -> str:
    return f"puntos:{cliente_id}"


def _get_saldo_cache(cliente_id: str):
    return cache.get(_cache_key(cliente_id))


def _set_saldo_cache(cliente_id: str, saldo: int) -> None:
    ttl = getattr(settings, "REDIS_PUNTOS_TTL", 300)
    cache.set(_cache_key(cliente_id), saldo, timeout=ttl)


def _invalidar_cache(cliente_id: str) -> None:
    cache.delete(_cache_key(cliente_id))


# ---------------------------------------------------------------------------
# Puntos
# ---------------------------------------------------------------------------

class PuntosViewSet(viewsets.ViewSet):
    """
    Rutas:
        GET  /puntos/{cliente_id}/  → saldo con caché Redis
        POST /puntos/acumular/      → acumulación manual
        POST /puntos/canjear/       → canje de puntos
    """

    def retrieve(self, request, pk=None):
        """
        GET /puntos/{cliente_id}/
        Intenta resolver desde Redis. Si no hay caché, va a PostgreSQL
        y guarda el resultado con TTL configurado en settings.
        """
        cliente_id = str(pk)

        saldo = _get_saldo_cache(cliente_id)
        if saldo is not None:
            cuenta = CuentaPuntos.objects.filter(
                cliente_id=cliente_id
            ).first()
            if not cuenta:
                return Response(
                    {"detail": "El cliente no tiene cuenta de puntos."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            # Retornar datos completos con saldo desde caché
            data = CuentaPuntosSerializer(cuenta).data
            data["saldo"] = saldo
            data["_cache"] = True
            return Response(data)

        # Cache miss → ir a PostgreSQL
        cuenta = CuentaPuntos.objects.filter(cliente_id=cliente_id).first()
        if not cuenta:
            return Response(
                {"detail": "El cliente no tiene cuenta de puntos."},
                status=status.HTTP_404_NOT_FOUND,
            )

        _set_saldo_cache(cliente_id, cuenta.saldo)
        data = CuentaPuntosSerializer(cuenta).data
        data["_cache"] = False
        return Response(data)

    @action(detail=False, methods=["post"])
    def acumular(self, request):
        """
        POST /puntos/acumular/
        Acumulación manual de puntos (ajuste por operador).
        Crea la CuentaPuntos si no existe.
        """
        serializer = AcumularPuntosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        cuenta, _ = CuentaPuntos.objects.get_or_create(
            cliente_id=d["cliente_id"],
            defaults={"saldo": 0, "puntos_totales_historicos": 0},
        )

        saldo_anterior = cuenta.saldo
        cuenta.saldo += d["puntos"]
        cuenta.puntos_totales_historicos += d["puntos"]
        cuenta.actualizar_nivel()
        cuenta.save(update_fields=[
                    "saldo", "puntos_totales_historicos", "nivel"])

        TransaccionPuntos.objects.create(
            cuenta=cuenta,
            tipo="acumulacion",
            puntos=d["puntos"],
            saldo_anterior=saldo_anterior,
            saldo_posterior=cuenta.saldo,
            pedido_id=d.get("pedido_id"),
            restaurante_id=d.get("restaurante_id"),
            descripcion=d.get("descripcion", "Ajuste manual"),
        )

        _invalidar_cache(str(d["cliente_id"]))

        return Response(
            CuentaPuntosSerializer(cuenta).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def canjear(self, request):
        """
        POST /puntos/canjear/
        El serializer ya validó saldo suficiente e inyectó _cuenta.
        """
        serializer = CanjearPuntosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        cuenta = d["_cuenta"]
        saldo_anterior = cuenta.saldo
        cuenta.saldo -= d["puntos"]
        cuenta.save(update_fields=["saldo"])

        TransaccionPuntos.objects.create(
            cuenta=cuenta,
            tipo="canje",
            puntos=-d["puntos"],
            saldo_anterior=saldo_anterior,
            saldo_posterior=cuenta.saldo,
            pedido_id=d.get("pedido_id"),
            descripcion=d.get("descripcion", "Canje de puntos"),
        )

        _invalidar_cache(str(d["cliente_id"]))

        return Response(CuentaPuntosSerializer(cuenta).data)


# ---------------------------------------------------------------------------
# Transacciones
# Read-only — se crean por el consumer o por acumular/canjear
# ---------------------------------------------------------------------------

class TransaccionPuntosViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TransaccionPuntosSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = TransaccionPuntos.objects.select_related("cuenta").all()

        cliente_id = self.request.query_params.get("cliente_id")
        tipo = self.request.query_params.get("tipo")
        pedido_id = self.request.query_params.get("pedido_id")
        fecha_desde = self.request.query_params.get("fecha_desde")
        fecha_hasta = self.request.query_params.get("fecha_hasta")

        if not cliente_id and not pedido_id:
            return qs.none()

        if cliente_id:
            qs = qs.filter(cuenta__cliente_id=cliente_id)
        if pedido_id:
            qs = qs.filter(pedido_id=pedido_id)
        if tipo:
            qs = qs.filter(tipo=tipo)
        if fecha_desde:
            qs = qs.filter(created_at__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(created_at__date__lte=fecha_hasta)

        return qs.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        if not request.query_params.get("cliente_id") and \
           not request.query_params.get("pedido_id"):
            return Response(
                {"detail": "Se requiere 'cliente_id' o 'pedido_id'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().list(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Promociones
# ---------------------------------------------------------------------------

class PromocionViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    # El BrowsableAPIRenderer intenta renderizar el formulario de
    # PromocionWriteSerializer con DateTimeField vacios, lo que causa
    # ValueError en Django 5.x. Se fuerza JSON puro en este ViewSet.
    renderer_classes = [JSONRenderer]

    def get_queryset(self):
        qs = Promocion.objects.prefetch_related("reglas").all()

        activa = self.request.query_params.get("activa")
        alcance = self.request.query_params.get("alcance")
        restaurante_id = self.request.query_params.get("restaurante_id")
        tipo_beneficio = self.request.query_params.get("tipo_beneficio")

        if activa is not None:
            qs = qs.filter(activa=activa.lower() == "true")
        if alcance:
            qs = qs.filter(alcance=alcance)
        if restaurante_id:
            from django.db.models import Q
            qs = qs.filter(
                Q(alcance="global") |
                Q(alcance="local", restaurante_id=restaurante_id)
            )
        if tipo_beneficio:
            qs = qs.filter(tipo_beneficio=tipo_beneficio)

        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "list":
            return PromocionListSerializer
        if self.action in ["create", "partial_update"]:
            return PromocionWriteSerializer
        return PromocionSerializer

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        """POST /promociones/{id}/activar/"""
        promo = self.get_object()
        if promo.activa:
            return Response(
                {"detail": "La promoción ya está activa."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        promo.activa = True
        promo.save(update_fields=["activa"])
        return Response(PromocionSerializer(promo).data)

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        """POST /promociones/{id}/desactivar/"""
        promo = self.get_object()
        if not promo.activa:
            return Response(
                {"detail": "La promoción ya está inactiva."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        promo.activa = False
        promo.save(update_fields=["activa"])
        return Response(PromocionSerializer(promo).data)

    @action(detail=False, methods=["post"])
    def evaluar(self, request):
        """
        POST /promociones/evaluar/
        Evalúa si alguna promoción activa aplica para el pedido dado.
        Si aplica, crea AplicacionPromocion y publica PROMOCION_APLICADA
        (el signal lo hace automáticamente al crear).
        Idempotente: si el pedido ya tiene aplicación, retorna la existente.
        """
        serializer = EvaluarPromocionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        pedido_id = d["pedido_id"]
        cliente_id = d["cliente_id"]
        restaurante_id = d["restaurante_id"]
        total = d["total"]
        detalles = d["detalles"]

        # Idempotencia
        existente = AplicacionPromocion.objects.filter(
            pedido_id=pedido_id
        ).select_related("promocion").first()

        if existente:
            return Response(
                AplicacionPromocionSerializer(existente).data,
                status=status.HTTP_200_OK,
            )

        ahora = timezone.now()

        from django.db.models import Q
        promociones = Promocion.objects.filter(
            activa=True,
            fecha_inicio__lte=ahora,
            fecha_fin__gte=ahora,
        ).filter(
            Q(alcance="global") |
            Q(alcance="local", restaurante_id=restaurante_id)
        ).prefetch_related("reglas")

        plato_ids = {str(d_item.get("plato_id")) for d_item in detalles}
        orden = {"local": 0, "marca": 1, "global": 2}
        promos = sorted(promociones, key=lambda p: orden.get(p.alcance, 99))

        promo_aplicada = None
        for promo in promos:
            if self._cumple_reglas(promo, total, plato_ids, ahora):
                promo_aplicada = promo
                break

        if not promo_aplicada:
            return Response(
                {"detail": "Ninguna promoción aplica para este pedido."},
                status=status.HTTP_200_OK,
            )

        descuento, puntos_bonus = self._calcular_beneficio(
            promo_aplicada, total)

        aplicacion = AplicacionPromocion.objects.create(
            promocion=promo_aplicada,
            pedido_id=pedido_id,
            cliente_id=cliente_id,
            descuento_aplicado=descuento,
            puntos_bonus_otorgados=puntos_bonus,
        )

        return Response(
            AplicacionPromocionSerializer(aplicacion).data,
            status=status.HTTP_201_CREATED,
        )

    def _cumple_reglas(self, promo, total, plato_ids, ahora) -> bool:
        reglas = list(promo.reglas.all())
        if not reglas:
            return True

        for regla in reglas:
            if regla.tipo_condicion == "monto_minimo":
                if total < (regla.monto_minimo or 0):
                    return False
            elif regla.tipo_condicion == "plato":
                if str(regla.plato_id) not in plato_ids:
                    return False
            elif regla.tipo_condicion == "categoria":
                if not CatalogoPlato.objects.filter(
                    plato_id__in=plato_ids,
                    categoria_id=regla.categoria_id,
                    activo=True,
                ).exists():
                    return False
            elif regla.tipo_condicion == "hora":
                if not (regla.hora_inicio <= ahora.hour < regla.hora_fin):
                    return False
        return True

    def _calcular_beneficio(self, promo, total) -> tuple:
        descuento = Decimal("0")
        puntos_bonus = 0

        if promo.tipo_beneficio == "descuento_pct":
            descuento = (total * promo.valor / Decimal("100")).quantize(
                Decimal("0.01")
            )
        elif promo.tipo_beneficio == "descuento_monto":
            descuento = min(promo.valor, total)
        elif promo.tipo_beneficio == "puntos_extra":
            puntos_bonus = promo.puntos_bonus

        return descuento, puntos_bonus


# ---------------------------------------------------------------------------
# Cupones
# ---------------------------------------------------------------------------

class CuponViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = Cupon.objects.all()

        cliente_id = self.request.query_params.get("cliente_id")
        activo = self.request.query_params.get("activo")
        codigo = self.request.query_params.get("codigo")

        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")
        if codigo:
            qs = qs.filter(codigo__iexact=codigo)

        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "list":
            return CuponListSerializer
        if self.action == "create":
            return CuponWriteSerializer
        return CuponSerializer

    @action(detail=False, methods=["get"])
    def validar(self, request):
        """
        GET /cupones/validar/?codigo=ABC123
        Verifica si el cupón existe, está disponible y no ha expirado.
        """
        codigo = request.query_params.get("codigo", "").upper()
        if not codigo:
            return Response(
                {"detail": "Parámetro 'codigo' requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cupon = Cupon.objects.filter(codigo=codigo).first()
        if not cupon:
            return Response(
                {"detail": "Cupón no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = CuponSerializer(cupon).data
        data["disponible"] = cupon.disponible

        if not cupon.disponible:
            motivo = self._motivo_no_disponible(cupon)
            return Response(
                {"detail": motivo, "cupon": data},
                status=status.HTTP_200_OK,
            )

        return Response(data)

    @action(detail=True, methods=["post"])
    def canjear(self, request, pk=None):
        """
        POST /cupones/{id}/canjear/
        Valida disponibilidad, incrementa usos_actuales y desactiva
        si alcanzó el límite. El signal publica CUPON_CANJEADO.
        """
        cupon = self.get_object()

        if not cupon.disponible:
            motivo = self._motivo_no_disponible(cupon)
            return Response(
                {"detail": motivo},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CanjearCuponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cupon.usos_actuales += 1
        fields = ["usos_actuales"]

        # Si alcanza el límite, desactivar automáticamente
        if cupon.usos_actuales >= cupon.limite_uso:
            cupon.activo = False
            fields.append("activo")

        cupon.save(update_fields=fields)

        return Response(CuponSerializer(cupon).data)

    @staticmethod
    def _motivo_no_disponible(cupon) -> str:
        hoy = timezone.now().date()
        if not cupon.activo:
            return "El cupón está inactivo."
        if cupon.usos_actuales >= cupon.limite_uso:
            return "El cupón ha alcanzado su límite de usos."
        if hoy < cupon.fecha_inicio:
            return f"El cupón no es válido antes del {cupon.fecha_inicio}."
        if hoy > cupon.fecha_fin:
            return f"El cupón expiró el {cupon.fecha_fin}."
        return "El cupón no está disponible."


# ---------------------------------------------------------------------------
# Catálogo — solo lectura
# ---------------------------------------------------------------------------

class CatalogoPlatoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CatalogoPlatoSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = CatalogoPlato.objects.all()

        activo = self.request.query_params.get("activo")
        categoria_id = self.request.query_params.get("categoria_id")

        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)

        return qs.order_by("nombre")


class CatalogoCategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CatalogoCategoriaSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = CatalogoCategoria.objects.all()

        activo = self.request.query_params.get("activo")
        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")

        return qs.order_by("nombre")

# tests/integration/test_promociones.py
# GET    /api/loyalty/promociones/
# POST   /api/loyalty/promociones/
# GET    /api/loyalty/promociones/{id}/
# PATCH  /api/loyalty/promociones/{id}/
# POST   /api/loyalty/promociones/{id}/activar/
# POST   /api/loyalty/promociones/{id}/desactivar/
# POST   /api/loyalty/promociones/evaluar/

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from app.loyalty.models import AplicacionPromocion, Promocion
from tests.conftest import (
    PromocionFactory, ReglaPromocionFactory, CatalogoPlatoFactory,
)

PROMOS_URL = "/api/loyalty/promociones/"


def _payload(**kwargs):
    base = {
        "nombre": "Promo test",
        "alcance": "global",
        "tipo_beneficio": "descuento_pct",
        "valor": "10.00",
        "fecha_inicio": (timezone.now() + timedelta(hours=1)).isoformat(),
        "fecha_fin": (timezone.now() + timedelta(days=30)).isoformat(),
    }
    base.update(kwargs)
    return base


class TestPromocionCRUD:

    def test_listar_promociones(self, db, api_client, promo_global):
        res = api_client.get(PROMOS_URL)
        assert res.status_code == 200
        assert len(res.data) >= 1

    def test_list_usa_serializer_ligero(self, db, api_client, promo_global):
        res = api_client.get(PROMOS_URL)
        assert "reglas" not in res.data[0]

    def test_crear_promocion(self, db, api_client):
        res = api_client.post(PROMOS_URL, _payload(), format="json",
                              HTTP_ACCEPT="application/json")
        assert res.status_code == 201
        assert res.data["nombre"] == "Promo test"

    def test_crear_con_reglas(self, db, api_client):
        res = api_client.post(PROMOS_URL, _payload(nombre="Promo con reglas", reglas=[{
            "tipo_condicion": "monto_minimo",
            "monto_minimo": "20000",
            "moneda": "COP",
        }]), format="json", HTTP_ACCEPT="application/json")
        assert res.status_code == 201
        # PromocionWriteSerializer no incluye id en su response.
        # Verificamos en DB por nombre.
        promo = Promocion.objects.filter(nombre="Promo con reglas").first()
        assert promo is not None
        assert promo.reglas.count() == 1

    def test_crear_local_sin_restaurante_falla(self, db, api_client):
        res = api_client.post(PROMOS_URL, _payload(alcance="local"),
                              format="json", HTTP_ACCEPT="application/json")
        assert res.status_code == 400

    def test_detalle_incluye_reglas(self, db, api_client, promo_global):
        ReglaPromocionFactory(promocion=promo_global)
        res = api_client.get(f"{PROMOS_URL}{promo_global.id}/")
        assert res.status_code == 200
        assert "reglas" in res.data
        assert len(res.data["reglas"]) == 1

    def test_detalle_incluye_total_aplicaciones(self, db, api_client, promo_global):
        res = api_client.get(f"{PROMOS_URL}{promo_global.id}/")
        assert "total_aplicaciones" in res.data

    def test_promo_inexistente_404(self, db, api_client):
        res = api_client.get(f"{PROMOS_URL}{uuid.uuid4()}/")
        assert res.status_code == 404

    def test_patch_nombre(self, db, api_client, promo_global):
        res = api_client.patch(
            f"{PROMOS_URL}{promo_global.id}/",
            {"nombre": "Nuevo nombre"},
            format="json", HTTP_ACCEPT="application/json",
        )
        assert res.status_code == 200
        promo_global.refresh_from_db()
        assert promo_global.nombre == "Nuevo nombre"

    def test_no_permite_delete(self, db, api_client, promo_global):
        res = api_client.delete(f"{PROMOS_URL}{promo_global.id}/")
        assert res.status_code == 405

    def test_filtrar_por_activa(self, db, api_client, promo_global, promo_inactiva):
        res = api_client.get(f"{PROMOS_URL}?activa=true")
        ids = [str(p["id"]) for p in res.data]
        assert str(promo_global.id) in ids
        assert str(promo_inactiva.id) not in ids

    def test_filtrar_por_alcance(self, db, api_client):
        PromocionFactory(alcance="global")
        r = uuid.uuid4()
        PromocionFactory.local(restaurante_id=r)
        res = api_client.get(f"{PROMOS_URL}?alcance=global")
        assert all(p["alcance"] == "global" for p in res.data)


class TestPromocionActivarDesactivar:

    def test_activar_inactiva(self, db, api_client, promo_inactiva):
        res = api_client.post(f"{PROMOS_URL}{promo_inactiva.id}/activar/",
                              HTTP_ACCEPT="application/json")
        assert res.status_code == 200
        promo_inactiva.refresh_from_db()
        assert promo_inactiva.activa is True

    def test_activar_ya_activa_falla(self, db, api_client, promo_global):
        res = api_client.post(f"{PROMOS_URL}{promo_global.id}/activar/",
                              HTTP_ACCEPT="application/json")
        assert res.status_code == 400

    def test_desactivar_activa(self, db, api_client, promo_global):
        res = api_client.post(f"{PROMOS_URL}{promo_global.id}/desactivar/",
                              HTTP_ACCEPT="application/json")
        assert res.status_code == 200
        promo_global.refresh_from_db()
        assert promo_global.activa is False

    def test_desactivar_ya_inactiva_falla(self, db, api_client, promo_inactiva):
        res = api_client.post(f"{PROMOS_URL}{promo_inactiva.id}/desactivar/",
                              HTTP_ACCEPT="application/json")
        assert res.status_code == 400


class TestEvaluarPromocion:

    def _payload(self, restaurante_id=None, total="30000", **kwargs):
        return {
            "pedido_id":      str(uuid.uuid4()),
            "cliente_id":     str(uuid.uuid4()),
            "restaurante_id": str(restaurante_id or uuid.uuid4()),
            "total":          total,
            "detalles":       [],
            **kwargs,
        }

    def test_evaluar_sin_promos_activas(self, db, api_client):
        res = api_client.post(f"{PROMOS_URL}evaluar/", self._payload(),
                              format="json", HTTP_ACCEPT="application/json")
        assert res.status_code == 200
        assert "detail" in res.data

    def test_evaluar_promo_global_aplica(self, db, api_client):
        PromocionFactory(
            alcance="global",
            tipo_beneficio="descuento_pct",
            valor=Decimal("10"),
        )
        res = api_client.post(f"{PROMOS_URL}evaluar/", self._payload(),
                              format="json", HTTP_ACCEPT="application/json")
        assert res.status_code == 201
        assert Decimal(res.data["descuento_aplicado"]) > 0

    def test_evaluar_promo_inactiva_no_aplica(self, db, api_client):
        PromocionFactory.inactiva()
        res = api_client.post(f"{PROMOS_URL}evaluar/", self._payload(),
                              format="json", HTTP_ACCEPT="application/json")
        assert res.status_code == 200
        assert "detail" in res.data

    def test_evaluar_promo_expirada_no_aplica(self, db, api_client):
        PromocionFactory.expirada()
        res = api_client.post(f"{PROMOS_URL}evaluar/", self._payload(),
                              format="json", HTTP_ACCEPT="application/json")
        assert res.status_code == 200
        assert "detail" in res.data

    def test_evaluar_con_regla_monto_minimo_cumplida(self, db, api_client):
        promo = PromocionFactory()
        ReglaPromocionFactory(
            promocion=promo,
            tipo_condicion="monto_minimo",
            monto_minimo=Decimal("20000"),
        )
        res = api_client.post(f"{PROMOS_URL}evaluar/",
                              self._payload(total="25000"),
                              format="json", HTTP_ACCEPT="application/json")
        assert res.status_code == 201

    def test_evaluar_con_regla_monto_minimo_no_cumplida(self, db, api_client):
        promo = PromocionFactory()
        ReglaPromocionFactory(
            promocion=promo,
            tipo_condicion="monto_minimo",
            monto_minimo=Decimal("50000"),
        )
        res = api_client.post(f"{PROMOS_URL}evaluar/",
                              self._payload(total="10000"),
                              format="json", HTTP_ACCEPT="application/json")
        assert res.status_code == 200
        assert "detail" in res.data

    def test_evaluar_idempotente(self, db, api_client):
        PromocionFactory()
        payload = self._payload()
        res1 = api_client.post(f"{PROMOS_URL}evaluar/", payload,
                               format="json", HTTP_ACCEPT="application/json")
        res2 = api_client.post(f"{PROMOS_URL}evaluar/", payload,
                               format="json", HTTP_ACCEPT="application/json")
        assert res1.status_code == 201
        assert res2.status_code == 200
        assert res1.data["id"] == res2.data["id"]
        assert AplicacionPromocion.objects.filter(
            pedido_id=payload["pedido_id"]
        ).count() == 1

    def test_evaluar_promo_puntos_extra(self, db, api_client):
        PromocionFactory.puntos_extra(puntos=150)
        res = api_client.post(f"{PROMOS_URL}evaluar/", self._payload(),
                              format="json", HTTP_ACCEPT="application/json")
        assert res.status_code == 201
        assert res.data["puntos_bonus_otorgados"] == 150

    def test_evaluar_promo_local_solo_aplica_en_su_restaurante(self, db, api_client):
        rid = uuid.uuid4()
        PromocionFactory.local(restaurante_id=rid)
        # mismo restaurante — debe aplicar
        res = api_client.post(f"{PROMOS_URL}evaluar/",
                              self._payload(restaurante_id=rid),
                              format="json", HTTP_ACCEPT="application/json")
        assert res.status_code == 201

    def test_evaluar_promo_local_no_aplica_en_otro_restaurante(self, db, api_client):
        PromocionFactory.local(restaurante_id=uuid.uuid4())
        res = api_client.post(f"{PROMOS_URL}evaluar/",
                              self._payload(restaurante_id=uuid.uuid4()),
                              format="json", HTTP_ACCEPT="application/json")
        assert res.status_code == 200
        assert "detail" in res.data

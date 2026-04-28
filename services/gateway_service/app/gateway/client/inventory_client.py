# services/gateway_service/app/gateway/client/inventory_client.py
# CAMBIOS vs original:
# 1. get_costo_plato → corregido a /recetas/costo_plato/ (estaba en /stock/costo-plato/)
# 2. Agrega get_recetas(plato_id) → GET /recetas/?plato_id=UUID
# Todo lo demás idéntico al archivo actual.

import httpx
import os
import socket
import logging

logger = logging.getLogger(__name__)


def _resolve_url() -> str:
    base = os.getenv("INVENTORY_SERVICE_URL",
                     "http://inventory_service:8000/api/inventory")
    try:
        hostname = base.split("//")[1].split(":")[0].split("/")[0]
        ip = socket.gethostbyname(hostname)
        resolved = base.replace(hostname, ip)
        logger.info("[inventory_client] URL resuelta: %s → %s", base, resolved)
        return resolved
    except Exception as e:
        logger.warning(
            "[inventory_client] No se pudo resolver hostname: %s", e)
        return base


INVENTORY_SERVICE_URL = _resolve_url()


def _get(path: str, params: dict = None) -> dict | list | None:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f"{INVENTORY_SERVICE_URL}{path}", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("[inventory_client] HTTP %s: %s",
                     e.response.status_code, path)
        try:
            return {"_error": True, "status": e.response.status_code, **e.response.json()}
        except Exception:
            return {"_error": True, "status": e.response.status_code, "detail": str(e)}
    except httpx.RequestError as e:
        logger.error("[inventory_client] Request error: %s", e)
        return {"_error": True, "detail": str(e)}


def _post(path: str, data: dict = None) -> dict | None:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                f"{INVENTORY_SERVICE_URL}{path}", json=data or {})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("[inventory_client] HTTP %s: %s",
                     e.response.status_code, path)
        try:
            return {"_error": True, "status": e.response.status_code, **e.response.json()}
        except Exception:
            return {"_error": True, "status": e.response.status_code, "detail": str(e)}
    except httpx.RequestError as e:
        logger.error("[inventory_client] Request error: %s", e)
        return {"_error": True, "detail": str(e)}


def _patch(path: str, data: dict) -> dict | None:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.patch(
                f"{INVENTORY_SERVICE_URL}{path}", json=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("[inventory_client] HTTP %s: %s",
                     e.response.status_code, path)
        try:
            return {"_error": True, "status": e.response.status_code, **e.response.json()}
        except Exception:
            return {"_error": True, "status": e.response.status_code, "detail": str(e)}
    except httpx.RequestError as e:
        logger.error("[inventory_client] Request error: %s", e)
        return {"_error": True, "detail": str(e)}


def _is_error(data) -> bool:
    return isinstance(data, dict) and data.get("_error") is True


def _extract_error(data: dict, fallback: str) -> str:
    if not data:
        return fallback
    errores_campo = {
        k: v for k, v in data.items()
        if k not in ("_error", "status", "detail") and isinstance(v, (list, str))
    }
    if errores_campo:
        partes = []
        for campo, msg in errores_campo.items():
            texto = msg[0] if isinstance(msg, list) else msg
            partes.append(f"{campo}: {texto}")
        return " | ".join(partes)
    return data.get("detail") or data.get("error") or fallback


# ─── Proveedor (idéntico) ─────────────────────────────────────────────────────

def get_proveedores(activo=None, pais=None, ciudad=None, alcance=None):
    params = {}
    if activo is not None:
        params["activo"] = activo
    if pais:
        params["pais"] = pais
    if ciudad:
        params["ciudad"] = ciudad
    if alcance:
        params["alcance"] = alcance
    result = _get("/proveedores/", params=params)
    return [] if _is_error(result) else (result or [])


def get_proveedores_para_gerente(restaurante_id, pais=None, ciudad=None, activo=None):
    params = {"scope": "gerente", "restaurante_id": str(restaurante_id)}
    if pais:
        params["pais_destino"] = pais
    if ciudad:
        params["ciudad_destino"] = ciudad
    if activo is not None:
        params["activo"] = activo
    result = _get("/proveedores/", params=params)
    return [] if _is_error(result) else (result or [])


def get_proveedor(id: str):
    result = _get(f"/proveedores/{id}/")
    return None if _is_error(result) else result


def crear_proveedor(data: dict):
    return _post("/proveedores/", data)


def actualizar_proveedor(id: str, data: dict):
    return _patch(f"/proveedores/{id}/", data)


# ─── Almacén (idéntico) ───────────────────────────────────────────────────────

def get_almacenes(restaurante_id=None, activo=None):
    params = {}
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if activo is not None:
        params["activo"] = activo
    result = _get("/almacenes/", params=params)
    return [] if _is_error(result) else (result or [])


def get_almacen(id: str):
    result = _get(f"/almacenes/{id}/")
    return None if _is_error(result) else result


def get_stock_almacen(id: str, bajo_minimo=None):
    params = {}
    if bajo_minimo:
        params["bajo_minimo"] = "true"
    result = _get(f"/almacenes/{id}/stock/", params=params)
    return [] if _is_error(result) else (result or [])


def crear_almacen(data: dict):
    return _post("/almacenes/", data)


# ─── Stock (idéntico) ─────────────────────────────────────────────────────────

def get_stock(almacen_id=None, bajo_minimo=None, agotado=None):
    params = {}
    if almacen_id:
        params["almacen_id"] = almacen_id
    if bajo_minimo:
        params["bajo_minimo"] = "true"
    if agotado:
        params["agotado"] = "true"
    result = _get("/stock/", params=params)
    return [] if _is_error(result) else (result or [])


def get_stock_item(id: str):
    result = _get(f"/stock/{id}/")
    return None if _is_error(result) else result


def crear_stock(data: dict):
    return _post("/stock/", data)


def ajustar_stock(id: str, cantidad: float, descripcion: str):
    return _post(f"/stock/{id}/ajustar/", {"cantidad": cantidad, "descripcion": descripcion})


def get_movimientos(id: str):
    result = _get(f"/stock/{id}/movimientos/")
    return [] if _is_error(result) else (result or [])


# ─── RECETAS Y COSTO — NUEVO/CORREGIDO ───────────────────────────────────────

def get_recetas(plato_id: str = None) -> list:
    """
    GET /api/inventory/recetas/?plato_id=UUID
    Devuelve los ingredientes de la receta de un plato.
    Se sincronizan automáticamente vía RabbitMQ desde menu_service.
    """
    params = {}
    if plato_id:
        params["plato_id"] = plato_id
    result = _get("/recetas/", params=params)
    if _is_error(result):
        return []
    # DRF puede devolver lista directa o paginada
    if isinstance(result, dict) and "results" in result:
        return result["results"]
    return result or []


def get_costo_plato(plato_id: str, restaurante_id: str = None) -> dict | None:
    """
    GET /api/inventory/recetas/costo_plato/?plato_id=UUID&restaurante_id=UUID
    Calcula costo de producción del plato y porciones disponibles.

    Responde:
      - costo_total: suma de (cantidad_receta × costo_unitario) por ingrediente
      - tiene_costos_vacios: True si algún ingrediente tiene costo=0
      - porciones_disponibles: mínimo de porciones posibles (cuello de botella)
      - ingredientes[]: desglose con stock_actual y porciones_posibles
      - advertencia: mensaje si costos incompletos

    El costo_unitario se actualiza automáticamente al recibir una orden de compra.
    """
    params = {"plato_id": plato_id}
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    result = _get("/recetas/costo_plato/", params=params)
    return None if _is_error(result) else result


# ─── Lotes (idéntico) ─────────────────────────────────────────────────────────

def get_lotes(estado=None, almacen_id=None, por_vencer=None):
    params = {}
    if estado:
        params["estado"] = estado
    if almacen_id:
        params["almacen_id"] = almacen_id
    if por_vencer:
        params["por_vencer"] = por_vencer
    result = _get("/lotes/", params=params)
    return [] if _is_error(result) else (result or [])


def get_lote(id: str):
    result = _get(f"/lotes/{id}/")
    return None if _is_error(result) else result


def crear_lote(data: dict):
    return _post("/lotes/", data)


def retirar_lote(id: str):
    return _post(f"/lotes/{id}/retirar/")


# ─── Órdenes de compra (idéntico) ────────────────────────────────────────────

def get_ordenes_compra(estado=None, proveedor_id=None, restaurante_id=None):
    params = {}
    if estado:
        params["estado"] = estado
    if proveedor_id:
        params["proveedor_id"] = proveedor_id
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    result = _get("/ordenes-compra/", params=params)
    return [] if _is_error(result) else (result or [])


def get_orden_compra(id: str):
    result = _get(f"/ordenes-compra/{id}/")
    return None if _is_error(result) else result


def crear_orden_compra(data: dict):
    return _post("/ordenes-compra/", data)


def enviar_orden_compra(id: str):
    return _post(f"/ordenes-compra/{id}/enviar/")


def recibir_orden_compra(id: str, data: dict):
    return _post(f"/ordenes-compra/{id}/recibir/", data)


def cancelar_orden_compra(id: str):
    return _post(f"/ordenes-compra/{id}/cancelar/")


# ─── Alertas (idéntico) ───────────────────────────────────────────────────────

def get_alertas(tipo=None, estado=None, restaurante_id=None):
    params = {}
    if tipo:
        params["tipo"] = tipo
    if estado:
        params["estado"] = estado
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    result = _get("/alertas/", params=params)
    return [] if _is_error(result) else (result or [])


def get_alerta(id: str):
    result = _get(f"/alertas/{id}/")
    return None if _is_error(result) else result


def resolver_alerta(id: str):
    return _post(f"/alertas/{id}/resolver/")


def ignorar_alerta(id: str):
    return _post(f"/alertas/{id}/ignorar/")

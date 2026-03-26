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
        return None
    except httpx.RequestError as e:
        logger.error("[inventory_client] Request error: %s", e)
        return None


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
        return None
    except httpx.RequestError as e:
        logger.error("[inventory_client] Request error: %s", e)
        return None


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
        return None
    except httpx.RequestError as e:
        logger.error("[inventory_client] Request error: %s", e)
        return None


# ─────────────────────────────────────────
# Proveedor
# ─────────────────────────────────────────

def get_proveedores(activo=None, pais=None):
    params = {}
    if activo is not None:
        params["activo"] = activo
    if pais:
        params["pais"] = pais
    return _get("/proveedores/", params=params) or []


def get_proveedor(id: str):
    return _get(f"/proveedores/{id}/")


def crear_proveedor(data: dict):
    return _post("/proveedores/", data)


def actualizar_proveedor(id: str, data: dict):
    return _patch(f"/proveedores/{id}/", data)


# ─────────────────────────────────────────
# Almacén
# ─────────────────────────────────────────

def get_almacenes(restaurante_id=None, activo=None):
    params = {}
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if activo is not None:
        params["activo"] = activo
    return _get("/almacenes/", params=params) or []


def get_almacen(id: str):
    return _get(f"/almacenes/{id}/")


def get_stock_almacen(id: str, bajo_minimo=None):
    params = {}
    if bajo_minimo:
        params["bajo_minimo"] = "true"
    return _get(f"/almacenes/{id}/stock/", params=params) or []


def crear_almacen(data: dict):
    return _post("/almacenes/", data)


# ─────────────────────────────────────────
# Stock (IngredienteInventario)
# ─────────────────────────────────────────

def get_stock(almacen_id=None, bajo_minimo=None, agotado=None):
    params = {}
    if almacen_id:
        params["almacen_id"] = almacen_id
    if bajo_minimo:
        params["bajo_minimo"] = "true"
    if agotado:
        params["agotado"] = "true"
    return _get("/stock/", params=params) or []


def get_stock_item(id: str):
    return _get(f"/stock/{id}/")


def crear_stock(data: dict):
    return _post("/stock/", data)


def ajustar_stock(id: str, cantidad: float, descripcion: str):
    return _post(f"/stock/{id}/ajustar/", {
        "cantidad":    cantidad,
        "descripcion": descripcion,
    })


def get_movimientos(id: str):
    return _get(f"/stock/{id}/movimientos/") or []


def get_costo_plato(plato_id: str):
    return _get("/stock/costo-plato/", params={"plato_id": plato_id})


# ─────────────────────────────────────────
# Lotes
# ─────────────────────────────────────────

def get_lotes(estado=None, almacen_id=None, por_vencer=None):
    params = {}
    if estado:
        params["estado"] = estado
    if almacen_id:
        params["almacen_id"] = almacen_id
    if por_vencer:
        params["por_vencer"] = por_vencer
    return _get("/lotes/", params=params) or []


def get_lote(id: str):
    return _get(f"/lotes/{id}/")


def crear_lote(data: dict):
    return _post("/lotes/", data)


def retirar_lote(id: str):
    return _post(f"/lotes/{id}/retirar/")


# ─────────────────────────────────────────
# Órdenes de compra
# ─────────────────────────────────────────

def get_ordenes_compra(estado=None, proveedor_id=None, restaurante_id=None):
    params = {}
    if estado:
        params["estado"] = estado
    if proveedor_id:
        params["proveedor_id"] = proveedor_id
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    return _get("/ordenes-compra/", params=params) or []


def get_orden_compra(id: str):
    return _get(f"/ordenes-compra/{id}/")


def crear_orden_compra(data: dict):
    return _post("/ordenes-compra/", data)


def enviar_orden_compra(id: str):
    return _post(f"/ordenes-compra/{id}/enviar/")


def recibir_orden_compra(id: str, data: dict):
    return _post(f"/ordenes-compra/{id}/recibir/", data)


def cancelar_orden_compra(id: str):
    return _post(f"/ordenes-compra/{id}/cancelar/")


# ─────────────────────────────────────────
# Alertas
# ─────────────────────────────────────────

def get_alertas(tipo=None, estado=None, restaurante_id=None):
    params = {}
    if tipo:
        params["tipo"] = tipo
    if estado:
        params["estado"] = estado
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    return _get("/alertas/", params=params) or []


def get_alerta(id: str):
    return _get(f"/alertas/{id}/")


def resolver_alerta(id: str):
    return _post(f"/alertas/{id}/resolver/")


def ignorar_alerta(id: str):
    return _post(f"/alertas/{id}/ignorar/")

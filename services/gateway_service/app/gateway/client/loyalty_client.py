import logging
import os
import socket

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Resolución de hostname → IP para evitar DisallowedHost en Django
# ---------------------------------------------------------------------------

def _resolve_url() -> str:
    base = os.getenv("LOYALTY_SERVICE_URL",
                     "http://loyalty_service:8000/api/loyalty")
    try:
        hostname = base.split("//")[1].split(":")[0].split("/")[0]
        ip = socket.gethostbyname(hostname)
        return base.replace(hostname, ip)
    except Exception:
        return base


LOYALTY_SERVICE_URL = _resolve_url()


# ---------------------------------------------------------------------------
# Helpers HTTP
# ---------------------------------------------------------------------------

def _get(path: str, params: dict = None):
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{LOYALTY_SERVICE_URL}{path}", params=params)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[loyalty_client] HTTP %s en GET %s",
                     exc.response.status_code, path)
        return None
    except Exception as exc:
        logger.error("[loyalty_client] Error en GET %s: %s", path, exc)
        return None


def _post(path: str, data: dict = None):
    try:
        with httpx.Client(timeout=10) as client:
            r = client.post(f"{LOYALTY_SERVICE_URL}{path}", json=data or {})
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[loyalty_client] HTTP %s en POST %s",
                     exc.response.status_code, path)
        return None
    except Exception as exc:
        logger.error("[loyalty_client] Error en POST %s: %s", path, exc)
        return None


def _patch(path: str, data: dict = None):
    try:
        with httpx.Client(timeout=10) as client:
            r = client.patch(f"{LOYALTY_SERVICE_URL}{path}", json=data or {})
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[loyalty_client] HTTP %s en PATCH %s",
                     exc.response.status_code, path)
        return None
    except Exception as exc:
        logger.error("[loyalty_client] Error en PATCH %s: %s", path, exc)
        return None


# ---------------------------------------------------------------------------
# Puntos
# ---------------------------------------------------------------------------

def get_puntos(cliente_id: str):
    return _get(f"/puntos/{cliente_id}/")


def acumular_puntos(data: dict):
    return _post("/puntos/acumular/", data=data)


def canjear_puntos(data: dict):
    return _post("/puntos/canjear/", data=data)


# ---------------------------------------------------------------------------
# Transacciones
# ---------------------------------------------------------------------------

def get_transacciones(cliente_id: str = None, tipo: str = None,
                      pedido_id: str = None, fecha_desde: str = None,
                      fecha_hasta: str = None):
    params = {}
    if cliente_id:
        params["cliente_id"] = cliente_id
    if tipo:
        params["tipo"] = tipo
    if pedido_id:
        params["pedido_id"] = pedido_id
    if fecha_desde:
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        params["fecha_hasta"] = fecha_hasta
    return _get("/transacciones/", params=params)


def get_transaccion(transaccion_id: str):
    return _get(f"/transacciones/{transaccion_id}/")


# ---------------------------------------------------------------------------
# Promociones
# ---------------------------------------------------------------------------

def get_promociones(activa: bool = None, alcance: str = None,
                    restaurante_id: str = None, tipo_beneficio: str = None):
    params = {}
    if activa is not None:
        params["activa"] = str(activa).lower()
    if alcance:
        params["alcance"] = alcance
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if tipo_beneficio:
        params["tipo_beneficio"] = tipo_beneficio
    return _get("/promociones/", params=params)


def get_promocion(promocion_id: str):
    return _get(f"/promociones/{promocion_id}/")


def crear_promocion(data: dict):
    return _post("/promociones/", data=data)


def editar_promocion(promocion_id: str, data: dict):
    return _patch(f"/promociones/{promocion_id}/", data=data)


def activar_promocion(promocion_id: str):
    return _post(f"/promociones/{promocion_id}/activar/")


def desactivar_promocion(promocion_id: str):
    return _post(f"/promociones/{promocion_id}/desactivar/")


def evaluar_promocion(data: dict):
    return _post("/promociones/evaluar/", data=data)


# ---------------------------------------------------------------------------
# Cupones
# ---------------------------------------------------------------------------

def get_cupones(cliente_id: str = None, activo: bool = None, codigo: str = None):
    params = {}
    if cliente_id:
        params["cliente_id"] = cliente_id
    if activo is not None:
        params["activo"] = str(activo).lower()
    if codigo:
        params["codigo"] = codigo
    return _get("/cupones/", params=params)


def get_cupon(cupon_id: str):
    return _get(f"/cupones/{cupon_id}/")


def validar_cupon(codigo: str):
    return _get("/cupones/validar/", params={"codigo": codigo})


def crear_cupon(data: dict):
    return _post("/cupones/", data=data)


def canjear_cupon(cupon_id: str, pedido_id: str = None):
    data = {}
    if pedido_id:
        data["pedido_id"] = pedido_id
    return _post(f"/cupones/{cupon_id}/canjear/", data=data)


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------

def get_catalogo_platos(activo: bool = None, categoria_id: str = None):
    params = {}
    if activo is not None:
        params["activo"] = str(activo).lower()
    if categoria_id:
        params["categoria_id"] = categoria_id
    return _get("/catalogo/platos/", params=params)


def get_catalogo_categorias(activo: bool = None):
    params = {}
    if activo is not None:
        params["activo"] = str(activo).lower()
    return _get("/catalogo/categorias/", params=params)

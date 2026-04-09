# gateway_service/app/gateway/client/loyalty_client.py
# CORRECCIÓN: loyalty_service usa PageNumberPagination → retorna
# {"count": N, "results": [...]} en lugar de lista directa.
# Fix: _get_list() extrae "results" si la respuesta es paginada.

import logging
import os
import socket

import httpx

logger = logging.getLogger(__name__)


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


def _get(path: str, params: dict = None):
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f"{LOYALTY_SERVICE_URL}{path}", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[loyalty_client] HTTP %s en GET %s",
                     exc.response.status_code, path)
        return None
    except Exception as exc:
        logger.error("[loyalty_client] Error en GET %s: %s", path, exc)
        return None


def _get_list(path: str, params: dict = None) -> list:
    """
    GET que siempre retorna lista.
    Maneja respuesta paginada {"count": N, "results": [...]}
    y también respuesta directa [...].
    """
    data = _get(path, params=params)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    logger.warning(
        "[loyalty_client] Respuesta inesperada en %s: %s", path, type(data))
    return []


def _post(path: str, data: dict = None):
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                f"{LOYALTY_SERVICE_URL}{path}", json=data or {})
            response.raise_for_status()
            return response.json()
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
            response = client.patch(
                f"{LOYALTY_SERVICE_URL}{path}", json=data or {})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[loyalty_client] HTTP %s en PATCH %s",
                     exc.response.status_code, path)
        return None
    except Exception as exc:
        logger.error("[loyalty_client] Error en PATCH %s: %s", path, exc)
        return None


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------

def get_cliente(cliente_id: str = None, telefono: str = None):
    """Retorna un objeto cliente, no lista."""
    if cliente_id:
        return _get(f"/clientes/{cliente_id}/")
    if telefono:
        results = _get_list("/clientes/", params={"telefono": telefono})
        return results[0] if results else None
    return None


def get_o_crear_cliente(telefono: str, nombre: str = None):
    return _post("/clientes/get-or-create/", data={"telefono": telefono, "nombre": nombre})


def get_puntos(cliente_id: str):
    """Retorna objeto con puntos actuales, no lista."""
    return _get(f"/clientes/{cliente_id}/puntos/")


# ---------------------------------------------------------------------------
# Transacciones de puntos
# ---------------------------------------------------------------------------

def get_transacciones(cliente_id: str = None, restaurante_id: str = None,
                      tipo: str = None, fecha_desde: str = None, fecha_hasta: str = None):
    params = {}
    if cliente_id:
        params["cliente_id"] = cliente_id
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if tipo:
        params["tipo"] = tipo
    if fecha_desde:
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        params["fecha_hasta"] = fecha_hasta
    return _get_list("/transacciones/", params=params)


def acumular_puntos(cliente_id: str, pedido_id: str, restaurante_id: str, monto: float):
    return _post("/transacciones/acumular/", data={
        "cliente_id": cliente_id,
        "pedido_id": pedido_id,
        "restaurante_id": restaurante_id,
        "monto": monto,
    })


# ---------------------------------------------------------------------------
# Niveles
# ---------------------------------------------------------------------------

def get_niveles():
    return _get_list("/niveles/")


def get_nivel(nivel_id: str):
    return _get(f"/niveles/{nivel_id}/")


# ---------------------------------------------------------------------------
# Promociones
# ---------------------------------------------------------------------------

def get_promociones(restaurante_id: str = None, activa: bool = None,
                    tipo: str = None, alcance: str = None,
                    tipo_beneficio: str = None):
    params = {}
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if activa is not None:
        params["activa"] = str(activa).lower()
    if tipo:
        params["tipo"] = tipo
    if alcance:
        params["alcance"] = alcance
    if tipo_beneficio:
        params["tipo_beneficio"] = tipo_beneficio
    return _get_list("/promociones/", params=params)


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
# Aplicaciones de promociones
# ---------------------------------------------------------------------------

def get_aplicaciones(cliente_id: str = None, restaurante_id: str = None,
                     promocion_id: str = None):
    params = {}
    if cliente_id:
        params["cliente_id"] = cliente_id
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if promocion_id:
        params["promocion_id"] = promocion_id
    return _get_list("/aplicaciones/", params=params)


# ---------------------------------------------------------------------------
# Cupones
# ---------------------------------------------------------------------------

def get_cupones(cliente_id: str = None, activo: bool = None,
                restaurante_id: str = None, codigo: str = None):
    params = {}
    if cliente_id:
        params["cliente_id"] = cliente_id
    if activo is not None:
        params["activo"] = str(activo).lower()
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if codigo:
        params["codigo"] = codigo
    return _get_list("/cupones/", params=params)


def get_cupon(cupon_id: str):
    return _get(f"/cupones/{cupon_id}/")


def validar_cupon(codigo: str):
    """Valida cupón por código. Retorna el cupon si existe, None si no."""
    return _get("/cupones/validar/", params={"codigo": codigo})


def canjear_cupon(cupon_id: str, pedido_id: str = None):
    data = {}
    if pedido_id:
        data["pedido_id"] = pedido_id
    return _post(f"/cupones/{cupon_id}/canjear/", data=data)


def crear_cupon(data: dict):
    return _post("/cupones/", data=data)


# ---------------------------------------------------------------------------
# Puntos — mutaciones
# ---------------------------------------------------------------------------

def acumular_puntos(data: dict):
    """Recibe dict con cliente_id, puntos, pedido_id, restaurante_id, descripcion."""
    return _post("/transacciones/acumular/", data=data)


def canjear_puntos(data: dict):
    """Recibe dict con cliente_id, puntos, pedido_id, descripcion."""
    return _post("/transacciones/canjear/", data=data)


def get_transaccion(transaccion_id: str):
    return _get(f"/transacciones/{transaccion_id}/")


# ---------------------------------------------------------------------------
# Historial de niveles
# ---------------------------------------------------------------------------

def get_historial_niveles(cliente_id: str):
    return _get_list(f"/clientes/{cliente_id}/historial-niveles/")


# ---------------------------------------------------------------------------
# Catálogo (caché local de platos/categorías en loyalty_service)
# _get_list() aplica automáticamente — resuelve el count/next/results
# ---------------------------------------------------------------------------

def get_catalogo_platos(activo: bool = None, categoria_id: str = None):
    params = {}
    if activo is not None:
        params["activo"] = str(activo).lower()
    if categoria_id:
        params["categoria_id"] = categoria_id
    return _get_list("/catalogo/platos/", params=params)


def get_catalogo_categorias(activo: bool = None):
    params = {}
    if activo is not None:
        params["activo"] = str(activo).lower()
    return _get_list("/catalogo/categorias/", params=params)

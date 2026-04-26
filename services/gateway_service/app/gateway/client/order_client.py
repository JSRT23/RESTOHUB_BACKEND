import httpx
import os
import socket
import logging

logger = logging.getLogger(__name__)


def _resolve_url() -> str:
    base = os.getenv("ORDER_SERVICE_URL",
                     "http://order_service:8000/api/orders")
    try:
        hostname = base.split("//")[1].split(":")[0].split("/")[0]
        ip = socket.gethostbyname(hostname)
        resolved = base.replace(hostname, ip)
        logger.info("[order_client] URL resuelta: %s → %s", base, resolved)
        return resolved
    except Exception as e:
        logger.warning("[order_client] No se pudo resolver hostname: %s", e)
        return base


ORDER_SERVICE_URL = _resolve_url()


def _get(path: str, params: dict = None) -> dict | list | None:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{ORDER_SERVICE_URL}{path}", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("[order_client] HTTP error %s: %s",
                     e.response.status_code, path)
        return None
    except httpx.RequestError as e:
        logger.error("[order_client] Request error: %s", e)
        return None


def _post(path: str, data: dict = None) -> dict | None:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                f"{ORDER_SERVICE_URL}{path}", json=data or {})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("[order_client] HTTP error %s: %s",
                     e.response.status_code, path)
        # ── CAMBIO: propagar el error real del order_service ──────────────
        try:
            body = e.response.json()
            detail = (
                body.get("detail")
                or body.get("error")
                or body.get("message")
                or "; ".join(
                    f"{k}: {v[0] if isinstance(v, list) else v}"
                    for k, v in body.items()
                    if isinstance(v, (str, list)) and k not in ("status",)
                )
                or f"HTTP {e.response.status_code}"
            )
            return {"_error": True, "status": e.response.status_code, "detail": detail}
        except Exception:
            return {"_error": True, "status": e.response.status_code, "detail": str(e)}
    except httpx.RequestError as e:
        logger.error("[order_client] Request error: %s", e)
        return {"_error": True, "detail": str(e)}


def _patch(path: str, data: dict) -> dict | None:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.patch(f"{ORDER_SERVICE_URL}{path}", json=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("[order_client] HTTP error %s: %s",
                     e.response.status_code, path)
        try:
            body = e.response.json()
            detail = body.get("detail") or f"HTTP {e.response.status_code}"
            return {"_error": True, "status": e.response.status_code, "detail": detail}
        except Exception:
            return {"_error": True, "status": e.response.status_code, "detail": str(e)}
    except httpx.RequestError as e:
        logger.error("[order_client] Request error: %s", e)
        return {"_error": True, "detail": str(e)}


# ─────────────────────────────────────────
# Pedido
# ─────────────────────────────────────────

def get_pedidos(estado=None, canal=None, restaurante_id=None, cliente_id=None):
    params = {}
    if estado:
        params["estado"] = estado
    if canal:
        params["canal"] = canal
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if cliente_id:
        params["cliente_id"] = cliente_id
    data = _get("/pedidos/", params=params)
    # order_service devuelve respuesta paginada: {"count": N, "results": [...]}
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data or []


def get_pedido(id: str):
    return _get(f"/pedidos/{id}/")


def crear_pedido(data: dict):
    return _post("/pedidos/", data)


def confirmar_pedido(id: str, descripcion: str = ""):
    return _post(f"/pedidos/{id}/confirmar/", {"descripcion": descripcion})


def cancelar_pedido(id: str, descripcion: str = ""):
    return _post(f"/pedidos/{id}/cancelar/", {"descripcion": descripcion})


def marcar_listo(id: str, descripcion: str = ""):
    return _post(f"/pedidos/{id}/marcar_listo/", {"descripcion": descripcion})


def entregar_pedido(id: str, descripcion: str = "", metodo_pago: str = None):
    payload = {"descripcion": descripcion}
    if metodo_pago:
        payload["metodo_pago"] = metodo_pago
    return _post(f"/pedidos/{id}/entregar/", payload)


def get_seguimiento(id: str):
    return _get(f"/pedidos/{id}/seguimiento/") or []


def get_detalles(id: str):
    return _get(f"/pedidos/{id}/detalles/") or []


def agregar_detalle(id: str, data: dict):
    return _post(f"/pedidos/{id}/detalles/", data)


# ─────────────────────────────────────────
# Comanda
# ─────────────────────────────────────────

def get_comandas(estado=None, estacion=None, pedido_id=None):
    params = {}
    if estado:
        params["estado"] = estado
    if estacion:
        params["estacion"] = estacion
    if pedido_id:
        params["pedido_id"] = pedido_id
    data = _get("/comandas/", params=params)
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data or []


def get_comanda(id: str):
    return _get(f"/comandas/{id}/")


def crear_comanda(data: dict):
    return _post("/comandas/", data)


def iniciar_comanda(id: str):
    return _post(f"/comandas/{id}/iniciar/")


def comanda_lista(id: str):
    return _post(f"/comandas/{id}/lista/")


# ─────────────────────────────────────────
# Entrega
# ─────────────────────────────────────────

def get_entrega(id: str):
    return _get(f"/entregas/{id}/")


def crear_entrega(data: dict):
    return _post("/entregas/", data)


def entrega_en_camino(id: str):
    return _post(f"/entregas/{id}/en_camino/")


def completar_entrega(id: str):
    return _post(f"/entregas/{id}/completar/")


def entrega_fallo(id: str):
    return _post(f"/entregas/{id}/fallo/")

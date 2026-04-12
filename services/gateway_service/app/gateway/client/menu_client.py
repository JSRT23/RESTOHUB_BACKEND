# gateway_service/app/gateway/client/menu_client.py
import httpx
import os
import socket
import logging

logger = logging.getLogger(__name__)


def _resolve_url() -> str:
    base = os.getenv("MENU_SERVICE_URL", "http://menu_service:8000/api/menu")
    try:
        hostname = base.split("//")[1].split(":")[0].split("/")[0]
        ip = socket.gethostbyname(hostname)
        resolved = base.replace(hostname, ip)
        logger.info("[menu_client] URL resuelta: %s → %s", base, resolved)
        return resolved
    except Exception as e:
        logger.warning("[menu_client] No se pudo resolver hostname: %s", e)
        return base


MENU_SERVICE_URL = _resolve_url()


def _get(path: str, params: dict = None):
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{MENU_SERVICE_URL}{path}", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("[menu_client] HTTP %s: %s", e.response.status_code, path)
        return None
    except httpx.RequestError as e:
        logger.error("[menu_client] Request error: %s", e)
        return None


def _post(path: str, data: dict) -> dict | None:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(f"{MENU_SERVICE_URL}{path}", json=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("[menu_client] HTTP %s: %s", e.response.status_code, path)
        return None
    except httpx.RequestError as e:
        logger.error("[menu_client] Request error: %s", e)
        return None


def _patch(path: str, data: dict) -> dict | None:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.patch(f"{MENU_SERVICE_URL}{path}", json=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("[menu_client] HTTP %s: %s", e.response.status_code, path)
        return None
    except httpx.RequestError as e:
        logger.error("[menu_client] Request error: %s", e)
        return None


def _delete(path: str) -> bool:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.delete(f"{MENU_SERVICE_URL}{path}")
            response.raise_for_status()
            return True
    except Exception as e:
        logger.error("[menu_client] Delete error: %s", e)
        return False


# ── Restaurante ────────────────────────────────────────────────────────────

def get_restaurantes(activo=None, pais=None):
    params = {}
    if activo is not None:
        params["activo"] = activo
    if pais:
        params["pais"] = pais
    return _get("/restaurantes/", params=params) or []


def get_restaurante(id: str):
    return _get(f"/restaurantes/{id}/")


def get_menu_restaurante(id: str):
    return _get(f"/restaurantes/{id}/menu/")


def crear_restaurante(data: dict):
    return _post("/restaurantes/", data)


def actualizar_restaurante(id: str, data: dict):
    return _patch(f"/restaurantes/{id}/", data)


def activar_restaurante(id: str):
    return _post(f"/restaurantes/{id}/activar/", {})


def desactivar_restaurante(id: str):
    return _post(f"/restaurantes/{id}/desactivar/", {})


# ── Categoría ──────────────────────────────────────────────────────────────

def get_categorias(activo=None):
    params = {}
    if activo is not None:
        params["activo"] = activo
    return _get("/categorias/", params=params) or []


def get_categoria(id: str):
    return _get(f"/categorias/{id}/")


def crear_categoria(data: dict):
    return _post("/categorias/", data)


def actualizar_categoria(id: str, data: dict):
    return _patch(f"/categorias/{id}/", data)


def activar_categoria(id: str):
    return _post(f"/categorias/{id}/activar/", {})


def desactivar_categoria(id: str):
    return _post(f"/categorias/{id}/desactivar/", {})


# ── Ingrediente ────────────────────────────────────────────────────────────

def get_ingredientes(activo=None, restaurante_id=None, disponibles=None):
    """
    disponibles=UUID → globales + del restaurante X (para el gerente)
    restaurante_id=UUID → solo de ese restaurante
    sin parámetro → todos (admin)
    """
    params = {}
    if activo is not None:
        params["activo"] = activo
    if disponibles:
        params["disponibles"] = disponibles
    elif restaurante_id:
        params["restaurante_id"] = restaurante_id
    return _get("/ingredientes/", params=params) or []


def crear_ingrediente(data: dict):
    # data puede incluir "restaurante" (UUID del restaurante) o no (global)
    return _post("/ingredientes/", data)


def actualizar_ingrediente(id: str, data: dict):
    return _patch(f"/ingredientes/{id}/", data)


def activar_ingrediente(id: str):
    return _post(f"/ingredientes/{id}/activar/", {})


def desactivar_ingrediente(id: str):
    return _post(f"/ingredientes/{id}/desactivar/", {})


# ── Plato ──────────────────────────────────────────────────────────────────

def get_platos(activo=None, categoria_id=None, restaurante_id=None, disponibles=None):
    """
    disponibles=UUID → globales + del restaurante X (para el gerente)
    restaurante_id=UUID → solo de ese restaurante
    sin parámetro → todos (admin)
    """
    params = {}
    if activo is not None:
        params["activo"] = activo
    if categoria_id:
        params["categoria"] = categoria_id
    if disponibles:
        params["disponibles"] = disponibles
    elif restaurante_id:
        params["restaurante_id"] = restaurante_id
    return _get("/platos/", params=params) or []


def get_plato(id: str):
    return _get(f"/platos/{id}/")


def crear_plato(data: dict):
    # data puede incluir "restaurante" (UUID) o no (global)
    return _post("/platos/", data)


def actualizar_plato(id: str, data: dict):
    return _patch(f"/platos/{id}/", data)


def eliminar_plato(id: str):
    return _delete(f"/platos/{id}/")


def activar_plato(id: str):
    return _post(f"/platos/{id}/activar/", {})


def desactivar_plato(id: str):
    return _post(f"/platos/{id}/desactivar/", {})


def agregar_ingrediente_plato(plato_id: str, data: dict):
    return _post(f"/platos/{plato_id}/ingredientes/", data)


def quitar_ingrediente_plato(plato_id: str, ingrediente_id: str):
    return _delete(f"/platos/{plato_id}/ingredientes/{ingrediente_id}/")


# ── Precio ─────────────────────────────────────────────────────────────────

def get_precios(plato_id=None, restaurante_id=None, activo=None):
    params = {}
    if plato_id:
        params["plato"] = plato_id
    if restaurante_id:
        params["restaurante"] = restaurante_id
    if activo is not None:
        params["activo"] = activo
    return _get("/precios/", params=params) or []


def crear_precio(data: dict):
    return _post("/precios/", data)


def activar_precio(id: str):
    return _post(f"/precios/{id}/activar/", {})


def desactivar_precio(id: str):
    return _post(f"/precios/{id}/desactivar/", {})

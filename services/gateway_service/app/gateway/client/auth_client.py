# gateway_service/app/gateway/client/auth_client.py
import logging
import os
import socket

import httpx

logger = logging.getLogger(__name__)


def _resolve_url() -> str:
    base = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8000/api/auth")
    try:
        hostname = base.split("//")[1].split(":")[0].split("/")[0]
        ip = socket.gethostbyname(hostname)
        return base.replace(hostname, ip)
    except Exception:
        return base


AUTH_SERVICE_URL = _resolve_url()


def _post(path: str, data: dict = None):
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                f"{AUTH_SERVICE_URL}{path}", json=data or {})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[auth_client] HTTP %s en POST %s",
                     exc.response.status_code, path)
        try:
            return {"_error": True, "status": exc.response.status_code, **exc.response.json()}
        except Exception:
            return {"_error": True, "status": exc.response.status_code, "detail": str(exc)}
    except Exception as exc:
        logger.error("[auth_client] Error en POST %s: %s", path, exc)
        return {"_error": True, "detail": str(exc)}


def _post_auth(path: str, data: dict, token: str):
    """POST autenticado — para endpoints que requieren Bearer token."""
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                f"{AUTH_SERVICE_URL}{path}",
                json=data,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[auth_client] HTTP %s en POST %s",
                     exc.response.status_code, path)
        try:
            return {"_error": True, "status": exc.response.status_code, **exc.response.json()}
        except Exception:
            return {"_error": True, "detail": str(exc)}
    except Exception as exc:
        logger.error("[auth_client] Error en POST %s: %s", path, exc)
        return {"_error": True, "detail": str(exc)}


def _get(path: str, headers: dict = None, params: dict = None):
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f"{AUTH_SERVICE_URL}{path}",
                headers=headers or {},
                params=params or {},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[auth_client] HTTP %s en GET %s",
                     exc.response.status_code, path)
        return None
    except Exception as exc:
        logger.error("[auth_client] Error en GET %s: %s", path, exc)
        return None


def login(email: str, password: str) -> dict:
    return _post("/login/", {"email": email, "password": password})


def auto_registro(data: dict) -> dict:
    return _post("/auto-registro/", data)


def registro(data: dict, token: str) -> dict:
    return _post_auth("/registro/", data, token)


def verificar_codigo(email: str, codigo: str) -> dict:
    return _post("/verificar-codigo/", {"email": email, "codigo": codigo})


def reenviar_codigo(email: str) -> dict:
    return _post("/reenviar-codigo/", {"email": email})


def refresh_token(refresh_token_str: str) -> dict:
    return _post("/refresh/", {"refresh_token": refresh_token_str})


def verificar_jwt(token: str) -> dict:
    return _post("/verificar/", {"token": token})


def desactivar_usuario(email: str, token: str) -> dict:
    return _post_auth("/usuarios/desactivar/", {"email": email}, token)


def activar_usuario(email: str, token: str) -> dict:
    return _post_auth("/usuarios/activar/", {"email": email}, token)


def vincular_empleado(email: str, empleado_id: str, token: str) -> dict:
    """
    Asigna el empleado_id de staff_service a la cuenta auth por email.
    Se llama automáticamente desde el gateway al crear un empleado en staff_service.
    También puede llamarse manualmente desde la vista de admin de usuarios.
    """
    return _post_auth(
        "/usuarios/vincular-empleado/",
        {"email": email, "empleado_id": empleado_id},
        token,
    )


def get_usuarios(rol: str = None, activo: bool = None,
                 restaurante_id: str = None, token: str = None) -> list:
    """
    Lista usuarios del auth_service.
    Requiere token de admin_central o gerente_local.
    """
    params = {}
    if rol:
        params["rol"] = rol
    if activo is not None:
        params["activo"] = str(activo).lower()
    if restaurante_id:
        params["restaurante_id"] = restaurante_id

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    result = _get("/usuarios/", headers=headers, params=params)
    if result is None:
        return []
    if isinstance(result, list):
        return result
    # DRF paginado: {"count": N, "results": [...]}
    if isinstance(result, dict) and "results" in result:
        return result["results"]
    return []

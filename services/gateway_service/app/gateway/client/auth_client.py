# gateway_service/app/gateway/client/auth_client.py
# CAMBIO: agrega función bootstrap_admin() al final.

import logging
import os
import httpx

logger = logging.getLogger(__name__)


def _resolve_url() -> str:
    base = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8000/api/auth")
    # Normalizar: asegurar que termina en /api/auth
    # Si la env var no incluye el path (ej: https://host.onrender.com), agregarlo
    if base.endswith("/api/auth") or base.endswith("/api/auth/"):
        return base.rstrip("/")
    # Quitar trailing slash y agregar /api/auth
    return base.rstrip("/") + "/api/auth"


AUTH_SERVICE_URL = _resolve_url()


def _post(path: str, data: dict = None):
    try:
        with httpx.Client(timeout=10, verify=False) as client:
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
        with httpx.Client(timeout=10, verify=False) as client:
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
        with httpx.Client(timeout=10, verify=False) as client:
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
    return _post_auth(
        "/usuarios/vincular-empleado/",
        {"email": email, "empleado_id": empleado_id},
        token,
    )


def get_autenticado(path: str, params: dict = None, token: str = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _get(path, headers=headers, params=params)


def get(path: str, params: dict = None, token: str = None):
    return get_autenticado(path, params=params, token=token)


def get_usuarios(rol: str = None, activo: bool = None,
                 restaurante_id: str = None, token: str = None) -> list:
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
    if isinstance(result, dict) and "results" in result:
        return result["results"]
    return []


def bootstrap_admin(data: dict) -> dict:
    """
    Crea el primer admin_central del sistema.
    Solo funciona si no existe ningún admin_central en la BD.
    Llama a POST /api/auth/bootstrap-admin/ (endpoint público, sin token).
    """
    return _post("/bootstrap-admin/", data)

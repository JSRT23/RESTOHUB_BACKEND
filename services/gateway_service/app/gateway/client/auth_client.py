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
        # Retornar el body del error para que el resolver pueda inspeccionarlo
        try:
            return {"_error": True, "status": exc.response.status_code, **exc.response.json()}
        except Exception:
            return {"_error": True, "status": exc.response.status_code, "detail": str(exc)}
    except Exception as exc:
        logger.error("[auth_client] Error en POST %s: %s", path, exc)
        return {"_error": True, "detail": str(exc)}


def _get(path: str, headers: dict = None):
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f"{AUTH_SERVICE_URL}{path}", headers=headers or {})
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
    """Registro interno — requiere token de admin/gerente."""
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                f"{AUTH_SERVICE_URL}/registro/",
                json=data,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        try:
            return {"_error": True, "status": exc.response.status_code, **exc.response.json()}
        except Exception:
            return {"_error": True, "detail": str(exc)}
    except Exception as exc:
        return {"_error": True, "detail": str(exc)}


def verificar_codigo(email: str, codigo: str) -> dict:
    return _post("/verificar-codigo/", {"email": email, "codigo": codigo})


def reenviar_codigo(email: str) -> dict:
    return _post("/reenviar-codigo/", {"email": email})


def refresh_token(refresh_token_str: str) -> dict:
    return _post("/refresh/", {"refresh_token": refresh_token_str})


def verificar_jwt(token: str) -> dict:
    """Verifica el JWT — usado por el middleware."""
    return _post("/verificar/", {"token": token})

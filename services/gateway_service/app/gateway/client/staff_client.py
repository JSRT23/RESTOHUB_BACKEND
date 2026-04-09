# gateway_service/app/gateway/client/staff_client.py
# CORRECCIÓN: staff_service usa PageNumberPagination → retorna
# {"count": N, "results": [...]} en lugar de lista directa.
# Fix: _get_list() extrae "results" si la respuesta es paginada.
# Mismo patrón aplicable a loyalty_client si activa paginación.

import logging
import os
import socket

import httpx

logger = logging.getLogger(__name__)


def _resolve_url() -> str:
    base = os.getenv("STAFF_SERVICE_URL",
                     "http://staff_service:8000/api/staff")
    try:
        hostname = base.split("//")[1].split(":")[0].split("/")[0]
        ip = socket.gethostbyname(hostname)
        return base.replace(hostname, ip)
    except Exception:
        return base


STAFF_SERVICE_URL = _resolve_url()


def _get(path: str, params: dict = None):
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{STAFF_SERVICE_URL}{path}", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[staff_client] HTTP %s en GET %s",
                     exc.response.status_code, path)
        return None
    except Exception as exc:
        logger.error("[staff_client] Error en GET %s: %s", path, exc)
        return None


def _get_list(path: str, params: dict = None) -> list:
    """
    GET que siempre retorna lista.
    ✅ Maneja respuesta paginada {"count": N, "results": [...]}
    y también respuesta directa [...].
    """
    data = _get(path, params=params)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    # Fallback — retornar vacío antes que explotar graphene
    logger.warning(
        "[staff_client] Respuesta inesperada en %s: %s", path, type(data))
    return []


def _post(path: str, data: dict = None):
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                f"{STAFF_SERVICE_URL}{path}", json=data or {})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[staff_client] HTTP %s en POST %s",
                     exc.response.status_code, path)
        return None
    except Exception as exc:
        logger.error("[staff_client] Error en POST %s: %s", path, exc)
        return None


def _patch(path: str, data: dict = None):
    try:
        with httpx.Client(timeout=10) as client:
            response = client.patch(
                f"{STAFF_SERVICE_URL}{path}", json=data or {})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("[staff_client] HTTP %s en PATCH %s",
                     exc.response.status_code, path)
        return None
    except Exception as exc:
        logger.error("[staff_client] Error en PATCH %s: %s", path, exc)
        return None


# ---------------------------------------------------------------------------
# Restaurantes
# ---------------------------------------------------------------------------

def get_restaurantes(pais: str = None, activo: bool = None):
    params = {}
    if pais:
        params["pais"] = pais
    if activo is not None:
        params["activo"] = str(activo).lower()
    return _get_list("/restaurantes/", params=params)


def get_restaurante(restaurante_id: str):
    return _get(f"/restaurantes/{restaurante_id}/")


def get_config_laboral(restaurante_id: str):
    return _get(f"/restaurantes/{restaurante_id}/config-laboral/")


# ---------------------------------------------------------------------------
# Empleados
# ---------------------------------------------------------------------------

def get_empleados(restaurante_id: str = None, rol: str = None, activo: bool = None):
    params = {}
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if rol:
        params["rol"] = rol
    if activo is not None:
        params["activo"] = str(activo).lower()
    return _get_list("/empleados/", params=params)


def get_empleado(empleado_id: str):
    return _get(f"/empleados/{empleado_id}/")


def crear_empleado(data: dict):
    return _post("/empleados/", data=data)


def editar_empleado(empleado_id: str, data: dict):
    return _patch(f"/empleados/{empleado_id}/", data=data)


def desactivar_empleado(empleado_id: str):
    return _post(f"/empleados/{empleado_id}/desactivar/")


# ---------------------------------------------------------------------------
# Turnos
# ---------------------------------------------------------------------------

def get_turnos(empleado_id: str = None, restaurante_id: str = None,
               estado: str = None, fecha_desde: str = None, fecha_hasta: str = None):
    params = {}
    if empleado_id:
        params["empleado_id"] = empleado_id
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if estado:
        params["estado"] = estado
    if fecha_desde:
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        params["fecha_hasta"] = fecha_hasta
    return _get_list("/turnos/", params=params)


def get_turno(turno_id: str):
    return _get(f"/turnos/{turno_id}/")


def crear_turno(data: dict):
    return _post("/turnos/", data=data)


def iniciar_turno(turno_id: str):
    return _post(f"/turnos/{turno_id}/iniciar/")


def cancelar_turno(turno_id: str):
    return _post(f"/turnos/{turno_id}/cancelar/")


# ---------------------------------------------------------------------------
# Asistencia
# ---------------------------------------------------------------------------

def get_asistencia(empleado_id: str = None, fecha_desde: str = None,
                   fecha_hasta: str = None, restaurante_id: str = None):
    params = {}
    if empleado_id:
        params["empleado_id"] = empleado_id
    if fecha_desde:
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        params["fecha_hasta"] = fecha_hasta
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    return _get_list("/asistencia/", params=params)


def registrar_entrada(qr_token: str = None, turno_id: str = None, metodo: str = "qr"):
    data = {"metodo_registro": metodo}
    if qr_token:
        data["qr_token"] = qr_token
    if turno_id:
        data["turno_id"] = turno_id
    return _post("/asistencia/entrada/", data=data)


def registrar_salida(turno_id: str):
    return _post("/asistencia/salida/", data={"turno_id": turno_id})


# ---------------------------------------------------------------------------
# Estaciones y asignaciones de cocina
# ---------------------------------------------------------------------------

def get_estaciones(restaurante_id: str = None, activa: bool = None):
    params = {}
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if activa is not None:
        params["activa"] = str(activa).lower()
    return _get_list("/estaciones/", params=params)


def crear_estacion(data: dict):
    return _post("/estaciones/", data=data)


def get_asignaciones_cocina(restaurante_id: str = None, cocinero_id: str = None,
                            fecha_desde: str = None, sin_completar: bool = None):
    params = {}
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if cocinero_id:
        params["cocinero_id"] = cocinero_id
    if fecha_desde:
        params["fecha_desde"] = fecha_desde
    if sin_completar is not None:
        params["sin_completar"] = str(sin_completar).lower()
    return _get_list("/asignaciones-cocina/", params=params)


# ---------------------------------------------------------------------------
# Entregas
# ---------------------------------------------------------------------------

def get_entregas(repartidor_id: str = None, estado: str = None):
    params = {}
    if repartidor_id:
        params["repartidor_id"] = repartidor_id
    if estado:
        params["estado"] = estado
    return _get_list("/entregas/", params=params)


def get_repartidores_disponibles(restaurante_id: str = None):
    params = {}
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    return _get_list("/entregas/disponibles/", params=params)


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------

def get_alertas(restaurante_id: str = None, nivel: str = None,
                tipo: str = None, resuelta: bool = None):
    params = {}
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if nivel:
        params["nivel"] = nivel
    if tipo:
        params["tipo"] = tipo
    if resuelta is not None:
        params["resuelta"] = str(resuelta).lower()
    return _get_list("/alertas/", params=params)


def resolver_alerta(alerta_id: str):
    return _post(f"/alertas/{alerta_id}/resolver/")


# ---------------------------------------------------------------------------
# Nómina
# ---------------------------------------------------------------------------

def get_nomina(empleado_id: str = None, restaurante_id: str = None, cerrado: bool = None):
    params = {}
    if empleado_id:
        params["empleado_id"] = empleado_id
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if cerrado is not None:
        params["cerrado"] = str(cerrado).lower()
    return _get_list("/nomina/", params=params)


def generar_nomina(data: dict):
    return _post("/nomina/generar/", data=data)


def cerrar_nomina(resumen_id: str):
    return _post(f"/nomina/{resumen_id}/cerrar/")


# ---------------------------------------------------------------------------
# Predicción de personal
# ---------------------------------------------------------------------------

def get_predicciones(restaurante_id: str = None, fecha_desde: str = None,
                     fecha_hasta: str = None):
    params = {}
    if restaurante_id:
        params["restaurante_id"] = restaurante_id
    if fecha_desde:
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        params["fecha_hasta"] = fecha_hasta
    return _get_list("/predicciones/", params=params)


def get_prediccion_semana(restaurante_id: str):
    return _get_list(f"/predicciones/{restaurante_id}/semana/")


def crear_prediccion(data: dict):
    return _post("/predicciones/", data=data)

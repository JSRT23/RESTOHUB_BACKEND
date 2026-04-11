# auth_service/app/auth/email_validator.py
"""
Validación de correos reales mediante MX lookup.

Verifica que el dominio del email tenga servidores de correo
configurados (registros MX en DNS). Esto garantiza que el correo
es de un dominio real que puede recibir emails.

Ejemplos:
    gmail.com       → ✓ tiene MX
    hotmail.com     → ✓ tiene MX
    fake123.xyz     → ✗ sin MX o dominio inexistente
    dominiofalso.co → ✗ NXDOMAIN

No verifica que el buzón específico exista (eso requeriría SMTP ping
que es lento y muchos servidores lo bloquean).
"""
import logging
import re

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
)

# Dominios conocidos que siempre tienen MX — cache local para evitar
# lookups innecesarios en los más comunes
DOMINIOS_CONOCIDOS = {
    "gmail.com", "googlemail.com",
    "hotmail.com", "hotmail.es", "hotmail.co",
    "outlook.com", "outlook.es",
    "yahoo.com", "yahoo.es", "yahoo.co",
    "icloud.com", "me.com", "mac.com",
    "live.com", "live.es",
    "protonmail.com", "proton.me",
    "ucc.edu.co", "unicordoba.edu.co",
}


def validar_formato(email: str) -> bool:
    """Valida que el email tenga formato correcto."""
    return bool(EMAIL_REGEX.match(email.strip()))


def validar_dominio_mx(email: str) -> tuple[bool, str]:
    """
    Verifica que el dominio del email tenga registros MX.

    Retorna:
        (True, "")           → dominio válido con MX
        (False, "mensaje")   → dominio inválido o sin MX
    """
    email = email.strip().lower()

    if not validar_formato(email):
        return False, "El formato del correo no es válido."

    try:
        dominio = email.split("@")[1]
    except IndexError:
        return False, "El correo no tiene un dominio válido."

    # Cache local para dominios muy comunes — evita lookup innecesario
    if dominio in DOMINIOS_CONOCIDOS:
        return True, ""

    # MX lookup real
    try:
        import dns.resolver

        registros = dns.resolver.resolve(dominio, "MX", lifetime=5)
        if registros:
            logger.debug("[email_validator] MX OK para %s", dominio)
            return True, ""
        return False, f"El dominio '{dominio}' no tiene servidores de correo."

    except Exception as exc:
        # Importar los tipos específicos de excepción dentro del bloque
        # para no fallar si dns no está instalado
        exc_name = type(exc).__name__

        if "NXDOMAIN" in exc_name:
            return False, f"El dominio '{dominio}' no existe."
        if "NoAnswer" in exc_name or "NoNameservers" in exc_name:
            return False, f"El dominio '{dominio}' no tiene servidores de correo configurados."
        if "Timeout" in exc_name or "LifetimeTimeout" in exc_name:
            # Timeout — asumir válido para no bloquear el registro
            logger.warning(
                "[email_validator] Timeout verificando MX de %s — asumiendo válido", dominio)
            return True, ""

        # Error inesperado — log y asumir válido para no bloquear
        logger.error(
            "[email_validator] Error verificando MX de %s: %s", dominio, exc)
        return True, ""


def validar_email_completo(email: str) -> tuple[bool, str]:
    """
    Validación completa: formato + MX lookup.
    Punto de entrada principal — usar este en los serializers.
    """
    if not email:
        return False, "El correo es obligatorio."

    if not validar_formato(email):
        return False, "El formato del correo no es válido (ejemplo: usuario@dominio.com)."

    return validar_dominio_mx(email)

# auth_service/app/auth/email_service.py
import logging
import datetime
from django.conf import settings

logger = logging.getLogger(__name__)


def _resend():
    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY
        return resend
    except ImportError:
        logger.error(
            "[email] librería 'resend' no instalada: pip install resend")
        return None


def _from_email():
    # Resend requiere formato "Nombre <email>" — sin nombre falla silenciosamente
    return f"RestoHub <{getattr(settings, 'RESEND_FROM_EMAIL', 'onboarding@resend.dev')}>"


def _reply_to():
    return getattr(settings, "RESEND_REPLY_TO", "") or None


# ── Templates ──────────────────────────────────────────────────────────────

def _html_codigo(nombre: str, codigo: str) -> str:
    year = datetime.date.today().year
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f5ec;font-family:Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
  <tr><td align="center">
    <table width="520" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">
      <tr>
        <td style="background:#0a3828;padding:32px 40px;text-align:center;">
          <p style="margin:0 0 4px;font-size:11px;color:rgba(255,250,202,.6);letter-spacing:.12em;text-transform:uppercase;">RestoHub</p>
          <h1 style="margin:0;font-family:Georgia,serif;font-size:26px;font-weight:700;color:#fff;">Verifica tu correo</h1>
        </td>
      </tr>
      <tr>
        <td style="padding:40px 40px 32px;">
          <p style="margin:0 0 20px;font-size:15px;color:#52524a;line-height:1.6;">
            Hola <strong style="color:#141410;">{nombre}</strong>,<br>
            usa este código para activar tu cuenta. Expira en <strong>10 minutos</strong>.
          </p>
          <div style="background:#f5f5ec;border:2px dashed rgba(10,56,40,.2);border-radius:14px;padding:28px;text-align:center;margin:0 0 24px;">
            <p style="margin:0 0 6px;font-size:11px;color:#909088;letter-spacing:.1em;text-transform:uppercase;">Código de verificación</p>
            <p style="margin:0;font-family:monospace;font-size:42px;font-weight:800;color:#0a3828;letter-spacing:.18em;line-height:1;">{codigo}</p>
          </div>
          <p style="margin:0;font-size:13px;color:#909088;line-height:1.55;">
            Si no creaste esta cuenta ignora este correo.<br>
            Nunca compartas este código con nadie.
          </p>
        </td>
      </tr>
      <tr>
        <td style="background:#f5f5ec;padding:20px 40px;border-top:1px solid rgba(0,0,0,.06);">
          <p style="margin:0;font-size:12px;color:#aaa;text-align:center;">© {year} RestoHub · Correo automático, no respondas.</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body></html>"""


def _html_bienvenida(nombre: str) -> str:
    year = datetime.date.today().year
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f5ec;font-family:Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
  <tr><td align="center">
    <table width="520" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">
      <tr>
        <td style="background:#0a3828;padding:32px 40px;text-align:center;">
          <h1 style="margin:0;font-family:Georgia,serif;font-size:26px;font-weight:700;color:#fffaca;">¡Bienvenido a RestoHub!</h1>
        </td>
      </tr>
      <tr>
        <td style="padding:40px;">
          <p style="margin:0 0 16px;font-size:15px;color:#52524a;line-height:1.6;">
            Hola <strong style="color:#141410;">{nombre}</strong>, tu cuenta está activa y lista.
          </p>
          <p style="margin:0 0 28px;font-size:14px;color:#52524a;line-height:1.6;">
            Ya puedes explorar restaurantes, hacer pedidos y acumular puntos.
          </p>
          <div style="text-align:center;">
            <a href="http://localhost:5175"
               style="display:inline-block;padding:14px 32px;background:#0a3828;color:#fffaca;
                      text-decoration:none;border-radius:10px;font-weight:700;font-size:13px;
                      letter-spacing:.06em;text-transform:uppercase;">
              Ir a RestoHub
            </a>
          </div>
        </td>
      </tr>
      <tr>
        <td style="background:#f5f5ec;padding:20px 40px;border-top:1px solid rgba(0,0,0,.06);">
          <p style="margin:0;font-size:12px;color:#aaa;text-align:center;">© {year} RestoHub</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body></html>"""


# ── Funciones públicas ─────────────────────────────────────────────────────

def enviar_codigo_verificacion(usuario, codigo: str) -> bool:
    """Envía el código OTP. Retorna True si el envío fue exitoso."""
    api_key = getattr(settings, "RESEND_API_KEY", "")
    if not api_key:
        logger.warning("[email] RESEND_API_KEY no configurada.")
        logger.info(
            f"[email] (fallback) Código para {usuario.email}: {codigo}")
        return False

    r = _resend()
    if not r:
        logger.info(
            f"[email] (fallback) Código para {usuario.email}: {codigo}")
        return False

    nombre = (usuario.nombre or usuario.email.split("@")[0]).split()[0]
    params = {
        "from":    _from_email(),
        "to":      [usuario.email],
        "subject": f"{codigo} — tu código RestoHub",
        "html":    _html_codigo(nombre, codigo),
    }
    reply = _reply_to()
    if reply:
        params["reply_to"] = reply

    try:
        resp = r.Emails.send(params)
        # v2 retorna dict con 'id' en éxito
        email_id = resp.get("id") if isinstance(
            resp, dict) else getattr(resp, "id", None)
        if email_id:
            logger.info(
                f"[email] ✓ Código enviado a {usuario.email} (id={email_id})")
            return True
        logger.error(f"[email] Resend sin id en respuesta: {resp}")
        return False
    except Exception as exc:
        logger.error(f"[email] Error enviando a {usuario.email}: {exc}")
        logger.info(
            f"[email] (fallback) Código para {usuario.email}: {codigo}")
        return False


def enviar_bienvenida(usuario) -> bool:
    """Envía bienvenida tras verificar email. Fallo silencioso."""
    api_key = getattr(settings, "RESEND_API_KEY", "")
    if not api_key:
        return False

    r = _resend()
    if not r:
        return False

    nombre = (usuario.nombre or usuario.email.split("@")[0]).split()[0]
    params = {
        "from":    _from_email(),
        "to":      [usuario.email],
        "subject": f"¡Bienvenido a RestoHub, {nombre}!",
        "html":    _html_bienvenida(nombre),
    }
    reply = _reply_to()
    if reply:
        params["reply_to"] = reply

    try:
        resp = r.Emails.send(params)
        email_id = resp.get("id") if isinstance(
            resp, dict) else getattr(resp, "id", None)
        if email_id:
            logger.info(
                f"[email] ✓ Bienvenida enviada a {usuario.email} (id={email_id})")
            return True
        return False
    except Exception as exc:
        logger.error(f"[email] Error bienvenida a {usuario.email}: {exc}")
        return False

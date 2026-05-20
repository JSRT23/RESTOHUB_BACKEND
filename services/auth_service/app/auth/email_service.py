# auth_service/app/auth/email_service.py
# CAMBIO: reemplaza Resend por Gmail SMTP
# El remitente es jramostorralvo@gmail.com — llega a CUALQUIER correo de usuario

import logging
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.conf import settings

logger = logging.getLogger(__name__)


# ── Configuración SMTP ─────────────────────────────────────────────────────

def _smtp_config():
    return {
        "host":     getattr(settings, "EMAIL_HOST",     "smtp.gmail.com"),
        "port":     getattr(settings, "EMAIL_PORT",     587),
        "user":     getattr(settings, "EMAIL_HOST_USER",     ""),
        "password": getattr(settings, "EMAIL_HOST_PASSWORD", ""),
        "from":     getattr(settings, "EMAIL_FROM",     "RestoHub <jramostorralvo@gmail.com>"),
    }


def _send(to_email: str, subject: str, html: str) -> bool:
    """Envía un email HTML via Gmail SMTP. Retorna True si tuvo éxito."""
    cfg = _smtp_config()

    if not cfg["user"] or not cfg["password"]:
        logger.warning(
            "[email] EMAIL_HOST_USER o EMAIL_HOST_PASSWORD no configurados.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from"]
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], [to_email], msg.as_string())
        logger.info(f"[email] ✓ Email enviado a {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "[email] Error de autenticación Gmail — verifica EMAIL_HOST_PASSWORD (App Password).")
        return False
    except Exception as exc:
        logger.error(f"[email] Error enviando a {to_email}: {exc}")
        return False


# ── Templates HTML ─────────────────────────────────────────────────────────

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
            <a href="https://restohub-nine.vercel.app"
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
    """Envía el código OTP al correo del usuario. Retorna True si tuvo éxito."""
    nombre = (usuario.nombre or usuario.email.split("@")[0]).split()[0]

    enviado = _send(
        to_email=usuario.email,
        subject=f"{codigo} — tu código RestoHub",
        html=_html_codigo(nombre, codigo),
    )

    if not enviado:
        # Fallback en logs para desarrollo
        logger.info(
            f"[email] (fallback) Código para {usuario.email}: {codigo}")

    return enviado


def enviar_bienvenida(usuario) -> bool:
    """Envía email de bienvenida tras verificar. Fallo silencioso."""
    nombre = (usuario.nombre or usuario.email.split("@")[0]).split()[0]

    return _send(
        to_email=usuario.email,
        subject=f"¡Bienvenido a RestoHub, {nombre}!",
        html=_html_bienvenida(nombre),
    )

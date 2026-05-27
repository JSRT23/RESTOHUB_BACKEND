# auth_service/app/auth/email_service.py
#
# Backends:
#   brevo  → Brevo API HTTP (producción — HTTP nunca bloqueado en Render)
#   gmail  → Gmail SMTP (desarrollo local)
#
# Brevo API no usa SMTP — usa HTTPS hacia api.brevo.com:443
# Render nunca bloquea HTTPS saliente.
#
# SETUP — vars en Render:
#   EMAIL_BACKEND=brevo
#   BREVO_API_KEY=xkeysib-xxxxxxxxxxxxxxxx   ← Brevo → SMTP y API → API Keys → crear
#   BREVO_SENDER_EMAIL=claudecodepro10@gmail.com
#   BREVO_SENDER_NAME=RestoHub

import logging
import datetime
import json
import urllib.request
import urllib.error
from django.conf import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

def _send(to_email: str, subject: str, html: str) -> bool:
    backend = getattr(settings, "EMAIL_BACKEND_CUSTOM",
                      "gmail").lower().strip()
    if backend == "brevo":
        return _send_brevo_api(to_email, subject, html)
    return _send_gmail(to_email, subject, html)


# ─────────────────────────────────────────────────────────────────────────────
# BACKEND BREVO API — producción
# Usa urllib (stdlib) — sin dependencias extra, solo HTTPS
# ─────────────────────────────────────────────────────────────────────────────

def _send_brevo_api(to_email: str, subject: str, html: str) -> bool:
    api_key = getattr(settings, "BREVO_API_KEY",      "")
    sender_email = getattr(settings, "BREVO_SENDER_EMAIL", "")
    sender_name = getattr(settings, "BREVO_SENDER_NAME",  "RestoHub")

    if not api_key:
        logger.error("[email/brevo] BREVO_API_KEY no configurado en Render.")
        return False
    if not sender_email:
        logger.error(
            "[email/brevo] BREVO_SENDER_EMAIL no configurado en Render.")
        return False

    payload = json.dumps({
        "sender":     {"name": sender_name, "email": sender_email},
        "to":         [{"email": to_email}],
        "subject":    subject,
        "htmlContent": html,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={
            "accept":       "application/json",
            "content-type": "application/json",
            "api-key":      api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
            msg_id = body.get("messageId", "")
            logger.info(
                f"[email/brevo] ✓ Enviado a {to_email} — messageId: {msg_id}")
            return True
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error(
            f"[email/brevo] HTTP {exc.code} enviando a {to_email}: {body}")
        return False
    except Exception as exc:
        logger.error(f"[email/brevo] Error enviando a {to_email}: {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# BACKEND GMAIL SMTP — desarrollo local
# ─────────────────────────────────────────────────────────────────────────────

def _send_gmail(to_email: str, subject: str, html: str) -> bool:
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    host = getattr(settings, "EMAIL_HOST",          "smtp.gmail.com")
    port = getattr(settings, "EMAIL_PORT",          587)
    user = getattr(settings, "EMAIL_HOST_USER",     "")
    password = getattr(settings, "EMAIL_HOST_PASSWORD", "")
    from_addr = getattr(settings, "EMAIL_FROM",          f"RestoHub <{user}>")

    if not user or not password:
        logger.warning(
            "[email/gmail] EMAIL_HOST_USER o EMAIL_HOST_PASSWORD vacíos.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(user, password)
            server.sendmail(user, [to_email], msg.as_string())
        logger.info(f"[email/gmail] ✓ Enviado a {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "[email/gmail] Error de autenticación — verifica el App Password.")
        return False
    except Exception as exc:
        logger.error(f"[email/gmail] Error enviando a {to_email}: {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATES HTML
# ─────────────────────────────────────────────────────────────────────────────

def _html_codigo(nombre: str, codigo: str) -> str:
    year = datetime.date.today().year
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f5f5ec;font-family:Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
  <tr><td align="center">
    <table width="520" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:20px;overflow:hidden;
                  box-shadow:0 4px 24px rgba(0,0,0,.08);">
      <tr>
        <td style="background:#0a3828;padding:32px 40px;text-align:center;">
          <p style="margin:0 0 4px;font-size:11px;color:rgba(255,250,202,.6);
                    letter-spacing:.12em;text-transform:uppercase;">RestoHub</p>
          <h1 style="margin:0;font-family:Georgia,serif;font-size:26px;
                     font-weight:700;color:#fff;">Verifica tu correo</h1>
        </td>
      </tr>
      <tr>
        <td style="padding:40px 40px 32px;">
          <p style="margin:0 0 20px;font-size:15px;color:#52524a;line-height:1.6;">
            Hola <strong style="color:#141410;">{nombre}</strong>,<br>
            usa este código para activar tu cuenta.
            Expira en <strong>10 minutos</strong>.
          </p>
          <div style="background:#f5f5ec;border:2px dashed rgba(10,56,40,.2);
                      border-radius:14px;padding:28px;text-align:center;margin:0 0 24px;">
            <p style="margin:0 0 6px;font-size:11px;color:#909088;
                      letter-spacing:.1em;text-transform:uppercase;">
              Código de verificación
            </p>
            <p style="margin:0;font-family:monospace;font-size:42px;font-weight:800;
                      color:#0a3828;letter-spacing:.18em;line-height:1;">{codigo}</p>
          </div>
          <p style="margin:0;font-size:13px;color:#909088;line-height:1.55;">
            Si no creaste esta cuenta ignora este correo.<br>
            Nunca compartas este código con nadie.
          </p>
        </td>
      </tr>
      <tr>
        <td style="background:#f5f5ec;padding:20px 40px;
                   border-top:1px solid rgba(0,0,0,.06);">
          <p style="margin:0;font-size:12px;color:#aaa;text-align:center;">
            © {year} RestoHub · Correo automático, no respondas.
          </p>
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
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f5f5ec;font-family:Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
  <tr><td align="center">
    <table width="520" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:20px;overflow:hidden;
                  box-shadow:0 4px 24px rgba(0,0,0,.08);">
      <tr>
        <td style="background:#0a3828;padding:32px 40px;text-align:center;">
          <h1 style="margin:0;font-family:Georgia,serif;font-size:26px;
                     font-weight:700;color:#fffaca;">
            ¡Bienvenido a RestoHub!
          </h1>
        </td>
      </tr>
      <tr>
        <td style="padding:40px;">
          <p style="margin:0 0 16px;font-size:15px;color:#52524a;line-height:1.6;">
            Hola <strong style="color:#141410;">{nombre}</strong>,
            tu cuenta está activa y lista.
          </p>
          <p style="margin:0 0 28px;font-size:14px;color:#52524a;line-height:1.6;">
            Ya puedes explorar restaurantes, hacer pedidos y acumular puntos.
          </p>
          <div style="text-align:center;">
            <a href="https://restohub-nine.vercel.app"
               style="display:inline-block;padding:14px 32px;background:#0a3828;
                      color:#fffaca;text-decoration:none;border-radius:10px;
                      font-weight:700;font-size:13px;letter-spacing:.06em;
                      text-transform:uppercase;">
              Ir a RestoHub
            </a>
          </div>
        </td>
      </tr>
      <tr>
        <td style="background:#f5f5ec;padding:20px 40px;
                   border-top:1px solid rgba(0,0,0,.06);">
          <p style="margin:0;font-size:12px;color:#aaa;text-align:center;">
            © {year} RestoHub
          </p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES PÚBLICAS
# ─────────────────────────────────────────────────────────────────────────────

def enviar_codigo_verificacion(usuario, codigo: str) -> bool:
    nombre = (usuario.nombre or usuario.email.split("@")[0]).split()[0]
    enviado = _send(
        to_email=usuario.email,
        subject=f"{codigo} — tu código RestoHub",
        html=_html_codigo(nombre, codigo),
    )
    if not enviado:
        logger.info(
            f"[email] (fallback log) Código para {usuario.email}: {codigo}")
    return enviado


def enviar_bienvenida(usuario) -> bool:
    nombre = (usuario.nombre or usuario.email.split("@")[0]).split()[0]
    return _send(
        to_email=usuario.email,
        subject=f"¡Bienvenido a RestoHub, {nombre}!",
        html=_html_bienvenida(nombre),
    )

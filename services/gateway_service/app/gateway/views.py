# gateway_service/app/gateway/views.py

import datetime
import json
import logging
import urllib.request
import urllib.error
import mercadopago
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL — Brevo API HTTP en prod, Gmail en dev
# ─────────────────────────────────────────────────────────────────────────────

def _send_email(to_email: str, subject: str, html: str) -> bool:
    backend = getattr(settings, "EMAIL_BACKEND_CUSTOM",
                      "gmail").lower().strip()
    if backend == "brevo":
        return _send_brevo_api(to_email, subject, html)
    return _send_gmail(to_email, subject, html)


def _send_brevo_api(to_email: str, subject: str, html: str) -> bool:
    api_key = getattr(settings, "BREVO_API_KEY",      "")
    sender_email = getattr(settings, "BREVO_SENDER_EMAIL", "")
    sender_name = getattr(settings, "BREVO_SENDER_NAME",  "RestoHub")

    if not api_key or not sender_email:
        logger.error(
            "[pagos/brevo] BREVO_API_KEY o BREVO_SENDER_EMAIL no configurados.")
        return False

    payload = json.dumps({
        "sender":      {"name": sender_name, "email": sender_email},
        "to":          [{"email": to_email}],
        "subject":     subject,
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
            logger.info(
                f"[pagos/brevo] ✓ Enviado a {to_email} — id: {body.get('messageId', '')}")
            return True
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        logger.error(f"[pagos/brevo] HTTP {exc.code}: {err}")
        return False
    except Exception as exc:
        logger.error(f"[pagos/brevo] Error: {exc}")
        return False


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
        logger.warning("[pagos/gmail] Credenciales vacías.")
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
        logger.info(f"[pagos/gmail] ✓ Enviado a {to_email}")
        return True
    except Exception as exc:
        logger.error(f"[pagos/gmail] Error: {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE EMAIL CONFIRMACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def _html_confirmacion(nombre: str, items: list, total: float,
                       moneda: str, payment_id: str) -> str:
    year = datetime.date.today().year
    fecha = datetime.date.today().strftime("%d de %B de %Y")

    def fmt(n):
        return f"${int(n):,}".replace(",", ".")

    rows = ""
    for item in items:
        sub = item.get("precio", 0) * item.get("cantidad", 1)
        rows += f"""<tr>
          <td style="padding:10px 0;border-bottom:1px solid #f0f0e8;">
            <strong style="color:#141410;font-size:14px;">{item.get('nombre', '')}</strong><br>
            <span style="color:#909088;font-size:12px;">{item.get('cantidad', 1)} unidad(es)</span>
          </td>
          <td style="padding:10px 0;border-bottom:1px solid #f0f0e8;text-align:right;
                     font-family:Georgia,serif;font-weight:700;color:#0a3828;">
            {fmt(sub)} {moneda}
          </td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f5ec;font-family:Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
  <tr><td align="center">
    <table width="520" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">
      <tr><td style="background:#0a3828;padding:32px 40px;text-align:center;">
        <p style="margin:0 0 4px;font-size:10px;color:rgba(255,250,202,.6);letter-spacing:.14em;text-transform:uppercase;">RestoHub</p>
        <h1 style="margin:0;font-family:Georgia,serif;font-size:24px;font-weight:700;color:#fffaca;">¡Compra confirmada!</h1>
        <p style="margin:8px 0 0;font-size:12px;color:rgba(255,255,255,.45);">{fecha}</p>
      </td></tr>
      <tr><td style="padding:28px 40px 8px;">
        <p style="margin:0;font-size:15px;color:#52524a;line-height:1.6;">
          Hola <strong style="color:#141410;">{nombre}</strong>,<br>
          tu pedido fue procesado exitosamente. Aquí tienes el resumen:
        </p>
      </td></tr>
      <tr><td style="padding:8px 40px 20px;">
        <div style="background:#f5f5ec;border-radius:10px;padding:12px 16px;">
          <span style="font-size:11px;color:#909088;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">Referencia: </span>
          <span style="font-family:monospace;font-size:13px;font-weight:700;color:#0a3828;">#{payment_id}</span>
        </div>
      </td></tr>
      <tr><td style="padding:0 40px 20px;">
        <p style="margin:0 0 12px;font-size:10px;font-weight:700;color:#909088;letter-spacing:.1em;text-transform:uppercase;">Artículos</p>
        <table width="100%" cellpadding="0" cellspacing="0">
          {rows}
          <tr>
            <td style="padding:16px 0 0;font-family:Georgia,serif;font-size:16px;font-weight:700;color:#141410;">Total</td>
            <td style="padding:16px 0 0;text-align:right;font-family:Georgia,serif;font-size:22px;font-weight:900;color:#0a3828;">{fmt(total)} {moneda}</td>
          </tr>
        </table>
      </td></tr>
      <tr><td style="padding:0 40px 32px;text-align:center;">
        <a href="https://restohub-nine.vercel.app"
           style="display:inline-block;padding:13px 28px;background:#0a3828;color:#fffaca;
                  text-decoration:none;border-radius:10px;font-weight:700;font-size:12px;
                  letter-spacing:.06em;text-transform:uppercase;">Ir a RestoHub</a>
      </td></tr>
      <tr><td style="background:#f5f5ec;padding:18px 40px;border-top:1px solid rgba(0,0,0,.06);">
        <p style="margin:0;font-size:11px;color:#aaa;text-align:center;">© {year} RestoHub · Correo automático, no respondas.</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: Crear Preferencia MP
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class CrearPreferenciaView(View):
    """POST /api/pagos/crear-preferencia/"""

    def post(self, request):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Body JSON inválido."}, status=400)

        items = body.get("items", [])
        total = body.get("total", 0)
        moneda = body.get("moneda", "COP")
        payer_email = body.get("payer_email", "")
        pedido_id = body.get("pedido_id")

        if not items:
            return JsonResponse({"error": "items requeridos."}, status=400)

        access_token = getattr(settings, "MP_ACCESS_TOKEN", "")
        frontend_url = getattr(settings, "FRONTEND_URL",
                               "https://restohub-nine.vercel.app")

        if not access_token:
            logger.error("[pagos] MP_ACCESS_TOKEN no configurado.")
            return JsonResponse({"error": "MP_ACCESS_TOKEN no configurado."}, status=500)

        sdk = mercadopago.SDK(access_token)

        # Validar y limpiar items — MP rechaza si unit_price <= 0
        mp_items = []
        for item in items:
            price = float(item.get("unit_price", 0))
            qty = int(item.get("quantity", 1))
            if price <= 0 or qty <= 0:
                logger.warning(f"[pagos] Item inválido ignorado: {item}")
                continue
            mp_items.append({
                "title":       str(item.get("title", "Producto"))[:255],
                "quantity":    qty,
                "unit_price":  price,
                "currency_id": str(item.get("currency_id", moneda)),
            })

        if not mp_items:
            return JsonResponse({"error": "Ningún item válido (precio o cantidad = 0)."}, status=400)

        preference_data = {
            "items": mp_items,
            "back_urls": {
                "success": f"{frontend_url}/pago-exitoso",
                "failure": f"{frontend_url}/pago-fallido",
                "pending": f"{frontend_url}/pago-exitoso",
            },
            "auto_return":          "approved",
            "statement_descriptor": "RestoHub",
            "external_reference":   str(pedido_id) if pedido_id else "sin-pedido",
        }

        if payer_email:
            preference_data["payer"] = {"email": payer_email}

        logger.info(
            f"[pagos] Creando preferencia — pedido={pedido_id}, items={len(mp_items)}, total={total} {moneda}")

        result = sdk.preference().create(preference_data)

        # Log detallado para diagnosticar errores de MP
        status = result.get("status")
        response = result.get("response", {})
        logger.info(
            f"[pagos] MP status={status} | response={json.dumps(response)[:600]}")

        if status not in (200, 201):
            logger.error(f"[pagos] Error MP: status={status}")
            return JsonResponse(
                {"error": "Error al crear preferencia.", "detail": response},
                status=502,
            )

        logger.info(f"[pagos] ✓ Preferencia creada: {response.get('id')}")

        return JsonResponse({
            "ok":            True,
            "preference_id": response.get("id"),
            "init_point":    response.get("init_point"),
        })


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: Email Confirmación post-pago
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class EmailConfirmacionView(View):
    """POST /api/pagos/email-confirmacion/"""

    def post(self, request):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Body JSON inválido."}, status=400)

        email = body.get("email", "")
        nombre = body.get("nombre", "Cliente")
        items = body.get("items", [])
        total = body.get("total", 0)
        moneda = body.get("moneda", "COP")
        payment_id = body.get("payment_id", "N/A")

        if not email:
            return JsonResponse({"ok": False, "error": "email requerido."}, status=400)

        nombre_corto = (nombre or email.split("@")[0]).split()[0]
        html = _html_confirmacion(
            nombre_corto, items, total, moneda, payment_id or "N/A")

        enviado = _send_email(
            to_email=email,
            subject=f"✅ Compra confirmada — RestoHub #{payment_id}",
            html=html,
        )

        if not enviado:
            logger.warning(
                f"[email_confirmacion] No enviado a {email} — el pago ya fue procesado")

        return JsonResponse({"ok": enviado})

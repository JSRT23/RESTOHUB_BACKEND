import logging

import resend
from django.conf import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY
FROM_EMAIL = settings.RESEND_FROM_EMAIL
APP_NAME = "RestoHub"


def enviar_codigo_verificacion(usuario, codigo: str) -> bool:
    """
    Envía el código de 6 dígitos al email del usuario.
    Retorna True si se envió correctamente.
    """
    html = f"""
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
    <tr>
      <td align="center">
        <table width="480" cellpadding="0" cellspacing="0"
               style="background:#fff;border-radius:12px;overflow:hidden;
                      box-shadow:0 2px 8px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background:#111827;padding:28px 40px;text-align:center;">
              <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;letter-spacing:-0.5px;">
                {APP_NAME}
              </h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 40px 28px;">
              <p style="margin:0 0 8px;color:#374151;font-size:16px;font-weight:600;">
                Hola, {usuario.nombre}
              </p>
              <p style="margin:0 0 28px;color:#6b7280;font-size:14px;line-height:1.6;">
                Usa el siguiente código para verificar tu correo electrónico.
                Es válido por <strong style="color:#374151;">10 minutos</strong>.
              </p>

              <!-- Código -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:0 0 28px;">
                    <div style="display:inline-block;background:#f9fafb;
                                border:2px solid #e5e7eb;border-radius:12px;
                                padding:20px 48px;">
                      <span style="font-size:40px;font-weight:700;letter-spacing:12px;
                                   color:#111827;font-family:'Courier New',monospace;">
                        {codigo}
                      </span>
                    </div>
                  </td>
                </tr>
              </table>

              <hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 20px;">

              <p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.5;">
                Si no solicitaste este código, ignora este correo.
                Tienes máximo <strong>3 intentos</strong> antes de que el código se invalide.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f9fafb;border-top:1px solid #e5e7eb;
                       padding:16px 40px;text-align:center;">
              <p style="margin:0;color:#9ca3af;font-size:11px;">
                Mensaje automático de {APP_NAME} — no respondas este correo.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [usuario.email],
            "subject": f"{APP_NAME} — Tu código de verificación: {codigo}",
            "html":    html,
            "text":    (
                f"Hola {usuario.nombre},\n\n"
                f"Tu código de verificación es: {codigo}\n\n"
                f"Es válido por 10 minutos y tienes 3 intentos.\n\n"
                f"Si no solicitaste esto, ignora este correo.\n\n"
                f"— {APP_NAME}"
            ),
        })
        logger.info(
            "[email] Código de verificación enviado a %s", usuario.email)
        return True
    except Exception as exc:
        logger.error("[email] Error enviando código a %s: %s",
                     usuario.email, exc)
        return False


def enviar_bienvenida(usuario) -> bool:
    """Email de bienvenida tras verificar el correo exitosamente."""
    html = f"""
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
    <tr>
      <td align="center">
        <table width="480" cellpadding="0" cellspacing="0"
               style="background:#fff;border-radius:12px;overflow:hidden;
                      box-shadow:0 2px 8px rgba(0,0,0,0.08);">
          <tr>
            <td style="background:#111827;padding:28px 40px;text-align:center;">
              <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;">{APP_NAME}</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:36px 40px 28px;">
              <p style="margin:0 0 12px;color:#374151;font-size:16px;font-weight:600;">
                ¡Bienvenido, {usuario.nombre}!
              </p>
              <p style="margin:0;color:#6b7280;font-size:14px;line-height:1.6;">
                Tu correo ha sido verificado correctamente.
                Ya puedes iniciar sesión en {APP_NAME}.
              </p>
            </td>
          </tr>
          <tr>
            <td style="background:#f9fafb;border-top:1px solid #e5e7eb;
                       padding:16px 40px;text-align:center;">
              <p style="margin:0;color:#9ca3af;font-size:11px;">
                Mensaje automático de {APP_NAME}.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [usuario.email],
            "subject": f"¡Bienvenido a {APP_NAME}!",
            "html":    html,
            "text":    f"¡Bienvenido {usuario.nombre}! Tu cuenta en {APP_NAME} está activa.",
        })
        return True
    except Exception as exc:
        logger.error("[email] Error enviando bienvenida a %s: %s",
                     usuario.email, exc)
        return False

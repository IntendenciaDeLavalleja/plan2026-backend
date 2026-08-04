"""Mail helpers (uses Flask-Mail with synchronous fallback)."""

from __future__ import annotations

import os
from threading import Thread

from flask import current_app
from flask_mail import Message

from app.extensions import mail


def _send_async(app, msg: Message) -> None:
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as exc:  # pragma: no cover
            app.logger.warning("[email] failed to send: %s", exc)


def send_email(subject: str, recipients: list[str], html_body: str, text_body: str | None = None) -> None:
    msg = Message(subject, recipients=recipients)
    msg.body = text_body or ""
    msg.html = html_body
    try:
        if current_app.config.get("MAIL_SUPPRESS_SEND") or os.environ.get("MAIL_SUPPRESS_SEND") == "1":
            current_app.logger.info("[email suppressed] subject=%s to=%s body=%s", subject, recipients, text_body)
            return
        Thread(target=_send_async, args=(current_app._get_current_object(), msg), daemon=True).start()
    except Exception as exc:  # pragma: no cover
        current_app.logger.warning("[email] dispatch failed: %s", exc)


def _simple_html(title: str, body_html: str) -> str:
    return f"""
    <html>
      <body style=\"font-family: 'Segoe UI', Roboto, Arial, sans-serif; background:#f4f6fa; padding:24px; color:#0f172a;\">
        <div style=\"max-width:620px;margin:0 auto;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 16px 40px rgba(15,23,42,0.08);\">
          <div style=\"background:linear-gradient(135deg,#081122 0%,#1f3a8a 42%,#4338ca 100%);color:#fff;padding:28px 32px;\">
            <div style=\"display:inline-block;padding:6px 12px;border-radius:999px;background:rgba(255,255,255,0.14);font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;\">Intendencia de Lavalleja</div>
            <h1 style=\"margin:16px 0 6px;font-size:24px;line-height:1.2;font-weight:700;\">Amnist&iacute;a Financiera</h1>
            <p style=\"margin:0;font-size:14px;opacity:0.86;\">Sistema oficial de gesti&oacute;n y atenci&oacute;n</p>
          </div>
          <div style=\"padding:30px 32px;\">
            <div style=\"display:inline-block;margin:0 0 16px;padding:6px 10px;border-radius:999px;background:#eff6ff;color:#1e3a8a;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;\">{title}</div>
            {body_html}
          </div>
          <div style=\"background:#f8fafc;padding:18px 32px;font-size:12px;color:#475569;border-top:1px solid #e2e8f0;\">
            Este mensaje es generado autom&aacute;ticamente. Por favor no responder a este correo.
          </div>
        </div>
      </body>
    </html>
    """


def send_2fa_email(to_email: str, code: str) -> None:
    body = f"""
      <p style=\"margin:0 0 14px;font-size:16px;line-height:1.6;color:#0f172a;\">Su c&oacute;digo de verificaci&oacute;n para acceder al panel administrativo es:</p>
      <p style=\"text-align:center;margin:24px 0;\">
        <span style=\"display:inline-block;font-family:Consolas,monospace;font-size:30px;letter-spacing:10px;background:linear-gradient(135deg,#081122 0%,#1f3a8a 52%,#4338ca 100%);color:#fff;padding:16px 30px;border-radius:14px;box-shadow:0 10px 24px rgba(31,58,138,0.22);\">{code}</span>
      </p>
      <div style=\"padding:14px 16px;border-radius:14px;background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a8a;font-size:14px;line-height:1.6;\">
        El c&oacute;digo expira en 10 minutos. Si no realiz&oacute; esta solicitud puede ignorar este mensaje.
      </div>
    """
    send_email(
        subject="[Amnistía Financiera] Código de verificación",
        recipients=[to_email],
        text_body=f"Su código de verificación es {code}. Expira en 10 minutos.",
        html_body=_simple_html("Verificación de identidad", body),
    )


def send_reservation_confirmed_email(appointment) -> None:
    slot = appointment.slot
    tribute = appointment.tribute_type
    body = f"""
      <p style=\"margin:0 0 10px;font-size:16px;line-height:1.6;color:#0f172a;\">Hola <strong>{appointment.citizen_name}</strong>,</p>
      <p style=\"margin:0 0 18px;font-size:16px;line-height:1.6;color:#0f172a;\">Su turno para <strong>{tribute.name if tribute else 'el trámite seleccionado'}</strong> fue registrado correctamente.</p>
      <div style=\"margin:18px 0 20px;padding:18px;border-radius:16px;background:linear-gradient(180deg,#f8fafc 0%,#eff6ff 100%);border:1px solid #dbeafe;\">
        <table style=\"width:100%;border-collapse:collapse;\">
          <tr><td style=\"padding:8px 0;color:#64748b;width:90px;\">C&oacute;digo</td><td style=\"padding:8px 0;font-weight:700;color:#0f172a;\">{appointment.reservation_code}</td></tr>
          <tr><td style=\"padding:8px 0;color:#64748b;\">Fecha</td><td style=\"padding:8px 0;font-weight:600;color:#0f172a;\">{slot.date.strftime('%d/%m/%Y') if slot and slot.date else ''}</td></tr>
          <tr><td style=\"padding:8px 0;color:#64748b;\">Hora</td><td style=\"padding:8px 0;font-weight:600;color:#0f172a;\">{slot.start_time.strftime('%H:%M') if slot and slot.start_time else ''}</td></tr>
          <tr><td style=\"padding:8px 0;color:#64748b;\">Sede</td><td style=\"padding:8px 0;font-weight:600;color:#0f172a;\">{appointment.location.name if appointment.location else ''}</td></tr>
        </table>
      </div>
      <div style=\"padding:14px 16px;border-radius:14px;background:#f0fdf4;border:1px solid #bbf7d0;color:#14532d;font-size:14px;line-height:1.6;\">Conserve este c&oacute;digo para consultar o cancelar su turno. Lo esperamos en la fecha y hora indicadas.</div>
    """
    send_email(
        subject=f"[Amnistía Financiera] Reserva {appointment.reservation_code}",
        recipients=[appointment.email] if appointment.email else [],
        text_body=(
            f"Su turno {appointment.reservation_code} para {tribute.name if tribute else ''} "
            f"quedó registrado para el {slot.date.strftime('%d/%m/%Y') if slot else ''} a las "
            f"{slot.start_time.strftime('%H:%M') if slot else ''}."
        ),
        html_body=_simple_html("Reserva registrada", body),
    )

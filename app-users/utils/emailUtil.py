import base64
import httpx
import logging
import os
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)


def _build_html(title: str, message: str) -> str:
    return f"""
    <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; color: #1a202c; padding: 20px; margin: 0;">
            <div style="max-width: 600px; margin: 40px auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
                <h2 style="color: #2d3748; text-align: center; margin: 0 0 20px 0; font-size: 24px;">{title}</h2>
                <div style="margin: 20px 0;">{message}</div>
                <p style="font-size: 12px; color: #718096; text-align: left; margin: 20px 0;">
                    Si no solicitaste este cambio, ignora este correo.<br>
                    Este es un mensaje automático, por favor no responder a este correo.
                </p>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 25px 0;">
                <p style="font-size: 12px; color: #718096; text-align: center; margin: 0;">
                    © 2025 Corpochivor. Todos los derechos reservados.
                </p>
            </div>
        </body>
    </html>
    """


async def _get_access_token() -> str:
    """Obtiene un access token fresco usando el refresh token de OAuth2."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
                "grant_type": "refresh_token",
            },
        )
    if resp.status_code != 200:
        raise RuntimeError(f"OAuth2 token error {resp.status_code}: {resp.text}")
    return resp.json()["access_token"]


async def _send_via_gmail_api(to_email: str, subject: str, html_content: str) -> None:
    """Envía un email usando la Gmail API (HTTPS puerto 443, sin SMTP)."""
    from_email = os.getenv("SMTP_FROM")
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.add_alternative(html_content, subtype="html")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    access_token = await _get_access_token()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            json={"raw": raw},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Gmail API error {resp.status_code}: {resp.text}")


async def sendEmail(title: str, message: str, email: str, subject: str) -> None:
    await _send_via_gmail_api(email, subject, _build_html(title, message))


async def send_single_email(title: str, message: str, email: str, subject: str, html_content: Optional[str] = None) -> bool:
    try:
        final_html = html_content if html_content else _build_html(title, message)
        await _send_via_gmail_api(email, subject, final_html)
        return True
    except Exception as e:
        logger.error(f"Error enviando email a {email}: {e}")
        raise

def generar_html_reporte_alertas(title: str, alertas_data: dict) -> str:
    """Genera el HTML del reporte de alertas"""
    from datetime import datetime

    NOMBRE_SISTEMA = "Sistema de Administración de Trámites de Corpochivor"

    ESTADO_COLOR = {
        "verde": "#15803d",
        "amarillo": "#b45309",
        "rojo": "#b91c1c",
        "vencido": "#1f2937",
    }
    ESTADO_LABEL = {
        "verde": "En término",
        "amarillo": "Próximo a vencer",
        "rojo": "Urgente",
        "vencido": "Vencido",
    }
    # Orden de severidad para mostrar primero lo más urgente
    ORDEN_ESTADO = {"vencido": 0, "rojo": 1, "amarillo": 2, "verde": 3}

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #eef1f5; margin: 0; padding: 20px; color: #1f2937; }}
            .container {{ max-width: 760px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #d8dde3; }}
            .header {{ background: #1e3a5f; color: #ffffff; padding: 24px 30px; }}
            .header .marca {{ font-size: 13px; letter-spacing: 0.04em; text-transform: uppercase; opacity: 0.85; margin: 0 0 6px 0; }}
            .header h1 {{ margin: 0; font-size: 22px; font-weight: 600; }}
            .header .fecha {{ margin: 10px 0 0 0; font-size: 13px; opacity: 0.85; }}
            .stats {{ display: table; width: 100%; border-collapse: collapse; }}
            .stats-row {{ display: table-row; }}
            .stat-cell {{ display: table-cell; width: 25%; text-align: center; padding: 16px 8px; border-bottom: 1px solid #d8dde3; border-right: 1px solid #d8dde3; }}
            .stat-cell:last-child {{ border-right: none; }}
            .stat-num {{ font-size: 26px; font-weight: 700; margin: 0; }}
            .stat-label {{ font-size: 12px; color: #4b5563; margin: 4px 0 0 0; text-transform: uppercase; letter-spacing: 0.03em; }}
            .content {{ padding: 24px 30px; }}
            .resumen {{ background: #f3f5f8; border: 1px solid #d8dde3; padding: 14px 18px; border-radius: 6px; margin-bottom: 22px; font-size: 14px; }}
            .resumen strong {{ color: #1e3a5f; }}
            .seccion-titulo {{ font-size: 15px; font-weight: 600; color: #1e3a5f; margin: 0 0 12px 0; border-bottom: 2px solid #1e3a5f; padding-bottom: 6px; }}
            .expediente {{ border: 1px solid #d8dde3; border-radius: 6px; padding: 16px 18px; margin: 0 0 16px 0; }}
            .expediente-titulo {{ margin: 0 0 12px 0; font-size: 14px; font-weight: 700; color: #1f2937; }}
            .alerta {{ background: #f9fafb; border: 1px solid #e5e7eb; border-left: 4px solid #9ca3af; border-radius: 4px; padding: 12px 14px; margin: 10px 0 0 0; }}
            .alerta-top {{ display: flex; justify-content: space-between; align-items: baseline; gap: 10px; margin-bottom: 6px; }}
            .alerta-etapa {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; color: #6b7280; }}
            .alerta-estado {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; padding: 2px 8px; border-radius: 10px; color: #ffffff; white-space: nowrap; }}
            .alerta-accion {{ font-size: 14px; font-weight: 600; color: #1f2937; margin: 0 0 4px 0; }}
            .alerta-msg {{ font-size: 13px; color: #4b5563; margin: 0 0 8px 0; }}
            .alerta-meta {{ font-size: 12px; color: #6b7280; }}
            .alerta-meta b {{ color: #374151; }}
            .footer {{ background: #1e3a5f; color: #ffffff; padding: 16px 30px; text-align: center; font-size: 11px; }}
            .footer p {{ margin: 2px 0; opacity: 0.9; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <p class="marca">{NOMBRE_SISTEMA}</p>
                <h1>{title}</h1>
                <p class="fecha">{datetime.now().strftime("%d de %B de %Y")}</p>
            </div>
    """

    # Estadísticas
    stats = alertas_data.get("estadisticas_semaforo", {})
    html += '<div class="stats"><div class="stats-row">'
    for estado in ("verde", "amarillo", "rojo", "vencido"):
        html += f"""
                <div class="stat-cell">
                    <p class="stat-num" style="color:{ESTADO_COLOR[estado]}">{stats.get(estado, 0)}</p>
                    <p class="stat-label">{ESTADO_LABEL[estado]}</p>
                </div>
        """
    html += "</div></div>"

    html += f"""
            <div class="content">
                <div class="resumen">
                    <strong>Total de expedientes a cargo:</strong> {alertas_data.get('total_expedientes', 0)}
                    &nbsp;&middot;&nbsp;
                    <strong>Con alertas pendientes:</strong> {alertas_data.get('expedientes_con_alertas', 0)}
                </div>
    """

    # Detalles por expediente
    alertas = alertas_data.get("alertas", {})
    if alertas:
        html += '<p class="seccion-titulo">Detalle de alertas por expediente</p>'
        for radicado, alertas_exp in alertas.items():
            html += f"""
            <div class="expediente">
                <p class="expediente-titulo">Expediente: {radicado}</p>
            """
            alertas_ordenadas = sorted(
                alertas_exp.values(),
                key=lambda a: ORDEN_ESTADO.get(a.get("semaforo", {}).get("estado"), 9),
            )
            for alerta in alertas_ordenadas:
                semaforo = alerta.get("semaforo", {})
                estado = semaforo.get("estado", "verde")
                color = ESTADO_COLOR.get(estado, "#6b7280")
                label = ESTADO_LABEL.get(estado, estado.upper())
                dias_restantes = semaforo.get("dias_restantes")
                dias_txt = "Vencido" if semaforo.get("esta_vencido") else f"{dias_restantes} día(s) restante(s)" if dias_restantes is not None else "N/A"

                html += f"""
                <div class="alerta" style="border-left-color:{color}">
                    <div class="alerta-top">
                        <span class="alerta-etapa">{alerta.get('etapa', '')}</span>
                        <span class="alerta-estado" style="background:{color}">{label}</span>
                    </div>
                    <p class="alerta-accion">{alerta.get('accion_requerida', '')}</p>
                    <p class="alerta-msg">{alerta.get('msg', '')}</p>
                    <p class="alerta-meta">
                        <b>Plazo legal:</b> {alerta.get('plazo_legal', 'N/A')}
                        &nbsp;&middot;&nbsp;
                        <b>Fecha límite:</b> {alerta.get('fecha_limite', 'N/A')}
                        &nbsp;&middot;&nbsp;
                        <b>{dias_txt}</b>
                    </p>
                </div>
                """
            html += "</div>"
    else:
        html += """
        <div style="text-align: center; padding: 30px 10px; color: #4b5563;">
            <p style="font-size: 15px; font-weight: 600; margin: 0 0 4px 0;">No hay alertas pendientes</p>
            <p style="font-size: 13px; margin: 0;">Todos los expedientes a su cargo están al día.</p>
        </div>
        """

    html += f"""
            </div>
            <div class="footer">
                <p>{NOMBRE_SISTEMA}</p>
                <p>&copy; {datetime.now().year} Corpochivor. Este es un mensaje automático, por favor no responder.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html
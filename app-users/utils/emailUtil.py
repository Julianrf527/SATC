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
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.15); }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 28px; }}
            .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; padding: 20px; background: #f7fafc; }}
            .stat-card {{ padding: 20px; border-radius: 8px; text-align: center; color: white; }}
            .stat-card h3 {{ margin: 0 0 10px 0; font-size: 16px; opacity: 0.9; }}
            .stat-card p {{ margin: 0; font-size: 32px; font-weight: bold; }}
            .verde {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
            .amarillo {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
            .rojo {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
            .vencido {{ background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }}
            .content {{ padding: 30px; }}
            .resumen {{ background: #edf2f7; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .resumen h2 {{ margin: 0 0 15px 0; color: #2d3748; }}
            .expediente {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 15px 0; }}
            .expediente h3 {{ margin: 0 0 15px 0; color: #2d3748; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
            .alerta {{ background: #f7fafc; padding: 15px; margin: 10px 0; border-radius: 6px; border-left: 4px solid #667eea; }}
            .alerta h4 {{ margin: 0 0 10px 0; color: #4a5568; }}
            .alerta-info {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
            .alerta-info-item {{ font-size: 14px; color: #718096; }}
            .alerta-info-item strong {{ color: #2d3748; }}
            .footer {{ background: #2d3748; color: white; padding: 20px; text-align: center; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{title}</h1>
                <p>📅 {datetime.now().strftime("%d de %B de %Y")}</p>
            </div>
    """
    
    # Estadísticas
    stats = alertas_data.get("estadisticas_semaforo", {})
    html += f"""
            <div class="stats">
                <div class="stat-card verde">
                    <h3>✅ Verde</h3>
                    <p>{stats.get('verde', 0)}</p>
                </div>
                <div class="stat-card amarillo">
                    <h3>⚠️ Amarillo</h3>
                    <p>{stats.get('amarillo', 0)}</p>
                </div>
                <div class="stat-card rojo">
                    <h3>🚨 Rojo</h3>
                    <p>{stats.get('rojo', 0)}</p>
                </div>
                <div class="stat-card vencido">
                    <h3>❌ Vencido</h3>
                    <p>{stats.get('vencido', 0)}</p>
                </div>
            </div>
            
            <div class="content">
                <div class="resumen">
                    <h2>📊 Resumen General</h2>
                    <p><strong>Total de expedientes:</strong> {alertas_data.get('total_expedientes', 0)}</p>
                    <p><strong>Expedientes con alertas:</strong> {alertas_data.get('expedientes_con_alertas', 0)}</p>
                </div>
    """
    
    # Detalles por expediente
    alertas = alertas_data.get("alertas", {})
    if alertas:
        html += "<h2>📋 Detalle de Alertas por Expediente</h2>"
        for radicado, alertas_exp in alertas.items():
            html += f"""
            <div class="expediente">
                <h3>📁 Expediente: {radicado}</h3>
            """
            for tipo, alerta in alertas_exp.items():
                semaforo = alerta.get("semaforo", {})
                emoji = {"verde": "✅", "amarillo": "⚠️", "rojo": "🚨", "vencido": "❌"}.get(semaforo.get('estado', ''), "ℹ️")
                
                html += f"""
                <div class="alerta">
                    <h4>{emoji} {tipo.replace('_', ' ').title()}</h4>
                    <div class="alerta-info">
                        <div class="alerta-info-item">
                            <strong>Estado:</strong> {semaforo.get('estado', 'N/A').upper()}
                        </div>
                        <div class="alerta-info-item">
                            <strong>Días restantes:</strong> {alerta.get('dias_restantes', 'N/A')}
                        </div>
                    </div>
                    <p style="margin: 10px 0 0 0; color: #4a5568;">{alerta.get('mensaje', '')}</p>
                </div>
                """
            html += "</div>"
    else:
        html += """
        <div style="text-align: center; padding: 40px; color: #718096;">
            <h3>🎉 No hay alertas pendientes</h3>
            <p>Todos los expedientes están al día.</p>
        </div>
        """
    
    html += """
            </div>
            <div class="footer">
                <p>© 2025 Corpochivor. Todos los derechos reservados.</p>
                <p style="margin-top: 10px; opacity: 0.8;">Este es un mensaje automático, por favor no responder.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import logging

router = APIRouter(prefix="/email", tags=["email"])
logger = logging.getLogger(__name__)

from utils.emailUtil import send_single_email, generar_html_reporte_alertas
from utils.verify_token_service import verify_service_jwt

class EmailRequest(BaseModel):
    title: str
    message: str
    email: EmailStr
    subject: str
    html_content: Optional[str] = None


class BulkEmailRequest(BaseModel):
    title: str
    message: str
    emails: List[EmailStr]
    subject: str
    html_content: Optional[str] = None

@router.post("/send")
async def enviar_email(
    request: Request,
    email_data: EmailRequest
):
    """
    Endpoint para enviar un email individual.
    Requiere autenticación con X-API-Key en el header.
    """
    verify_service_jwt(request)
    
    try:
        await send_single_email(
            title=email_data.title,
            message=email_data.message,
            email=email_data.email,
            subject=email_data.subject,
            html_content=email_data.html_content
        )
        
        return {
            "ok": True,
            "mensaje": f"Email enviado exitosamente a {email_data.email}"
        }
        
    except Exception as e:
        logger.error(f"Error en endpoint de envío: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al enviar email: {str(e)}"
        )

@router.post("/send-bulk")
async def enviar_emails_masivo(
    request: Request,
    email_data: BulkEmailRequest
):
    """
    Endpoint para enviar emails masivos.
    Requiere autenticación con X-API-Key en el header.
    """
    verify_service_jwt(request)
    
    enviados = []
    fallidos = []
    
    for email in email_data.emails:
        try:
            await send_single_email(
                title=email_data.title,
                message=email_data.message,
                email=email,
                subject=email_data.subject,
                html_content=email_data.html_content
            )
            enviados.append(email)
            
        except Exception as e:
            logger.error(f"Error enviando a {email}: {e}")
            fallidos.append({"email": email, "error": str(e)})
    
    return {
        "ok": True,
        "total": len(email_data.emails),
        "enviados": len(enviados),
        "fallidos": len(fallidos),
        "detalles_fallidos": fallidos
    }

@router.post("/send-alert-report")
async def enviar_reporte_alertas(
    request: Request,
    title: str,
    emails: List[EmailStr],
    alertas_data: dict,
):
    """
    Endpoint especializado para enviar reportes de alertas del sistema sancionatorio.
    """
    verify_service_jwt(request)
    
    # Generar HTML del reporte de alertas
    html_content = generar_html_reporte_alertas(title, alertas_data)
    
    enviados = []
    fallidos = []
    
    for email in emails:
        try:
            await send_single_email(
                title=title,
                message="Reporte de alertas adjunto",
                email=email,
                subject=title,
                html_content=html_content
            )
            enviados.append(email)
            
        except Exception as e:
            logger.error(f"Error enviando reporte a {email}: {e}")
            fallidos.append({"email": email, "error": str(e)})
    
    return {
        "ok": True,
        "total": len(emails),
        "enviados": len(enviados),
        "fallidos": len(fallidos),
        "detalles_fallidos": fallidos
    }

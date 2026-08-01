import os
import httpx
from dotenv import load_dotenv
import logging
import traceback

from utils.generate_service_jwt import generate_service_jwt

load_dotenv()
logger = logging.getLogger(__name__)
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://app-users:8001")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")


logger.info(f"Servicio de notificaciones configurado")

async def create_notification(
    mensaje: str,
    id_vinculada: str,
    tipo: str,
    usuario_id: int
) -> dict:
    """
    Crea una notificación para un usuario en app-users.

    Nunca lanza: los fallos se devuelven como {'ok': False, ...} para que un
    problema de notificación no aborte la operación que la disparó.
    """
    try:
        endpoint_url = f"{USER_SERVICE_URL}/notification/add"
        logger.info(f"Intentando crear notificación en: {endpoint_url}")
        logger.info(f"Datos: tipo={tipo}, usuario_id={usuario_id}, mensaje={mensaje[:50]}...")
        
        if not SERVICE_SECRET_KEY:
            logger.error("SERVICE_SECRET_KEY no configurado, no se puede autenticar contra app-users")
            return {"ok": False, "message": "Servicio de notificaciones mal configurado"}

        headers = {
            "Content-Type": "application/json",
            "x-service-token": generate_service_jwt("docs-service", SERVICE_SECRET_KEY),
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                endpoint_url,
                json={
                    "mensaje": mensaje,
                    "id_vinculada": id_vinculada,
                    "tipo": tipo,
                    "usuario_id": usuario_id
                },
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Notificación creada para usuario {usuario_id}: {mensaje}")
                return {"ok": True, "message": "Notificación creada"}
            else:
                logger.warning(
                    f"Error al crear notificación: {response.status_code} - {response.text}"
                )
                return {"ok": False, "message": "Error al crear notificación"}
    
    except Exception as e:
        logger.error(f"Error llamando al servicio de notificaciones: {e}")
        return {"ok": False, "message": str(e)}

async def notify_assignment(
    documento_id: int,
    documento_nombre: str,
    revisor_id: int,
    version_actual: int
) -> dict:
    """Notifica a un revisor que ha sido asignado a un documento."""
    try:
        logger.info(f"=== INICIANDO notify_assignment ===")
        logger.info(f"documento_id={documento_id}, revisor_id={revisor_id}")
        
        mensaje = f"Te han asignado como revisor del documento '{documento_nombre}' (versión {version_actual})"
        resultado = await create_notification(
            mensaje=mensaje,
            id_vinculada=str(documento_id),
            tipo="documento",
            usuario_id=revisor_id
        )
        logger.info(f"Resultado notificar_asignacion_revisor: {resultado}")
        return resultado
    except Exception as e:
        logger.error(f"ERROR en notificar_asignacion_revisor: {e}")
        logger.error(traceback.format_exc())
        return {"ok": False, "message": str(e)}

async def notify_new_version(
    documento_id: int,
    documento_nombre: str,
    version_numero: int,
    revisores_ids: list[int]
) -> list[dict]:
    """Notifica a todos los revisores que se subió una nueva versión."""
    resultados = []
    mensaje = f"Se ha subido una nueva versión ({version_numero}) del documento '{documento_nombre}'"
    
    for revisor_id in revisores_ids:
        resultado = await create_notification(
            mensaje=mensaje,
            id_vinculada=str(documento_id),
            tipo="documento",
            usuario_id=revisor_id
        )
        resultados.append(resultado)
    
    return resultados

async def notify_document_rejected(
    documento_id: int,
    documento_nombre: str,
    creador_id: int,
    numero_devoluciones: int
) -> dict:
    """Notifica al creador que su documento fue rechazado."""
    mensaje = f"Tu documento '{documento_nombre}' ha sido devuelto. Devolución {numero_devoluciones}/3"
    return await create_notification(
        mensaje=mensaje,
        id_vinculada=str(documento_id),
        tipo="documento",
        usuario_id=creador_id
    )

async def notify_document_approved(
    documento_id: int,
    documento_nombre: str,
    creador_id: int
) -> dict:
    """Notifica al creador que su documento fue aprobado."""
    mensaje = f"¡Felicidades! Tu documento '{documento_nombre}' ha sido aprobado"
    return await create_notification(
        mensaje=mensaje,
        id_vinculada=str(documento_id),
        tipo="documento",
        usuario_id=creador_id
    )

async def notify_document_finalized(
    documento_id: int,
    documento_nombre: str,
    creador_id: int
) -> dict:
    """Notifica al creador que su documento fue finalizado tras 3 rechazos."""
    mensaje = f"Tu documento '{documento_nombre}' ha sido finalizado tras alcanzar 3 devoluciones"
    return await create_notification(
        mensaje=mensaje,
        id_vinculada=str(documento_id),
        tipo="documento",
        usuario_id=creador_id
    )

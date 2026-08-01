import os
import httpx
from dotenv import load_dotenv
import logging

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
    Crea una notificación para un usuario.

    Args:
        mensaje: Texto de la notificación
        id_vinculada: ID del documento/entidad relacionada
        tipo: Tipo de notificación ('documento', 'expediente', etc.)
        usuario_id: ID del usuario que recibirá la notificación

    Returns:
        dict con 'ok' (bool) y 'message' (str)
    """
    if not SERVICE_SECRET_KEY:
        logger.error("SERVICE_SECRET_KEY no configurado, no se puede autenticar contra app-users")
        return {"ok": False, "message": "Servicio de notificaciones mal configurado"}

    try:
        endpoint_url = f"{USER_SERVICE_URL}/notification/add"
        logger.info(f"Intentando crear notificación en: {endpoint_url}")
        logger.info(f"Datos: tipo={tipo}, usuario_id={usuario_id}, mensaje={mensaje[:50]}...")

        headers = {
            "X-Service-Token": generate_service_jwt("infraction-service", SERVICE_SECRET_KEY),
            "Content-Type": "application/json"
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

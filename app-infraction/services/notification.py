"""Notificaciones en app-users vía satc_shared.clients.UsersClient
(directo, x-service-token de infraction-service)."""
from dotenv import load_dotenv
import logging

from satc_shared.clients import UsersClient

load_dotenv()

logger = logging.getLogger(__name__)

users_client = UsersClient.from_env("infraction-service")


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
        dict con 'ok' (bool) y 'message' (str). Nunca lanza.
    """
    try:
        logger.info(f"Datos notificación: tipo={tipo}, usuario_id={usuario_id}, mensaje={mensaje[:50]}...")
        await users_client.create_notification(
            mensaje=mensaje, id_vinculada=id_vinculada, tipo=tipo, usuario_id=usuario_id
        )
        logger.info(f"Notificación creada para usuario {usuario_id}: {mensaje}")
        return {"ok": True, "message": "Notificación creada"}
    except Exception as e:
        logger.error(f"Error llamando al servicio de notificaciones: {e}")
        return {"ok": False, "message": str(e)}

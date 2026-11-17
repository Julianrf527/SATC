"""Consultas/notificaciones a app-users vía satc_shared.clients.UsersClient.

Directo a app-users (sin gateway) con x-service-token de sanctioning-service.
Los wrappers conservan firmas, caché y política ante fallo (nunca lanzan).
"""
from dotenv import load_dotenv
import logging

from satc_shared.clients import UsersClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from utils.cache import permission_cache, users_cache

users_client = UsersClient.from_env("sanctioning-service")


async def get_users_by_permission(permission_name: str) -> dict:
    """
    Usuarios que tienen un permiso específico, como {user_id: {nombre, correo}}.
    """
    if not permission_name:
        return {}

    cache_key = f"users_by_permission:{permission_name}"
    cached_result = await users_cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    try:
        usuarios = await users_client.users_by_permission(permission_name)
    except Exception as e:
        logger.error(f"Error llamando al servicio de usuarios por permiso '{permission_name}': {e}")
        return {}

    result = {
        u.id: {
            "nombre": u.nombre,
            "correo": u.correo or "",
            "numero_documento": u.numero_documento,
            "documento": u.numero_documento,
        }
        for u in usuarios
    }
    await users_cache.set(cache_key, result)
    return result

async def get_user_info(user_ids: list[int]) -> dict:
    """
    Información de múltiples usuarios por sus IDs, como
    {user_id: {nombre, correo, numero_documento}}.
    """
    if not user_ids:
        return {}

    cache_key = f"users_batch:{sorted(user_ids)}"
    cached_result = await users_cache.get(cache_key)
    if cached_result is not None:
        logger.info(f"Usuarios obtenidos de caché: {len(cached_result)}")
        return cached_result

    try:
        usuarios = await users_client.users_batch(user_ids)
    except Exception as e:
        logger.error(f"Error llamando al servicio de usuarios batch: {e}", exc_info=True)
        return {}

    result = {
        u.id: {
            "nombre": u.nombre,
            "correo": u.correo,
            "numero_documento": u.numero_documento if u.numero_documento is not None else "",
        }
        for u in usuarios
    }
    logger.info(f"Usuarios procesados: {len(result)}")
    await users_cache.set(cache_key, result)
    return result

async def verify_permission(user_id: int, permission: str):
    """
    Verifica si un usuario tiene un permiso específico. Fail-closed.
    """
    cache_key = f"permission:{user_id}:{permission}"
    cached_result = await permission_cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    try:
        result = await users_client.verify_permission(user_id, permission)
    except Exception as e:
        logger.error(f"verify_permission error usuario {user_id}: {e}")
        return False

    await permission_cache.set(cache_key, result)
    return result

async def create_user_notification(
    mensaje: str,
    id_vinculada: str,
    usuario_id: int,
    tipo: str = "expediente"
) -> dict:
    """
    Crea una notificación en el servicio de usuarios.

    id_vinculada es el radicado de la entidad relacionada: el frontend lo usa
    para construir la ruta de navegación de la notificación.
    """
    try:
        await users_client.create_notification(
            mensaje=mensaje, id_vinculada=id_vinculada, tipo=tipo, usuario_id=usuario_id
        )
        return {"ok": True, "message": "Notificación creada"}
    except Exception as e:
        logger.error(f"Error llamando al servicio de notificaciones: {e}")
        return {"ok": False, "message": str(e)}

"""Consultas a app-users vía satc_shared.clients.UsersClient (directo, con
x-service-token de involved-service)."""
import logging

from dotenv import load_dotenv

from satc_shared.clients import UsersClient
from utils.cache import permission_cache, users_cache

load_dotenv()

logger = logging.getLogger(__name__)

users_client = UsersClient.from_env("involved-service")


async def get_user_info(user_ids: list[int]) -> dict:
    """Devuelve {user_id: {nombre, correo, numero_documento}} consultando app-users directo.

    Falla en silencio devolviendo {}: solo enriquece el log de auditoría, así que
    caerse app-users no debe tumbar la consulta del log.
    """
    if not user_ids:
        return {}

    cache_key = f"users_batch:{sorted(user_ids)}"
    cached = await users_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        usuarios = await users_client.users_batch(user_ids)
    except Exception as e:
        logger.error(f"get_user_info error: {e}", exc_info=True)
        return {}

    result = {
        u.id: {
            "nombre": u.nombre or "",
            "correo": u.correo or "",
            "numero_documento": u.numero_documento,
        }
        for u in usuarios
    }
    await users_cache.set(cache_key, result)
    return result


async def verify_permission(user_id: int, permission: str) -> bool:
    """Consulta a app-users si el usuario tiene el permiso.

    Fail-closed a propósito: cualquier error de red o respuesta no-200 devuelve
    False, nunca concede acceso por defecto.
    """
    cache_key = f"permission:{user_id}:{permission}"
    cached = await permission_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        result = await users_client.verify_permission(user_id, permission)
    except Exception as e:
        logger.error(f"verify_permission error usuario {user_id}: {e}")
        return False

    await permission_cache.set(cache_key, result)
    return result

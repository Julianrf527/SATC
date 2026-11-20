"""Consultas a app-users vía satc_shared.clients.UsersClient.

Llamadas directas a app-users (sin pasar por gateway) con x-service-token de
recurso-service. Los wrappers conservan firmas, caché y la política ante
fallo (``{}`` / ``False``, nunca lanzan).
"""
import logging
from dotenv import load_dotenv

from satc_shared.clients import UsersClient
from satc_shared.permisos_version import SincronizadorPermisos

load_dotenv()

logger = logging.getLogger(__name__)

from utils.cache import permission_cache, users_cache

users_client = UsersClient.from_env("recurso-service")

# Cuando app-users cambia roles o permisos sube la versión en Redis: las cachés
# de este worker se vacían en el siguiente acceso (TTL como red de seguridad).
_sincronizador = SincronizadorPermisos()


async def _sincronizar_caches() -> None:
    if await _sincronizador.cambio():
        await permission_cache.clear()
        await users_cache.clear()


async def get_users_by_permission(permission_name: str) -> dict:
    """
    Obtiene usuarios que tienen un permiso específico.
    Retorna {user_id: {nombre, correo, numero_documento, documento}}
    """
    if not permission_name:
        return {}

    await _sincronizar_caches()
    cache_key = f"users_by_permission:{permission_name}"
    cached = await users_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        usuarios = await users_client.users_by_permission(permission_name)
    except Exception as e:
        logger.error(f"get_users_by_permission '{permission_name}' error: {e}")
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
    Obtiene info de múltiples usuarios por IDs.
    Retorna {user_id: {nombre, correo, numero_documento}}. Caché por usuario:
    solo se piden a app-users los que no estén en caché.
    """
    result: dict = {}
    faltantes = []
    for uid in dict.fromkeys(user_ids or []):
        cached = await users_cache.get(f"user:{uid}")
        if cached is None:
            faltantes.append(uid)
        else:
            result[uid] = cached
    if not faltantes:
        return result

    try:
        usuarios = await users_client.users_batch(faltantes)
    except Exception as e:
        logger.error(f"get_user_info error: {e}", exc_info=True)
        return result

    for u in usuarios:
        info = {
            "nombre": u.nombre,
            "correo": u.correo,
            "numero_documento": u.numero_documento if u.numero_documento is not None else "",
        }
        result[u.id] = info
        await users_cache.set(f"user:{u.id}", info)
    return result


async def verify_permission(user_id: int, permission: str) -> bool:
    """
    Verifica si un usuario tiene un permiso específico. Fail-closed: cualquier
    error devuelve False.
    """
    await _sincronizar_caches()
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

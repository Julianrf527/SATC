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

# Llamadas directas a app-users (east-west, sin gateway) con x-service-token
# de docs-service. URL/secreto: USER_SERVICE_URL / SERVICE_SECRET_KEY.
users_client = UsersClient.from_env("docs-service")


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

    result = {u.id: {"nombre": u.nombre, "correo": u.correo} for u in usuarios}
    # No cachear resultados vacíos: evita que un permiso recién asignado
    # quede invisible hasta que expire el TTL del caché.
    if result:
        await users_cache.set(cache_key, result)
    return result

async def get_user_names(user_ids: list[int]) -> dict[int, str]:
    """Nombres por id (``POST /user/batch``), sin depender de los permisos
    actuales del usuario: un revisor que perdió el permiso sigue teniendo
    nombre en el historial. Fallo del servicio -> {} (la UI muestra el id)."""
    ids = sorted({int(u) for u in user_ids if u})
    if not ids:
        return {}

    cache_key = f"users_batch:{ids}"
    cached = await users_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        usuarios = await users_client.users_batch(ids)
    except Exception as e:
        logger.error(f"get_user_names error: {e}")
        return {}

    result = {u.id: u.nombre for u in usuarios if u.nombre}
    if result:
        await users_cache.set(cache_key, result)
    return result


async def verify_permission(user_id: int, permission: str):
    """
    Verifica si un usuario tiene un permiso específico. Fail-closed: cualquier
    error devuelve False.
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

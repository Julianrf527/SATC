import httpx
import logging
import os
from dotenv import load_dotenv

load_dotenv()
USERS_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://app-users:8001")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from utils.generate_service_jwt import generate_service_jwt
from utils.cache import permission_cache, users_cache

def _service_headers() -> dict:
    if not SERVICE_SECRET_KEY:
        raise RuntimeError("SERVICE_SECRET_KEY no configurado, no se puede autenticar contra app-users")
    token = generate_service_jwt("infraction-service", SERVICE_SECRET_KEY)
    return {"X-Service-Token": token}

async def get_users_by_permission(permission_name: str) -> dict:
    """
    Obtiene usuarios que tienen un permiso específico.
    Retorna {user_id: {nombre, correo, ...}}
    Llamada directa a app-users (sin pasar por gateway).
    """
    if not permission_name:
        return {}

    cache_key = f"users_by_permission:{permission_name}"
    cached = await users_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{USERS_SERVICE_URL}/user/permission/{permission_name}",
                headers=_service_headers(),
            )

        if response.status_code == 200:
            data = response.json()
            result = {
                user["id"]: {
                    "nombre": user.get("nombre"),
                    "correo": user.get("correo", ""),
                    "numero_documento": user.get("numero_documento"),
                    "documento": user.get("numero_documento"),
                }
                for user in data.get("data", [])
            }
            await users_cache.set(cache_key, result)
            return result
        else:
            logger.warning(f"get_users_by_permission '{permission_name}': status {response.status_code}")
            return {}

    except Exception as e:
        logger.error(f"get_users_by_permission error: {e}")
        return {}

async def get_user_info(user_ids: list[int]) -> dict:
    """
    Obtiene info de múltiples usuarios por IDs.
    Retorna {user_id: {nombre, correo}}
    Llamada directa a app-users (sin pasar por gateway).
    """
    if not user_ids:
        return {}

    cache_key = f"users_batch:{sorted(user_ids)}"
    cached = await users_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{USERS_SERVICE_URL}/user/batch",
                headers=_service_headers(),
                json={"user_ids": user_ids},
            )

        if response.status_code == 200:
            data = response.json()
            result = {
                user["id"]: {
                    "nombre": user["nombre"],
                    "correo": user["correo"],
                    "numero_documento": user.get("numero_documento", ""),
                }
                for user in data.get("data", [])
            }
            await users_cache.set(cache_key, result)
            return result
        else:
            logger.warning(f"get_user_info batch: status {response.status_code} - {response.text}")
            return {}

    except Exception as e:
        logger.error(f"get_user_info error: {e}", exc_info=True)
        return {}

async def verify_permission(user_id: int, permission: str) -> bool:
    """
    Verifica si un usuario tiene un permiso específico.
    Llamada directa a app-users (sin pasar por gateway).
    Retorna True/False.
    """
    cache_key = f"permission:{user_id}:{permission}"
    cached = await permission_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{USERS_SERVICE_URL}/role/verify",
                headers=_service_headers(),
                json={"user_id": user_id, "permission_name": permission},
            )

        if resp.status_code != 200:
            logger.error(f"verify_permission status {resp.status_code} para usuario {user_id}: {resp.text}")
            return False

        result: bool = resp.json().get("tiene_permiso", False)
        await permission_cache.set(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"verify_permission error usuario {user_id}: {e}")
        return False

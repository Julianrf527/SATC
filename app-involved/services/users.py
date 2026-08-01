import logging
import os

import httpx
from dotenv import load_dotenv

from utils.generate_service_jwt import generate_service_jwt
from utils.cache import permission_cache, users_cache

load_dotenv()
USERS_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://app-users:8001")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")

logger = logging.getLogger(__name__)


def _service_headers() -> dict:
    if not SERVICE_SECRET_KEY:
        raise RuntimeError("SERVICE_SECRET_KEY no configurado, no se puede autenticar contra app-users")
    token = generate_service_jwt("involved-service", SERVICE_SECRET_KEY)
    return {"X-Service-Token": token}


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
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{USERS_SERVICE_URL}/user/batch",
                headers=_service_headers(),
                json={"user_ids": user_ids},
            )

        if response.status_code != 200:
            logger.warning(f"get_user_info batch: status {response.status_code}")
            return {}

        result = {
            user["id"]: {
                "nombre": user.get("nombre", ""),
                "correo": user.get("correo", ""),
                "numero_documento": user.get("numero_documento"),
            }
            for user in response.json().get("data", [])
        }
        await users_cache.set(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"get_user_info error: {e}", exc_info=True)
        return {}


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
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{USERS_SERVICE_URL}/role/verify",
                headers=_service_headers(),
                json={"user_id": user_id, "permission_name": permission},
            )

        if resp.status_code != 200:
            logger.error(f"verify_permission status {resp.status_code} para usuario {user_id}")
            return False

        result: bool = resp.json().get("tiene_permiso", False)
        await permission_cache.set(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"verify_permission error usuario {user_id}: {e}")
        return False

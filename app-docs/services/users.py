from fastapi import HTTPException
from dotenv import load_dotenv
import httpx
import logging
import os

load_dotenv()
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://app-users:8001")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from utils.generate_service_jwt import generate_service_jwt
from utils.cache import permission_cache, users_cache


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
        service_token = generate_service_jwt("docs-service", SERVICE_SECRET_KEY)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{USER_SERVICE_URL}/user/permission/{permission_name}",
                headers={"x-service-token": service_token}
            )

            if response.status_code == 200:
                data = response.json()
                result = {
                    user["id"]: {
                        "nombre": user["nombre"],
                        "correo": user["correo"]
                    }
                    for user in data.get("data", [])
                }
                # No cachear resultados vacíos: evita que un permiso recién asignado
                # quede invisible hasta que expire el TTL del caché.
                if result:
                    await users_cache.set(cache_key, result)
                return result
            else:
                logger.warning(
                    f"Error al obtener usuarios por permiso '{permission_name}': "
                    f"{response.status_code}"
                )
                return {}
    
    except Exception as e:
        logger.error(f"Error llamando al servicio de usuarios por permiso: {e}")
        return {}

async def verify_permission(user_id: int, permission: str):
    """
    Verifica si un usuario tiene un permiso específico.
    """
    try:
        service_token = generate_service_jwt("docs-service", SERVICE_SECRET_KEY)

        cache_key = f"permission:{user_id}:{permission}"
        cached_result = await permission_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{USER_SERVICE_URL}/role/verify",
                headers={"x-service-token": service_token},
                json={"user_id": user_id, "permission_name": permission}
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

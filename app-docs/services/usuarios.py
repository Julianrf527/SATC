from fastapi import HTTPException
from dotenv import load_dotenv
import httpx
import logging
import os

# -------- ENV ------------

load_dotenv()
GATEWAY_URL = os.getenv("API_GATEWAY_URL")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")

# ---------- LOGGER ------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

#  ----------  UTILS  ------------
from utils.generate_service_jwt import generate_service_jwt
from utils.cache import permission_cache, users_cache


async def obtener_usuarios_por_permiso(permission_name: str) -> dict:
    """
    Llama al servicio de usuarios para obtener usuarios que tienen un permiso específico.
    Retorna un diccionario {user_id: {nombre, correo}}
    
    OPTIMIZACIÓN: Usa caché para evitar llamadas HTTP repetitivas.
    """
    if not permission_name:
        return {}
    
    # Intentar obtener del caché primero
    cache_key = f"users_by_permission:{permission_name}"
    cached_result = await users_cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        # Generar token de servicio
        service_token = generate_service_jwt("expedientes-service", SERVICE_SECRET_KEY)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GATEWAY_URL}/users/user/permission/{permission_name}",
                headers={"X-Service-Token": service_token}
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
                # Guardar en caché
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


async def verificar_permiso_externo(user_id: int, name: str):
    """
    Verifica si un usuario tiene un permiso específico.
    
    OPTIMIZACIÓN: Usa caché para evitar llamadas HTTP repetitivas.
    """
    # Intentar obtener del caché primero
    cache_key = f"permission:{user_id}:{name}"
    cached_result = await permission_cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{GATEWAY_URL}/users/role/permission/verify",
            params={"user_id": user_id, "name": name}
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    result = resp.json()
    
    # Guardar en caché
    await permission_cache.set(cache_key, result)
    
    return result
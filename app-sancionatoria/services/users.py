from dotenv import load_dotenv
import httpx
import logging
import os

load_dotenv()
USERS_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://app-users:8001")
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
        service_token = generate_service_jwt("sanctioning-service", SERVICE_SECRET_KEY)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{USERS_SERVICE_URL}/user/permission/{permission_name}",
                headers={"X-Service-Token": service_token}
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
                logger.warning(
                    f"Error al obtener usuarios por permiso '{permission_name}': "
                    f"{response.status_code}"
                )
                return {}
    
    except Exception as e:
        logger.error(f"Error llamando al servicio de usuarios por permiso: {e}")
        return {}

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
        service_token = generate_service_jwt("sanctioning-service", SERVICE_SECRET_KEY)

        users_url = f"{USERS_SERVICE_URL}/user/batch"
        logger.info(f"Llamando a {users_url} con {len(user_ids)} IDs: {user_ids}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                users_url,
                headers={
                    "X-Service-Token": service_token,
                    "Content-Type": "application/json"
                },
                json={"user_ids": user_ids}
            )
            
            logger.info(f"Respuesta del servicio de usuarios: status={response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Datos recibidos: {data}")
                result = {
                    user["id"]: {
                        "nombre": user["nombre"],
                        "correo": user["correo"],
                        "numero_documento": user.get("numero_documento", ""),
                    }
                    for user in data.get("data", [])
                }
                logger.info(f"Usuarios procesados: {len(result)}")
                await users_cache.set(cache_key, result)
                return result
            else:
                logger.warning(
                    f"Error al obtener usuarios batch: {response.status_code} - {response.text}"
                )
                return {}
    
    except Exception as e:
        logger.error(f"Error llamando al servicio de usuarios batch: {e}", exc_info=True)
        return {}

async def verify_permission(user_id: int, permission: str):
    """
    Verifica si un usuario tiene un permiso específico.
    """
    try:
        service_token = generate_service_jwt("sanctioning-service", SERVICE_SECRET_KEY)

        cache_key = f"permission:{user_id}:{permission}"
        cached_result = await permission_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{USERS_SERVICE_URL}/role/verify",
                headers={"X-Service-Token": service_token},
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
        service_token = generate_service_jwt("sanctioning-service", SERVICE_SECRET_KEY)

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{USERS_SERVICE_URL}/notification/add",
                headers={"X-Service-Token": service_token},
                json={
                    "mensaje": mensaje,
                    "id_vinculada": id_vinculada,
                    "tipo": tipo,
                    "usuario_id": usuario_id
                },
            )
            
            if response.status_code in [200, 201]:
                return {"ok": True, "message": "Notificación creada"}
            else:
                logger.warning(
                    f"Error al crear notificación: {response.status_code} - {response.text}"
                )
                return {"ok": False, "message": "Error al crear notificación"}
    
    except Exception as e:
        logger.error(f"Error llamando al servicio de notificaciones: {e}")
        return {"ok": False, "message": str(e)}


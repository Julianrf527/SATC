from fastapi import HTTPException
from dotenv import load_dotenv
import httpx
import logging
import os

# -------- ENV ------------

load_dotenv()
GATEWAY_URL = os.getenv("GATEWAY_URL")
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

async def obtener_info_usuarios(user_ids: list[int]) -> dict:
    """
    Llama al servicio de usuarios para obtener información de múltiples usuarios por sus IDs.
    Retorna un diccionario {user_id: {nombre, correo}}
    
    OPTIMIZACIÓN: Usa caché para evitar llamadas HTTP repetitivas.
    """
    if not user_ids:
        return {}
    
    # Intentar obtener del caché primero
    cache_key = f"users_batch:{sorted(user_ids)}"
    cached_result = await users_cache.get(cache_key)
    if cached_result is not None:
        logger.info(f"Usuarios obtenidos de caché: {len(cached_result)}")
        return cached_result
    
    try:
        # Generar token de servicio
        service_token = generate_service_jwt("expedientes-service", SERVICE_SECRET_KEY)
        
        gateway_url = f"{GATEWAY_URL}/users/user/batch"
        logger.info(f"Llamando a {gateway_url} con {len(user_ids)} IDs: {user_ids}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                gateway_url,
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
                        "correo": user["correo"]
                    }
                    for user in data.get("data", [])
                }
                logger.info(f"Usuarios procesados: {len(result)}")
                # Guardar en caché
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

async def crear_notificacion_usuario(
    mensaje: str,
    ruta: str,
    usuario_id: int
) -> dict:
    """
    Helper para crear notificaciones llamando al servicio de usuarios.
    
    Args:
        mensaje: Texto de la notificación
        ruta: Ruta donde redirigir (ej: "/expedientes/RAD-2024-001")
        usuario_id: ID del usuario que recibirá la notificación
    
    Returns:
        dict con 'ok' (bool) y 'message' (str)
    """
    try:        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/users/notification/new",
                json={
                    "mensaje": mensaje,
                    "ruta": ruta,
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


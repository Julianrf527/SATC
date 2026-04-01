import redis.asyncio as redis
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB_SESSIONS"))
REDIS_ENABLED = os.getenv("REDIS_SESSIONS_ENABLED")

# Pool de conexiones — se inicializa una vez al arrancar la app
redis_client: Optional[redis.Redis] = None


# ==========================================
# INICIALIZACIÓN
# ==========================================
async def init_redis() -> None:
    """Llamar en el startup de FastAPI."""
    global redis_client

    if not REDIS_ENABLED:
        logger.info("Redis deshabilitado por configuración")
        return

    try:
        redis_client = redis.Redis(           # sin await
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB,
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
            max_connections=50
        )
        await redis_client.ping()             # aquí sí hay await, para verificar
        logger.info(f"Redis conectado: {REDIS_HOST}:{REDIS_PORT} DB={REDIS_DB}")
    except Exception as e:
        logger.warning(f"Redis no disponible: {e}. Fallback a PostgreSQL activo.")
        redis_client = None


async def close_redis() -> None:
    """Llamar en el shutdown de FastAPI."""
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None
        logger.info("Redis desconectado")


def get_redis_client() -> Optional[redis.Redis]:
    """Retorna el cliente global. None si Redis no está disponible."""
    return redis_client


# ==========================================
# OPERACIONES DE SESIÓN
# ==========================================
async def save_session_redis(
    token_jti: str,
    user_id: int,
    ip_address: str,
    user_agent: str,
    permisos: list,
    nombre: str,
    documento: str,
    ttl_days: int = 1
) -> bool:
    """
    Guarda sesión + permisos en Redis en un solo pipeline.
    Retorna True si se guardó, False si hubo error o Redis no disponible.
    """
    r = get_redis_client()
    if r is None:
        return False

    ttl_seconds = int(timedelta(days=ttl_days).total_seconds())
    session_data = {
        "user_id": str(user_id),
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": datetime.now(ZoneInfo("America/Bogota")).isoformat()
    }

    try:
        async with r.pipeline() as pipe:
            pipe.setex(f"session:{token_jti}", ttl_seconds, json.dumps(session_data))
            pipe.setex(f"session_permisos:{token_jti}", ttl_seconds, json.dumps(permisos))
            pipe.setex(f"session_nombre:{token_jti}", ttl_seconds, nombre)
            pipe.setex(f"session_documento:{token_jti}", ttl_seconds, documento)
            await pipe.execute()

        logger.info(f"Sesión guardada en Redis: {token_jti[:8]}... (user_id={user_id}, TTL={ttl_days}d)")
        return True

    except Exception as e:
        logger.error(f"Error guardando sesión en Redis: {e}")
        return False


async def verify_session_and_permisos(
    token_jti: str,
    path_solicitado: str
) -> Dict[str, Any]:
    """
    Verifica sesión activa y permiso en un solo pipeline.
    Úsalo en el gateway para cada request autenticado.

    Retorna:
        { "valid": True, "user_id": "..." }
        { "valid": False, "reason": "sesion_invalida" | "sin_permiso" }
    """
    r = get_redis_client()
    if r is None:
        # Redis caído → fallback: validar contra PostgreSQL en el gateway
        return {"valid": False, "reason": "redis_no_disponible"}

    try:
        async with r.pipeline() as pipe:
            pipe.get(f"session:{token_jti}")
            pipe.get(f"session_permisos:{token_jti}")
            sesion_raw, permisos_raw = await pipe.execute()

        if not sesion_raw:
            return {"valid": False, "reason": "sesion_invalida"}

        permisos: list = json.loads(permisos_raw) if permisos_raw else []
        if path_solicitado not in permisos:
            return {"valid": False, "reason": "sin_permiso"}

        sesion = json.loads(sesion_raw)
        return {"valid": True, "user_id": sesion["user_id"]}

    except Exception as e:
        logger.error(f"Error verificando sesión en Redis: {e}")
        return {"valid": False, "reason": "error_interno"}


async def delete_session_redis(token_jti: str) -> bool:
    """Elimina sesión y permisos al hacer logout."""
    r = get_redis_client()
    if r is None:
        return False

    try:
        async with r.pipeline() as pipe:
            pipe.delete(f"session:{token_jti}")
            pipe.delete(f"session_permisos:{token_jti}")
            pipe.delete(f"session_nombre:{token_jti}")
            pipe.delete(f"session_documento:{token_jti}")
            await pipe.execute()

        logger.info(f"Sesión eliminada de Redis: {token_jti[:8]}...")
        return True

    except Exception as e:
        logger.error(f"Error eliminando sesión: {e}")
        return False


async def refresh_session_ttl(token_jti: str, ttl_days: int = 1) -> bool:
    """Renueva TTL de sesión y permisos juntos."""
    r = get_redis_client()
    if r is None:
        return False

    ttl_seconds = int(timedelta(days=ttl_days).total_seconds())

    try:
        async with r.pipeline() as pipe:
            pipe.expire(f"session:{token_jti}", ttl_seconds)
            pipe.expire(f"session_permisos:{token_jti}", ttl_seconds)
            pipe.expire(f"session_nombre:{token_jti}", ttl_seconds)
            pipe.expire(f"session_documento:{token_jti}", ttl_seconds)
            results = await pipe.execute()

        if not any(results):
            logger.warning(f"Sesión no existe en Redis: {token_jti[:8]}...")
            return False

        return True

    except Exception as e:
        logger.error(f"Error renovando TTL: {e}")
        return False


# ==========================================
# HEALTH CHECK
# ==========================================
async def redis_health_check() -> Dict[str, Any]:
    r = get_redis_client()
    if r is None:
        return {"status": "disabled"}

    try:
        await r.ping()
        info = await r.info("stats")

        # SCAN en lugar de KEYS para no bloquear Redis
        count = 0
        async for _ in r.scan_iter("session:*"):
            count += 1

        return {
            "status": "healthy",
            "sessions_active": count,
            "total_connections": info.get("total_connections_received", 0),
            "used_memory": info.get("used_memory_human", "N/A")
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
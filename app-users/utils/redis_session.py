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


# INICIALIZACIÓN
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

# HEALTH CHECK
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
import redis.asyncio as redis
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "redis_password")
REDIS_DB = int(os.getenv("REDIS_DB_SESSIONS", "1"))  # misma DB que app-users

redis_client: Optional[redis.Redis] = None


async def init_redis() -> None:
    """Llamar en el startup del gateway."""
    global redis_client
    try:
        redis_client = redis.Redis(
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
        await redis_client.ping()
        logger.info(f"Redis conectado en gateway: {REDIS_HOST}:{REDIS_PORT} DB={REDIS_DB}")
    except Exception as e:
        logger.warning(f"Redis no disponible en gateway: {e}")
        redis_client = None


async def close_redis() -> None:
    """Llamar en el shutdown del gateway."""
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None


def get_redis_client() -> Optional[redis.Redis]:
    return redis_client
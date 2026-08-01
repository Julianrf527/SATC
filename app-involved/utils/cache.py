from datetime import datetime, timedelta
from typing import Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

class SimpleCache:
    """Caché en memoria con TTL, serializado con asyncio.Lock."""
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl_seconds = ttl_seconds
        self.lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor del caché si no ha expirado"""
        async with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if datetime.now() < expiry:
                    logger.debug(f"Cache HIT: {key}")
                    return value
                else:
                    del self.cache[key]
                    logger.debug(f"Cache EXPIRED: {key}")
            else:
                logger.debug(f"Cache MISS: {key}")
            return None
    
    async def set(self, key: str, value: Any):
        """Guarda un valor en el caché con TTL"""
        async with self.lock:
            expiry = datetime.now() + timedelta(seconds=self.ttl_seconds)
            self.cache[key] = (value, expiry)
            logger.debug(f"Cache SET: {key} (TTL: {self.ttl_seconds}s)")
    
    async def delete(self, key: str):
        """Elimina una clave del caché"""
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Cache DELETE: {key}")
    
    async def clear(self):
        """Limpia todo el caché"""
        async with self.lock:
            self.cache.clear()
            logger.debug("Cache CLEARED")
    
    async def cleanup_expired(self):
        """Limpia entradas expiradas (ejecutar periódicamente)"""
        async with self.lock:
            now = datetime.now()
            expired_keys = [k for k, (_, exp) in self.cache.items() if now >= exp]
            for key in expired_keys:
                del self.cache[key]
            if expired_keys:
                logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")

# TTL corto en permisos: un cambio de rol debe propagarse rápido. Los datos
# de usuario cambian mucho menos, así que aguantan un TTL mayor.
permission_cache = SimpleCache(ttl_seconds=300)
users_cache = SimpleCache(ttl_seconds=600)

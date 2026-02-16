"""
Cache Manager - Soporte para caché distribuido (Caso 4)

Soporta tres estrategias:
1. Local (en memoria) - Para desarrollo y sistemas pequeños
2. Redis - Para alta disponibilidad con múltiples instancias del Gateway
3. Sin caché (None) - Siempre decodifica JWT (más simple, para baja concurrencia)

Fecha: 2026-02-13
"""
import os
import time
import json
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Configuración desde variables de entorno
CACHE_TYPE = os.getenv("CACHE_TYPE", "local").lower()  # local, redis, none
CACHE_TTL = int(os.getenv("CACHE_TTL", "120"))  # 120 segundos por defecto
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)


class CacheBackend(ABC):
    """Clase abstracta para diferentes backends de caché"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Obtiene un valor del caché"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Dict[str, Any], ttl: int) -> bool:
        """Guarda un valor en el caché con TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Elimina un valor del caché"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Limpia todo el caché"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché"""
        pass


class LocalCache(CacheBackend):
    """Caché local en memoria (compatible con código actual)"""
    
    def __init__(self, max_size: int = 500):
        self.cache: Dict[str, tuple] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        logger.info(f"Cache local inicializado (max_size={max_size})")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < CACHE_TTL:
                self.hits += 1
                return value
            else:
                # Expirado, eliminar
                del self.cache[key]
        
        self.misses += 1
        return None
    
    async def set(self, key: str, value: Dict[str, Any], ttl: int = None) -> bool:
        # Limpiar caché si está muy lleno
        if len(self.cache) >= self.max_size:
            # Eliminar entradas más antiguas
            sorted_keys = sorted(self.cache.items(), key=lambda x: x[1][1])
            for k, _ in sorted_keys[:self.max_size // 4]:  # Eliminar 25%
                del self.cache[k]
            logger.info(f"Cache local limpiado: {len(self.cache)} entradas")
        
        self.cache[key] = (value, time.time())
        return True
    
    async def delete(self, key: str) -> bool:
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    async def clear(self) -> bool:
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache local limpiado completamente")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "type": "local",
            "entries": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "ttl": CACHE_TTL
        }


class RedisCache(CacheBackend):
    """Caché distribuido usando Redis"""
    
    def __init__(self):
        self.redis = None
        self.connected = False
        self._initialize()
    
    def _initialize(self):
        """Inicializa la conexión a Redis"""
        try:
            import redis.asyncio as redis_async
            
            self.redis = redis_async.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            self.connected = True
            logger.info(f"Cache Redis inicializado: {REDIS_HOST}:{REDIS_PORT}")
        except ImportError:
            logger.error("redis no instalado. Instalar con: pip install redis")
            self.connected = False
        except Exception as e:
            logger.error(f"Error inicializando Redis: {e}")
            self.connected = False
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        if not self.connected:
            return None
        
        try:
            value = await self.redis.get(f"token:{key}")
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error obteniendo de Redis: {e}")
            return None
    
    async def set(self, key: str, value: Dict[str, Any], ttl: int = None) -> bool:
        if not self.connected:
            return False
        
        try:
            ttl = ttl or CACHE_TTL
            await self.redis.setex(
                f"token:{key}",
                ttl,
                json.dumps(value)
            )
            return True
        except Exception as e:
            logger.error(f"Error guardando en Redis: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        if not self.connected:
            return False
        
        try:
            result = await self.redis.delete(f"token:{key}")
            return result > 0
        except Exception as e:
            logger.error(f"Error eliminando de Redis: {e}")
            return False
    
    async def clear(self) -> bool:
        if not self.connected:
            return False
        
        try:
            # Eliminar solo las keys de tokens
            keys = await self.redis.keys("token:*")
            if keys:
                await self.redis.delete(*keys)
            logger.info(f"Cache Redis limpiado: {len(keys)} entradas")
            return True
        except Exception as e:
            logger.error(f"Error limpiando Redis: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        if not self.connected:
            return {
                "type": "redis",
                "connected": False,
                "error": "No conectado a Redis"
            }
        
        try:
            # Esto es síncrono, pero para stats es aceptable
            import asyncio
            loop = asyncio.get_event_loop()
            info = loop.run_until_complete(self.redis.info("stats"))
            
            return {
                "type": "redis",
                "connected": True,
                "host": REDIS_HOST,
                "port": REDIS_PORT,
                "db": REDIS_DB,
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "ttl": CACHE_TTL
            }
        except Exception as e:
            return {
                "type": "redis",
                "connected": True,
                "error": str(e)
            }


class NoCache(CacheBackend):
    """Sin caché - Siempre decodifica JWT (más simple)"""
    
    def __init__(self):
        logger.info("Cache deshabilitado - Siempre decodificando JWT")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        return None  # Siempre miss
    
    async def set(self, key: str, value: Dict[str, Any], ttl: int = None) -> bool:
        return True  # No hace nada
    
    async def delete(self, key: str) -> bool:
        return True  # No hace nada
    
    async def clear(self) -> bool:
        return True  # No hace nada
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "none",
            "enabled": False,
            "message": "Cache deshabilitado - JWT se decodifica en cada request"
        }


# ============================================
# Factory para crear la instancia correcta
# ============================================

def create_cache() -> CacheBackend:
    """Crea la instancia de caché según configuración"""
    
    if CACHE_TYPE == "redis":
        logger.info("Usando cache REDIS distribuido")
        return RedisCache()
    elif CACHE_TYPE == "local":
        logger.info("Usando cache LOCAL (en memoria)")
        return LocalCache()
    elif CACHE_TYPE == "none":
        logger.info("Cache DESHABILITADO")
        return NoCache()
    else:
        logger.warning(f"CACHE_TYPE desconocido: {CACHE_TYPE}, usando local")
        return LocalCache()


# Instancia global del caché
cache_backend: CacheBackend = create_cache()


# ============================================
# API pública simplificada
# ============================================

async def get_from_cache(token: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene datos del token desde el caché.
    Retorna None si no está en caché o está expirado.
    """
    return await cache_backend.get(token)


async def save_to_cache(token: str, data: Dict[str, Any], ttl: int = None) -> bool:
    """
    Guarda datos del token en el caché con TTL opcional.
    """
    return await cache_backend.set(token, data, ttl or CACHE_TTL)


async def invalidate_cache(token: str) -> bool:
    """
    Invalida/elimina un token específico del caché.
    Útil para logout o cambios de permisos.
    """
    return await cache_backend.delete(token)


async def clear_all_cache() -> bool:
    """
    Limpia todo el caché.
    Útil para mantenimiento o emergencias.
    """
    return await cache_backend.clear()


def get_cache_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas del caché actual.
    """
    return cache_backend.get_stats()


# ============================================
# Health check para monitoreo
# ============================================

async def check_cache_health() -> Dict[str, Any]:
    """
    Verifica que el caché esté funcionando correctamente.
    Retorna estado y mensaje.
    """
    try:
        # Test básico: guardar y leer
        test_key = "__health_check__"
        test_value = {"test": True, "timestamp": time.time()}
        
        await save_to_cache(test_key, test_value, ttl=10)
        retrieved = await get_from_cache(test_key)
        await invalidate_cache(test_key)
        
        if retrieved and retrieved.get("test") == True:
            return {
                "status": "healthy",
                "cache_type": CACHE_TYPE,
                "working": True
            }
        else:
            return {
                "status": "degraded",
                "cache_type": CACHE_TYPE,
                "working": False,
                "message": "Test falló"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "cache_type": CACHE_TYPE,
            "working": False,
            "error": str(e)
        }

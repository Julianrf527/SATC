"""
Sistema de Rate Limiting para Red Local
Protege contra brute force sin afectar operación normal interna
"""
import redis
import os
import time
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

# Configuración Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Cliente Redis
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=2
    )
    redis_client.ping()
except Exception as e:
    print(f"⚠️ Redis no disponible para rate limiting: {e}")
    redis_client = None


class RateLimiter:
    """
    Rate Limiter optimizado para red local con Redis
    
    Configuración adaptada a red local:
    - Límites más generosos que internet público
    - Múltiples ventanas de tiempo
    - Bloqueo temporal progresivo
    """
    
    # Límites para red local (más generosos que público)
    LIMITS = {
        # Login: 10 intentos por minuto, 30 por hora
        "login": {
            "per_minute": 10,
            "per_hour": 30,
            "per_day": 100
        },
        # API general: 300 requests por minuto
        "api": {
            "per_minute": 300,
            "per_hour": 5000
        },
        # Endpoints administrativos: 100 por minuto
        "admin": {
            "per_minute": 100,
            "per_hour": 1000
        }
    }
    
    @staticmethod
    def check_rate_limit(identifier: str, limit_type: str = "api") -> Dict:
        """
        Verifica si el identifier (IP o user) ha excedido el rate limit
        
        Returns:
            {
                "allowed": bool,
                "remaining": int,
                "reset_at": int (timestamp),
                "retry_after": int (seconds)
            }
        """
        if not redis_client:
            # Si Redis no está disponible, permitir todo (fail-open)
            return {"allowed": True, "remaining": 999, "reset_at": 0, "retry_after": 0}
        
        limits = RateLimiter.LIMITS.get(limit_type, RateLimiter.LIMITS["api"])
        current_time = int(time.time())
        
        # Verificar límite por minuto
        key_minute = f"rate:{limit_type}:{identifier}:minute:{current_time // 60}"
        try:
            count_minute = redis_client.incr(key_minute)
            if count_minute == 1:
                redis_client.expire(key_minute, 60)
            
            per_minute = limits.get("per_minute", 300)
            if count_minute > per_minute:
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_at": (current_time // 60 + 1) * 60,
                    "retry_after": 60 - (current_time % 60)
                }
            
            # Verificar límite por hora
            key_hour = f"rate:{limit_type}:{identifier}:hour:{current_time // 3600}"
            count_hour = redis_client.incr(key_hour)
            if count_hour == 1:
                redis_client.expire(key_hour, 3600)
            
            per_hour = limits.get("per_hour", 5000)
            if count_hour > per_hour:
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_at": (current_time // 3600 + 1) * 3600,
                    "retry_after": 3600 - (current_time % 3600)
                }
            
            return {
                "allowed": True,
                "remaining": per_minute - count_minute,
                "reset_at": (current_time // 60 + 1) * 60,
                "retry_after": 0
            }
        
        except Exception as e:
            print(f"⚠️ Error en rate limiter: {e}")
            # Fail-open: permitir en caso de error
            return {"allowed": True, "remaining": 999, "reset_at": 0, "retry_after": 0}


class LoginThrottler:
    """
    Control de intentos fallidos de login
    Bloqueo progresivo: 5 intentos → 5 min, 10 intentos → 30 min, 15+ → 2 horas
    """
    
    @staticmethod
    def record_failed_login(identifier: str) -> Dict:
        """
        Registra un intento fallido de login
        
        Returns:
            {
                "blocked": bool,
                "attempts": int,
                "block_duration": int (seconds),
                "retry_after": int (timestamp)
            }
        """
        if not redis_client:
            return {"blocked": False, "attempts": 0, "block_duration": 0, "retry_after": 0}
        
        key = f"login_fails:{identifier}"
        try:
            # Incrementar contador
            attempts = redis_client.incr(key)
            
            # Primera tentativa: set TTL de 1 hora
            if attempts == 1:
                redis_client.expire(key, 3600)
            
            # Determinar bloqueo progresivo
            block_duration = 0
            if attempts >= 15:
                block_duration = 7200  # 2 horas
            elif attempts >= 10:
                block_duration = 1800  # 30 minutos
            elif attempts >= 5:
                block_duration = 300   # 5 minutos
            
            if block_duration > 0:
                # Establecer bloqueo temporal
                block_key = f"login_block:{identifier}"
                redis_client.setex(block_key, block_duration, attempts)
                
                return {
                    "blocked": True,
                    "attempts": attempts,
                    "block_duration": block_duration,
                    "retry_after": int(time.time()) + block_duration
                }
            
            return {
                "blocked": False,
                "attempts": attempts,
                "block_duration": 0,
                "retry_after": 0
            }
        
        except Exception as e:
            print(f"⚠️ Error en login throttler: {e}")
            return {"blocked": False, "attempts": 0, "block_duration": 0, "retry_after": 0}
    
    @staticmethod
    def check_login_block(identifier: str) -> Dict:
        """
        Verifica si un identifier está bloqueado por intentos fallidos
        """
        if not redis_client:
            return {"blocked": False, "attempts": 0, "retry_after": 0}
        
        block_key = f"login_block:{identifier}"
        try:
            ttl = redis_client.ttl(block_key)
            if ttl > 0:
                attempts = redis_client.get(block_key) or 0
                return {
                    "blocked": True,
                    "attempts": int(attempts),
                    "retry_after": int(time.time()) + ttl
                }
            
            # No bloqueado, verificar intentos actuales
            key = f"login_fails:{identifier}"
            attempts = redis_client.get(key) or 0
            return {
                "blocked": False,
                "attempts": int(attempts),
                "retry_after": 0
            }
        
        except Exception as e:
            print(f"⚠️ Error verificando bloqueo: {e}")
            return {"blocked": False, "attempts": 0, "retry_after": 0}
    
    @staticmethod
    def reset_failed_logins(identifier: str):
        """
        Resetear contador de intentos fallidos (después de login exitoso)
        """
        if not redis_client:
            return
        
        try:
            redis_client.delete(f"login_fails:{identifier}")
            redis_client.delete(f"login_block:{identifier}")
        except Exception as e:
            print(f"⚠️ Error reseteando intentos: {e}")

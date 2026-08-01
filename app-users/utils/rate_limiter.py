"""
Control de rate limiting y bloqueo progresivo para autenticación.
"""
import logging
import os
import time
from typing import Dict

import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configuración Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Cliente Redis para rate limiting
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=2,
    )
    redis_client.ping()
except Exception as e:
    logger.warning(f"Redis no disponible para rate limiting: {e}")
    redis_client = None


class RateLimiter:
    """
    Rate limiter para red interna con Redis.

    La validación se realiza por ventanas de tiempo configurables
    (minuto/hora/día) según tipo de tráfico.
    """

    WINDOW_SECONDS = {
        "per_minute": 60,
        "per_hour": 3600,
        "per_day": 86400,
    }

    LIMITS = {
        "login": {
            "per_minute": 10,
            "per_hour": 30,
            "per_day": 100,
        },
        "api": {
            "per_minute": 300,
            "per_hour": 5000,
        },
        "admin": {
            "per_minute": 100,
            "per_hour": 1000,
        },
    }

    @staticmethod
    def _allow_fallback_response() -> Dict:
        return {"allowed": True, "remaining": 999, "reset_at": 0, "retry_after": 0}

    @staticmethod
    def _window_key(limit_type: str, identifier: str, window_name: str, current_time: int) -> str:
        window_size = RateLimiter.WINDOW_SECONDS[window_name]
        bucket = current_time // window_size
        window_label = window_name.replace("per_", "")
        return f"rate:{limit_type}:{identifier}:{window_label}:{bucket}"

    @staticmethod
    def _increment_window_counter(key: str, window_seconds: int) -> Dict[str, int]:
        """
        Incrementa contador y garantiza TTL de la ventana.
        """
        count = redis_client.incr(key)
        ttl = redis_client.ttl(key)

        if count == 1 or ttl < 0:
            redis_client.expire(key, window_seconds)
            ttl = window_seconds

        return {"count": int(count), "ttl": int(ttl)}

    @staticmethod
    def check_rate_limit(identifier: str, limit_type: str = "api") -> Dict:
        """
        Verifica si un identificador excede los límites configurados.

        Returns:
            {
                "allowed": bool,
                "remaining": int,
                "reset_at": int (timestamp),
                "retry_after": int (seconds)
            }
        """
        if not redis_client:
            return RateLimiter._allow_fallback_response()

        limits = RateLimiter.LIMITS.get(limit_type, RateLimiter.LIMITS["api"])
        current_time = int(time.time())

        try:
            window_results = []
            for window_name, window_size in RateLimiter.WINDOW_SECONDS.items():
                limit_value = limits.get(window_name)
                if limit_value is None:
                    continue

                key = RateLimiter._window_key(limit_type, identifier, window_name, current_time)
                result = RateLimiter._increment_window_counter(key, window_size)
                count = result["count"]
                ttl = result["ttl"]

                if count > limit_value:
                    retry_after = max(ttl, 1)
                    logger.warning(
                        "Rate limit excedido: type=%s identifier=%s window=%s count=%s limit=%s retry_after=%ss",
                        limit_type,
                        identifier,
                        window_name,
                        count,
                        limit_value,
                        retry_after,
                    )
                    return {
                        "allowed": False,
                        "remaining": 0,
                        "reset_at": current_time + retry_after,
                        "retry_after": retry_after,
                    }

                window_results.append({
                    "remaining": max(limit_value - count, 0),
                    "ttl": max(ttl, 1),
                })

            if not window_results:
                logger.warning("Tipo de límite sin ventanas configuradas: %s", limit_type)
                return RateLimiter._allow_fallback_response()

            remaining = min(window["remaining"] for window in window_results)
            retry_after = min(window["ttl"] for window in window_results)
            return {
                "allowed": True,
                "remaining": remaining,
                "reset_at": current_time + retry_after,
                "retry_after": 0,
            }

        except Exception as e:
            logger.exception(
                "Error en rate limiter: type=%s identifier=%s error=%s",
                limit_type,
                identifier,
                e,
            )
            return RateLimiter._allow_fallback_response()


class LoginThrottler:
    """
    Control de intentos fallidos de login con bloqueo progresivo:
    5 intentos -> 5 minutos, 10 intentos -> 30 minutos, 15+ intentos -> 2 horas.
    """

    @staticmethod
    def record_failed_login(identifier: str) -> Dict:
        """
        Registra un intento fallido de login.

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
            attempts = redis_client.incr(key)

            if attempts == 1:
                redis_client.expire(key, 3600)

            block_duration = 0
            if attempts >= 15:
                block_duration = 7200
            elif attempts >= 10:
                block_duration = 1800
            elif attempts >= 5:
                block_duration = 300

            if block_duration > 0:
                block_key = f"login_block:{identifier}"
                redis_client.setex(block_key, block_duration, attempts)
                logger.warning(
                    "Login bloqueado temporalmente: identifier=%s attempts=%s block_duration=%ss",
                    identifier,
                    attempts,
                    block_duration,
                )
                return {
                    "blocked": True,
                    "attempts": attempts,
                    "block_duration": block_duration,
                    "retry_after": int(time.time()) + block_duration,
                }

            return {
                "blocked": False,
                "attempts": attempts,
                "block_duration": 0,
                "retry_after": 0,
            }

        except Exception as e:
            logger.exception("Error registrando login fallido: identifier=%s error=%s", identifier, e)
            return {"blocked": False, "attempts": 0, "block_duration": 0, "retry_after": 0}

    @staticmethod
    def check_login_block(identifier: str) -> Dict:
        """
        Verifica si un identificador está bloqueado por intentos fallidos.
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
                    "retry_after": int(time.time()) + ttl,
                }

            key = f"login_fails:{identifier}"
            attempts = redis_client.get(key) or 0
            return {
                "blocked": False,
                "attempts": int(attempts),
                "retry_after": 0,
            }

        except Exception as e:
            logger.exception("Error verificando bloqueo de login: identifier=%s error=%s", identifier, e)
            return {"blocked": False, "attempts": 0, "retry_after": 0}

    @staticmethod
    def reset_failed_logins(identifier: str):
        """
        Reinicia contador y bloqueo de login para el identificador.
        """
        if not redis_client:
            return

        try:
            redis_client.delete(f"login_fails:{identifier}")
            redis_client.delete(f"login_block:{identifier}")
        except Exception as e:
            logger.exception("Error reiniciando intentos fallidos: identifier=%s error=%s", identifier, e)

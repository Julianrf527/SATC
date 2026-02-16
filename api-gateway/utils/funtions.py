from fastapi import HTTPException
from dotenv import load_dotenv
from datetime import datetime, timedelta
from jose import jwt, jwe, JWTError
import os
import httpx
import json
import logging

# Importar el nuevo sistema de caché distribuido (Caso 4)
from utils.cache_manager import (
    get_from_cache,
    save_to_cache,
    invalidate_cache
)

load_dotenv()
SECRET_KEY_GATEWAY = os.getenv("SECRET_KEY_GATEWAY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
SECRET_GATEWAY = os.getenv("SECRET_GATEWAY")
USER_ROUTE = os.getenv("USER_ROUTE")

# Configurar logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Circuit Breaker (Caso 5 - Pendiente de implementación completa)
CIRCUIT_BREAKER = {}
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 30

NO_CACHE_PATHS = {
    "auth/logout",
    "user/delete",
    "admin/"
}

async def validate_session_jti(jti: str) -> bool:
    """
    Valida que el JTI de la sesión esté activo llamando al microservicio de usuarios.
    Retorna True si la sesión es válida, False en caso contrario.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{USER_ROUTE}/auth/validate-session",
                json={"jti": jti},
                headers={"X-Gateway-Token": SECRET_GATEWAY}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("valid", False)
            return False
    except Exception as e:
        # En caso de error, permitir el acceso para no bloquear el sistema
        # pero en producción podrías querer ser más estricto
        print(f"Error validando sesión: {e}")
        return False

def decode_jwt_token(access_token: str):
    """
    Decodifica el token JWT encriptado (JWE) y extrae user_id y permisos.
    Retorna un dict con 'user_id' y 'permissions' (lista de nombres de permisos).
    
    PRODUCCIÓN: Soporta tokens JWE encriptados con A256GCM.
    Fallback: Tokens JWT legacy sin encriptar (para migración).
    """
    if not access_token:
        raise HTTPException(401, "No token")
    
    try:
        # ═══════════════════════════════════════════════════════════════
        # PRODUCCIÓN: Desencriptar payload JWE
        # ═══════════════════════════════════════════════════════════════
        try:
            # Intentar desencriptar con JWE (tokens de producción)
            decrypted_payload = jwe.decrypt(access_token, SECRET_KEY_GATEWAY)
            payload = json.loads(decrypted_payload.decode('utf-8'))
        except Exception as jwe_error:
            # Fallback: Intentar decodificar JWT sin encriptar (tokens legacy)
            try:
                payload = jwt.decode(access_token, SECRET_KEY_GATEWAY, algorithms=[JWT_ALGORITHM])
                logger.warning(f"⚠️ Token sin encriptar detectado en gateway. Migrar a JWE.")
            except Exception as jwt_error:
                logger.error(f"❌ Error decodificando token: JWE={jwe_error}, JWT={jwt_error}")
                raise HTTPException(401, f"Token inválido: {str(jwe_error)}")
        
        user_id = payload.get("id")
        permisos = payload.get("permisos", [])
        jti = payload.get("jti")
        
        # Extraer solo los nombres de permisos (lista de strings)
        permission_names = [p.get("name") for p in permisos if isinstance(p, dict) and "name" in p]
        
        return {
            "user_id": user_id,
            "permissions": permission_names,
            "jti": jti
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado decodificando token: {e}")
        raise HTTPException(401, f"Invalid token: {str(e)}")

async def decode_jwt_token_with_session_validation(access_token: str):
    """
    Decodifica el token JWT, extrae user_id y permisos, y valida que la sesión esté activa.
    """
    token_data = decode_jwt_token(access_token)
    jti = token_data.get("jti")
    
    # Validar sesión solo si hay JTI (tokens nuevos)
    if jti:
        is_valid = await validate_session_jti(jti)
        if not is_valid:
            raise HTTPException(401, "Sesión inválida o expirada. Por favor, inicia sesión nuevamente.")
    
    return token_data

async def get_current_user_cached(access_token: str):
    """
    Obtiene los datos del usuario decodificados del token usando cache distribuido.
    Caso 4: Usa cache_manager para soportar estrategia local, Redis o sin caché.
    """
    if not access_token:
        raise HTTPException(401, "No token")
    
    # Intentar obtener del cache distribuido
    cached_data = await get_from_cache(access_token)
    if cached_data is not None:
        return cached_data
    
    # Si no está en cache, decodificar token
    token_data = decode_jwt_token(access_token)
    
    # Guardar en cache distribuido (TTL configurado en cache_manager)
    await save_to_cache(access_token, token_data)
    
    return token_data


async def invalidate_token_cache(access_token: str):
    """
    Invalida el token en el cache distribuido.
    Caso 4: Usa cache_manager para invalidación consistente.
    """
    await invalidate_cache(access_token)


async def get_current_user_smart(access_token: str, path: str):
    """
    Obtiene los datos del usuario desde el token.
    Para rutas críticas (logout, delete, admin), valida la sesión activa.
    Para otras rutas, usa cache sin validar sesión para mejor performance.
    """
    if any(path.startswith(critical) for critical in NO_CACHE_PATHS):
        # Rutas críticas: siempre validar sesión
        return await decode_jwt_token_with_session_validation(access_token)
    else:
        # Rutas normales: usar cache distribuido sin validar sesión (mejor performance)
        # La sesión se invalida en login y logout, no es necesario validar en cada request
        return await get_current_user_cached(access_token)


def is_circuit_open(service: str) -> bool:
    if service not in CIRCUIT_BREAKER:
        return False
    
    failures, last_failure = CIRCUIT_BREAKER[service]
    
    if datetime.now() - last_failure > timedelta(seconds=CIRCUIT_BREAKER_TIMEOUT):
        del CIRCUIT_BREAKER[service]
        return False
    
    return failures >= CIRCUIT_BREAKER_THRESHOLD


def record_failure(service: str):
    if service not in CIRCUIT_BREAKER:
        CIRCUIT_BREAKER[service] = (1, datetime.now())
    else:
        failures, _ = CIRCUIT_BREAKER[service]
        CIRCUIT_BREAKER[service] = (failures + 1, datetime.now())


def record_success(service: str):
    if service in CIRCUIT_BREAKER:
        del CIRCUIT_BREAKER[service]
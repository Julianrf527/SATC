from fastapi import HTTPException
from dotenv import load_dotenv
from datetime import datetime, timedelta
from jose import jwt, JWTError
import os
import time

load_dotenv()
SECRET_KEY_GATEWAY = os.getenv("SECRET_KEY_GATEWAY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")


TOKEN_CACHE = {}
TOKEN_CACHE_TTL = 120
CIRCUIT_BREAKER = {}
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 30

NO_CACHE_PATHS = {
    "auth/logout",
    "user/delete",
    "admin/"
}

def decode_jwt_token(access_token: str):
    """
    Decodifica el token JWT y extrae user_id y permisos.
    Retorna un dict con 'user_id' y 'permissions' (lista de nombres de permisos).
    """
    if not access_token:
        raise HTTPException(401, "No token")
    
    try:
        payload = jwt.decode(access_token, SECRET_KEY_GATEWAY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("id")
        permisos = payload.get("permisos", [])
        
        # Extraer solo los nombres de permisos (lista de strings)
        permission_names = [p.get("name") for p in permisos if isinstance(p, dict) and "name" in p]
        
        return {
            "user_id": user_id,
            "permissions": permission_names
        }
    except JWTError as e:
        raise HTTPException(401, f"Invalid token: {str(e)}")

def get_current_user_cached(access_token: str):
    if not access_token:
        raise HTTPException(401, "No token")
    
    if access_token in TOKEN_CACHE:
        cached_data, timestamp = TOKEN_CACHE[access_token]
        if time.time() - timestamp < TOKEN_CACHE_TTL:
            return cached_data
    
    # Decodificar token para obtener user_id y permisos
    token_data = decode_jwt_token(access_token)
    TOKEN_CACHE[access_token] = (token_data, time.time())
    
    if len(TOKEN_CACHE) > 500:
        TOKEN_CACHE.clear()
    
    return token_data


def invalidate_token_cache(access_token: str):
    TOKEN_CACHE.pop(access_token, None)


def get_current_user_smart(access_token: str, path: str):
    if any(path.startswith(critical) for critical in NO_CACHE_PATHS):
        return decode_jwt_token(access_token)
    return get_current_user_cached(access_token)


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
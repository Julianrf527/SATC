from fastapi import HTTPException
from dotenv import load_dotenv
from datetime import datetime, timedelta
from jose import jwe
import os
import json
import logging
from utils.redis_client import get_redis_client

load_dotenv()
SECRET_KEY_GATEWAY = os.getenv("SECRET_KEY_GATEWAY")
SECRET_GATEWAY = os.getenv("SECRET_GATEWAY")

logger = logging.getLogger(__name__)

CIRCUIT_BREAKER = {}
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 30


def decode_jwt_token(access_token: str) -> dict:
    """Desencripta el JWE y retorna el payload limpio."""
    if not access_token:
        raise HTTPException(401, "No autenticado")

    try:
        decrypted = jwe.decrypt(access_token, SECRET_KEY_GATEWAY)
        payload = json.loads(decrypted.decode('utf-8'))
    except Exception as e:
        logger.error(f"Error decodificando token: {e}")
        raise HTTPException(401, "Token inválido")

    user_id = payload.get("sub")
    jti = payload.get("jti")
    rol_id = payload.get("rol_id")

    if not user_id or not jti:
        raise HTTPException(401, "Token malformado")

    return {
        "user_id": user_id,
        "jti": jti,
        "rol_id": rol_id,
    }


async def validate_session_and_get_data(jti: str) -> list:
    """
    Valida que la sesión esté activa y retorna los datos.
    Solo el gateway habla con Redis.
    """
    r = get_redis_client()
    if r is None:
        logger.warning("Redis no disponible en gateway, omitiendo validación de sesión")
        return []

    try:
        async with r.pipeline() as pipe:
            pipe.get(f"session:{jti}")
            pipe.get(f"session_permisos:{jti}")
            pipe.get(f"session_nombre:{jti}")
            pipe.get(f"session_documento:{jti}")
            sesion_raw, permisos_raw, nombre_raw, documento_raw = await pipe.execute()

        if not sesion_raw:
            raise HTTPException(401, "Sesión expirada o inválida")

        return {"permisos": json.loads(permisos_raw) if permisos_raw else [],
                "nombre": nombre_raw if nombre_raw else "",
                "documento": documento_raw if documento_raw else "" }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validando sesión en Redis: {e}")
        raise HTTPException(500, "Error interno de autenticación")


async def get_current_user_smart(access_token: str) -> dict:
    """
    Decodifica el token, valida sesión y obtiene permisos desde Redis.
    Retorna token_data con permisos incluidos.
    """
    token_data = decode_jwt_token(access_token)
    data = await validate_session_and_get_data(token_data["jti"])
    token_data["permisos"] = data["permisos"]
    token_data["nombre"] = data["nombre"]
    token_data["documento"] = data["documento"]
    return token_data


# Circuit Breaker
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
from fastapi import HTTPException
from dotenv import load_dotenv
from datetime import datetime, timedelta
from jose import jwe
import os
import json
import time
import logging

load_dotenv()
SECRET_KEY_GATEWAY = os.getenv("SECRET_KEY_GATEWAY")
SECRET_GATEWAY = os.getenv("SECRET_GATEWAY")

logger = logging.getLogger(__name__)

CIRCUIT_BREAKER = {}
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 30


def decode_jwt_token(access_token: str) -> dict:
    """Desencripta el JWE y retorna el payload limpio.

    `jwe.decrypt` solo descifra: no valida ninguna claim. La expiración se
    verifica acá explícitamente — sin esto un token vencido seguiría siendo
    aceptado mientras el cliente conserve el valor de la cookie.
    """
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

    if not user_id or not jti or not rol_id:
        raise HTTPException(401, "Token malformado")

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or exp <= time.time():
        raise HTTPException(401, "Token expirado")

    return {
        "user_id": user_id,
        "jti": jti,
        "rol_id": rol_id,
    }


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
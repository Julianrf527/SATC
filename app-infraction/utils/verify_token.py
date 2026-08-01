from fastapi import APIRouter, Request, HTTPException
from dotenv import load_dotenv
from jose import jwt
import os
import json

router = APIRouter()

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
SECRET_GATEWAY = os.getenv("SECRET_GATEWAY")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")

# Secreto propio de cada microservicio que llama a app-infraction. Hoy
# ningún servicio consume un endpoint interno acá, así que este dict queda
# vacío a propósito -- si en el futuro se agrega un endpoint
# service-to-service, sumar acá el secreto del caller esperado (ver el mismo
# patrón ya en uso en app-users/app-docs/app-involved).
EXPECTED_CALLERS: dict[str, str] = {}

def verify_gateway_token(request: Request) -> dict:
    """Verifica el token del gateway y retorna user_id y rol_id."""
    gw_token = request.headers.get("x-gateway-token")
    if not gw_token or gw_token != SECRET_GATEWAY:
        raise HTTPException(status_code=403, detail="Gateway token inválido")

    user_id = request.headers.get("X-Gateway-User-Id")
    if not user_id:
        raise HTTPException(status_code=403, detail="User ID no enviado por el gateway")

    rol_id = request.headers.get("X-Gateway-Role-Id")
    if not rol_id:
        raise HTTPException(status_code=403, detail="Role ID no enviado por el gateway")

    return {
        "user_id": int(user_id),
        "rol_id": int(rol_id)
    }


def verify_service_token(request: Request) -> str:
    """Autentica al microservicio llamante vía X-Service-Token firmado y
    devuelve su identidad verificada.

    No se acepta X-Gateway-Token como alternativa: el gateway lo inyecta en
    TODAS las peticiones que reenvía, incluidas las anónimas, así que tomarlo
    como prueba de origen interno dejaría a cualquier cliente externo suplantar
    a un microservicio.

    La identidad la determina qué secreto de EXPECTED_CALLERS validó la firma,
    no el campo `service` del payload (que por sí solo no prueba nada) -- se
    exige que ambos coincidan, así una firma válida con identidad falseada
    también se rechaza.
    """
    if not EXPECTED_CALLERS:
        raise HTTPException(status_code=500, detail="No hay secretos de servicio configurados")

    service_token = request.headers.get("x-service-token")
    if not service_token:
        raise HTTPException(status_code=403, detail="Service token requerido")

    for caller_name, secret in EXPECTED_CALLERS.items():
        try:
            payload = jwt.decode(service_token, secret, algorithms=[JWT_ALGORITHM])
        except Exception:
            continue
        if payload.get("service") != caller_name:
            raise HTTPException(status_code=403, detail="Service token inválido")
        return caller_name

    raise HTTPException(status_code=403, detail="Service token inválido")

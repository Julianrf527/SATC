from fastapi import APIRouter, Request, HTTPException
from dotenv import load_dotenv
from satc_shared.auth import (
    ServiceTokenConfigError,
    ServiceTokenInvalid,
    ServiceTokenMissing,
    identify_caller,
)
import os
import json

router = APIRouter()

load_dotenv()
SECRET_GATEWAY = os.getenv("SECRET_GATEWAY")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Secreto propio de cada microservicio que llama a app-users: la identidad del
# caller la determina qué secreto validó la firma, no el campo `service` del
# payload.
EXPECTED_CALLERS: dict[str, str] = {
    name: secret
    for name, secret in {
        "sanctioning-service": os.getenv("SANCTIONING_SERVICE_SECRET"),
        "infraction-service": os.getenv("INFRACTION_SERVICE_SECRET"),
        "docs-service": os.getenv("DOCS_SERVICE_SECRET"),
        "involved-service": os.getenv("INVOLVED_SERVICE_SECRET"),
    }.items()
    if secret
}

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
        "rol_id": int(rol_id),
    }


def verify_service_token(request: Request) -> str:
    """Valida el X-Service-Token firmado de otro microservicio y devuelve la
    identidad verificada del caller (ej. "sanctioning-service").

    No se acepta el X-Gateway-Token como alternativa: el gateway lo inyecta en
    TODAS las peticiones que reenvía (incluidas las anónimas/públicas), así que
    usarlo como prueba de origen interno dejaría a cualquier cliente externo
    suplantar a un microservicio.

    La identidad la determina qué secreto validó la firma, no el campo
    `service` del payload (que por sí solo no prueba nada); se exige además que
    ambos coincidan, para rechazar una firma válida con identidad falseada.
    """
    try:
        return identify_caller(
            request.headers.get("x-service-token"), EXPECTED_CALLERS, algorithm=JWT_ALGORITHM
        )
    except ServiceTokenConfigError:
        raise HTTPException(status_code=500, detail="No hay secretos de servicio configurados")
    except ServiceTokenMissing:
        raise HTTPException(status_code=403, detail="Service token requerido")
    except ServiceTokenInvalid:
        raise HTTPException(status_code=403, detail="Service token inválido")

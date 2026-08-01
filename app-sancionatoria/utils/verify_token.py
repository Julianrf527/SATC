from fastapi import Request, HTTPException
from dotenv import load_dotenv
from jose import jwt
import os

load_dotenv()
SECRET_GATEWAY = os.getenv("SECRET_GATEWAY")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Secreto propio de cada microservicio que llama a app-sancionatoria. Vacío a
# propósito: ningún servicio consume endpoints internos acá. Al agregar uno,
# sumar el secreto del caller esperado (mismo patrón que app-users/app-docs).
EXPECTED_CALLERS: dict[str, str] = {}

def verify_gateway_token(request: Request) -> dict:
    """
    Verifica el token del gateway y retorna user_id y rol_id.
    """
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
    """
    Verifica que la petición venga de un microservicio autenticado mediante
    un token de servicio firmado (X-Service-Token), y devuelve la identidad
    verificada del caller.

    No sirve el X-Gateway-Token como alternativa: el gateway lo inyecta en
    TODAS las peticiones que reenvía, incluidas las anónimas, así que
    aceptarlo dejaría a cualquier cliente externo suplantar un microservicio.

    La identidad la determina qué secreto de EXPECTED_CALLERS validó la firma,
    no el campo `service` del payload -- se exige que ambos coincidan, así una
    firma válida con identidad falseada también se rechaza.
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

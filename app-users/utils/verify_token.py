from fastapi import APIRouter, Request, HTTPException
from dotenv import load_dotenv
import os
import json

router = APIRouter()

load_dotenv()
SECRET_GATEWAY = os.getenv("SECRET_GATEWAY")

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

    permission_raw = request.headers.get("X-Gateway-Permissions")
    if not permission_raw:
        raise HTTPException(status_code=403, detail="Permissions no enviado por el gateway")
    
    name = request.headers.get("X-Gateway-Name")
    if not name:
        raise HTTPException(status_code=403, detail="Name no enviado por el gateway")
    document = request.headers.get("X-Gateway-Document")
    if not document:
        raise HTTPException(status_code=403, detail="Document no enviado por el gateway")

    try:
        permisos = json.loads(permission_raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Permisos mal formateados")

    return {
        "user_id": int(user_id),
        "rol_id": int(rol_id),
        "nombre": name,
        "documento": document,
        "permisos": permisos
    }


def verify_service_token(request: Request) -> bool:
    """
    Verifica que la petición venga de un microservicio autenticado.
    Solo valida X-Gateway-Token, no requiere user_id.
    """
    gw_token = request.headers.get("x-gateway-token")
    if not gw_token or gw_token != SECRET_GATEWAY:
        raise HTTPException(status_code=403, detail="Gateway token inválido")
    return True

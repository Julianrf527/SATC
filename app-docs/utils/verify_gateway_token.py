from fastapi import APIRouter, Request, HTTPException
from dotenv import load_dotenv
import json
import os

router = APIRouter()

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
SECRET_GATEWAY = os.getenv("SECRET_GATEWAY")

def verify_gateway_token(request: Request):
    """
    Verifica el token del gateway y retorna el user_id.
    """
    # Verificar token del gateway
    gw_token = request.headers.get("X-Gateway-Token")
    if not gw_token or gw_token != SECRET_GATEWAY:
        raise HTTPException(status_code=403, detail="Gateway token inválido")

    # Extraer el user_id que envía el gateway
    user_id = request.headers.get("X-Gateway-User-Id")
    if not user_id:
        raise HTTPException(status_code=403, detail="User ID no enviado por el Gateway")

    return int(user_id)


def get_user_permissions(request: Request) -> list[str]:
    """
    Extrae la lista de permisos del usuario desde los headers del gateway.
    Retorna una lista de nombres de permisos.
    """
    permissions_json = request.headers.get("X-Gateway-Permissions")
    if not permissions_json:
        return []
    
    try:
        permissions = json.loads(permissions_json)
        return permissions if isinstance(permissions, list) else []
    except json.JSONDecodeError:
        return []


def verify_permission(request: Request, required_permission: str) -> int:
    """
    Verifica que el usuario tenga un permiso específico.
    Retorna el user_id si tiene el permiso, lanza HTTPException si no.
    
    Args:
        request: Request de FastAPI
        required_permission: Nombre del permiso requerido (ej: "documento_gestionar")
    
    Returns:
        int: user_id del usuario autenticado
    
    Raises:
        HTTPException: Si no tiene el permiso o el token es inválido
    """
    # Primero verificar el token del gateway
    gw_token = request.headers.get("X-Gateway-Token")
    if not gw_token or gw_token != SECRET_GATEWAY:
        raise HTTPException(status_code=403, detail="Gateway token inválido")

    # Obtener user_id
    user_id = request.headers.get("X-Gateway-User-Id")
    if not user_id:
        raise HTTPException(status_code=403, detail="User ID no enviado por el Gateway")

    # Obtener permisos del usuario
    permissions = get_user_permissions(request)
    
    # Verificar si tiene el permiso requerido
    if required_permission not in permissions:
        raise HTTPException(
            status_code=403, 
            detail=f"No cuenta con el permiso necesario: {required_permission}"
        )
    
    return int(user_id)
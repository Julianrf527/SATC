import hmac
import os

from dotenv import load_dotenv
from fastapi import HTTPException, Request

load_dotenv()
SECRET_GATEWAY = os.getenv("SECRET_GATEWAY")


def verify_gateway_token(request: Request) -> dict:
    """Verifica el token del gateway y retorna user_id y rol_id."""
    gw_token = request.headers.get("x-gateway-token")
    if not gw_token or not SECRET_GATEWAY or not hmac.compare_digest(gw_token, SECRET_GATEWAY):
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

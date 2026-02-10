from fastapi import HTTPException, Request
from jose import jwt
from dotenv import load_dotenv
import os

load_dotenv()
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")


def verify_service_jwt(request: Request) -> str:
    token = request.headers.get("X-Service-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Token requerido")
    
    try:
        payload = jwt.decode(token, SERVICE_SECRET_KEY, algorithms=["HS256"])
        return payload["service"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
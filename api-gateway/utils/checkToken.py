from fastapi import HTTPException, Cookie
from jose import jwt, JWTError
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_EXP_DAYS = os.getenv("JWT_EXP_DAYS")

def get_current_user(access_token: str = Cookie(None)):
    if access_token is None:
        # no hay cookie
        raise HTTPException(status_code=401, detail="Token faltante")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        # token corrupto/expirado
        raise HTTPException(status_code=401, detail="Token inválido")
    
    user_id = payload.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token sin ID")

    return user_id
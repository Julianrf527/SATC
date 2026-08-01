from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from routes import auth, notification, role, email
from routes import user_crud, user_profile, user_auditoria, user_internal
from utils.redis_session import init_redis, close_redis, redis_health_check
from db.database import init_db

import os


app = FastAPI()

@app.on_event("startup")
async def startup_event():
    try:
        await init_db()
        print("Tablas de user_db inicializadas correctamente")
        from db.seeds import seed_initial_data
        await seed_initial_data()
    except Exception as e:
        import traceback
        print(f"Error inicializando BD: {e}")
        print(f"Stacktrace completo: {traceback.format_exc()}")

    await init_redis()

@app.on_event("shutdown")
async def shutdown_event():
    await close_redis()

# Fuerza charset UTF-8: sin esto los acentos llegan mal a algunos clientes.
class CharsetMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if "application/json" in response.headers.get("content-type", ""):
            response.headers["content-type"] = "application/json; charset=utf-8"
        return response

app.add_middleware(CharsetMiddleware)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user_crud.router, prefix="/user", tags=["Users - Gestión"])
app.include_router(user_profile.router, prefix="/user", tags=["Users - Autoservicio"])
app.include_router(user_auditoria.router, prefix="/user", tags=["Users - Auditoría"])
app.include_router(user_internal.router, prefix="/user", tags=["Users - Interno"])
app.include_router(notification.router, prefix="/notification", tags=["Notifications"])
app.include_router(role.router, prefix="/role", tags=["Roles"])
app.include_router(email.router, prefix="/email", tags=["Email"])

@app.get("/health")
async def health_check():
    redis_info = await redis_health_check()
    
    return {
        "status": "healthy",
        "service": "app-users",
        "version": "1.0.0",
        "redis": redis_info
    }



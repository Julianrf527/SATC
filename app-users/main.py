from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import os
from routes import auth, notification, role, user, email
from utils.session_cleanup import start_cleanup_task
from utils.redis_session import get_redis, close_redis, redis_health_check

app = FastAPI()

# Startup event - iniciar tarea de limpieza de sesiones y conectar Redis
@app.on_event("startup")
async def startup_event():
    # Iniciar cleanup de sesiones PostgreSQL (fallback)
    start_cleanup_task()
    
    # Conectar Redis
    try:
        redis_client = await get_redis()
        if redis_client:
            print("Redis conectado exitosamente para sesiones")
        else:
            print("Redis deshabilitado - usando PostgreSQL para sesiones")
    except Exception as e:
        print(f"Error conectando Redis: {e}")

# Shutdown event - cerrar Redis
@app.on_event("shutdown")
async def shutdown_event():
    await close_redis()

# Middleware para forzar charset UTF-8 en todas las respuestas
class CharsetMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if "application/json" in response.headers.get("content-type", ""):
            response.headers["content-type"] = "application/json; charset=utf-8"
        return response

app.add_middleware(CharsetMiddleware)

# CORS configurable desde variables de entorno
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user.router, prefix="/user", tags=["Users"])
app.include_router(notification.router, prefix="/notification", tags=["Notifications"])
app.include_router(role.router, prefix="/role", tags=["Roles"])
app.include_router(email.router, prefix="/email", tags=["Email"])

# Health check endpoint (Caso 3: Alta Disponibilidad)
@app.get("/health")
async def health_check():
    # Obtener info de Redis
    redis_info = await redis_health_check()
    
    return {
        "status": "healthy",
        "service": "app-users",
        "version": "1.0.0",
        "redis": redis_info
    }



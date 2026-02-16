from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import os
# --- Endpoints ---
from routes import town, file, involved, document
# --- Scheduler de alertas ---
from db.deps import get_db 
from services.alertas_scheduler import configurar_scheduler_alertas, router as alertas_router

app = FastAPI()

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

configurar_scheduler_alertas(app, get_db)

# Rutas
app.include_router(town.router, prefix="/town", tags=["Town"])
app.include_router(file.router, prefix="/file", tags=["File"])
app.include_router(involved.router, prefix="/involved", tags=["Involved"])
app.include_router(document.router, prefix="/document", tags=["Documents"])
app.include_router(alertas_router)

# Health check endpoint (Caso 3: Alta Disponibilidad)
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "app-sanctioning",
        "version": "1.0.0"
    }



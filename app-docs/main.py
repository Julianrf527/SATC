from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Endpoints ---
from routes import docs, files

app = FastAPI()

# Startup event - inicializar BD
@app.on_event("startup")
async def startup_event():
    # Crear tablas desde models
    from db.database import init_db
    try:
        await init_db()
        print("Tablas de documentos_db inicializadas correctamente")
    except Exception as e:
        print(f"Error inicializando BD: {e}")

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

from db.deps import get_db
from services.cleanup_scheduler import configurar_scheduler_limpieza
configurar_scheduler_limpieza(app, get_db)

app.include_router(docs.router, prefix="/docs", tags=["Documents"])
app.include_router(files.router, prefix="/files", tags=["Files Hash Centralized"])

# Health check endpoint (Caso 3: Alta Disponibilidad)
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "app-docs",
        "version": "1.0.0"
    }

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from routes import documentos, revision, docs_service, files

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    from db.database import init_db
    try:
        await init_db()
        print("Tablas de documentos_db inicializadas correctamente")
    except Exception as e:
        print(f"Error inicializando BD: {e}")

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

from db.deps import get_db
from services.cleanup_scheduler import configurar_scheduler_limpieza
configurar_scheduler_limpieza(app, get_db)

# Los tres routers comparten el prefijo "/docs": el frontend los ve como una
# sola API, la división es solo organización interna.
app.include_router(documentos.router, prefix="/docs", tags=["Documents"])
app.include_router(revision.router, prefix="/docs", tags=["Documents - Revisión"])
app.include_router(docs_service.router, prefix="/docs", tags=["Documents - Service"])
app.include_router(files.router, prefix="/files", tags=["Files Hash Centralized"])

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "app-docs",
        "version": "1.0.0"
    }

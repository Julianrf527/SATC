import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Cada módulo de routes/ define `router = APIRouter()`. Todos se registran aquí
# (el orden de la lista es el orden de registro).
from routes import (
    catalogos,
    expediente_query,
    expediente_mutations,
    expediente_descarga,
    involucrados,
    actos,
    revision_documentos,
    mis_documentos,
    etapa_admite,
    etapa_concepto,
    etapa_requerimiento,
    etapa_decision,
    etapa_memorias,
    etapa_obras,
    tercero_interviniente,
    documentos_anexos,
    super_gestion,
    alertas,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Crea/migra las tablas y siembra los catálogos. Si falla, el servicio NO
    arranca (sin tablas cualquier petición fallaría)."""
    from db.database import init_db
    from db.seeds import seed_initial_data

    await init_db()
    logger.info("Tablas de recurso_db inicializadas correctamente")
    await seed_initial_data()
    yield


app = FastAPI(lifespan=lifespan)


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

app.include_router(catalogos.router, prefix="/catalogos", tags=["Catálogos"])
app.include_router(expediente_query.router, prefix="/expedientes", tags=["Expedientes"])
app.include_router(expediente_mutations.router, prefix="/expedientes", tags=["Expedientes"])
app.include_router(expediente_descarga.router, prefix="/expedientes", tags=["Expedientes - Descarga"])
app.include_router(involucrados.router, prefix="/involucrados", tags=["Involucrados"])
app.include_router(actos.router, prefix="/actos", tags=["Actos, comunicación y notificación"])
app.include_router(revision_documentos.router, prefix="/revision-documentos", tags=["Documentos - Revisión"])
app.include_router(mis_documentos.router, prefix="/mis-documentos", tags=["Mis actuaciones"])
app.include_router(etapa_admite.router, prefix="/etapas", tags=["Etapa 1 - Auto admite"])
app.include_router(etapa_concepto.router, prefix="/etapas", tags=["Etapa 2 - Concepto técnico"])
app.include_router(etapa_requerimiento.router, prefix="/etapas", tags=["Etapa 3 - Requerimiento"])
app.include_router(etapa_decision.router, prefix="/etapas", tags=["Etapa 4 - Decisión y recurso"])
app.include_router(etapa_memorias.router, prefix="/etapas", tags=["Etapa 5 - Memorias de cálculo"])
app.include_router(etapa_obras.router, prefix="/etapas", tags=["Etapa 6 - Recibo de obras"])
app.include_router(tercero_interviniente.router, prefix="/terceros", tags=["Tercero interviniente"])
app.include_router(documentos_anexos.router, prefix="/documentos-anexos", tags=["Documentos anexos"])
app.include_router(super_gestion.router, prefix="/super-gestion", tags=["Super gestión"])
app.include_router(alertas.router, prefix="/alertas", tags=["Alertas"])


@app.get("/health")
async def health_check():
    """200 si el servicio y su base de datos responden; 503 si la BD no."""
    from db.database import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check: la base de datos no responde: {e}")
        return JSONResponse(status_code=503, content={"status": "unhealthy", "service": "app-recurso"})
    return {"status": "healthy", "service": "app-recurso", "version": "1.0.0"}

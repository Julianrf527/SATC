from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import os

from routes import involved, town, reports, revision_informes
from routes import file_query, file_mutations, file_audit, file_alerts, file_download
from routes import stage_respuesta, stage_informe, stage_concepto, stage_cierre
from routes import acto_admin, acto_notificacion, acto_comunicacion
from db.deps import get_db
from services.alertas_scheduler import configurar_scheduler_alertas

app = FastAPI()

configurar_scheduler_alertas(app, get_db)

@app.on_event("startup")
async def startup_event():
    from db.database import init_db
    try:
        await init_db()
        print("Tablas de infracciones_db inicializadas correctamente")

        from db.seeds import seed_initial_data
        await seed_initial_data()
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

app.include_router(file_query.router, prefix="/expedientes", tags=["Expedientes"])
app.include_router(file_mutations.router, prefix="/expedientes", tags=["Expedientes"])
app.include_router(file_audit.router, prefix="/expedientes", tags=["Expedientes - Auditoría"])
app.include_router(file_alerts.router, prefix="/expedientes", tags=["Expedientes - Alertas"])
app.include_router(file_download.router, prefix="/expedientes", tags=["Expedientes - Descarga"])
app.include_router(involved.router, prefix="/involucrados", tags=["Involucrados"])
app.include_router(town.router, prefix="/municipios", tags=["Municipios"])
app.include_router(acto_admin.router, prefix="/actos", tags=["Acto Administrativo"])
app.include_router(acto_notificacion.router, prefix="/actos", tags=["Notificación"])
app.include_router(acto_comunicacion.router, prefix="/actos", tags=["Comunicación"])
app.include_router(stage_respuesta.router, prefix="/etapas", tags=["Etapas - Respuesta"])
app.include_router(stage_informe.router, prefix="/etapas", tags=["Etapas - Informe"])
app.include_router(stage_concepto.router, prefix="/etapas", tags=["Etapas - Concepto"])
app.include_router(stage_cierre.router, prefix="/etapas", tags=["Etapas - Cierre"])
app.include_router(reports.router, prefix="/informes", tags=["Informes técnicos"])
app.include_router(revision_informes.router, prefix="/revision-informes", tags=["Informes técnicos - Revisión"])


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "app-infracciones",
        "version": "1.0.0"
    }

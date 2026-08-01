from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import os

from routes import involved, town, reports
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

app.include_router(file_query.router, prefix="/file", tags=["File"])
app.include_router(file_mutations.router, prefix="/file", tags=["File"])
app.include_router(file_audit.router, prefix="/file", tags=["File - Auditoría"])
app.include_router(file_alerts.router, prefix="/file", tags=["File - Alertas"])
app.include_router(file_download.router, prefix="/file", tags=["File - Descarga"])
app.include_router(involved.router, prefix="/involved", tags=["Involved"])
app.include_router(town.router, prefix="/town", tags=["Town"])
app.include_router(acto_admin.router, prefix="/acto", tags=["Acto Administrativo"])
app.include_router(acto_notificacion.router, prefix="/acto", tags=["Notificación"])
app.include_router(acto_comunicacion.router, prefix="/acto", tags=["Comunicación"])
app.include_router(stage_respuesta.router, prefix="/stage", tags=["Stage - Respuesta"])
app.include_router(stage_informe.router, prefix="/stage", tags=["Stage - Informe"])
app.include_router(stage_concepto.router, prefix="/stage", tags=["Stage - Concepto"])
app.include_router(stage_cierre.router, prefix="/stage", tags=["Stage - Cierre"])
app.include_router(reports.router, prefix="/informes", tags=["Reports"])


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "app-infracciones",
        "version": "1.0.0"
    }

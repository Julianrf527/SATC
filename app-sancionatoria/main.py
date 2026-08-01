from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from routes import town, involucrado, stage, alerts
from routes import acto_admin, acto_comunicacion, acto_notificacion
from routes import expediente_crud, expediente_encargado, expediente_alertas, expediente_auditoria
from db.deps import get_db
from services.alertas_scheduler import configurar_scheduler_alertas
import os

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    from db.database import init_db
    try:
        await init_db()
        print("Tablas de expedientes_db inicializadas correctamente")

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

configurar_scheduler_alertas(app, get_db)

app.include_router(town.router, prefix="/town", tags=["Town"])
app.include_router(acto_admin.router, prefix="/acto", tags=["Acto Administrativo"])
app.include_router(acto_comunicacion.router, prefix="/acto", tags=["Comunicación"])
app.include_router(acto_notificacion.router, prefix="/acto", tags=["Notificación"])
app.include_router(stage.router, prefix="/stage", tags=["Stage"])
app.include_router(expediente_crud.router, prefix="/expediente", tags=["Expediente"])
app.include_router(expediente_encargado.router, prefix="/expediente", tags=["Expediente - Encargado"])
app.include_router(expediente_alertas.router, prefix="/expediente", tags=["Expediente - Alertas"])
app.include_router(expediente_auditoria.router, prefix="/expediente", tags=["Expediente - Auditoría"])
app.include_router(involucrado.router, prefix="/involved", tags=["Involved"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alertas"])

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "app-sanctioning",
        "version": "1.0.0"
    }



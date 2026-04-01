from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import os

from routes import involved

app = FastAPI()

# Startup event - inicializar BD
@app.on_event("startup")
async def startup_event():
    # Crear tablas desde models
    from db.database import init_db
    try:
        await init_db()
        print("Tablas de involucrados_db inicializadas correctamente")
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

app.include_router(involved.router, prefix="/involved", tags=["Involved"])


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "app-involved",
        "version": "1.0.0"
    }

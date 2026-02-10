from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# --- Endpoints ---
from routes import town, file, involved, document
# --- Scheduler de alertas ---
from db.deps import get_db 
from services.alertas_scheduler import configurar_scheduler_alertas, router as alertas_router

app = FastAPI()

# CORS: cambia esto en producción
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
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

# correr directamente: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)

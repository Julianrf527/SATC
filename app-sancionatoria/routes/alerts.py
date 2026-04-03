from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
import os
import logging

router = APIRouter()

# --------- DB MODELS ---------
from db.deps import get_db
from core.permission import Permission
from utils.verify_gateway_token import verify_gateway_token
from services.alertas_scheduler import tarea_envio_alertas_semanal

logger = logging.getLogger(__name__)

# -------- ENV ------------
load_dotenv()

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")

FILE_MANAGE = Permission.FILE_MANAGE
scheduler = AsyncIOScheduler()



@router.post("/send-weekly-report")
async def enviar_reporte_manual(
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Ejecuta el envío de alertas manualmente (solo admin)
    """
    try:
        user_id = verify_gateway_token(request)
        
        # Verificar si es admin (ajusta según tu lógica)
        # ... tu validación de admin aquí ...
        
        # Ejecutar en background
        background_tasks.add_task(tarea_envio_alertas_semanal, db)
        
        return {
            "ok": True,
            "mensaje": "Envío de alertas iniciado en segundo plano"
        }
        
    except Exception as e:
        logger.error(f"Error en envío manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/status")
async def estado_scheduler(request: Request):
    """Estado del scheduler"""
    try:
        verify_gateway_token(request)
        
        jobs = scheduler.get_jobs()
        jobs_info = [{
            "id": job.id,
            "nombre": job.name,
            "proxima_ejecucion": job.next_run_time.isoformat() if job.next_run_time else None
        } for job in jobs]
        
        return {
            "ok": True,
            "activo": scheduler.running,
            "tareas": jobs_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
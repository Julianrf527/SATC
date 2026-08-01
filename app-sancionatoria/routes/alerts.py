from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

router = APIRouter()

from db.deps import get_db_managed
from utils.verify_token import verify_gateway_token
from services.alertas_scheduler import tarea_envio_alertas_semanal, scheduler

load_dotenv()

@router.post("/send-weekly-report")
async def enviar_reporte_manual(
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    """Ejecuta el envío de alertas manualmente."""
    verify_gateway_token(request)

    background_tasks.add_task(tarea_envio_alertas_semanal, db)

    return {
        "ok": True,
        "mensaje": "Envío de alertas iniciado en segundo plano"
    }


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
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from dotenv import load_dotenv
import httpx
import os
import logging


# --------- DB MODELS ---------
from db.models.expediente import Expediente
from services.usuarios import obtener_usuarios_por_permiso
from services.alertas import calcular_alertas_expediente


logger = logging.getLogger(__name__)

# -------- ENV ------------
load_dotenv()
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")

scheduler = AsyncIOScheduler()

#  ----------  UTILS  ------------
from utils.generate_service_jwt import generate_service_jwt

async def obtener_alertas_usuario(user_id: int, db: AsyncSession) -> dict:
    """
    Obtiene las alertas para un usuario específico usando tu lógica existente
    """
    try:
        stmt = select(Expediente.radicado).where(Expediente.encargado_id == user_id)
        result = await db.execute(stmt)
        expedientes = result.scalars().all()

        if not expedientes:
            return None  

        alertas_totales = {}
        fecha_hoy = date.today()

        for radicado in expedientes:
            alertas = await calcular_alertas_expediente(radicado, db, fecha_hoy)
            if alertas:
                alertas_totales[radicado] = alertas

        if not alertas_totales:
            return None  # Sin alertas = no enviar email

        # Calcular estadísticas (igual que tu endpoint)
        estadisticas = {
            "verde": 0,
            "amarillo": 0,
            "rojo": 0,
            "vencido": 0
        }
        
        for radicado, alertas_expediente in alertas_totales.items():
            for alerta in alertas_expediente.values():
                estado = alerta["semaforo"]["estado"]
                estadisticas[estado] += 1

        return {
            "alertas": alertas_totales,
            "total_expedientes": len(expedientes),
            "expedientes_con_alertas": len(alertas_totales),
            "estadisticas_semaforo": estadisticas
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo alertas para usuario {user_id}: {e}")
        return None


async def enviar_reporte_alertas(email: str, alertas_data: dict) -> bool:
    """Envía el reporte de alertas usando la API de users"""
    try:
        service_token = generate_service_jwt("expedientes-service", SERVICE_SECRET_KEY)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_GATEWAY_URL}/users/email/send-alert-report",
                headers={"X-Service-Token": service_token},
                json={
                    "title": "Reporte Semanal de Alertas - Sistema Sancionatorio",
                    "emails": [email],
                    "alertas_data": alertas_data
                }
            )
            
            return response.status_code == 200
                
    except Exception as e:
        logger.error(f"Error enviando email a {email}: {e}")
        return False


async def tarea_envio_alertas_semanal(db: AsyncSession):
    """
    Tarea que se ejecuta automáticamente cada semana
    """
    logger.info("=" * 60)
    logger.info("🚀 Iniciando envío semanal de alertas...")
    logger.info("=" * 60)
    
    try:
        # Obtener todos los usuarios con permiso de expedientes
        usuarios = await obtener_usuarios_por_permiso("expedientes")
        
        if not usuarios:
            logger.warning("⚠️ No hay usuarios con permiso de expedientes")
            return
        
        logger.info(f"📧 Procesando {len(usuarios)} usuarios...")
        
        enviados = 0
        sin_alertas = 0
        errores = 0
        
        for user_id, datos in usuarios.items():
            nombre = datos.get("nombre")
            email = datos.get("correo")
            
            if not email:
                logger.warning(f"  ⚠️ Usuario {nombre} sin correo")
                continue
                
            try:
                logger.info(f"  👤 Procesando: {nombre} ({email})")
                
                # Obtener alertas del usuario
                alertas_data = await obtener_alertas_usuario(user_id, db)
                
                if alertas_data:
                    # Hay alertas, enviar email
                    resultado = await enviar_reporte_alertas(email, alertas_data)
                    if resultado:
                        expedientes_con_alertas = alertas_data.get("expedientes_con_alertas", 0)
                        logger.info(f"    ✅ Email enviado ({expedientes_con_alertas} expedientes)")
                        enviados += 1
                    else:
                        logger.error(f"    ❌ Fallo al enviar email")
                        errores += 1
                else:
                    logger.info(f"    ℹ️ Sin alertas pendientes")
                    sin_alertas += 1
                    
            except Exception as e:
                logger.error(f"    ❌ Error procesando usuario {user_id}: {e}")
                errores += 1
        
        # Resumen
        logger.info("=" * 60)
        logger.info("📊 RESUMEN DEL ENVÍO")
        logger.info(f"  ✅ Emails enviados: {enviados}")
        logger.info(f"  ℹ️ Sin alertas: {sin_alertas}")
        logger.info(f"  ❌ Errores: {errores}")
        logger.info(f"  📧 Total: {len(usuarios)}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error en tarea de envío: {e}", exc_info=True)


async def ejecutar_tarea_con_db(get_db):
    """Helper para ejecutar la tarea con DB"""
    async for db in get_db():
        await tarea_envio_alertas_semanal(db)
        break


def configurar_scheduler_alertas(app, get_db):
    """
    Configura el scheduler en FastAPI
    """
    @app.on_event("startup")
    async def start_scheduler():
        # Ejecutar cada lunes a las 8:00 AM
        scheduler.add_job(
            func=lambda: ejecutar_tarea_con_db(get_db),
            trigger=CronTrigger(
                day_of_week="mon",
                hour=8,
                minute=0,
                timezone="America/Bogota"
            ),
            id="envio_alertas_semanal",
            name="Envío semanal de alertas",
            replace_existing=True,
        )
        
        scheduler.start()
        logger.info("✅ Scheduler iniciado - Lunes 8:00 AM")
    
    @app.on_event("shutdown")
    async def stop_scheduler():
        scheduler.shutdown()
        logger.info("⛔ Scheduler detenido")


# ============================================
# Router para endpoints manuales
# ============================================

from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
from db.deps import get_db
from utils.verify_gateway_token import verify_gateway_token

router = APIRouter(prefix="/alerts", tags=["alertas"])


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
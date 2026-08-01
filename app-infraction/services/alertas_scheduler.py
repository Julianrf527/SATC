from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from dotenv import load_dotenv
import httpx
import os
import logging


#DB MODELS Y PERMISOS
from db.models.expediente import Expediente
from services.users import get_users_by_permission
from routes.file_alerts import _calcular_alertas_expediente_infraccion
from core.permission import Permission

load_dotenv()
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://app-users:8001")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")
FILE_MANAGE = Permission.FILE_MANAGE
scheduler = AsyncIOScheduler()

#LOGGER
logger = logging.getLogger(__name__)

#FUNCIONES HELPER
from utils.generate_service_jwt import generate_service_jwt


async def obtener_alertas_usuario(user_id: int, db: AsyncSession) -> dict:
    """
    Obtiene las alertas de todos los expedientes de infracción a cargo del abogado.
    """
    try:
        stmt = select(Expediente.id, Expediente.radicado).where(
            Expediente.abogado_responsable_id == user_id
        )
        result = await db.execute(stmt)
        expedientes = result.all()

        if not expedientes:
            return None

        alertas_totales = {}
        fecha_hoy = date.today()

        for expediente_id, radicado in expedientes:
            alertas = await _calcular_alertas_expediente_infraccion(expediente_id, db, fecha_hoy)
            if alertas:
                alertas_totales[radicado] = alertas

        if not alertas_totales:
            return None  # Sin alertas = no enviar email

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
    """Envía el reporte de alertas llamando directo a app-users (east-west, sin pasar por el gateway)"""
    try:
        service_token = generate_service_jwt("infraction-service", SERVICE_SECRET_KEY)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{USER_SERVICE_URL}/email/send-alert-report",
                params={"title": "Reporte Semanal de Alertas - Sistema de Infracciones"},
                headers={"X-Service-Token": service_token},
                json={
                    "emails": [email],
                    "alertas_data": alertas_data
                }
            )

            return response.status_code == 200

    except Exception as e:
        logger.error(f"Error enviando email a {email}: {e}")
        return False


async def tarea_envio_alertas_semanal(db: AsyncSession):

    try:
        # Obtener todos los usuarios con permiso de gestión de infracciones
        usuarios = await get_users_by_permission(FILE_MANAGE)

        if not usuarios:
            logger.warning("No hay usuarios con permiso de infracciones")
            return

        logger.info(f"Procesando {len(usuarios)} usuarios...")

        enviados = 0
        sin_alertas = 0
        errores = 0

        for user_id, datos in usuarios.items():
            nombre = datos.get("nombre")
            email = datos.get("correo")

            if not email:
                logger.warning(f"  Usuario {nombre} sin correo")
                continue

            try:
                logger.info(f"  Procesando: {nombre} ({email})")

                alertas_data = await obtener_alertas_usuario(user_id, db)

                if alertas_data:
                    resultado = await enviar_reporte_alertas(email, alertas_data)
                    if resultado:
                        expedientes_con_alertas = alertas_data.get("expedientes_con_alertas", 0)
                        logger.info(f"    Email enviado ({expedientes_con_alertas} expedientes)")
                        enviados += 1
                    else:
                        logger.error(f"    Fallo al enviar email")
                        errores += 1
                else:
                    logger.info(f"    Sin alertas pendientes")
                    sin_alertas += 1

            except Exception as e:
                logger.error(f"    Error procesando usuario {user_id}: {e}")
                errores += 1

        logger.info("=" * 60)
        logger.info("RESUMEN DEL ENVIO - INFRACCIONES")
        logger.info(f"  Emails enviados: {enviados}")
        logger.info(f"  Sin alertas: {sin_alertas}")
        logger.info(f"  Errores: {errores}")
        logger.info(f"  Total: {len(usuarios)}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error en tarea de envio: {e}", exc_info=True)


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
            id="envio_alertas_semanal_infraccion",
            name="Envío semanal de alertas - Infracciones",
            replace_existing=True,
        )

        scheduler.start()
        logger.info("Scheduler de alertas de infracciones iniciado - Lunes 8:00 AM")

    @app.on_event("shutdown")
    async def stop_scheduler():
        scheduler.shutdown()
        logger.info("⛔ Scheduler de alertas de infracciones detenido")

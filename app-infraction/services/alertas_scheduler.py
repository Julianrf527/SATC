from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os
import logging


#DB MODELS Y PERMISOS
from db.models.expediente import Expediente
from db.models.envio_alertas_semanal import EnvioAlertasSemanal
from services.users import get_users_by_permission, users_client
from services.alertas import calcular_alertas_expedientes
from core.permission import Permission

load_dotenv()
FILE_MANAGE = Permission.FILE_MANAGE
scheduler = AsyncIOScheduler()

#LOGGER
logger = logging.getLogger(__name__)

#FUNCIONES HELPER


async def obtener_alertas_usuario(user_id: int, db: AsyncSession) -> dict:
    """
    Obtiene las alertas de todos los expedientes de infracción a cargo del abogado.
    """
    try:
        stmt = select(Expediente.id, Expediente.radicado).where(
            Expediente.abogado_responsable_id == user_id
        ).order_by(Expediente.id)
        result = await db.execute(stmt)
        expedientes = result.all()

        if not expedientes:
            return None

        alertas_totales = {}
        fecha_hoy = date.today()

        por_expediente = await calcular_alertas_expedientes([e[0] for e in expedientes], db, fecha_hoy)
        for expediente_id, radicado in expedientes:
            alertas = por_expediente.get(expediente_id)
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
        await users_client.send_alert_report(
            [email], alertas_data,
            title="Reporte Semanal de Alertas - Sistema de Infracciones",
        )
        return True
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
                        logger.error("    Fallo al enviar email")
                        errores += 1
                else:
                    logger.info("    Sin alertas pendientes")
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


def lunes_de(dia: date) -> date:
    return dia - timedelta(days=dia.weekday())


async def reclamar_envio(db: AsyncSession, semana: date) -> bool:
    """True si este proceso queda a cargo del envío de ``semana``.

    Gunicorn corre varios workers y cada uno tiene su scheduler: todos
    disparan el job a la misma hora. El INSERT sobre la clave primaria lo
    gana uno solo; los demás (y un reinicio posterior) no envían.
    """
    fila = await db.execute(
        pg_insert(EnvioAlertasSemanal)
        .values(semana=semana)
        .on_conflict_do_nothing(index_elements=["semana"])
        .returning(EnvioAlertasSemanal.semana)
    )
    reclamado = fila.scalar_one_or_none() is not None
    await db.commit()
    return reclamado


async def ejecutar_envio_semanal(get_db) -> bool:
    """Job del lunes: envía el reporte si este worker reclama la semana.
    Devuelve si envió."""
    async for db in get_db():
        semana = lunes_de(datetime.now(ZoneInfo("America/Bogota")).date())
        if not await reclamar_envio(db, semana):
            logger.info(f"Reporte semanal de alertas {semana} ya enviado por otro proceso")
            return False
        await tarea_envio_alertas_semanal(db)
        return True
    return False


def configurar_scheduler_alertas(app, get_db):
    """Registra el envío semanal (lunes 8:00, America/Bogota).

    El job debe ser una función ``async``: APScheduler solo espera las
    corrutinas si la función registrada es corrutina (con una ``lambda`` que
    devuelve una corrutina, esta se crea y nunca se ejecuta).

    ``ALERTAS_CORREO_SEMANAL=false`` lo apaga (p. ej. en entornos de prueba),
    igual que en app-recurso.
    """
    if os.getenv("ALERTAS_CORREO_SEMANAL", "true").lower() == "false":
        logger.info("Correo semanal de alertas de infracciones desactivado (ALERTAS_CORREO_SEMANAL=false)")
        return

    async def job_envio_semanal():
        await ejecutar_envio_semanal(get_db)

    @app.on_event("startup")
    async def start_scheduler():
        scheduler.add_job(
            job_envio_semanal,
            trigger=CronTrigger(day_of_week="mon", hour=8, minute=0, timezone="America/Bogota"),
            id="envio_alertas_semanal_infraccion",
            name="Envío semanal de alertas - Infracciones",
            replace_existing=True,
            # Si el servicio estaba caído o reiniciando a las 8:00, se envía al
            # volver (hasta 12 h después); varias ejecuciones atrasadas = una.
            misfire_grace_time=12 * 3600,
            coalesce=True,
            max_instances=1,
        )
        scheduler.start()
        logger.info("Scheduler de alertas de infracciones iniciado - Lunes 8:00 AM")

    @app.on_event("shutdown")
    async def stop_scheduler():
        scheduler.shutdown()
        logger.info("Scheduler de alertas de infracciones detenido")

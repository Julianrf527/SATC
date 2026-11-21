from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Iterable, Optional
from dotenv import load_dotenv
import os
import logging


#DB MODELS Y PERMISOS
from services.users import get_users_by_permission, users_client
from services.alertas import agrupar_alertas, calcular_alertas_activas, hoy_bogota
from satc_shared.alertas import permisos_de_roles
import services.etapas as etapas_mod
from core.permission import Permission

load_dotenv()
FILE_MANAGE = Permission.FILE_MANAGE
# Quienes pueden ser responsables de una alerta: abogado (gestionar),
# técnico / líder técnico (conceptos), líder de proyecto (revisa actos) y
# quien asigna visitas. Cada uno recibe sus "Mis alertas".
PERMISOS_DESTINATARIOS = (
    Permission.FILE_MANAGE,
    Permission.TECNICO,
    Permission.LIDER_TECNICO,
    Permission.LIDER_PROYECTO,
    Permission.ASSIGN_REPORTS,
)
scheduler = AsyncIOScheduler()

#LOGGER
logger = logging.getLogger(__name__)

#FUNCIONES HELPER


async def obtener_alertas_usuario(
    user_id: int,
    db: AsyncSession,
    permisos: Optional[Iterable[str]] = None,
    calculadas: Optional[tuple[dict, dict]] = None,
) -> Optional[dict]:
    """"Mis alertas" del usuario para el reporte semanal: las que le tocan
    como persona (``encargado_id``) o por rol (``roles_responsables``), igual
    que la pestaña. ``None`` si no tiene ninguna (no se envía correo).

    ``permisos``: los del usuario entre los roles de las alertas; si no
    llegan, se consultan. ``calculadas``: resultado de
    ``calcular_alertas_activas`` para no recalcular por cada destinatario.
    """
    try:
        radicados, por_expediente = calculadas or await calcular_alertas_activas(db, hoy_bogota())
        if permisos is None:
            roles = permisos_de_roles(a for alertas in por_expediente.values() for a in alertas.values())
            permisos = {p for p in roles if await etapas_mod.verify_permission(user_id, p)}

        alertas_totales = agrupar_alertas(radicados, por_expediente, user_id, permisos, solo_mias=True)
        if not alertas_totales:
            return None  # Sin alertas = no enviar email

        estadisticas = {"verde": 0, "amarillo": 0, "rojo": 0, "vencido": 0}
        for alertas_expediente in alertas_totales.values():
            for alerta in alertas_expediente.values():
                estadisticas[alerta["semaforo"]["estado"]] += 1

        return {
            "alertas": alertas_totales,
            "total_expedientes": len(alertas_totales),
            "expedientes_con_alertas": len(alertas_totales),
            "estadisticas_semaforo": estadisticas,
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
        # Destinatarios: todo el que pueda ser responsable de una alerta, con
        # sus permisos de rol (de los mismos listados, sin consultar uno a uno).
        usuarios: dict = {}
        permisos_por_usuario: dict = {}
        for permiso in PERMISOS_DESTINATARIOS:
            for uid, datos in (await get_users_by_permission(permiso)).items():
                usuarios.setdefault(uid, datos)
                permisos_por_usuario.setdefault(uid, set()).add(permiso)

        if not usuarios:
            logger.warning("No hay usuarios con permisos de infracciones")
            return

        calculadas = await calcular_alertas_activas(db, hoy_bogota())

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

                alertas_data = await obtener_alertas_usuario(
                    user_id, db, permisos=permisos_por_usuario[user_id], calculadas=calculadas
                )

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

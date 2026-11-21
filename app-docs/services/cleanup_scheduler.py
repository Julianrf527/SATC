import asyncio
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
import logging

from db.models.file_hash import FileHash
from utils.minio_client import delete_file_from_minio

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Horas que un archivo sin uso se conserva desde su última subida. Cubre el
# tiempo entre que se sube y que el módulo lo asocia (increment-usage): sin esto,
# un archivo subido a las 23:58 se borraba a las 23:59 aunque se asociara después.
GRACIA_HORAS = float(os.getenv("LIMPIEZA_GRACIA_HORAS", "24"))

async def tarea_limpieza_temporales(db: AsyncSession):
    """
    Elimina los archivos sin uso (numero_usos = 0) cuya última subida supera
    el periodo de gracia: el registro en la BD y el objeto en MinIO.
    """
    logger.info("=" * 60)
    logger.info("Iniciando tarea de limpieza de archivos sin uso...")

    try:
        # with_for_update bloquea las filas para que un increment_file_usage concurrente
        # (otro upload reutilizando el mismo hash) no quede huérfano si lo borramos aquí.
        # skip_locked evita esperar archivos que ya están siendo usados en este instante.
        limite = datetime.now(ZoneInfo("America/Bogota")) - timedelta(hours=GRACIA_HORAS)
        stmt = (
            select(FileHash)
            .where(
                FileHash.numero_usos == 0,
                func.coalesce(FileHash.ultima_subida, FileHash.created_at) < limite,
            )
            .with_for_update(skip_locked=True)
        )
        result = await db.execute(stmt)
        sin_uso = result.scalars().all()

        if not sin_uso:
            logger.info("No hay archivos sin uso para eliminar.")
            return

        eliminados_db = 0
        eliminados_minio = 0

        for file in sin_uso:
            # Eliminar el objeto de MinIO
            # file.file_url viene con el prefijo "bucket/object_name",
            # delete_file_from_minio se encarga de limpiarlo internamente.
            minio_resultado = await asyncio.to_thread(delete_file_from_minio, file.file_url)
            
            if minio_resultado.get("ok", False):
                 eliminados_minio += 1
            else:
                 logger.warning(f"Atencion con MinIO ({file.file_url}): {minio_resultado.get('message')}")
            
            # Independientemente si en MinIO falló (ej. no existía), lo eliminamos de la DB
            await db.delete(file)
            eliminados_db += 1
            
        await db.commit()
        
        logger.info(f"Limpieza completada: {eliminados_minio} archivos borrados en MinIO, {eliminados_db} registros borrados en DB.")
        
    except Exception as e:
        logger.error(f"Error en tarea de limpieza: {e}", exc_info=True)
        await db.rollback()

async def ejecutar_tarea_con_db(get_db):
    """Helper para ejecutar la tarea de limpieza con DB"""
    async for db in get_db():
        await tarea_limpieza_temporales(db)
        break

def configurar_scheduler_limpieza(app, get_db):
    """
    Configura el scheduler en FastAPI
    """
    @app.on_event("startup")
    async def start_scheduler():
        # Ejecutar todos los días a las 23:59 (11:59 pm)
        scheduler.add_job(
            func=lambda: ejecutar_tarea_con_db(get_db),
            trigger=CronTrigger(
                hour=23,
                minute=59,
                timezone="America/Bogota"
            ),
            id="limpieza_archivos_sin_uso",
            name="Limpieza diaria de archivos sin uso",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Scheduler de limpieza de documentos configurado.")

    @app.on_event("shutdown")
    async def stop_scheduler():
        scheduler.shutdown()

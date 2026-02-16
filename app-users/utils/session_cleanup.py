"""
Background task para limpiar sesiones expiradas periódicamente
Evita acumulación de sesiones inactivas en la base de datos
"""
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import delete
from db.database import SessionLocal
from db.models.sesion_activa import SesionActiva
import logging

logger = logging.getLogger(__name__)

async def cleanup_expired_sessions():
    """
    Elimina sesiones inactivas de más de 24 horas
    Se ejecuta cada 1 hora en background
    """
    while True:
        try:
            async with SessionLocal() as db:
                # Calcular timestamp de hace 24 horas
                expiration_time = datetime.now(ZoneInfo("America/Bogota")) - timedelta(hours=24)
                
                # Eliminar sesiones antiguas
                stmt = delete(SesionActiva).where(
                    SesionActiva.fecha_ultimo_uso < expiration_time
                )
                result = await db.execute(stmt)
                await db.commit()
                
                deleted_count = result.rowcount
                if deleted_count > 0:
                    logger.info(f"✅ Limpieza de sesiones: {deleted_count} sesiones antiguas eliminadas")
                
        except Exception as e:
            logger.error(f"❌ Error en limpieza de sesiones: {e}")
        
        # Esperar 1 hora antes de la próxima limpieza
        await asyncio.sleep(3600)  # 1 hora

def start_cleanup_task():
    """Inicia la tarea de limpieza en background"""
    asyncio.create_task(cleanup_expired_sessions())
    logger.info("🔄 Tarea de limpieza de sesiones iniciada (cada 1 hora)")

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
import logging
from zoneinfo import ZoneInfo

from db.models.auditoria import Auditoria

logger = logging.getLogger(__name__)

async def insert_auditoria(
    db: AsyncSession,
    usuario_id: int | None,
    tipo_evento: str,
    resultado: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    detalle: str | None = None,
    datos_anteriores: dict | None = None,
    datos_nuevos: dict | None = None,
):
    try:
        stmt = insert(Auditoria).values(
            usuario_id=usuario_id,
            tipo_evento=tipo_evento,
            resultado=resultado,
            ip_address=ip_address,
            user_agent=user_agent,
            fecha=datetime.now(ZoneInfo("America/Bogota")),
            detalle=detalle,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
        ).returning(Auditoria.id)

        result = await db.execute(stmt)
        inserted_id = result.scalar()
        return {"ok": True, "id": inserted_id}
    except Exception as e:
        logger.error(f"Error insertando log de auditoría: {e}")
        return {"ok": False, "error": str(e)}

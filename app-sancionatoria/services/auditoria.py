"""
Operaciones de auditoría y utilidades comunes para el módulo sancionatorio.
La lógica de etapas vive en stage.py, no acá.
"""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import logging

from db.models.auditoria import Auditoria

load_dotenv()
logger = logging.getLogger(__name__)


async def insert_log(
    db: AsyncSession,
    tipo_evento: str,
    resultado: str,
    usuario_id: int | None = None,
    expediente_id: int | None = None,
    expediente_radicado: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    detalle: str | None = None,
    datos_anteriores: dict | None = None,
    datos_nuevos: dict | None = None,
):
    """Inserta el registro de auditoría. Si falla, hace rollback y lanza
    HTTPException(500) — el caller no necesita chequear un 'ok' manualmente."""
    try:
        stmt = insert(Auditoria).values(
            usuario_id=usuario_id,
            tipo_evento=tipo_evento,
            resultado=resultado,
            expediente_id=expediente_id,
            expediente_radicado=expediente_radicado,
            ip_address=ip_address,
            user_agent=user_agent,
            detalle=detalle,
            fecha=datetime.now(ZoneInfo("America/Bogota")),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
        ).returning(Auditoria.id)
        result = await db.execute(stmt)
        return {"ok": True, "id": result.scalar()}
    except Exception as e:
        logger.error(f"Error en insert_log: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar registro de auditoría: {e}")


async def insert_auditoria(
    db: AsyncSession,
    tipo_evento: str,
    resultado: str,
    usuario_id: int | None = None,
    expediente_id: int | None = None,
    expediente_radicado: str | None = None,
    datos_anteriores: dict | None = None,
    datos_nuevos: dict | None = None,
    detalle: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    return await insert_log(
        db=db,
        tipo_evento=tipo_evento,
        resultado=resultado,
        usuario_id=usuario_id,
        expediente_id=expediente_id,
        expediente_radicado=expediente_radicado,
        ip_address=ip_address,
        user_agent=user_agent,
        detalle=detalle,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
    )

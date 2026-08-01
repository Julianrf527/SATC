from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import logging
import os


from db.models.auditoria import Auditoria


load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
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
    if not tipo_evento or not resultado:
        return {"ok": False, "error": "tipo_evento y resultado son obligatorios"}

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
    inserted_id = result.scalar()
    return {"ok": True, "id": inserted_id}


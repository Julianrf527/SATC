from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo
import logging


# -------- MODELS ------------
from db.models.auditoria import Auditoria

# ---------- LOGGER ------------

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
            expediente_id=expediente_id,
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
    except Exception as e:
        return {"ok": False, "error": str(e)}


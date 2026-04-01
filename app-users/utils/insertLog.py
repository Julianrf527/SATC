from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from zoneinfo import ZoneInfo

from db.models.auditoria import Auditoria


async def insert_auditoria(
    db: AsyncSession,
    usuario_id: int | None,
    tipo_evento: str,
    resultado: str = "EXITOSO",
    detalle: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    datos_anteriores: dict | None = None,
    datos_nuevos: dict | None = None,
    documento_usuario: str | None = None,
    nombre_usuario: str | None = None,
):
    try:
        stmt = insert(Auditoria).values(
            usuario_id=usuario_id,
            documento_usuario=documento_usuario,
            nombre_usuario=nombre_usuario,
            tipo_evento=tipo_evento,
            resultado=resultado,
            detalle=detalle,
            ip_address=ip_address,
            user_agent=user_agent,
            fecha=datetime.now(ZoneInfo("America/Bogota")),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
        ).returning(Auditoria.id)

        result = await db.execute(stmt)
        inserted_id = result.scalar()
        return {"ok": True, "id": inserted_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}

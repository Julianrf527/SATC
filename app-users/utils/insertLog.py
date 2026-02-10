
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from datetime import datetime
import os


# -------- MODELS ------------
from db.models.auditoria import Auditoria


# --------- FUNTIONS --------

async def insert_auditoria(
    db: AsyncSession,
    usuario_id: int,
    descripcion: str,
    tabla_afectada: str | None = None,
    tipo_operacion: str | None = None,
    id_registro: str | None = None,
    datos_anteriores: dict | None = None,
    datos_nuevos: dict | None = None,
):
    try:
        stmt = insert(Auditoria).values(
            usuario_id=usuario_id,
            tabla_afectada=tabla_afectada,
            tipo_operacion=tipo_operacion,
            descripcion=descripcion,
            id_registro=id_registro,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
        ).returning(Auditoria.id)
        
        result = await db.execute(stmt)
        inserted_id = result.scalar()
        return {"ok": True, "id": inserted_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}
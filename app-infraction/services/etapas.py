"""Helpers de expediente compartidos por los routers de stage/acto."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.expediente import Expediente
from db.models.acto_administrativo import ActoAdministrativo
from db.models.notificacion import Notificacion
from db.models.comunicacion import Comunicacion


def serialize_notif(n) -> dict:
    return {
        "id": n.id,
        "involucrado_id": n.involucrado_id,
        "numerado": str(n.numerado) if n.numerado is not None else "",
        "fecha_numerado": n.fecha_numerado.isoformat() if n.fecha_numerado else None,
        "fecha_envio_citacion": n.fecha_envio_citacion.isoformat() if n.fecha_envio_citacion else None,
        "fecha_constancia_citacion": n.fecha_constancia_citacion.isoformat() if n.fecha_constancia_citacion else None,
        "notificacion_exitosa": n.notificacion_exitosa,
        "documento_citacion_id": n.documento_citacion_id,
        "documento_notificacion_id": n.documento_notificacion_id,
        "tipo_notificacion_id": n.tipo_notificacion_id,
        "fecha_notificacion": None,
        "fecha_creacion": n.fecha_creacion.isoformat() if n.fecha_creacion else "",
    }


async def build_acto_for_frontend(db: AsyncSession, acto: ActoAdministrativo) -> dict:
    """Construye el acto en formato compatible con ActoAdmin (igual a sancionatorio)."""
    notifs_rows = (await db.execute(
        select(Notificacion).where(Notificacion.acto_administrativo_id == acto.id)
    )).scalars().all()
    notifs_data = [serialize_notif(n) for n in notifs_rows]

    com_row = await db.scalar(
        select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto.id)
    )
    com_data = None
    if com_row:
        com_data = {
            "id": com_row.id,
            "numerado": str(com_row.numerado) if com_row.numerado is not None else "",
            "fecha_numerado": com_row.fecha_numerado.isoformat() if com_row.fecha_numerado else None,
            "fecha_envio": com_row.fecha_envio.isoformat() if com_row.fecha_envio else None,
            "fecha_creacion": com_row.fecha_creacion.isoformat() if com_row.fecha_creacion else "",
            "documento_comunicacion_id": com_row.documento_comunicacion_id,
        }

    return {
        "id": acto.id,
        "tipo_acto": acto.tipo_acto,
        "numerado": str(acto.numerado) if acto.numerado is not None else "",
        "fecha_numerado": acto.fecha_numerado.isoformat() if acto.fecha_numerado else None,
        "documento_acto_administrativo_id": acto.documento_acto_administrativo_id,
        "fecha_creacion": acto.fecha_creacion.isoformat() if acto.fecha_creacion else "",
        "etapa_id": 0,
        "nivel_auxiliar": None,
        "notificacion": {
            "id": 0,
            "fecha_creacion": "",
            "involucrados": notifs_data,
        } if notifs_data else None,
        "comunicacion": com_data,
    }


async def get_expediente_con_permiso(db: AsyncSession, expediente_id: int, user_id: int):
    """Verifica que el expediente existe y que el usuario es su abogado responsable.

    Filtra por id + abogado_responsable_id en el mismo WHERE y responde el mismo
    403 tanto si el expediente no existe como si existe pero es de otro: así
    nadie puede descubrir, probando IDs, qué expedientes existen. Se usa 403 y
    no 404 para conservar el toast de "sin permisos" que intercepta el frontend.

    Devuelve la Row (id, radicado, abogado_responsable_id).
    """
    row = (await db.execute(
        select(Expediente.id, Expediente.radicado, Expediente.abogado_responsable_id)
        .where(Expediente.id == expediente_id, Expediente.abogado_responsable_id == user_id)
    )).fetchone()
    if not row:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")
    return row

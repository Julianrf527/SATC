"""Helpers de expediente compartidos por los routers de stage/acto."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.expediente import Expediente
from db.models.acto_administrativo import ActoAdministrativo
from db.models.notificacion import Notificacion
from db.models.comunicacion import Comunicacion
from core.permission import Permission
from services.users import verify_permission


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


async def get_expediente_con_permiso(
    db: AsyncSession, expediente_id: int, user_id: int, require_owner: bool = True,
):
    """Verifica que el expediente existe y, si `require_owner`, que el usuario es
    su abogado responsable. 403 (no 404) en ambos casos para no distinguir "no
    existe" de "no es tuyo"; el frontend intercepta ese 403 con su toast.

    `require_owner=False` es para lecturas: el Modo Consulta abre cualquier
    expediente en solo lectura (misma regla que app-sancionatoria).

    Devuelve la Row (id, radicado, abogado_responsable_id).
    """
    stmt = select(Expediente.id, Expediente.radicado, Expediente.abogado_responsable_id).where(
        Expediente.id == expediente_id
    )
    if require_owner:
        stmt = stmt.where(Expediente.abogado_responsable_id == user_id)
    row = (await db.execute(stmt)).fetchone()
    if not row:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")
    return row


async def puede_leer_expediente(
    user_id: int, abogado_responsable_id: int | None, *ven_todos: str,
) -> bool:
    """Regla de lectura (la misma de GET /expedientes/completo):
    `infraccion_consultar` (o cualquiera de `ven_todos`) ve cualquier
    expediente; `infraccion_gestionar` solo los que tiene a cargo."""
    for permiso in (Permission.FILE_CONSULT, *ven_todos):
        if await verify_permission(user_id, permiso):
            return True
    return (
        abogado_responsable_id is not None
        and abogado_responsable_id == user_id
        and bool(await verify_permission(user_id, Permission.FILE_MANAGE))
    )


async def exigir_lectura_expediente(
    db: AsyncSession, expediente_id: int, user_id: int, *ven_todos: str,
):
    """Lecturas de un expediente (etapas, involucrados, descarga). 403 tanto si
    no existe como si no lo puede ver, para no revelar qué IDs existen.

    Devuelve la Row (id, radicado, abogado_responsable_id).
    """
    row = (await db.execute(
        select(Expediente.id, Expediente.radicado, Expediente.abogado_responsable_id)
        .where(Expediente.id == expediente_id)
    )).fetchone()
    if not row or not await puede_leer_expediente(user_id, row.abogado_responsable_id, *ven_todos):
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")
    return row

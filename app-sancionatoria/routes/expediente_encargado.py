from fastapi import Request, APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import List
import logging

from db.deps import get_db_managed
from db.models.expediente import Expediente

from core.permission import Permission
from utils.verify_token import verify_gateway_token
from services.auditoria import insert_log
from services.users import get_user_info, create_user_notification, verify_permission

router = APIRouter()
ASSIGN_PERMISSION = Permission.ASSIGN_PERMISSION
logger = logging.getLogger(__name__)


class BulkEncargadoRequest(BaseModel):
    expediente_id: List[int]
    encargado_id: int


@router.patch("/{expediente_id}/charge/{encargado_id}")
async def actualizar_encargado_de_expediente(
    request: Request,
    expediente_id: int,
    encargado_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    if not await verify_permission(user_id, ASSIGN_PERMISSION):
        raise HTTPException(status_code=403, detail="No cuenta con permisos")

    stmt_check = select(Expediente).where(Expediente.id == expediente_id)
    res_check = await db.execute(stmt_check)
    expediente = res_check.scalar_one_or_none()

    if expediente is None:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")

    ant_enc_info = (await get_user_info([expediente.encargado_id])).get(expediente.encargado_id, {}) if expediente.encargado_id else {}
    datos_anteriores = {
        "radicado": expediente.radicado,
        "encargado": ant_enc_info.get("nombre", f"ID {expediente.encargado_id}") if expediente.encargado_id else None,
    }

    new_value = None if encargado_id == 0 else encargado_id

    stmt = (
        update(Expediente)
        .where(Expediente.id == expediente_id)
        .values({Expediente.encargado_id: new_value})
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(stmt)

    if result.rowcount == 0:
        raise HTTPException(status_code=400, detail="Expediente no encontrado")

    new_enc_info = (await get_user_info([new_value])).get(new_value, {}) if new_value else {}
    datos_nuevos = {
        "radicado": expediente.radicado,
        "encargado": new_enc_info.get("nombre", f"ID {new_value}") if new_value else None,
    }

    await insert_log(
        db=db,
        tipo_evento="ACTUALIZAR_ENCARGADO_EXPEDIENTE",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Actualización de encargado del expediente {expediente.radicado}",
        expediente_id=expediente.id,
        expediente_radicado=expediente.radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos
    )

    await db.commit()

    if encargado_id != 0:
        notif_result = await create_user_notification(
            mensaje=f"Se te ha asignado el expediente {expediente.radicado}",
            id_vinculada=expediente.radicado,
            usuario_id=encargado_id
        )

        # Solo loguear si falla, no interrumpir el flujo
        if not notif_result["ok"]:
            logger.warning(
                f"No se pudo crear notificación para usuario {encargado_id}: {notif_result['message']}"
            )

    return JSONResponse(
        content={"ok": True, "message": "Encargado actualizado"},
        status_code=200
    )

@router.patch("/charge/bulk")
async def actualizar_encargado_bulk(
    request: Request,
    data: BulkEncargadoRequest,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    if not await verify_permission(user_id, ASSIGN_PERMISSION):
        raise HTTPException(status_code=403, detail="No cuenta con permisos")

    expediente_ids = list(dict.fromkeys(data.expediente_id or []))
    if not expediente_ids:
        raise HTTPException(status_code=400, detail="Debe enviar al menos un expediente_id")

    new_value = None if data.encargado_id == 0 else data.encargado_id
    updated = []

    res_check = await db.execute(
        select(Expediente).where(Expediente.id.in_(expediente_ids))
    )
    expedientes = res_check.scalars().all()

    if not expedientes:
        return JSONResponse(
            content={"ok": True, "updated": [], "msg": "No se encontraron expedientes para actualizar"},
            status_code=200,
        )

    ids_existentes = [exp.id for exp in expedientes]

    await db.execute(
        update(Expediente)
        .where(Expediente.id.in_(ids_existentes))
        .values({Expediente.encargado_id: new_value})
        .execution_options(synchronize_session=False)
    )

    old_enc_ids = [exp.encargado_id for exp in expedientes if exp.encargado_id]
    old_enc_info_map = await get_user_info(old_enc_ids) if old_enc_ids else {}
    new_enc_info_bulk = (await get_user_info([new_value])).get(new_value, {}) if new_value else {}

    for expediente in expedientes:
        ant_enc_info_bulk = old_enc_info_map.get(expediente.encargado_id, {})
        datos_anteriores = {
            "radicado": expediente.radicado,
            "encargado": ant_enc_info_bulk.get("nombre", f"ID {expediente.encargado_id}") if expediente.encargado_id else None,
        }

        await insert_log(
            db=db,
            tipo_evento="ACTUALIZAR_ENCARGADO_EXPEDIENTE_MASIVO",
            resultado="EXITOSO",
            usuario_id=user_id,
            detalle=f"Actualización masiva de encargado del expediente {expediente.radicado}",
            expediente_id=expediente.id,
            expediente_radicado=expediente.radicado,
            datos_anteriores=datos_anteriores,
            datos_nuevos={"radicado": expediente.radicado, "encargado": new_enc_info_bulk.get("nombre", f"ID {new_value}") if new_value else None},
        )
        updated.append({"id": expediente.id, "radicado": expediente.radicado})

    await db.commit()

    if new_value:
        for expediente_actualizado in updated:
            await create_user_notification(
                mensaje=f"Se te ha asignado el expediente {expediente_actualizado['radicado']}",
                id_vinculada=expediente_actualizado['radicado'],
                usuario_id=new_value
            )

    return JSONResponse(
        content={"ok": True, "updated": updated, "msg": f"Se actualizaron {len(updated)} expedientes"},
        status_code=200
    )

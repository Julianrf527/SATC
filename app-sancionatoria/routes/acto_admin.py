from fastapi import Request, APIRouter, Depends, HTTPException, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional
import pytz

from db.deps import get_db_managed
from db.models.expediente import Expediente
from db.models.acto_administrativo import ActoAdministrativo
from db.models.comunicacion import Comunicacion
from db.models.notificacion import Notificacion
from db.models.tipo_notificacion import TipoNotificacion

from utils.verify_token import verify_gateway_token
from services.docs import increment_file_usage, decrement_file_usage
from services.auditoria import insert_auditoria
from services.etapas import (
    ETAPA_MODELS as STAGE_MAP,
    find_stage_by_id as _find_stage_by_id_acto,
    get_expediente_con_permiso,
)

router = APIRouter()
load_dotenv()
bogota_tz = pytz.timezone("America/Bogota")


async def _get_expediente_from_stage(db, etapa_tipo, etapa_ref_id):
    Model = STAGE_MAP.get(etapa_tipo)
    if not Model:
        return None
    return await db.scalar(select(Model.expediente_id).where(Model.id == etapa_ref_id))

async def _update_stage_acto(db, etapa_tipo, etapa_ref_id, acto_id, is_recurso=False):
    Model = STAGE_MAP.get(etapa_tipo)
    if not Model:
        return
    if is_recurso and hasattr(Model, 'acto_recurso_id'):
        await db.execute(update(Model).where(Model.id == etapa_ref_id).values(acto_recurso_id=acto_id))
    else:
        await db.execute(update(Model).where(Model.id == etapa_ref_id).values(acto_administrativo_id=acto_id))

async def _clear_stage_acto(db, acto_id):
    for Model in STAGE_MAP.values():
        if hasattr(Model, 'acto_administrativo_id'):
            await db.execute(update(Model).where(Model.acto_administrativo_id == acto_id).values(acto_administrativo_id=None))
        if hasattr(Model, 'acto_recurso_id'):
            await db.execute(update(Model).where(Model.acto_recurso_id == acto_id).values(acto_recurso_id=None))


@router.post("/acto-admin")
async def crear_acto_admin(
    request: Request,
    tipo_acto: str = Form(...),
    numerado: int = Form(...),
    fecha_numerado: str = Form(...),
    nivel_auxiliar: Optional[str] = Form(None),
    documento_acto_administrativo_id: int = Form(...),
    etapa_tipo: Optional[str] = Form(None),
    etapa_ref_id: Optional[int] = Form(None),
    # Legado: frontend sancionatorio envía etapa_id
    etapa_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]
    fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
    if fecha_numerado_date > datetime.today().date():
        raise HTTPException(status_code=400, detail="La fecha de numerado no puede ser mayor a la fecha actual")

    if not numerado or len(str(numerado)) > 4:
        raise HTTPException(status_code=400, detail="El numerado debe tener como maximo 4 numeros")

    if tipo_acto not in ["AUTO", "RES"]:
        raise HTTPException(status_code=400, detail="El tipo de acto debe ser AUTO o RES")

    if not etapa_tipo and etapa_id:
        etapa_tipo, _, _ = await _find_stage_by_id_acto(db, etapa_id)
        etapa_ref_id = etapa_id

    if not etapa_tipo or etapa_tipo not in STAGE_MAP:
        raise HTTPException(status_code=400, detail="Tipo de etapa no válido")
    if not etapa_ref_id:
        raise HTTPException(status_code=400, detail="etapa_ref_id requerido")

    expediente_id = await _get_expediente_from_stage(db, etapa_tipo, etapa_ref_id)
    if not expediente_id:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")

    exp_row = await get_expediente_con_permiso(db, expediente_id, user_id)
    radicado_expediente = exp_row.radicado

    is_recurso = nivel_auxiliar == "true"

    Model = STAGE_MAP[etapa_tipo]
    if is_recurso and hasattr(Model, 'acto_recurso_id'):
        existing_id = await db.scalar(select(Model.acto_recurso_id).where(Model.id == etapa_ref_id))
    else:
        existing_id = await db.scalar(select(Model.acto_administrativo_id).where(Model.id == etapa_ref_id))

    if existing_id:
        raise HTTPException(status_code=400, detail="El acto administrativo ya existe")

    año_numerado = fecha_numerado_date.year

    stmt = (
        select(ActoAdministrativo.id)
        .where(
            ActoAdministrativo.numerado == numerado,
            ActoAdministrativo.fecha_numerado == fecha_numerado_date
        )
    )
    existing_acto = await db.scalar(stmt)

    if año_numerado > 2012 and existing_acto:
        existing_exp = None
        for M in STAGE_MAP.values():
            if hasattr(M, 'acto_administrativo_id'):
                eid = await db.scalar(select(M.expediente_id).where(M.acto_administrativo_id == existing_acto))
                if eid:
                    existing_exp = await db.scalar(select(Expediente.radicado).where(Expediente.id == eid))
                    break
            if hasattr(M, 'acto_recurso_id'):
                eid = await db.scalar(select(M.expediente_id).where(M.acto_recurso_id == existing_acto))
                if eid:
                    existing_exp = await db.scalar(select(Expediente.radicado).where(Expediente.id == eid))
                    break
        raise HTTPException(
            status_code=400,
            detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en el expediente {existing_exp}"
        )
    elif año_numerado <= 2012 and existing_acto:
        other_exp = None
        for M in STAGE_MAP.values():
            if hasattr(M, 'acto_administrativo_id'):
                eid = await db.scalar(select(M.expediente_id).where(M.acto_administrativo_id == existing_acto))
                if eid and eid != expediente_id:
                    other_exp = await db.scalar(select(Expediente.radicado).where(Expediente.id == eid))
                    break
            if hasattr(M, 'acto_recurso_id'):
                eid = await db.scalar(select(M.expediente_id).where(M.acto_recurso_id == existing_acto))
                if eid and eid != expediente_id:
                    other_exp = await db.scalar(select(Expediente.radicado).where(Expediente.id == eid))
                    break
        if other_exp:
            raise HTTPException(
                status_code=400,
                detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en el expediente {other_exp}"
            )

    if is_recurso:
        base_acto = await db.scalar(select(Model.acto_administrativo_id).where(Model.id == etapa_ref_id))
        if not base_acto:
            raise HTTPException(
                status_code=400,
                detail="Debe crear primero el acto administrativo de etapa antes de crear el acto de recurso"
            )

    nuevo_acto = ActoAdministrativo(
        tipo_acto=tipo_acto,
        numerado=numerado,
        fecha_numerado=fecha_numerado_date,
        documento_acto_administrativo_id=documento_acto_administrativo_id,
    )

    db.add(nuevo_acto)
    await db.flush()

    await _update_stage_acto(db, etapa_tipo, etapa_ref_id, nuevo_acto.id, is_recurso=is_recurso)

    await increment_file_usage( [documento_acto_administrativo_id])

    datos_nuevos = {
        "etapa_tipo": etapa_tipo,
        "tipo_acto": tipo_acto,
        "numerado": numerado,
        "fecha_numerado": fecha_numerado,
        "is_recurso": is_recurso,
    }

    await insert_auditoria(
        db=db,
        tipo_evento="CREAR_ACTO_ADMIN",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Creación de acto administrativo {tipo_acto} {numerado}",
        expediente_id=expediente_id,
        expediente_radicado=radicado_expediente,
        datos_nuevos=datos_nuevos
    )

    await db.commit()
    await db.refresh(nuevo_acto)

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": nuevo_acto.id,
                "numerado": nuevo_acto.numerado,
                "fecha_numerado": str(nuevo_acto.fecha_numerado),
                "documento_acto_administrativo_id": nuevo_acto.documento_acto_administrativo_id,
                "tipo_acto": nuevo_acto.tipo_acto,
                "fecha_creacion": str(nuevo_acto.fecha_creacion),
                "etapa_tipo": etapa_tipo,
                "etapa_ref_id": etapa_ref_id,
                "is_recurso": is_recurso
            }
        },
        status_code=201
    )

@router.put("/acto-admin/{acto_id}")
async def actualizar_acto_admin(
    request: Request,
    acto_id: int,
    tipo_acto: str = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    nivel_auxiliar: Optional[str] = Form(None),
    documento_acto_administrativo_id: Optional[int] = Form(None),
    etapa_tipo: Optional[str] = Form(None),
    etapa_ref_id: Optional[int] = Form(None),
    etapa_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]
    fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
    if fecha_numerado_date > datetime.today().date():
        raise HTTPException(status_code=400, detail="La fecha de numerado no puede ser mayor a la fecha actual")

    if not numerado or len(str(numerado)) > 4:
        raise HTTPException(status_code=400, detail="El numerado debe tener como maximo 4 numeros")

    if tipo_acto not in ["AUTO", "RES"]:
        raise HTTPException(status_code=400, detail="El tipo de acto debe ser AUTO o RES")

    if not etapa_tipo and etapa_id:
        etapa_tipo, _, _ = await _find_stage_by_id_acto(db, etapa_id)
        etapa_ref_id = etapa_id

    if etapa_tipo not in STAGE_MAP:
        raise HTTPException(status_code=400, detail="Tipo de etapa no válido")

    expediente_id = await _get_expediente_from_stage(db, etapa_tipo, etapa_ref_id)
    if not expediente_id:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")

    row = await get_expediente_con_permiso(db, expediente_id, user_id)
    radicado_expediente = row.radicado

    acto_admin = await db.scalar(select(ActoAdministrativo).where(ActoAdministrativo.id == acto_id))
    if not acto_admin:
        raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

    datos_anteriores = {
        "tipo_acto": acto_admin.tipo_acto,
        "numerado": acto_admin.numerado,
        "fecha_numerado": str(acto_admin.fecha_numerado) if acto_admin.fecha_numerado else None,
        "documento_acto_administrativo_id": acto_admin.documento_acto_administrativo_id,
    }

    año_numerado = fecha_numerado_date.year

    stmt = (
        select(ActoAdministrativo.id)
        .where(
            ActoAdministrativo.numerado == int(numerado),
            ActoAdministrativo.fecha_numerado == fecha_numerado_date,
            ActoAdministrativo.id != acto_id
        )
    )
    existing_acto = await db.scalar(stmt)

    if año_numerado > 2012 and existing_acto:
        raise HTTPException(
            status_code=400,
            detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso"
        )
    elif año_numerado <= 2012 and existing_acto:
        other_exp = None
        for M in STAGE_MAP.values():
            if hasattr(M, 'acto_administrativo_id'):
                eid = await db.scalar(select(M.expediente_id).where(M.acto_administrativo_id == existing_acto))
                if eid and eid != expediente_id:
                    other_exp = await db.scalar(select(Expediente.radicado).where(Expediente.id == eid))
                    break
            if hasattr(M, 'acto_recurso_id'):
                eid = await db.scalar(select(M.expediente_id).where(M.acto_recurso_id == existing_acto))
                if eid and eid != expediente_id:
                    other_exp = await db.scalar(select(Expediente.radicado).where(Expediente.id == eid))
                    break
        if other_exp:
            raise HTTPException(
                status_code=400,
                detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en el expediente {other_exp}"
            )

    is_recurso = nivel_auxiliar == "true"
    if is_recurso:
        Model = STAGE_MAP[etapa_tipo]
        if hasattr(Model, 'acto_recurso_id'):
            base_acto = await db.scalar(select(Model.acto_administrativo_id).where(Model.id == etapa_ref_id))
            if not base_acto or base_acto == acto_id:
                raise HTTPException(
                    status_code=400,
                    detail="Debe existir un acto administrativo de etapa antes de modificar el acto de recurso"
                )

    acto_admin.tipo_acto = tipo_acto
    acto_admin.numerado = int(numerado)
    acto_admin.fecha_numerado = fecha_numerado_date
    if datos_anteriores["documento_acto_administrativo_id"] and documento_acto_administrativo_id != datos_anteriores["documento_acto_administrativo_id"]:
        await decrement_file_usage( [datos_anteriores["documento_acto_administrativo_id"]])
        await increment_file_usage( [documento_acto_administrativo_id])
        acto_admin.documento_acto_administrativo_id = documento_acto_administrativo_id

    await db.flush()

    datos_nuevos = {
        "tipo_acto": acto_admin.tipo_acto,
        "numerado": acto_admin.numerado,
        "fecha_numerado": str(acto_admin.fecha_numerado),
    }

    await insert_auditoria(
        db=db,
        tipo_evento="ACTUALIZAR_ACTO_ADMIN",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Actualización de acto administrativo {tipo_acto} {numerado}",
        expediente_id=expediente_id,
        expediente_radicado=radicado_expediente,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos
    )

    await db.commit()
    await db.refresh(acto_admin)

    stmt = select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto_admin.id)
    comunicacion = await db.scalar(stmt)

    comunicacion_data = None
    if comunicacion:
        comunicacion_data = {
            "id": comunicacion.id,
            "numerado": comunicacion.numerado,
            "fecha_numerado": str(comunicacion.fecha_numerado),
            "fecha_envio": str(comunicacion.fecha_envio),
            "fecha_creacion": str(comunicacion.fecha_creacion)
        }

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": acto_admin.id,
                "numerado": acto_admin.numerado,
                "fecha_numerado": str(acto_admin.fecha_numerado),
                "documento_acto_administrativo_id": acto_admin.documento_acto_administrativo_id,
                "tipo_acto": acto_admin.tipo_acto,
                "fecha_creacion": str(acto_admin.fecha_creacion),
                "etapa_tipo": etapa_tipo,
                "etapa_ref_id": etapa_ref_id,
                "comunicacion": comunicacion_data
            }
        },
        status_code=200
    )

@router.delete("/acto-admin/{acto_id}")
async def delete_acto_admin(
    request: Request,
    acto_id: int,
    expediente_id: int = Query(...),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    row = await get_expediente_con_permiso(db, expediente_id, user_id)
    radicado_expediente = row.radicado

    acto_admin = await db.scalar(select(ActoAdministrativo).where(ActoAdministrativo.id == acto_id))
    if not acto_admin:
        raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

    datos_acto = {
        "numerado": acto_admin.numerado,
        "fecha_numerado": str(acto_admin.fecha_numerado) if acto_admin.fecha_numerado else None,
        "tipo_acto": acto_admin.tipo_acto,
    }

    comunicacion = await db.scalar(
        select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto_id)
    )

    datos_comunicacion = None
    notificaciones_eliminadas = []
    involucrados_notificacion_eliminados = []

    if comunicacion:
        datos_comunicacion = {
            "numerado": comunicacion.numerado,
            "fecha_numerado": str(comunicacion.fecha_numerado) if comunicacion.fecha_numerado else None,
            "fecha_envio": str(comunicacion.fecha_envio) if comunicacion.fecha_envio else None,
        }
        await db.execute(delete(Comunicacion).where(Comunicacion.id == comunicacion.id))
    else:
        notificaciones = (await db.execute(
            select(Notificacion).where(Notificacion.acto_administrativo_id == acto_id)
        )).scalars().all()

        for notificacion in notificaciones:
            tipo_notif_nombre = (await db.execute(
                select(TipoNotificacion.nombre).where(TipoNotificacion.id == notificacion.tipo_notificacion_id)
            )).scalar() if notificacion.tipo_notificacion_id else None
            notificaciones_eliminadas.append({
                "numerado": notificacion.numerado,
                "fecha_numerado": str(notificacion.fecha_numerado) if notificacion.fecha_numerado else None,
                "fecha_envio_citacion": str(notificacion.fecha_envio_citacion) if notificacion.fecha_envio_citacion else None,
                "fecha_constancia_citacion": str(notificacion.fecha_constancia_citacion) if notificacion.fecha_constancia_citacion else None,
                "notificacion_exitosa": notificacion.notificacion_exitosa,
                "tipo_notificacion": tipo_notif_nombre,
                "fecha_notificacion": str(notificacion.fecha_notificacion) if notificacion.fecha_notificacion else None,
            })

            await db.execute(delete(Notificacion).where(Notificacion.id == notificacion.id))

    await _clear_stage_acto(db, acto_id)
    await db.execute(delete(ActoAdministrativo).where(ActoAdministrativo.id == acto_id))
    await db.flush()

    descripcion_partes = [
        f"Eliminación de acto administrativo {datos_acto['tipo_acto']} {datos_acto['numerado']}"
    ]

    if datos_comunicacion:
        descripcion_partes.append(f"con comunicación (ID: {datos_comunicacion['id']})")

    if notificaciones_eliminadas:
        descripcion_partes.append(f"{len(notificaciones_eliminadas)} notificación(es)")

    if involucrados_notificacion_eliminados:
        descripcion_partes.append(f"{len(involucrados_notificacion_eliminados)} involucrado(s) en notificaciones")

    await insert_auditoria(
        db=db,
        tipo_evento="ELIMINAR_ACTO_ADMIN",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=" - ".join(descripcion_partes),
        expediente_id=expediente_id,
        expediente_radicado=radicado_expediente,
        datos_anteriores={
            "acto_admin": datos_acto,
            "comunicacion": datos_comunicacion,
            "notificaciones": notificaciones_eliminadas,
            "involucrados_notificacion": involucrados_notificacion_eliminados,
        },
        datos_nuevos={}
    )

    await db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "message": "Acto administrativo y registros relacionados eliminados correctamente",
            "deleted": {
                "acto_admin": 1,
                "comunicacion": 1 if datos_comunicacion else 0,
                "notificaciones": len(notificaciones_eliminadas),
                "involucrados_notificacion": len(involucrados_notificacion_eliminados),
            }
        },
        status_code=200
    )

from fastapi import Request, APIRouter, Depends, HTTPException, Form, Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional

from db.deps import get_db_managed
from db.models.acto_administrativo import ActoAdministrativo
from db.models.comunicacion import Comunicacion

from utils.verify_token import verify_gateway_token
from services.docs import increment_file_usage, decrement_file_usage
from services.auditoria import insert_auditoria
from services.etapas import get_expediente_con_permiso

router = APIRouter()


@router.post("/communication")
async def crear_comunicacion(
    request:Request,
    expediente_id: int = Form(...),
    acto_admin_id: int = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio: str = Form(...),
    documento_comunicacion_id: Optional[int] = Form(...),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]
    fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
    fecha_envio_date = datetime.strptime(fecha_envio, "%Y-%m-%d").date()
    today = datetime.today().date()
    if fecha_numerado_date > today:
        raise HTTPException(status_code=400, detail="La fecha de numerado no puede ser mayor a la fecha actual")
    if fecha_envio_date > today:
        raise HTTPException(status_code=400, detail="La fecha de envío no puede ser mayor a la fecha actual")

    if not numerado.isdigit() or len(numerado) != 4:
        raise HTTPException(
            status_code=400,
            detail="El numerado debe tener exactamente 4 dígitos"
        )

    stmt = select(ActoAdministrativo).where(ActoAdministrativo.id == acto_admin_id)
    acto_admin = await db.scalar(stmt)
    if not acto_admin:
        raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

    row = await get_expediente_con_permiso(db, expediente_id, user_id)
    radicado = row.radicado

    año_numerado = fecha_numerado_date.year

    if año_numerado > 2012:
        # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
        stmt = (
            select(Comunicacion.id)
            .where(
                Comunicacion.numerado == int(numerado),
                Comunicacion.fecha_numerado == fecha_numerado_date
            )
        )
        existe_comunicacion = await db.scalar(stmt)

        if existe_comunicacion:
            raise HTTPException(
                status_code=400,
                detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra comunicación"
            )

    nueva_comunicacion = Comunicacion(
        acto_administrativo_id=acto_admin_id,
        numerado=int(numerado),
        fecha_numerado=fecha_numerado_date,
        fecha_envio=fecha_envio_date,
        fecha_creacion=datetime.now().date(),
        documento_comunicacion_id=documento_comunicacion_id,
    )

    db.add(nueva_comunicacion)
    await db.flush()

    await increment_file_usage( [documento_comunicacion_id])

    datos_nuevos = {
        "numerado": int(numerado),
        "fecha_numerado": fecha_numerado,
        "fecha_envio": fecha_envio,
    }

    await insert_auditoria(
        db=db,
        tipo_evento="CREAR_COMUNICACION",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Creación de comunicación {numerado} para acto admin {acto_admin_id}",
        expediente_id=expediente_id,
        expediente_radicado=radicado,
        datos_nuevos=datos_nuevos
    )

    await db.commit()
    await db.refresh(nueva_comunicacion)

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": nueva_comunicacion.id,
                "numerado": nueva_comunicacion.numerado,
                "fecha_numerado": str(nueva_comunicacion.fecha_numerado),
                "fecha_envio": str(nueva_comunicacion.fecha_envio),
                "fecha_creacion": str(nueva_comunicacion.fecha_creacion),
                "documento_comunicacion_id": nueva_comunicacion.documento_comunicacion_id,
            },
        },
        status_code=201,
    )

@router.put("/communication/{comunicacion_id}")
async def actualizar_comunicacion(
    request:Request,
    comunicacion_id: int,
    expediente_id: int = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio: str = Form(...),
    documento_comunicacion_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]
    fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
    fecha_envio_date = datetime.strptime(fecha_envio, "%Y-%m-%d").date()
    today = datetime.today().date()
    if fecha_numerado_date > today:
        raise HTTPException(status_code=400, detail="La fecha de numerado no puede ser mayor a la fecha actual")
    if fecha_envio_date > today:
        raise HTTPException(status_code=400, detail="La fecha de envío no puede ser mayor a la fecha actual")

    if not numerado.isdigit() or len(numerado) != 4:
        raise HTTPException(
            status_code=400,
            detail="El numerado debe tener exactamente 4 dígitos"
        )

    stmt = select(Comunicacion).where(Comunicacion.id == comunicacion_id)
    comunicacion = await db.scalar(stmt)

    if not comunicacion:
        raise HTTPException(status_code=404, detail="Comunicación no encontrada")

    datos_anteriores = {
        "numerado": comunicacion.numerado,
        "fecha_numerado": str(comunicacion.fecha_numerado) if comunicacion.fecha_numerado else None,
        "fecha_envio": str(comunicacion.fecha_envio) if comunicacion.fecha_envio else None,
        "documento_comunicacion_id": comunicacion.documento_comunicacion_id,
    }

    stmt = select(ActoAdministrativo).where(ActoAdministrativo.id == comunicacion.acto_administrativo_id)
    acto_admin = await db.scalar(stmt)

    if not acto_admin:
        raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

    row = await get_expediente_con_permiso(db, expediente_id, user_id)
    radicado = row.radicado

    año_numerado = fecha_numerado_date.year

    if año_numerado > 2012:
        # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
        stmt = (
            select(Comunicacion.id)
            .where(
                Comunicacion.numerado == int(numerado),
                Comunicacion.fecha_numerado == fecha_numerado_date,
                Comunicacion.id != comunicacion_id
            )
        )
        existe_comunicacion = await db.scalar(stmt)

        if existe_comunicacion:
            raise HTTPException(
                status_code=400,
                detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra comunicación"
            )
    # Para años ≤ 2012: se permite duplicados en el mismo expediente, no validar

    if datos_anteriores["documento_comunicacion_id"] and documento_comunicacion_id != datos_anteriores["documento_comunicacion_id"]:
        await decrement_file_usage( [datos_anteriores["documento_comunicacion_id"]])
        await increment_file_usage( [documento_comunicacion_id])
        comunicacion.documento_comunicacion_id = documento_comunicacion_id

    comunicacion.numerado = int(numerado)
    comunicacion.fecha_numerado = fecha_numerado_date
    comunicacion.fecha_envio = fecha_envio_date

    await db.flush()

    datos_nuevos = {
        "numerado": comunicacion.numerado,
        "fecha_numerado": str(comunicacion.fecha_numerado),
        "fecha_envio": str(comunicacion.fecha_envio),
    }

    await insert_auditoria(
        db=db,
        tipo_evento="ACTUALIZAR_COMUNICACION",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Actualización de comunicación {numerado}",
        expediente_id=expediente_id,
        expediente_radicado=radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos
    )

    await db.commit()
    await db.refresh(comunicacion)

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": comunicacion.id,
                "numerado": comunicacion.numerado,
                "fecha_numerado": str(comunicacion.fecha_numerado),
                "fecha_envio": str(comunicacion.fecha_envio),
                "fecha_creacion": str(comunicacion.fecha_creacion),
                "documento_comunicacion_id": comunicacion.documento_comunicacion_id,
            },
        },
        status_code=200,
    )

@router.delete("/communication/{comunicacion_id}")
async def eliminar_comunicacion(
    request:Request,
    comunicacion_id: int,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]
    expediente_id = data.get("expediente_id")

    if not expediente_id:
        raise HTTPException(status_code=422, detail="expediente_id es requerido")

    stmt = select(Comunicacion).where(Comunicacion.id == comunicacion_id)
    comunicacion = await db.scalar(stmt)

    if not comunicacion:
        raise HTTPException(status_code=404, detail="Comunicación no encontrada")

    datos_anteriores = {
        "numerado": comunicacion.numerado,
        "fecha_numerado": str(comunicacion.fecha_numerado) if comunicacion.fecha_numerado else None,
        "fecha_envio": str(comunicacion.fecha_envio) if comunicacion.fecha_envio else None,
    }

    stmt = select(ActoAdministrativo).where(ActoAdministrativo.id == comunicacion.acto_administrativo_id)
    acto_admin = await db.scalar(stmt)

    if not acto_admin:
        raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

    row = await get_expediente_con_permiso(db, expediente_id, user_id)
    radicado = row.radicado

    await db.delete(comunicacion)
    await db.flush()

    await decrement_file_usage( [comunicacion.documento_comunicacion_id])

    await insert_auditoria(
        db=db,
        tipo_evento="ELIMINAR_COMUNICACION",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Eliminación de comunicación {datos_anteriores['numerado']}",
        expediente_id=expediente_id,
        expediente_radicado=radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos={}
    )

    await db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "message": "Comunicación eliminada exitosamente"
        },
        status_code=200,
    )

from fastapi import Request, APIRouter, Depends, HTTPException, Form, Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from datetime import datetime

from db.deps import get_db_managed
from db.models.acto_administrativo import ActoAdministrativo
from db.models.notificacion import Notificacion
from db.models.tipo_notificacion import TipoNotificacion

from utils.verify_token import verify_gateway_token
from services.involucrado import get_involucrados_by_expedientes_ids
from services.docs import increment_file_usage, decrement_file_usage
from services.auditoria import insert_auditoria
from services.etapas import get_expediente_con_permiso

router = APIRouter()


@router.post("/notificacion")
async def crear_notificacion(
    request: Request,
    expediente_id: int = Form(...),
    acto_admin_id: int = Form(...),
    involucrado_id: int = Form(...),
    numerado: int = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio_citacion: str = Form(...),
    fecha_constancia_citacion: str = Form(None),
    documento_citacion_id: int = Form(...),
    notificacion_exitosa: bool = Form(False),
    tipo_notificacion_id: int = Form(None),
    documento_notificacion_id: int = Form(None),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    today = datetime.today().date()
    fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
    fecha_envio_date = datetime.strptime(fecha_envio_citacion, "%Y-%m-%d").date()
    fecha_constancia_date = None
    if fecha_constancia_citacion and fecha_constancia_citacion.strip() and fecha_constancia_citacion != "None":
        fecha_constancia_date = datetime.strptime(fecha_constancia_citacion, "%Y-%m-%d").date()
    if fecha_numerado_date > today:
        raise HTTPException(status_code=400, detail="La fecha de numerado no puede ser mayor a la fecha actual")
    if fecha_envio_date > today:
        raise HTTPException(status_code=400, detail="La fecha de envío de citación no puede ser mayor a la fecha actual")
    if fecha_constancia_date and fecha_constancia_date > today:
        raise HTTPException(status_code=400, detail="La fecha de constancia de citación no puede ser mayor a la fecha actual")

    if not str(numerado).isdigit() or len(str(numerado)) > 4:
        raise HTTPException(
            status_code=400,
            detail="El numerado debe tener como máximo 4 dígitos"
        )

    if notificacion_exitosa and not tipo_notificacion_id:
        raise HTTPException(
            status_code=400,
            detail="Debe seleccionar un tipo de notificación si marca como exitosa"
        )

    if notificacion_exitosa and not documento_notificacion_id:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar un documento de notificación si marca como exitosa"
        )

    row = await get_expediente_con_permiso(db, expediente_id, user_id)
    radicado = row.radicado

    stmt = select(ActoAdministrativo).where(ActoAdministrativo.id == acto_admin_id)
    acto_admin = await db.scalar(stmt)

    if not acto_admin:
        raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

    involucrados_map = await get_involucrados_by_expedientes_ids(db, [expediente_id])
    involucrados_radicado = involucrados_map.get(expediente_id, [])
    inv_exp = any(inv.get("id") == involucrado_id for inv in involucrados_radicado)

    if not inv_exp:
        raise HTTPException(status_code=404, detail="El involucrado no pertenece a este expediente")

    stmt = select(Notificacion.id).where(
        and_(
            Notificacion.acto_administrativo_id == acto_admin_id,
            Notificacion.involucrado_id == involucrado_id
        )
    )
    existe = await db.scalar(stmt)

    if existe:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una notificación para este involucrado en este acto administrativo"
        )

    año_numerado = fecha_numerado_date.year

    if año_numerado > 2012:
        # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
        stmt = (
            select(Notificacion.id)
            .where(
                Notificacion.numerado == numerado,
                Notificacion.fecha_numerado == fecha_numerado_date
            )
        )
        existe_notificacion = await db.scalar(stmt)

        if existe_notificacion:
            raise HTTPException(
                status_code=400,
                detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra notificación"
            )

    nueva_notificacion = Notificacion(
        acto_administrativo_id=acto_admin_id,
        involucrado_id=involucrado_id,
        numerado=numerado,
        fecha_numerado=fecha_numerado_date,
        fecha_envio_citacion=fecha_envio_date,
        fecha_constancia_citacion=fecha_constancia_date,
        documento_citacion_id=documento_citacion_id,
        notificacion_exitosa=notificacion_exitosa,
        tipo_notificacion_id=tipo_notificacion_id if tipo_notificacion_id else None,
        documento_notificacion_id=documento_notificacion_id if notificacion_exitosa else None,
        fecha_notificacion=datetime.now().date() if notificacion_exitosa else None
    )

    db.add(nueva_notificacion)
    await db.flush()

    doc_ids_to_increment = [documento_citacion_id]
    if documento_notificacion_id and notificacion_exitosa:
        doc_ids_to_increment.append(documento_notificacion_id)

    await increment_file_usage( doc_ids_to_increment)

    tipo_notif_nombre_crear = await db.scalar(select(TipoNotificacion.nombre).where(TipoNotificacion.id == tipo_notificacion_id)) if tipo_notificacion_id else None
    datos_nuevos = {
        "involucrado_id": involucrado_id,
        "numerado": numerado,
        "fecha_numerado": fecha_numerado,
        "fecha_envio_citacion": fecha_envio_citacion,
        "fecha_constancia_citacion": fecha_constancia_citacion,
        "notificacion_exitosa": notificacion_exitosa,
        "tipo_notificacion": tipo_notif_nombre_crear,
    }

    await insert_auditoria(
        db=db,
        tipo_evento="CREAR_NOTIFICACION",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Creación de notificación {numerado} para involucrado {involucrado_id}",
        expediente_id=expediente_id,
        expediente_radicado=radicado,
        datos_nuevos=datos_nuevos
    )

    await db.commit()
    await db.refresh(nueva_notificacion)

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": nueva_notificacion.id,
                "acto_administrativo_id": nueva_notificacion.acto_administrativo_id,
                "involucrado_id": nueva_notificacion.involucrado_id,
                "numerado": nueva_notificacion.numerado,
                "fecha_numerado": str(nueva_notificacion.fecha_numerado),
                "fecha_envio_citacion": str(nueva_notificacion.fecha_envio_citacion),
                "fecha_constancia_citacion": str(nueva_notificacion.fecha_constancia_citacion) if nueva_notificacion.fecha_constancia_citacion else None,
                "documento_citacion_id": nueva_notificacion.documento_citacion_id,
                "notificacion_exitosa": nueva_notificacion.notificacion_exitosa,
                "tipo_notificacion_id": nueva_notificacion.tipo_notificacion_id,
                "documento_notificacion_id": nueva_notificacion.documento_notificacion_id,
                "fecha_notificacion": str(nueva_notificacion.fecha_notificacion) if nueva_notificacion.fecha_notificacion else None,
                "fecha_creacion": str(nueva_notificacion.fecha_creacion)
            }
        },
        status_code=201
    )

@router.put("/notificacion/{notificacion_id}")
async def actualizar_notificacion(
    request: Request,
    notificacion_id: int,
    expediente_id: int = Form(...),
    numerado: int = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio_citacion: str = Form(...),
    fecha_constancia_citacion: str = Form(None),
    documento_citacion_id: int = Form(...),
    notificacion_exitosa: bool = Form(False),
    tipo_notificacion_id: int = Form(None),
    documento_notificacion_id: int = Form(None),
    db: AsyncSession = Depends(get_db_managed)
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    today = datetime.today().date()
    fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
    fecha_envio_date = datetime.strptime(fecha_envio_citacion, "%Y-%m-%d").date()
    fecha_constancia_date = None
    if fecha_constancia_citacion and fecha_constancia_citacion.strip() and fecha_constancia_citacion != "None":
        fecha_constancia_date = datetime.strptime(fecha_constancia_citacion, "%Y-%m-%d").date()
    if fecha_numerado_date > today:
        raise HTTPException(status_code=400, detail="La fecha de numerado no puede ser mayor a la fecha actual")
    if fecha_envio_date > today:
        raise HTTPException(status_code=400, detail="La fecha de envío de citación no puede ser mayor a la fecha actual")
    if fecha_constancia_date and fecha_constancia_date > today:
        raise HTTPException(status_code=400, detail="La fecha de constancia de citación no puede ser mayor a la fecha actual")

    if not str(numerado).isdigit() or len(str(numerado)) > 4:
        raise HTTPException(
            status_code=400,
            detail="El numerado debe tener como máximo 4 dígitos"
        )

    if notificacion_exitosa and not tipo_notificacion_id:
        raise HTTPException(
            status_code=400,
            detail="Debe seleccionar un tipo de notificación si marca como exitosa"
        )

    if notificacion_exitosa and not documento_notificacion_id:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar un documento de notificación si marca como exitosa"
        )

    row = await get_expediente_con_permiso(db, expediente_id, user_id)
    radicado = row.radicado

    stmt = select(Notificacion).where(Notificacion.id == notificacion_id)
    notificacion = await db.scalar(stmt)

    if not notificacion:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    tipo_notif_ant_nombre = await db.scalar(select(TipoNotificacion.nombre).where(TipoNotificacion.id == notificacion.tipo_notificacion_id)) if notificacion.tipo_notificacion_id else None
    datos_anteriores = {
        "involucrado_id": notificacion.involucrado_id,
        "numerado": notificacion.numerado,
        "fecha_numerado": str(notificacion.fecha_numerado) if notificacion.fecha_numerado else None,
        "fecha_envio_citacion": str(notificacion.fecha_envio_citacion) if notificacion.fecha_envio_citacion else None,
        "fecha_constancia_citacion": str(notificacion.fecha_constancia_citacion) if notificacion.fecha_constancia_citacion else None,
        "notificacion_exitosa": notificacion.notificacion_exitosa,
        "tipo_notificacion": tipo_notif_ant_nombre,
        "fecha_notificacion": str(notificacion.fecha_notificacion) if notificacion.fecha_notificacion else None,
        "documento_citacion_id": notificacion.documento_citacion_id,
        "documento_notificacion_id": notificacion.documento_notificacion_id,
    }

    año_numerado = fecha_numerado_date.year

    if año_numerado > 2012:
        # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE (excepto este registro)
        stmt = (
            select(Notificacion.id)
            .where(
                Notificacion.numerado == numerado,
                Notificacion.fecha_numerado == fecha_numerado_date,
                Notificacion.id != notificacion_id
            )
        )
        existe_notificacion = await db.scalar(stmt)

        if existe_notificacion:
            raise HTTPException(
                status_code=400,
                detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra notificación"
            )

    docs_to_increment = []
    docs_to_decrement = []

    if documento_citacion_id != datos_anteriores["documento_citacion_id"]:
        if datos_anteriores["documento_citacion_id"]:
            docs_to_decrement.append(datos_anteriores["documento_citacion_id"])
        docs_to_increment.append(documento_citacion_id)

    if notificacion_exitosa:
        # Documento de notificación solo se reemplaza si cambió o si antes no existía
        if documento_notificacion_id != datos_anteriores["documento_notificacion_id"]:
            if datos_anteriores["documento_notificacion_id"]:
                docs_to_decrement.append(datos_anteriores["documento_notificacion_id"])
            if documento_notificacion_id:
                docs_to_increment.append(documento_notificacion_id)
    else:
        # Si ya no es exitosa pero antes tenía documento de notificación, se libera
        if datos_anteriores["documento_notificacion_id"]:
            docs_to_decrement.append(datos_anteriores["documento_notificacion_id"])

    if docs_to_decrement:
        await decrement_file_usage( docs_to_decrement)
    if docs_to_increment:
        await increment_file_usage( docs_to_increment)

    notificacion.numerado = numerado
    notificacion.fecha_numerado = fecha_numerado_date
    notificacion.fecha_envio_citacion = fecha_envio_date
    notificacion.fecha_constancia_citacion = fecha_constancia_date
    notificacion.documento_citacion_id = documento_citacion_id
    notificacion.notificacion_exitosa = notificacion_exitosa
    notificacion.tipo_notificacion_id = tipo_notificacion_id if tipo_notificacion_id else None
    notificacion.documento_notificacion_id = documento_notificacion_id if notificacion_exitosa else None

    if notificacion_exitosa and not datos_anteriores["notificacion_exitosa"]:
        # fecha_notificacion solo se fija en la transición a exitosa, no se recalcula después
        notificacion.fecha_notificacion = datetime.now().date()

    await db.flush()

    tipo_notif_nuevo_nombre = await db.scalar(select(TipoNotificacion.nombre).where(TipoNotificacion.id == tipo_notificacion_id)) if tipo_notificacion_id else None
    datos_nuevos = {
        "involucrado_id": notificacion.involucrado_id,
        "numerado": notificacion.numerado,
        "fecha_numerado": str(notificacion.fecha_numerado),
        "fecha_envio_citacion": str(notificacion.fecha_envio_citacion),
        "fecha_constancia_citacion": str(notificacion.fecha_constancia_citacion) if notificacion.fecha_constancia_citacion else None,
        "notificacion_exitosa": notificacion.notificacion_exitosa,
        "tipo_notificacion": tipo_notif_nuevo_nombre,
        "fecha_notificacion": str(notificacion.fecha_notificacion) if notificacion.fecha_notificacion else None,
    }

    await insert_auditoria(
        db=db,
        tipo_evento="ACTUALIZAR_NOTIFICACION",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Actualización de notificación {numerado} para involucrado {notificacion.involucrado_id}",
        expediente_id=expediente_id,
        expediente_radicado=radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos
    )

    await db.commit()
    await db.refresh(notificacion)

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": notificacion.id,
                "acto_administrativo_id": notificacion.acto_administrativo_id,
                "involucrado_id": notificacion.involucrado_id,
                "numerado": notificacion.numerado,
                "fecha_numerado": str(notificacion.fecha_numerado),
                "fecha_envio_citacion": str(notificacion.fecha_envio_citacion),
                "fecha_constancia_citacion": str(notificacion.fecha_constancia_citacion) if notificacion.fecha_constancia_citacion else None,
                "documento_citacion_id": notificacion.documento_citacion_id,
                "notificacion_exitosa": notificacion.notificacion_exitosa,
                "tipo_notificacion_id": notificacion.tipo_notificacion_id,
                "documento_notificacion_id": notificacion.documento_notificacion_id,
                "fecha_notificacion": str(notificacion.fecha_notificacion) if notificacion.fecha_notificacion else None
            }
        },
        status_code=200
    )

@router.delete("/notificacion/{notificacion_id}")
async def eliminar_notificacion(
    request: Request,
    notificacion_id: int,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]
    expediente_id = data.get("expediente_id")

    if not expediente_id:
        raise HTTPException(status_code=422, detail="expediente_id es requerido")

    row = await get_expediente_con_permiso(db, expediente_id, user_id)
    radicado = row.radicado

    stmt = select(Notificacion).where(Notificacion.id == notificacion_id)
    notificacion = await db.scalar(stmt)

    if not notificacion:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    tipo_notif_elim_nombre = await db.scalar(select(TipoNotificacion.nombre).where(TipoNotificacion.id == notificacion.tipo_notificacion_id)) if notificacion.tipo_notificacion_id else None
    datos_notificacion = {
        "involucrado_id": notificacion.involucrado_id,
        "numerado": notificacion.numerado,
        "fecha_numerado": str(notificacion.fecha_numerado) if notificacion.fecha_numerado else None,
        "fecha_envio_citacion": str(notificacion.fecha_envio_citacion) if notificacion.fecha_envio_citacion else None,
        "fecha_constancia_citacion": str(notificacion.fecha_constancia_citacion) if notificacion.fecha_constancia_citacion else None,
        "notificacion_exitosa": notificacion.notificacion_exitosa,
        "tipo_notificacion": tipo_notif_elim_nombre,
        "fecha_notificacion": str(notificacion.fecha_notificacion) if notificacion.fecha_notificacion else None,
    }

    doc_ids_to_decrement = []
    if notificacion.documento_citacion_id:
        doc_ids_to_decrement.append(notificacion.documento_citacion_id)
    if notificacion.documento_notificacion_id:
        doc_ids_to_decrement.append(notificacion.documento_notificacion_id)

    await db.execute(
        delete(Notificacion).where(Notificacion.id == notificacion_id)
    )

    await db.flush()

    if doc_ids_to_decrement:
        await decrement_file_usage( doc_ids_to_decrement)

    await insert_auditoria(
        db=db,
        tipo_evento="ELIMINAR_NOTIFICACION",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Eliminación de notificación (ID: {notificacion_id}) - numerado {datos_notificacion['numerado']}",
        expediente_id=expediente_id,
        expediente_radicado=radicado,
        datos_anteriores=datos_notificacion,
        datos_nuevos={}
    )

    await db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "message": "Notificación eliminada correctamente",
            "documentos_decrementados": len(doc_ids_to_decrement)
        },
        status_code=200
    )

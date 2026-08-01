from fastapi import Request, APIRouter, Depends, HTTPException, Form, Body, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from datetime import datetime
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
import logging
import os
import pytz

from db.deps import get_db_managed
from db.models.expediente import Expediente
from db.models.acto_administrativo import ActoAdministrativo
from db.models.notificacion import Notificacion
from db.models.tipo_notificacion import TipoNotificacion
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.medida_preventiva import MedidaPreventiva
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.comunicacion import Comunicacion

router = APIRouter()
load_dotenv()

bogota_tz = pytz.timezone("America/Bogota")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = BASE_DIR / "uploads" / "expedientes"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from utils.verify_token import verify_gateway_token
from services.involved import get_involved_by_expedientes_ids
from services.docs import increment_file_usage, decrement_file_usage
from services.actos import (
    resolve_etapa_ids as _resolve_etapa_ids,
    get_etapa_context as _get_etapa_context,
    get_acto_context as _get_acto_context,
)
from utils.log import insert_log


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

    fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
    fecha_envio_date = datetime.strptime(fecha_envio_citacion, "%Y-%m-%d").date()
    fecha_constancia_date = None
    if fecha_constancia_citacion and fecha_constancia_citacion.strip() and fecha_constancia_citacion != "None":
        fecha_constancia_date = datetime.strptime(fecha_constancia_citacion, "%Y-%m-%d").date()

    if not str(numerado).isdigit() or len(str(numerado)) > 4:
        raise HTTPException(
            status_code=400,
            detail="El numerado debe tener como máximo 4 dígitos",
        )

    if notificacion_exitosa and not tipo_notificacion_id:
        raise HTTPException(
            status_code=400,
            detail="Debe seleccionar un tipo de notificación si marca como exitosa",
        )

    if notificacion_exitosa and not documento_notificacion_id:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar un documento de notificación si marca como exitosa",
        )

    _, _, _, etapa_expediente_id, radicado, encargado_id = await _get_acto_context(
        db, acto_admin_id
    )

    if etapa_expediente_id != expediente_id:
        raise HTTPException(status_code=400, detail="El expediente no corresponde al acto administrativo")

    if encargado_id != user_id:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar esta infracción")

    existe = await db.scalar(
        select(Notificacion.id).where(
            Notificacion.acto_administrativo_id == acto_admin_id,
            Notificacion.involucrado_id == involucrado_id,
        )
    )
    if existe:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una notificación para este involucrado en este acto administrativo",
        )

    año_numerado = fecha_numerado_date.year
    if año_numerado > 2012:
        stmt = (
            select(Notificacion.id)
            .where(
                Notificacion.numerado == numerado,
                Notificacion.fecha_numerado == fecha_numerado_date,
            )
        )
        if await db.scalar(stmt):
            raise HTTPException(
                status_code=400,
                detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra notificación",
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
    )

    db.add(nueva_notificacion)
    await db.flush()

    doc_ids_to_increment = [documento_citacion_id]
    if documento_notificacion_id and notificacion_exitosa:
        doc_ids_to_increment.append(documento_notificacion_id)

    await increment_file_usage(doc_ids_to_increment)

    tipo_notif_nombre = None
    if tipo_notificacion_id:
        tipo_notif = await db.scalar(select(TipoNotificacion.nombre).where(TipoNotificacion.id == tipo_notificacion_id))
        tipo_notif_nombre = tipo_notif

    datos_nuevos = {
        "involucrado_id": involucrado_id,
        "numerado": numerado,
        "fecha_numerado": fecha_numerado,
        "fecha_envio_citacion": fecha_envio_citacion,
        "fecha_constancia_citacion": fecha_constancia_citacion,
        "notificacion_exitosa": notificacion_exitosa,
        "tipo_notificacion": tipo_notif_nombre,
        "fecha_creacion": str(nueva_notificacion.fecha_creacion),
    }

    audit_result = await insert_log(
        db=db,
        tipo_evento="CREAR_NOTIFICACION",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Creación de notificación {numerado} para involucrado {involucrado_id}",
        expediente_id=expediente_id,
        expediente_radicado=radicado,
        datos_nuevos=datos_nuevos,
    )

    if not audit_result.get("ok"):
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

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
                "fecha_creacion": str(nueva_notificacion.fecha_creacion),
            },
        },
        status_code=201,
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
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
    fecha_envio_date = datetime.strptime(fecha_envio_citacion, "%Y-%m-%d").date()
    fecha_constancia_date = None
    if fecha_constancia_citacion and fecha_constancia_citacion.strip() and fecha_constancia_citacion != "None":
        fecha_constancia_date = datetime.strptime(fecha_constancia_citacion, "%Y-%m-%d").date()

    if not str(numerado).isdigit() or len(str(numerado)) > 4:
        raise HTTPException(
            status_code=400,
            detail="El numerado debe tener como máximo 4 dígitos",
        )

    if notificacion_exitosa and not tipo_notificacion_id:
        raise HTTPException(
            status_code=400,
            detail="Debe seleccionar un tipo de notificación si marca como exitosa",
        )

    if notificacion_exitosa and not documento_notificacion_id:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar un documento de notificación si marca como exitosa",
        )

    notificacion = await db.scalar(
        select(Notificacion).where(Notificacion.id == notificacion_id)
    )
    if not notificacion:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    _, _, _, etapa_expediente_id, radicado, encargado_id = await _get_acto_context(
        db, notificacion.acto_administrativo_id
    )

    if etapa_expediente_id != expediente_id:
        raise HTTPException(status_code=400, detail="El expediente no corresponde al acto administrativo")

    if encargado_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="No tiene permisos para modificar esta infracción",
        )

    datos_anteriores = {
        "involucrado_id": notificacion.involucrado_id,
        "numerado": notificacion.numerado,
        "fecha_numerado": str(notificacion.fecha_numerado) if notificacion.fecha_numerado else None,
        "fecha_envio_citacion": str(notificacion.fecha_envio_citacion) if notificacion.fecha_envio_citacion else None,
        "fecha_constancia_citacion": str(notificacion.fecha_constancia_citacion) if notificacion.fecha_constancia_citacion else None,
        "notificacion_exitosa": notificacion.notificacion_exitosa,
        # campos usados solo para tracking de documentos (no van al log de auditoría)
        "documento_citacion_id": notificacion.documento_citacion_id,
        "documento_notificacion_id": notificacion.documento_notificacion_id,
    }
    tipo_notif_ant = None
    if notificacion.tipo_notificacion_id:
        tipo_notif_ant = await db.scalar(select(TipoNotificacion.nombre).where(TipoNotificacion.id == notificacion.tipo_notificacion_id))

    año_numerado = fecha_numerado_date.year
    if año_numerado > 2012:
        stmt = (
            select(Notificacion.id)
            .where(
                Notificacion.numerado == numerado,
                Notificacion.fecha_numerado == fecha_numerado_date,
                Notificacion.id != notificacion_id,
            )
        )
        if await db.scalar(stmt):
            raise HTTPException(
                status_code=400,
                detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra notificación",
            )

    docs_to_increment = []
    docs_to_decrement = []

    if documento_citacion_id != datos_anteriores["documento_citacion_id"]:
        if datos_anteriores["documento_citacion_id"]:
            docs_to_decrement.append(datos_anteriores["documento_citacion_id"])
        docs_to_increment.append(documento_citacion_id)

    if notificacion_exitosa:
        if documento_notificacion_id != datos_anteriores["documento_notificacion_id"]:
            if datos_anteriores["documento_notificacion_id"]:
                docs_to_decrement.append(datos_anteriores["documento_notificacion_id"])
            if documento_notificacion_id:
                docs_to_increment.append(documento_notificacion_id)
    else:
        if datos_anteriores["documento_notificacion_id"]:
            docs_to_decrement.append(datos_anteriores["documento_notificacion_id"])

    if docs_to_decrement:
        await decrement_file_usage(docs_to_decrement)
    if docs_to_increment:
        await increment_file_usage(docs_to_increment)

    notificacion.numerado = numerado
    notificacion.fecha_numerado = fecha_numerado_date
    notificacion.fecha_envio_citacion = fecha_envio_date
    notificacion.fecha_constancia_citacion = fecha_constancia_date
    notificacion.documento_citacion_id = documento_citacion_id
    notificacion.notificacion_exitosa = notificacion_exitosa
    notificacion.tipo_notificacion_id = tipo_notificacion_id if tipo_notificacion_id else None
    notificacion.documento_notificacion_id = (
        documento_notificacion_id if notificacion_exitosa else None
    )

    if notificacion_exitosa and not datos_anteriores["notificacion_exitosa"]:
        notificacion.fecha_notificacion = datetime.now(bogota_tz)

    await db.flush()

    tipo_notif_nuevo = None
    if notificacion.tipo_notificacion_id:
        tipo_notif_nuevo = await db.scalar(select(TipoNotificacion.nombre).where(TipoNotificacion.id == notificacion.tipo_notificacion_id))

    audit_ant = {k: v for k, v in datos_anteriores.items() if k not in ("documento_citacion_id", "documento_notificacion_id")}
    audit_ant["tipo_notificacion"] = tipo_notif_ant

    datos_nuevos = {
        "involucrado_id": notificacion.involucrado_id,
        "numerado": notificacion.numerado,
        "fecha_numerado": str(notificacion.fecha_numerado),
        "fecha_envio_citacion": str(notificacion.fecha_envio_citacion),
        "fecha_constancia_citacion": str(notificacion.fecha_constancia_citacion) if notificacion.fecha_constancia_citacion else None,
        "notificacion_exitosa": notificacion.notificacion_exitosa,
        "tipo_notificacion": tipo_notif_nuevo,
        "fecha_notificacion": str(notificacion.fecha_notificacion) if notificacion.fecha_notificacion else None,
    }

    audit_result = await insert_log(
        db=db,
        tipo_evento="ACTUALIZAR_NOTIFICACION",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Actualización de notificación {numerado} para involucrado {notificacion.involucrado_id}",
        expediente_id=expediente_id,
        expediente_radicado=radicado,
        datos_anteriores=audit_ant,
        datos_nuevos=datos_nuevos,
    )

    if not audit_result.get("ok"):
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

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
                "fecha_creacion": str(notificacion.fecha_creacion),
            },
        },
        status_code=200,
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

    stmt = select(Expediente.abogado_responsable_id, Expediente.radicado).where(
        Expediente.id == expediente_id
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

    encargado_id, radicado = row

    if encargado_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="No tiene permisos para modificar esta infracción",
        )

    notificacion = await db.scalar(
        select(Notificacion).where(Notificacion.id == notificacion_id)
    )

    if not notificacion:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    tipo_notif_elim = None
    if notificacion.tipo_notificacion_id:
        tipo_notif_elim = await db.scalar(select(TipoNotificacion.nombre).where(TipoNotificacion.id == notificacion.tipo_notificacion_id))

    datos_notificacion = {
        "involucrado_id": notificacion.involucrado_id,
        "numerado": notificacion.numerado,
        "fecha_numerado": str(notificacion.fecha_numerado) if notificacion.fecha_numerado else None,
        "notificacion_exitosa": notificacion.notificacion_exitosa,
        "tipo_notificacion": tipo_notif_elim,
    }

    docs_to_decrement = [notificacion.documento_citacion_id]
    if notificacion.documento_notificacion_id:
        docs_to_decrement.append(notificacion.documento_notificacion_id)

    await decrement_file_usage(docs_to_decrement)

    await db.delete(notificacion)
    await db.flush()

    audit_result = await insert_log(
        db=db,
        tipo_evento="ELIMINAR_NOTIFICACION",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Eliminación de notificación {notificacion.numerado}",
        expediente_id=expediente_id,
        expediente_radicado=radicado,
        datos_anteriores=datos_notificacion,
    )

    if not audit_result.get("ok"):
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse(
        content={"ok": True, "data": datos_notificacion},
        status_code=200,
    )


# ── TIPO NOTIFICACIÓN ─────────────────────────────────────────────────────────

@router.get("/tipo-notificacion", status_code=200)
async def listar_tipos_notificacion(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    verify_gateway_token(request)
    tipos = (await db.execute(select(TipoNotificacion).order_by(TipoNotificacion.id))).scalars().all()
    return JSONResponse(
        content={"ok": True, "data": [{"id": t.id, "nombre": t.nombre} for t in tipos]},
        status_code=200,
    )


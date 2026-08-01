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


@router.post("/acto-admin")
async def crear_acto_admin(
    request: Request,
    expediente_id: int = Form(...),
    etapa_concepto_id: Optional[int] = Form(None),
    etapa_cierre_id: Optional[int] = Form(None),
    etapa_id: Optional[int] = Form(None),
    medida_preventiva_id: Optional[int] = Form(None),
    tipo_acto: str = Form(...),
    numerado: int = Form(...),
    fecha_numerado: str = Form(...),
    documento_acto_administrativo_id: int = Form(...),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]
    fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()

    if not numerado or len(str(numerado)) > 4:
        raise HTTPException(status_code=400, detail="El numerado debe tener como máximo 4 números")

    if tipo_acto not in ["AUTO", "RES"]:
        raise HTTPException(status_code=400, detail="El tipo de acto debe ser AUTO o RES")

    if medida_preventiva_id:
        # Contexto de medida preventiva
        medida = await db.scalar(
            select(MedidaPreventiva).where(MedidaPreventiva.id == medida_preventiva_id)
        )
        if not medida:
            raise HTTPException(status_code=404, detail="Medida preventiva no encontrada")

        etapa_resp = await db.scalar(
            select(EtapaRespuesta).where(EtapaRespuesta.id == medida.etapa_respuesta_id)
        )
        exp_row = (await db.execute(
            select(Expediente.id, Expediente.radicado, Expediente.abogado_responsable_id)
            .where(Expediente.id == etapa_resp.expediente_id)
        )).fetchone()
        if not exp_row:
            raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

        etapa_expediente_id, radicado, encargado_id = exp_row
        if etapa_expediente_id != expediente_id:
            raise HTTPException(status_code=400, detail="El expediente no corresponde a la medida preventiva")
        if encargado_id != user_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para modificar esta infracción")
        if medida.acto_administrativo_id:
            raise HTTPException(status_code=400, detail="El acto administrativo ya existe para esta medida")
        etapa_tipo = "medida"
        etapa = medida
    else:
        etapa_concepto_id, etapa_cierre_id = _resolve_etapa_ids(
            etapa_concepto_id, etapa_cierre_id, etapa_id
        )
        etapa_tipo, etapa, etapa_expediente_id, radicado, encargado_id = await _get_etapa_context(
            db, etapa_concepto_id, etapa_cierre_id
        )

        if etapa_expediente_id != expediente_id:
            raise HTTPException(status_code=400, detail="El expediente no corresponde a la etapa seleccionada")

        if encargado_id != user_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para modificar esta infracción")

        if etapa.acto_administrativo_id:
            raise HTTPException(status_code=400, detail="El acto administrativo ya existe para esta etapa")

    año_numerado = fecha_numerado_date.year
    if año_numerado > 2012:
        stmt = (
            select(ActoAdministrativo.id)
            .where(
                ActoAdministrativo.numerado == numerado,
                ActoAdministrativo.fecha_numerado == fecha_numerado_date,
            )
        )
        if await db.scalar(stmt):
            raise HTTPException(
                status_code=400,
                detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso",
            )

    nuevo_acto = ActoAdministrativo(
        tipo_acto=tipo_acto,
        numerado=numerado,
        fecha_numerado=fecha_numerado_date,
        documento_acto_administrativo_id=documento_acto_administrativo_id,
    )

    db.add(nuevo_acto)
    await db.flush()

    etapa.acto_administrativo_id = nuevo_acto.id
    await db.flush()

    await increment_file_usage([documento_acto_administrativo_id])

    datos_nuevos = {
        "tipo_acto": tipo_acto,
        "numerado": numerado,
        "fecha_numerado": fecha_numerado,
        "fecha_creacion": str(nuevo_acto.fecha_creacion),
        "etapa_tipo": etapa_tipo,
    }

    audit_result = await insert_log(
        db=db,
        tipo_evento="CREAR_ACTO_ADMIN",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Creación de acto administrativo {tipo_acto} {numerado}",
        expediente_id=etapa_expediente_id,
        expediente_radicado=radicado,
        datos_nuevos=datos_nuevos,
    )

    if not audit_result.get("ok"):
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()
    await db.refresh(nuevo_acto)

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": nuevo_acto.id,
                "numerado": nuevo_acto.numerado,
                "fecha_numerado": str(nuevo_acto.fecha_numerado),
                "documento_acto_id": nuevo_acto.documento_acto_administrativo_id,
                "tipo_acto": nuevo_acto.tipo_acto,
                "fecha_creacion": str(nuevo_acto.fecha_creacion),
            },
        },
        status_code=201,
    )


@router.put("/acto-admin/{acto_id}")
async def actualizar_acto_admin(
    request: Request,
    acto_id: int,
    expediente_id: Optional[int] = Form(None),
    tipo_acto: str = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    documento_acto_administrativo_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]
    fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()

    if not numerado or len(str(numerado)) > 4:
        raise HTTPException(status_code=400, detail="El numerado debe tener como máximo 4 números")

    if tipo_acto not in ["AUTO", "RES"]:
        raise HTTPException(status_code=400, detail="El tipo de acto debe ser AUTO o RES")

    _, acto_admin, _, etapa_expediente_id, radicado, encargado_id = await _get_acto_context(
        db, acto_id
    )

    if expediente_id and expediente_id != etapa_expediente_id:
        raise HTTPException(status_code=400, detail="El expediente no corresponde al acto administrativo")

    if encargado_id != user_id:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar esta infracción")

    datos_anteriores = {
        "tipo_acto": acto_admin.tipo_acto,
        "numerado": acto_admin.numerado,
        "fecha_numerado": str(acto_admin.fecha_numerado) if acto_admin.fecha_numerado else None,
    }

    año_numerado = fecha_numerado_date.year
    if año_numerado > 2012:
        stmt = (
            select(ActoAdministrativo.id)
            .where(
                ActoAdministrativo.numerado == int(numerado),
                ActoAdministrativo.fecha_numerado == fecha_numerado_date,
                ActoAdministrativo.id != acto_id,
            )
        )
        if await db.scalar(stmt):
            raise HTTPException(
                status_code=400,
                detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso",
            )

    if (
        documento_acto_administrativo_id
        and documento_acto_administrativo_id != acto_admin.documento_acto_administrativo_id
    ):
        await decrement_file_usage([acto_admin.documento_acto_administrativo_id])
        await increment_file_usage([documento_acto_administrativo_id])
        acto_admin.documento_acto_administrativo_id = documento_acto_administrativo_id

    acto_admin.tipo_acto = tipo_acto
    acto_admin.numerado = int(numerado)
    acto_admin.fecha_numerado = fecha_numerado_date

    await db.flush()

    datos_nuevos = {
        "tipo_acto": acto_admin.tipo_acto,
        "numerado": acto_admin.numerado,
        "fecha_numerado": str(acto_admin.fecha_numerado),
    }

    audit_result = await insert_log(
        db=db,
        tipo_evento="ACTUALIZAR_ACTO_ADMIN",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Actualización de acto administrativo {acto_admin.tipo_acto} {acto_admin.numerado}",
        expediente_id=etapa_expediente_id,
        expediente_radicado=radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
    )

    if not audit_result.get("ok"):
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()
    await db.refresh(acto_admin)

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": acto_admin.id,
                "numerado": acto_admin.numerado,
                "fecha_numerado": str(acto_admin.fecha_numerado),
                "documento_acto_id": acto_admin.documento_acto_administrativo_id,
                "tipo_acto": acto_admin.tipo_acto,
                "fecha_creacion": str(acto_admin.fecha_creacion),
            },
        },
        status_code=200,
    )


@router.delete("/acto-admin/{acto_id}")
async def eliminar_acto_admin(
    request: Request,
    acto_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    etapa_tipo, acto_admin, etapa, etapa_expediente_id, radicado, encargado_id = await _get_acto_context(
        db, acto_id
    )

    if encargado_id != user_id:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar esta infracción")

    datos_acto = {
        "tipo_acto": acto_admin.tipo_acto,
        "numerado": acto_admin.numerado,
        "fecha_numerado": str(acto_admin.fecha_numerado) if acto_admin.fecha_numerado else None,
        "etapa_tipo": etapa_tipo,
    }

    # Decrementar documentos del acto y notificaciones asociadas
    docs_to_decrement = [acto_admin.documento_acto_administrativo_id]
    notificaciones = (await db.execute(
        select(Notificacion).where(Notificacion.acto_administrativo_id == acto_id)
    )).scalars().all()

    for notificacion in notificaciones:
        if notificacion.documento_citacion_id:
            docs_to_decrement.append(notificacion.documento_citacion_id)
        if notificacion.documento_notificacion_id:
            docs_to_decrement.append(notificacion.documento_notificacion_id)

    if docs_to_decrement:
        await decrement_file_usage(list(set(docs_to_decrement)))

    etapa.acto_administrativo_id = None
    await db.delete(acto_admin)
    await db.flush()

    audit_result = await insert_log(
        db=db,
        tipo_evento="ELIMINAR_ACTO_ADMIN",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Eliminación de acto administrativo {datos_acto['tipo_acto']} {datos_acto['numerado']}",
        expediente_id=etapa_expediente_id,
        expediente_radicado=radicado,
        datos_anteriores=datos_acto,
    )

    if not audit_result.get("ok"):
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse(
        content={"ok": True, "data": datos_acto},
        status_code=200,
    )


# Notificación

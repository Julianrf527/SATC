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


# ── COMUNICACIÓN ──────────────────────────────────────────────────────────────

@router.post("/comunicacion")
async def crear_comunicacion(
    request: Request,
    expediente_id: int = Form(...),
    acto_admin_id: int = Form(...),
    numerado: int = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio: str = Form(...),
    documento_comunicacion_id: int = Form(...),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
    fecha_envio_date = datetime.strptime(fecha_envio, "%Y-%m-%d").date()

    if not str(numerado).isdigit() or len(str(numerado)) > 4:
        raise HTTPException(status_code=400, detail="El numerado debe tener como máximo 4 dígitos")

    _, acto_admin, _, etapa_expediente_id, radicado, encargado_id = await _get_acto_context(db, acto_admin_id)

    if etapa_expediente_id != expediente_id:
        raise HTTPException(status_code=400, detail="El expediente no corresponde al acto administrativo")
    if encargado_id != user_id:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar esta infracción")

    existing = await db.scalar(
        select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto_admin_id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="La comunicación ya existe para este acto administrativo")

    nueva = Comunicacion(
        acto_administrativo_id=acto_admin_id,
        numerado=numerado,
        fecha_numerado=fecha_numerado_date,
        fecha_envio=fecha_envio_date,
        documento_comunicacion_id=documento_comunicacion_id,
    )
    db.add(nueva)
    await db.flush()

    await increment_file_usage([documento_comunicacion_id])

    audit_result = await insert_log(
        db=db,
        tipo_evento="CREAR_COMUNICACION",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Creación de comunicación {numerado}",
        expediente_id=expediente_id,
        expediente_radicado=radicado,
        datos_nuevos={"numerado": numerado, "fecha_numerado": fecha_numerado, "fecha_envio": fecha_envio},
    )
    if not audit_result.get("ok"):
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()
    await db.refresh(nueva)

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": nueva.id,
                "acto_administrativo_id": nueva.acto_administrativo_id,
                "numerado": nueva.numerado,
                "fecha_numerado": str(nueva.fecha_numerado),
                "fecha_envio": str(nueva.fecha_envio),
                "documento_comunicacion_id": nueva.documento_comunicacion_id,
            },
        },
        status_code=201,
    )


@router.put("/comunicacion/{comunicacion_id}")
async def actualizar_comunicacion(
    request: Request,
    comunicacion_id: int,
    expediente_id: int = Form(...),
    numerado: int = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio: str = Form(...),
    documento_comunicacion_id: int = Form(...),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
    fecha_envio_date = datetime.strptime(fecha_envio, "%Y-%m-%d").date()

    com = await db.scalar(select(Comunicacion).where(Comunicacion.id == comunicacion_id))
    if not com:
        raise HTTPException(status_code=404, detail="Comunicación no encontrada")

    _, _, _, etapa_expediente_id, radicado, encargado_id = await _get_acto_context(db, com.acto_administrativo_id)

    if etapa_expediente_id != expediente_id:
        raise HTTPException(status_code=400, detail="El expediente no corresponde al acto administrativo")
    if encargado_id != user_id:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar esta infracción")

    datos_anteriores = {
        "numerado": com.numerado,
        "fecha_numerado": str(com.fecha_numerado) if com.fecha_numerado else None,
        "fecha_envio": str(com.fecha_envio) if com.fecha_envio else None,
        "documento_comunicacion_id": com.documento_comunicacion_id,
    }

    if documento_comunicacion_id != com.documento_comunicacion_id:
        await decrement_file_usage([com.documento_comunicacion_id])
        await increment_file_usage([documento_comunicacion_id])

    com.numerado = numerado
    com.fecha_numerado = fecha_numerado_date
    com.fecha_envio = fecha_envio_date
    com.documento_comunicacion_id = documento_comunicacion_id
    await db.flush()

    audit_result = await insert_log(
        db=db,
        tipo_evento="ACTUALIZAR_COMUNICACION",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Actualización de comunicación {numerado}",
        expediente_id=expediente_id,
        expediente_radicado=radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos={"numerado": numerado, "fecha_numerado": fecha_numerado, "fecha_envio": fecha_envio},
    )
    if not audit_result.get("ok"):
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": com.id,
                "acto_administrativo_id": com.acto_administrativo_id,
                "numerado": com.numerado,
                "fecha_numerado": str(com.fecha_numerado),
                "fecha_envio": str(com.fecha_envio),
                "documento_comunicacion_id": com.documento_comunicacion_id,
            },
        },
        status_code=200,
    )


@router.delete("/comunicacion/{comunicacion_id}")
async def eliminar_comunicacion(
    request: Request,
    comunicacion_id: int,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]
    expediente_id = data.get("expediente_id")

    if not expediente_id:
        raise HTTPException(status_code=422, detail="expediente_id es requerido")

    com = await db.scalar(select(Comunicacion).where(Comunicacion.id == comunicacion_id))
    if not com:
        raise HTTPException(status_code=404, detail="Comunicación no encontrada")

    _, _, _, etapa_expediente_id, radicado, encargado_id = await _get_acto_context(db, com.acto_administrativo_id)

    if etapa_expediente_id != expediente_id:
        raise HTTPException(status_code=400, detail="El expediente no corresponde al acto administrativo")
    if encargado_id != user_id:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar esta infracción")

    datos_com = {
        "id": com.id,
        "acto_administrativo_id": com.acto_administrativo_id,
        "numerado": com.numerado,
        "documento_comunicacion_id": com.documento_comunicacion_id,
    }

    if com.documento_comunicacion_id:
        await decrement_file_usage([com.documento_comunicacion_id])

    await db.delete(com)
    await db.flush()

    audit_result = await insert_log(
        db=db,
        tipo_evento="ELIMINAR_COMUNICACION",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Eliminación de comunicación {com.numerado}",
        expediente_id=expediente_id,
        expediente_radicado=radicado,
        datos_anteriores=datos_com,
    )
    if not audit_result.get("ok"):
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse(content={"ok": True, "data": datos_com}, status_code=200)


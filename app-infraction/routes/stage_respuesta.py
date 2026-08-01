from fastapi import Request, APIRouter, Depends, HTTPException, Path as PathParam
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
import holidays
import logging
import os
import pytz
import re

from db.deps import get_db_managed
from db.models.expediente import Expediente
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.informe_tecnico import InformeTecnico
from db.models.medida_preventiva import MedidaPreventiva
from db.models.tipo_medida import TipoMedida
from db.models.acto_administrativo import ActoAdministrativo
from db.models.comunicacion import Comunicacion
from db.models.notificacion import Notificacion
from db.models.oficio_remite import OficioRemite
from db.models.solicitud_informacion import SolicitudInformacion
from db.models.expediente_involucrado import ExpedienteInvolucrado

router = APIRouter()
load_dotenv()

bogota_tz = pytz.timezone("America/Bogota")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from utils.verify_token import verify_gateway_token
from services.users import get_user_info
from services.involved import get_involucrados_by_ids
from services.docs import decrement_file_usage
from services.etapas import build_acto_for_frontend as _build_acto_for_frontend
from services.etapas import get_expediente_con_permiso
from utils.log import insert_log


class RespuestaBody(BaseModel):
    radicado: str
    fecha_radicado: date
    documento_radicado_id: int
    requiere_medida_preventiva: bool


class MedidaBody(BaseModel):
    tipo_medida_id: int
    cantidad: str
    especie: str
    estado_medida: Optional[bool] = None


async def _get_local_medida(db: AsyncSession, etapa_respuesta_id: int) -> dict:
    medida = await db.scalar(
        select(MedidaPreventiva).where(MedidaPreventiva.etapa_respuesta_id == etapa_respuesta_id)
    )
    if not medida:
        return {"ok": False, "message": "Medida preventiva aún no creada"}

    tipos = (await db.execute(select(TipoMedida).order_by(TipoMedida.id))).scalars().all()

    acto_data = None
    if medida.acto_administrativo_id:
        acto = await db.scalar(
            select(ActoAdministrativo).where(ActoAdministrativo.id == medida.acto_administrativo_id)
        )
        if acto:
            acto_data = await _build_acto_for_frontend(db, acto)

    return {
        "ok": True,
        "medida": {
            "id": medida.id,
            "etapa_respuesta_id": medida.etapa_respuesta_id,
            "acto_administrativo_id": medida.acto_administrativo_id,
            "informacion": {
                "tipo_medida_id": medida.tipo_medida_id,
                "cantidad": medida.cantidad,
                "especie": medida.especie,
                "estado_medida": medida.estado_medida,
                "tipo_medidas": [{"id": t.id, "nombre": t.nombre} for t in tipos],
            },
            "acto_admin": acto_data,
        },
    }


# ── ETAPA RESPUESTA ────────────────────────────────────────────────────────────

@router.post("/answer/{expediente_id}", status_code=201)
async def crear_respuesta(
    request: Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    body: RespuestaBody = ...,
    db: AsyncSession = Depends(get_db_managed),
):
    try:
        token_data = verify_gateway_token(request)
        user_id = token_data["user_id"]

        _eid, exp_radicado, _abg = await get_expediente_con_permiso(db, expediente_id, user_id)

        if await db.scalar(
            select(EtapaRespuesta.id).where(EtapaRespuesta.expediente_id == expediente_id)
        ):
            raise HTTPException(status_code=409, detail="La etapa de respuesta ya existe para este expediente")

        if await db.scalar(
            select(EtapaRespuesta.id).where(EtapaRespuesta.radicado == body.radicado)
        ):
            raise HTTPException(status_code=409, detail="El radicado ya está registrado en otra respuesta")

        nueva = EtapaRespuesta(
            expediente_id=expediente_id,
            radicado=body.radicado,
            fecha_radicado=body.fecha_radicado,
            documento_radicado_id=body.documento_radicado_id,
            requiere_medida_preventiva=body.requiere_medida_preventiva,
            fecha_creacion=datetime.now(bogota_tz).date(),
        )
        db.add(nueva)
        await db.flush()

        audit_result = await insert_log(
            db=db,
            tipo_evento="CREAR_ETAPA_RESPUESTA",
            resultado="EXITOSO",
            usuario_id=user_id,
            detalle="Creación Etapa respuesta",
            expediente_id=expediente_id,
            expediente_radicado=exp_radicado,
            datos_anteriores=None,
            datos_nuevos={
                "expediente_id": expediente_id,
                "radicado_siaf": body.radicado,
                "fecha_radicado_siaf": body.fecha_radicado.isoformat(),
                "documento_radicado_id": body.documento_radicado_id,
                "requiere_medida_preventiva": body.requiere_medida_preventiva,
            },
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

        await db.commit()

        medida_preventiva = {"ok": False, "message": "No se requiere medida preventiva"}
        if body.requiere_medida_preventiva:
            existing_medida = await db.scalar(
                select(MedidaPreventiva).where(MedidaPreventiva.etapa_respuesta_id == nueva.id)
            )
            if not existing_medida:
                db.add(MedidaPreventiva(etapa_respuesta_id=nueva.id))
                await db.commit()
            medida_preventiva = await _get_local_medida(db, nueva.id)

        return JSONResponse(
            content={
                "ok": True,
                "respuesta_data": {
                    "id": nueva.id,
                    "expediente_id": expediente_id,
                    "radicado": body.radicado,
                    "fecha_radicado": body.fecha_radicado.isoformat(),
                    "documento_radicado_id": body.documento_radicado_id,
                    "requiere_medida_preventiva": body.requiere_medida_preventiva,
                    "fecha_creacion": nueva.fecha_creacion.isoformat(),
                },
                "medida_preventiva": medida_preventiva,
                "message": "Etapa respuesta creada correctamente",
            },
            status_code=201,
        )

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"Integridad al crear respuesta: {e}", exc_info=True)
        raise HTTPException(status_code=409, detail="Conflicto de datos al crear la respuesta")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando etapa respuesta: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.put("/answer/{etapa_id}", status_code=200)
async def actualizar_respuesta(
    request: Request,
    etapa_id: int = PathParam(..., description="ID de la etapa a actualizar"),
    body: RespuestaBody = ...,
    db: AsyncSession = Depends(get_db_managed),
):
    try:
        token_data = verify_gateway_token(request)
        user_id = token_data["user_id"]

        etapa_respuesta = await db.scalar(
            select(EtapaRespuesta).where(EtapaRespuesta.id == etapa_id)
        )
        if not etapa_respuesta:
            raise HTTPException(status_code=404, detail="Etapa de respuesta no encontrada")

        exp_row = (await db.execute(
            select(Expediente.radicado, Expediente.abogado_responsable_id)
            .where(Expediente.id == etapa_respuesta.expediente_id)
        )).fetchone()

        if not exp_row:
            raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

        exp_radicado, abogado_id = exp_row
        if abogado_id != user_id:
            raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

        if await db.scalar(
            select(EtapaRespuesta.id).where(
                EtapaRespuesta.radicado == body.radicado,
                EtapaRespuesta.id != etapa_id,
            )
        ):
            raise HTTPException(status_code=409, detail="El radicado ya está registrado en otra respuesta")

        datos_anteriores = {
            "radicado_siaf": etapa_respuesta.radicado,
            "fecha_radicado_siaf": etapa_respuesta.fecha_radicado.isoformat(),
            "documento_radicado_id": etapa_respuesta.documento_radicado_id,
            "requiere_medida_preventiva": etapa_respuesta.requiere_medida_preventiva,
        }

        await db.execute(
            update(EtapaRespuesta)
            .where(EtapaRespuesta.id == etapa_id)
            .values(
                radicado=body.radicado,
                fecha_radicado=body.fecha_radicado,
                documento_radicado_id=body.documento_radicado_id,
                requiere_medida_preventiva=body.requiere_medida_preventiva,
            )
        )
        await db.flush()
        await db.refresh(etapa_respuesta)

        audit_result = await insert_log(
            db=db,
            tipo_evento="ACTUALIZAR_ETAPA_RESPUESTA",
            resultado="EXITOSO",
            usuario_id=user_id,
            detalle="Actualización Etapa respuesta",
            expediente_id=etapa_respuesta.expediente_id,
            expediente_radicado=exp_radicado,
            datos_anteriores=datos_anteriores,
            datos_nuevos={
                "radicado_siaf": body.radicado,
                "fecha_radicado_siaf": body.fecha_radicado.isoformat(),
                "documento_radicado_id": body.documento_radicado_id,
                "requiere_medida_preventiva": body.requiere_medida_preventiva,
            },
        )
        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

        await db.commit()

        # Medida preventiva: si se desmarca, la info se conserva en BD pero no se retorna
        medida_preventiva = {"ok": False, "message": "No se requiere medida preventiva"}
        if body.requiere_medida_preventiva:
            existing_medida = await db.scalar(
                select(MedidaPreventiva).where(MedidaPreventiva.etapa_respuesta_id == etapa_id)
            )
            if not existing_medida:
                db.add(MedidaPreventiva(etapa_respuesta_id=etapa_id))
                await db.commit()
            medida_preventiva = await _get_local_medida(db, etapa_id)

        return JSONResponse(
            content={
                "ok": True,
                "respuesta_data": {
                    "id": etapa_id,
                    "expediente_id": etapa_respuesta.expediente_id,
                    "radicado": body.radicado,
                    "fecha_radicado": body.fecha_radicado.isoformat(),
                    "documento_radicado_id": body.documento_radicado_id,
                    "requiere_medida_preventiva": body.requiere_medida_preventiva,
                    "fecha_creacion": etapa_respuesta.fecha_creacion.isoformat(),
                },
                "medida_preventiva": medida_preventiva,
                "message": "Etapa respuesta actualizada correctamente",
            },
            status_code=200,
        )

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"Integridad al actualizar respuesta: {e}", exc_info=True)
        raise HTTPException(status_code=409, detail="Conflicto de datos al actualizar la respuesta")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error actualizando etapa de respuesta: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/answer/{expediente_id}", status_code=200)
async def obtener_respuesta(
    request: Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    db: AsyncSession = Depends(get_db_managed),
):
    verify_gateway_token(request)

    etapa_respuesta = await db.scalar(
        select(EtapaRespuesta).where(EtapaRespuesta.expediente_id == expediente_id)
    )
    if not etapa_respuesta:
        raise HTTPException(status_code=404, detail="Etapa de respuesta no encontrada")

    medida_preventiva = {"ok": False, "message": "No se requiere medida preventiva"}
    if etapa_respuesta.requiere_medida_preventiva:
        medida_preventiva = await _get_local_medida(db, etapa_respuesta.id)

    return JSONResponse(
        content={
            "ok": True,
            "respuesta_data": {
                "id": etapa_respuesta.id,
                "expediente_id": etapa_respuesta.expediente_id,
                "radicado": etapa_respuesta.radicado,
                "fecha_radicado": etapa_respuesta.fecha_radicado.isoformat(),
                "documento_radicado_id": etapa_respuesta.documento_radicado_id,
                "requiere_medida_preventiva": etapa_respuesta.requiere_medida_preventiva,
                "fecha_creacion": etapa_respuesta.fecha_creacion.isoformat(),
            },
            "medida_preventiva": medida_preventiva,
        },
        status_code=200,
    )


# ── MEDIDA PREVENTIVA ──────────────────────────────────────────────────────────

@router.get("/tipo-medida", status_code=200)
async def listar_tipos_medida(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    verify_gateway_token(request)
    tipos = (await db.execute(select(TipoMedida).order_by(TipoMedida.id))).scalars().all()
    return JSONResponse(
        content={"ok": True, "data": [{"id": t.id, "nombre": t.nombre} for t in tipos]},
        status_code=200,
    )


@router.post("/medida/{etapa_respuesta_id}", status_code=201)
async def crear_medida(
    request: Request,
    etapa_respuesta_id: int = PathParam(..., description="ID de la etapa respuesta"),
    body: MedidaBody = ...,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    etapa = await db.scalar(
        select(EtapaRespuesta).where(EtapaRespuesta.id == etapa_respuesta_id)
    )
    if not etapa:
        raise HTTPException(status_code=404, detail="Etapa de respuesta no encontrada")

    exp_row = (await db.execute(
        select(Expediente.radicado, Expediente.abogado_responsable_id, Expediente.id)
        .where(Expediente.id == etapa.expediente_id)
    )).fetchone()
    if not exp_row:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

    exp_radicado, abogado_id, expediente_id = exp_row
    if abogado_id != user_id:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

    if not etapa.requiere_medida_preventiva:
        raise HTTPException(status_code=400, detail="Esta etapa no requiere medida preventiva")

    if await db.scalar(
        select(MedidaPreventiva.id).where(MedidaPreventiva.etapa_respuesta_id == etapa_respuesta_id)
    ):
        raise HTTPException(status_code=409, detail="La medida preventiva ya existe para esta etapa")

    nueva_medida = MedidaPreventiva(
        etapa_respuesta_id=etapa_respuesta_id,
        tipo_medida_id=body.tipo_medida_id,
        cantidad=body.cantidad,
        especie=body.especie,
        estado_medida=body.estado_medida,
    )
    db.add(nueva_medida)
    await db.flush()

    tipo_medida_nombre = await db.scalar(select(TipoMedida.nombre).where(TipoMedida.id == body.tipo_medida_id))

    audit_result = await insert_log(
        db=db,
        tipo_evento="CREAR_MEDIDA_PREVENTIVA",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle="Creación de medida preventiva",
        expediente_id=expediente_id,
        expediente_radicado=exp_radicado,
        datos_nuevos={
            "tipo_medida": tipo_medida_nombre,
            "cantidad": body.cantidad,
            "especie": body.especie,
            "estado_medida": body.estado_medida,
        },
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    result = await _get_local_medida(db, etapa_respuesta_id)
    return JSONResponse(content={"ok": True, **result}, status_code=201)


@router.put("/medida/{medida_id}", status_code=200)
async def actualizar_medida(
    request: Request,
    medida_id: int = PathParam(..., description="ID de la medida preventiva"),
    body: MedidaBody = ...,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    medida = await db.scalar(
        select(MedidaPreventiva).where(MedidaPreventiva.id == medida_id)
    )
    if not medida:
        raise HTTPException(status_code=404, detail="Medida preventiva no encontrada")

    etapa = await db.scalar(
        select(EtapaRespuesta).where(EtapaRespuesta.id == medida.etapa_respuesta_id)
    )
    exp_row = (await db.execute(
        select(Expediente.radicado, Expediente.abogado_responsable_id, Expediente.id)
        .where(Expediente.id == etapa.expediente_id)
    )).fetchone()
    if not exp_row:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

    exp_radicado, abogado_id, expediente_id = exp_row
    if abogado_id != user_id:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

    tipo_medida_ant = await db.scalar(select(TipoMedida.nombre).where(TipoMedida.id == medida.tipo_medida_id))
    datos_anteriores = {
        "tipo_medida": tipo_medida_ant,
        "cantidad": medida.cantidad,
        "especie": medida.especie,
        "estado_medida": medida.estado_medida,
    }

    await db.execute(
        update(MedidaPreventiva)
        .where(MedidaPreventiva.id == medida_id)
        .values(
            tipo_medida_id=body.tipo_medida_id,
            cantidad=body.cantidad,
            especie=body.especie,
            estado_medida=body.estado_medida,
        )
    )
    await db.flush()

    audit_result = await insert_log(
        db=db,
        tipo_evento="ACTUALIZAR_MEDIDA_PREVENTIVA",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle="Actualización de medida preventiva",
        expediente_id=expediente_id,
        expediente_radicado=exp_radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos={
            "tipo_medida": await db.scalar(select(TipoMedida.nombre).where(TipoMedida.id == body.tipo_medida_id)),
            "cantidad": body.cantidad,
            "especie": body.especie,
            "estado_medida": body.estado_medida,
        },
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    result = await _get_local_medida(db, medida.etapa_respuesta_id)
    return JSONResponse(content={"ok": True, **result}, status_code=200)


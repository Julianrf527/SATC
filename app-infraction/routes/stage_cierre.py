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


async def _build_cierre_response(db: AsyncSession, etapa: EtapaCierre) -> dict:
    """Construye el dict de respuesta enriquecido para una EtapaCierre."""
    acto_data = None
    if etapa.acto_administrativo_id:
        acto = await db.scalar(
            select(ActoAdministrativo).where(ActoAdministrativo.id == etapa.acto_administrativo_id)
        )
        if acto:
            acto_data = await _build_acto_for_frontend(db, acto)

    return {
        "id": etapa.id,
        "expediente_id": etapa.expediente_id,
        "acto_administrativo_id": etapa.acto_administrativo_id,
        "fecha_creacion": etapa.fecha_creacion.isoformat(),
        "acto_admin": acto_data,
    }


# ── ETAPA CIERRE ──────────────────────────────────────────────────────────────

@router.get("/cierre/{expediente_id}", status_code=200)
async def obtener_cierre(
    request: Request,
    expediente_id: int = PathParam(...),
    db: AsyncSession = Depends(get_db_managed),
):
    verify_gateway_token(request)

    etapa = await db.scalar(
        select(EtapaCierre).where(EtapaCierre.expediente_id == expediente_id)
    )

    if not etapa:
        concepto = await db.scalar(
            select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.expediente_id == expediente_id)
        )
        creable = False
        creable_msg = None

        if not concepto:
            creable_msg = "La etapa de Concepto Técnico aún no ha sido creada"
        elif concepto.tipo_acogida_concepto == "AUTO_REQUERIMIENTO":
            informe_seg = await db.scalar(
                select(InformeTecnico).where(
                    InformeTecnico.expediente_id == expediente_id,
                    InformeTecnico.tipo_informe == "SEGUIMIENTO",
                    InformeTecnico.fecha_aceptacion_informe.isnot(None),
                )
            )
            if not informe_seg:
                creable_msg = 'El informe técnico de "SEGUIMIENTO" aún no ha sido aceptado'
            else:
                creable = True
        elif concepto.tipo_acogida_concepto == "RESOLUCION_ARCHIVO":
            creable = True
        elif concepto.tipo_acogida_concepto == "OFICIO":
            oficio_r = await db.scalar(
                select(OficioRemite).where(OficioRemite.etapa_acoger_concepto_id == concepto.id)
            )
            if oficio_r and oficio_r.archivo_remite_id:
                creable = True
            else:
                creable_msg = "El oficio de remisión aún no ha sido registrado con su documento"

        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "detail": "Etapa cierre no encontrada",
                "creable": creable,
                "creable_msg": creable_msg,
            },
        )

    data = await _build_cierre_response(db, etapa)
    return JSONResponse(content={"ok": True, "data": data}, status_code=200)


@router.post("/cierre/{expediente_id}", status_code=201)
async def crear_cierre(
    request: Request,
    expediente_id: int = PathParam(...),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    _eid, exp_radicado, _abg = await get_expediente_con_permiso(db, expediente_id, user_id)

    if await db.scalar(select(EtapaCierre.id).where(EtapaCierre.expediente_id == expediente_id)):
        raise HTTPException(status_code=409, detail="La etapa de cierre ya existe para este expediente")

    concepto = await db.scalar(
        select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.expediente_id == expediente_id)
    )
    if not concepto:
        raise HTTPException(status_code=400, detail="La etapa de Concepto Técnico aún no ha sido creada")

    if concepto.tipo_acogida_concepto == "AUTO_REQUERIMIENTO":
        informe_seg = await db.scalar(
            select(InformeTecnico).where(
                InformeTecnico.expediente_id == expediente_id,
                InformeTecnico.tipo_informe == "SEGUIMIENTO",
                InformeTecnico.fecha_aceptacion_informe.isnot(None),
            )
        )
        if not informe_seg:
            raise HTTPException(
                status_code=400,
                detail='El informe técnico de "SEGUIMIENTO" aún no ha sido aceptado',
            )
    elif concepto.tipo_acogida_concepto == "OFICIO":
        oficio_r = await db.scalar(
            select(OficioRemite).where(OficioRemite.etapa_acoger_concepto_id == concepto.id)
        )
        if not oficio_r or not oficio_r.archivo_remite_id:
            raise HTTPException(
                status_code=400,
                detail="El oficio de remisión aún no ha sido registrado con su documento",
            )

    nueva = EtapaCierre(expediente_id=expediente_id)
    db.add(nueva)
    await db.flush()

    audit_result = await insert_log(
        db=db,
        tipo_evento="CREAR_ETAPA_CIERRE",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle="Creación Etapa de cierre",
        expediente_id=expediente_id,
        expediente_radicado=exp_radicado,
        datos_nuevos={"radicado": exp_radicado},
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()
    await db.refresh(nueva)

    data = await _build_cierre_response(db, nueva)
    return JSONResponse(
        content={"ok": True, "data": data, "message": "Etapa de cierre creada correctamente"},
        status_code=201,
    )


# ── MIGRACIÓN A SANCIONATORIO ──────────────────────────────────────────────────

@router.get("/migration/medida/{radicado}", status_code=200)
async def obtener_datos_migracion_medida(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Retorna datos de medida preventiva e informe técnico VISITA aprobado
    para un expediente de infracciones, por radicado.
    Usado por sancionatorio para importar datos al crear su medida preventiva.
    """
    try:
        verify_gateway_token(request)

        expediente = await db.scalar(
            select(Expediente).where(Expediente.radicado == radicado)
        )
        if not expediente:
            return JSONResponse(content={"ok": False, "detail": "Expediente de infracciones no encontrado"}, status_code=200)

        etapa_resp = await db.scalar(
            select(EtapaRespuesta).where(
                EtapaRespuesta.expediente_id == expediente.id,
                EtapaRespuesta.requiere_medida_preventiva == True,
            )
        )
        if not etapa_resp:
            return JSONResponse(content={"ok": False, "detail": "No existe medida preventiva en infracciones para este radicado"}, status_code=200)

        medida = await db.scalar(
            select(MedidaPreventiva).where(MedidaPreventiva.etapa_respuesta_id == etapa_resp.id)
        )
        if not medida:
            return JSONResponse(content={"ok": False, "detail": "Medida preventiva aún no registrada en infracciones"}, status_code=200)

        # Informe técnico VISITA aprobado
        informe = await db.scalar(
            select(InformeTecnico).where(
                InformeTecnico.expediente_id == expediente.id,
                InformeTecnico.tipo_informe == "VISITA",
                InformeTecnico.fecha_aceptacion_informe.isnot(None),
                InformeTecnico.documento_informe_id.isnot(None),
            )
        )

        # Acto administrativo de la medida (solo si tiene documento)
        acto_data = None
        if medida.acto_administrativo_id:
            acto_row = await db.scalar(
                select(ActoAdministrativo).where(ActoAdministrativo.id == medida.acto_administrativo_id)
            )
            if acto_row and acto_row.documento_acto_administrativo_id:
                acto_data = {
                    "tipo_acto": acto_row.tipo_acto,
                    "numerado": acto_row.numerado,
                    "fecha_numerado": acto_row.fecha_numerado.isoformat() if acto_row.fecha_numerado else None,
                    "documento_acto_administrativo_id": acto_row.documento_acto_administrativo_id,
                }

                # Comunicación asociada al acto (solo si tiene documento)
                com_row = await db.scalar(
                    select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto_row.id)
                )
                if com_row and com_row.documento_comunicacion_id:
                    acto_data["comunicacion"] = {
                        "numerado": com_row.numerado,
                        "fecha_numerado": com_row.fecha_numerado.isoformat() if com_row.fecha_numerado else None,
                        "fecha_envio": com_row.fecha_envio.isoformat() if com_row.fecha_envio else None,
                        "documento_comunicacion_id": com_row.documento_comunicacion_id,
                    }

        return JSONResponse(content={
            "ok": True,
            "medida": {
                "tipo_medida_id": medida.tipo_medida_id,
                "cantidad": medida.cantidad,
                "especie": medida.especie,
                "estado_medida": medida.estado_medida,
            },
            "informe_tecnico_documento_id": informe.documento_informe_id if informe else None,
            "acto": acto_data,
        }, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo datos migración medida: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

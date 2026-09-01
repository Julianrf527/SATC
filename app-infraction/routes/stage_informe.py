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
from services.users import get_user_info, verify_permission
from services.involved import get_involucrados_by_ids
from services.docs import decrement_file_usage
from services.etapas import build_acto_for_frontend as _build_acto_for_frontend
from services.etapas import get_expediente_con_permiso
from utils.log import insert_log
from core.permission import Permission


# ── INFORMES TÉCNICOS ──────────────────────────────────────────────────────────

@router.get("/technical-report/{expediente_id}/{tipo_informe}", status_code=200)
async def obtener_informe_tecnico(
    request: Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    tipo_informe: str = PathParam(..., description="Tipo de informe"),
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = verify_gateway_token(request)["user_id"]
    existe = await db.scalar(
        select(Expediente.id).where(Expediente.id == expediente_id)
    )
    if not existe:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

    informe_tecnico = await db.scalar(
        select(InformeTecnico).where(
            InformeTecnico.expediente_id == expediente_id,
            InformeTecnico.tipo_informe == tipo_informe,
        )
    )

    if not informe_tecnico:
        creable = False
        creable_msg = None

        if tipo_informe == "VISITA":
            etapa_respuesta = await db.scalar(
                select(EtapaRespuesta).where(EtapaRespuesta.expediente_id == expediente_id)
            )
            if not etapa_respuesta:
                creable_msg = 'La etapa "Respuesta" aún no ha sido creada'
            elif not etapa_respuesta.requiere_medida_preventiva:
                # Sin medida requerida: basta con que exista la etapa respuesta
                creable = True
            else:
                # Con medida requerida: verificar notificaciones a todos los involucrados
                medida = await db.scalar(
                    select(MedidaPreventiva).where(
                        MedidaPreventiva.etapa_respuesta_id == etapa_respuesta.id
                    )
                )
                if not medida:
                    creable_msg = "La medida preventiva aún no ha sido creada"
                elif not medida.acto_administrativo_id:
                    creable_msg = "El acto administrativo de la medida preventiva aún no ha sido creado"
                else:
                    involucrados = (await db.execute(
                        select(ExpedienteInvolucrado.involucrado_id)
                        .where(ExpedienteInvolucrado.expediente_id == expediente_id)
                    )).scalars().all()

                    comunicacion = await db.scalar(
                        select(Comunicacion).where(
                            Comunicacion.acto_administrativo_id == medida.acto_administrativo_id,
                            Comunicacion.documento_comunicacion_id.isnot(None),
                        )
                    )
                    if not comunicacion:
                        creable_msg = (
                            "El acto administrativo de la medida preventiva "
                            "aún no ha sido comunicado (falta documento de comunicación)"
                        )
                    else:
                        creable = True
        elif tipo_informe == "SEGUIMIENTO":
            concepto = await db.scalar(
                select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.expediente_id == expediente_id)
            )
            if not concepto:
                creable_msg = "La etapa de Concepto Técnico aún no ha sido creada"
            elif concepto.tipo_acogida_concepto == "OFICIO":
                creable_msg = "No aplica seguimiento: el concepto fue remitido por competencia (Oficio)"
            elif concepto.tipo_acogida_concepto == "RESOLUCION_ARCHIVO":
                creable_msg = "El trámite fue acogido por resolución de archivo"
            elif concepto.tipo_acogida_concepto == "AUTO_REQUERIMIENTO":
                if not concepto.fecha_termino_calculada:
                    creable_msg = "El término de días hábiles aún no ha sido calculado en la etapa de Concepto"
                elif date.today() <= concepto.fecha_termino_calculada:
                    # El rol de cargue manual (carga de expedientes históricos) no
                    # debe esperar a que venza el término real.
                    if await verify_permission(user_id, Permission.MANUAL_UPLOAD):
                        creable = True
                    else:
                        dias_restantes = (concepto.fecha_termino_calculada - date.today()).days
                        creable_msg = (
                            f"El término vence el {concepto.fecha_termino_calculada.isoformat()}. "
                            f"Faltan {dias_restantes} día(s) para poder crear el seguimiento"
                        )
                else:
                    creable = True
        else:
            # Otros informes: creable si existe etapa_respuesta
            result = await db.scalar(
                select(EtapaRespuesta.id).where(EtapaRespuesta.expediente_id == expediente_id)
            )
            if result:
                creable = True

        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "detail": "Informe técnico no encontrado",
                "creable": creable,
                "creable_msg": creable_msg,
            },
        )

    profesional_nombre = None
    revisor_nombre = None
    ids_a_buscar = [
        uid for uid in (informe_tecnico.profesional_asignado_id, informe_tecnico.revisor_asignado_id) if uid
    ]
    if ids_a_buscar:
        users = await get_user_info(ids_a_buscar)
        if informe_tecnico.profesional_asignado_id:
            user_data = users.get(informe_tecnico.profesional_asignado_id)
            profesional_nombre = user_data.get("nombre") if user_data else None
        if informe_tecnico.revisor_asignado_id:
            user_data = users.get(informe_tecnico.revisor_asignado_id)
            revisor_nombre = user_data.get("nombre") if user_data else None

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": informe_tecnico.id,
                "expediente_id": informe_tecnico.expediente_id,
                "profesional_asignado_id": informe_tecnico.profesional_asignado_id,
                "profesional_nombre": profesional_nombre,
                "revisor_asignado_id": informe_tecnico.revisor_asignado_id,
                "revisor_nombre": revisor_nombre,
                "fecha_programacion_visita": informe_tecnico.fecha_programacion_visita.isoformat() if informe_tecnico.fecha_programacion_visita else None,
                "fecha_recibido_informe": informe_tecnico.fecha_recibido_informe.isoformat() if informe_tecnico.fecha_recibido_informe else None,
                "fecha_aceptacion_informe": informe_tecnico.fecha_aceptacion_informe.isoformat() if informe_tecnico.fecha_aceptacion_informe else None,
                "documento_informe_id": informe_tecnico.documento_informe_id,
                "tipo_informe": informe_tecnico.tipo_informe,
                "fecha_creacion": informe_tecnico.fecha_creacion.isoformat(),
                "aceptado": informe_tecnico.fecha_aceptacion_informe is not None,
                "modo": informe_tecnico.modo,
            },
            "message": "Informe técnico obtenido correctamente",
        },
        status_code=200,
    )


@router.post("/technical-report/{expediente_id}/create/{tipo_informe}", status_code=200)
async def crear_informe_tecnico(
    request: Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    tipo_informe: str = PathParam(..., description="Tipo de informe"),
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = verify_gateway_token(request)["user_id"]
    await get_expediente_con_permiso(db, expediente_id, user_id)

    nuevo_informe = InformeTecnico(expediente_id=expediente_id, tipo_informe=tipo_informe)
    db.add(nuevo_informe)
    await db.flush()
    await db.refresh(nuevo_informe)

    audit_result = await insert_log(
        db=db,
        tipo_evento=f"CREAR_INFORME_{nuevo_informe.tipo_informe}",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle="Creación de informe técnico",
        expediente_id=expediente_id,
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": nuevo_informe.id,
                "expediente_id": nuevo_informe.expediente_id,
                "profesional_asignado_id": nuevo_informe.profesional_asignado_id,
                "fecha_programacion_visita": nuevo_informe.fecha_programacion_visita.isoformat() if nuevo_informe.fecha_programacion_visita else None,
                "fecha_recibido_informe": nuevo_informe.fecha_recibido_informe.isoformat() if nuevo_informe.fecha_recibido_informe else None,
                "fecha_aceptacion_informe": nuevo_informe.fecha_aceptacion_informe.isoformat() if nuevo_informe.fecha_aceptacion_informe else None,
                "tipo_informe": nuevo_informe.tipo_informe,
                "fecha_creacion": nuevo_informe.fecha_creacion.isoformat(),
                "modo": nuevo_informe.modo,
            },
            "message": "Informe técnico creado correctamente",
        },
        status_code=200,
    )


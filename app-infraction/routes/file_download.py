from fastapi import Request, APIRouter, Depends, HTTPException, Query, Path as PathParam
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func, desc, union_all, literal
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime, date, timedelta
from pydantic import BaseModel
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv
from typing import List
import logging
import os
import pytz
import re
import holidays

from db.deps import get_db_managed
from db.models.recurso_afectado import RecursoAfectado
from db.models.expediente_recurso import ExpedienteRecurso
from db.models.expediente_tipo_afectacion import ExpedienteTipoAfectacion
from db.models.tipo_afectacion import TipoAfectacion
from db.models.quejoso_expediente import QuejosoExpediente
from db.models.expediente import Expediente
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.informe_tecnico import InformeTecnico
from db.models.medida_preventiva import MedidaPreventiva
from db.models.notificacion import Notificacion
from db.models.comunicacion import Comunicacion
from db.models.acto_administrativo import ActoAdministrativo
from db.models.vereda import Vereda
from db.models.municipio import Municipio
from db.models.radicado_asociado import RadicadoAsociado
from db.models.oficio_remite import OficioRemite
from db.models.solicitud_informacion import SolicitudInformacion
from db.models.quejoso import Quejoso
from db.models.auditoria import Auditoria

from core.permission import Permission
ASSIGN_PERMISSION = Permission.ASSIGN_PERMISSION
FILE_MANAGE = Permission.FILE_MANAGE
LOG_PERMISSION = Permission.LOG_PERMISSION

router = APIRouter()
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_DAYS = os.getenv("JWT_EXP_DAYS")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://api-gateway:8000")

bogota_tz = pytz.timezone("America/Bogota")
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = BASE_DIR / "uploads" / "expedientes"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from .models.file_models import (
    ExpedienteSchema,
    QuejosoSchema,
    BulkEncargadoRequest,
    FiltroAvanzado,
)

from utils.verify_token import verify_gateway_token
from utils.log import insert_log
from services.notification import create_notification
from services.users import get_users_by_permission, get_user_info, verify_permission
from services.involved import get_involved_by_expedientes_ids
from services.docs import download_unified_pdf


# ── DESCARGA UNIFICADA DE DOCUMENTOS ─────────────────────────────────────────

@router.get("/download/{expediente_id}")
async def descargar_expediente_completo(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Descarga todos los documentos del expediente combinados en un único PDF.
    Recorre todas las etapas del proceso de infracciones en orden cronológico.
    """
    from fastapi.responses import StreamingResponse
    from io import BytesIO

    try:
        verify_gateway_token(request)

        row = (await db.execute(
            select(Expediente.radicado)
            .where(Expediente.id == expediente_id)
        )).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        radicado = row[0]

        documentos_ids: list = []

        def agregar(doc_id):
            if doc_id:
                documentos_ids.append(doc_id)

        # 1. Etapa Respuesta
        resp = await db.scalar(
            select(EtapaRespuesta).where(EtapaRespuesta.expediente_id == expediente_id)
        )
        if resp:
            agregar(resp.documento_radicado_id)

            # 1a. Medida Preventiva (si existe)
            medida = await db.scalar(
                select(MedidaPreventiva).where(MedidaPreventiva.etapa_respuesta_id == resp.id)
            )
            if medida and medida.acto_administrativo_id:
                acto = await db.scalar(
                    select(ActoAdministrativo).where(ActoAdministrativo.id == medida.acto_administrativo_id)
                )
                if acto:
                    agregar(acto.documento_acto_administrativo_id)
                    notifs = (await db.execute(
                        select(Notificacion).where(Notificacion.acto_administrativo_id == acto.id)
                    )).scalars().all()
                    for n in notifs:
                        agregar(n.documento_citacion_id)
                        agregar(n.documento_notificacion_id)

        # 2. Informe Técnico VISITA
        informe_visita = await db.scalar(
            select(InformeTecnico).where(
                InformeTecnico.expediente_id == expediente_id,
                InformeTecnico.tipo_informe == "VISITA",
            )
        )
        if informe_visita:
            agregar(informe_visita.documento_informe_id)

        # 3. Etapa Concepto
        concepto = await db.scalar(
            select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.expediente_id == expediente_id)
        )
        if concepto:
            solicitud_info = await db.scalar(
                select(SolicitudInformacion).where(SolicitudInformacion.etapa_acoger_concepto_id == concepto.id)
            )
            if solicitud_info:
                agregar(solicitud_info.archivo_solicitud_id)
            if concepto.acto_administrativo_id:
                acto_c = await db.scalar(
                    select(ActoAdministrativo).where(ActoAdministrativo.id == concepto.acto_administrativo_id)
                )
                if acto_c:
                    agregar(acto_c.documento_acto_administrativo_id)
                    notifs_c = (await db.execute(
                        select(Notificacion).where(Notificacion.acto_administrativo_id == acto_c.id)
                    )).scalars().all()
                    for n in notifs_c:
                        agregar(n.documento_citacion_id)
                        agregar(n.documento_notificacion_id)
                    com_c = await db.scalar(
                        select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto_c.id)
                    )
                    if com_c:
                        agregar(com_c.documento_comunicacion_id)
            oficio = await db.scalar(
                select(OficioRemite).where(OficioRemite.etapa_acoger_concepto_id == concepto.id)
            )
            if oficio:
                agregar(oficio.archivo_remite_id)

        # 4. Informe Técnico SEGUIMIENTO
        informe_seg = await db.scalar(
            select(InformeTecnico).where(
                InformeTecnico.expediente_id == expediente_id,
                InformeTecnico.tipo_informe == "SEGUIMIENTO",
            )
        )
        if informe_seg:
            agregar(informe_seg.documento_informe_id)

        # 5. Etapa Cierre
        cierre = await db.scalar(
            select(EtapaCierre).where(EtapaCierre.expediente_id == expediente_id)
        )
        if cierre and cierre.acto_administrativo_id:
            acto_cl = await db.scalar(
                select(ActoAdministrativo).where(ActoAdministrativo.id == cierre.acto_administrativo_id)
            )
            if acto_cl:
                agregar(acto_cl.documento_acto_administrativo_id)
                notifs_cl = (await db.execute(
                    select(Notificacion).where(Notificacion.acto_administrativo_id == acto_cl.id)
                )).scalars().all()
                for n in notifs_cl:
                    agregar(n.documento_citacion_id)
                    agregar(n.documento_notificacion_id)

        if not documentos_ids:
            raise HTTPException(status_code=404, detail="No se encontraron documentos para este expediente")

        logger.info(f"[DOWNLOAD] Expediente {radicado}: {len(documentos_ids)} documentos a combinar")

        cookies_dict = {k: v for k, v in request.cookies.items()}
        resultado = await download_unified_pdf(file_ids=documentos_ids, cookies=cookies_dict)

        if not resultado.get("ok"):
            raise HTTPException(
                status_code=500,
                detail=f"Error generando PDF: {resultado.get('message', 'Error desconocido')}"
            )

        return StreamingResponse(
            BytesIO(resultado["content"]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="infraccion_{radicado}_completo.pdf"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DOWNLOAD] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al generar PDF: {str(e)}")

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


# ── HELPERS ALERTAS ───────────────────────────────────────────────────────────

def _fecha_limite_habiles(fecha_inicio: date, dias_habiles: int) -> date:
    co_hol = holidays.Colombia(years=range(fecha_inicio.year, fecha_inicio.year + 2))
    count = 0
    current = fecha_inicio
    while count < dias_habiles:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in co_hol:
            count += 1
    return current

def _build_semaforo(fecha_inicio: date, fecha_limite: date, fecha_hoy: date) -> dict:
    esta_vencido = fecha_hoy > fecha_limite
    dias_totales = max((fecha_limite - fecha_inicio).days, 1)
    dias_transcurridos = max((fecha_hoy - fecha_inicio).days, 0)
    dias_restantes = max((fecha_limite - fecha_hoy).days, 0)
    porcentaje = min((dias_transcurridos / dias_totales) * 100, 100)

    if esta_vencido:
        estado, urgencia, color = "vencido", "critico", "#1f2937"
    elif porcentaje >= 80:
        estado, urgencia, color = "rojo", "alta", "#ef4444"
    elif porcentaje >= 50:
        estado, urgencia, color = "amarillo", "media", "#f59e0b"
    else:
        estado, urgencia, color = "verde", "baja", "#22c55e"

    return {
        "estado": estado,
        "color_hex": color,
        "porcentaje_avance": round(porcentaje, 1),
        "urgencia": urgencia,
        "dias_transcurridos": dias_transcurridos,
        "dias_restantes": dias_restantes,
        "dias_totales": dias_totales,
        "esta_vencido": esta_vencido,
    }

def _alerta(tipo: str, etapa: str, accion: str, plazo: str,
            fecha_inicio: date, fecha_limite: date, fecha_hoy: date, msg: str = None) -> dict:
    return {
        "tipo": tipo,
        "etapa": etapa,
        "accion_requerida": accion,
        "plazo_legal": plazo,
        "msg": msg or accion,
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_limite": fecha_limite.isoformat(),
        "semaforo": _build_semaforo(fecha_inicio, fecha_limite, fecha_hoy),
    }

async def _calcular_alertas_expediente_infraccion(
    expediente_id: int, db: AsyncSession, fecha_hoy: date
) -> dict:
    alertas = {}

    exp = await db.scalar(select(Expediente).where(Expediente.id == expediente_id))
    if not exp:
        return alertas

    fecha_creacion = exp.fecha_creacion.date() if hasattr(exp.fecha_creacion, 'date') else exp.fecha_creacion

    # 1. Respuesta: 15 días hábiles desde creación del expediente
    etapa_resp = await db.scalar(
        select(EtapaRespuesta).where(EtapaRespuesta.expediente_id == expediente_id)
    )
    if not etapa_resp:
        fecha_lim_resp = _fecha_limite_habiles(fecha_creacion, 15)
        alertas["respuesta_plazo"] = _alerta(
            tipo="respuesta_plazo",
            etapa="Respuesta",
            accion="Registrar la etapa de respuesta con radicado y fecha de radicado",
            plazo="15 días hábiles desde la creación del expediente",
            fecha_inicio=fecha_creacion,
            fecha_limite=fecha_lim_resp,
            fecha_hoy=fecha_hoy,
        )

    # 2. Concepto: 15 días hábiles desde fecha_constancia_citacion (cambiar a comunicación)
    concepto = await db.scalar(
        select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.expediente_id == expediente_id)
    )
    if (concepto and concepto.tipo_acogida_concepto == "AUTO_REQUERIMIENTO"
            and concepto.acto_administrativo_id):
        notifs_constancia = (await db.execute(
            select(Notificacion).where(
                Notificacion.acto_administrativo_id == concepto.acto_administrativo_id,
                Notificacion.fecha_constancia_citacion.isnot(None),
                Notificacion.notificacion_exitosa == False,
            )
        )).scalars().all()

        for notif in notifs_constancia:
            fecha_const = notif.fecha_constancia_citacion
            fecha_lim_com = _fecha_limite_habiles(fecha_const, 15)
            alertas[f"concepto_constancia_{notif.id}"] = _alerta(
                tipo="concepto_constancia",
                etapa="Concepto",
                accion="Constancia de citación registrada. Si no hay notificación exitosa al vencer el plazo, cambiar a comunicación",
                plazo="15 días hábiles desde fecha de constancia de citación",
                fecha_inicio=fecha_const,
                fecha_limite=fecha_lim_com,
                fecha_hoy=fecha_hoy,
                msg=f"15 días hábiles desde constancia del {fecha_const.isoformat()} para notificar o cambiar a comunicación",
            )

    # 3. Concepto: fecha término de los días hábiles definidos
    if concepto and concepto.fecha_termino_calculada and concepto.dias_termino:
        fecha_termino = concepto.fecha_termino_calculada
        dias = concepto.dias_termino
        # Inicio estimado: regresar ~1.4 días calendario por cada día hábil
        fecha_inicio_termino = fecha_termino - timedelta(days=int(dias * 1.45))
        alertas["concepto_termino"] = _alerta(
            tipo="concepto_termino",
            etapa="Concepto",
            accion=f"El término de {dias} días hábiles del concepto técnico está en curso",
            plazo=f"{dias} días hábiles desde notificación del concepto",
            fecha_inicio=fecha_inicio_termino,
            fecha_limite=fecha_termino,
            fecha_hoy=fecha_hoy,
            msg=f"Término de {dias} días hábiles vence el {fecha_termino.isoformat()}",
        )

    return alertas


# ── ALERTAS DE INFRACCIONES ────────────────────────────────────────────────────

@router.get("/alerts/all")
async def obtener_alertas_todos_expedientes_infraccion(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = verify_gateway_token(request)["user_id"]

    expedientes = (await db.execute(
        select(Expediente.id, Expediente.radicado)
        .where(Expediente.abogado_responsable_id == user_id)
    )).all()

    if not expedientes:
        return JSONResponse(content={
            "ok": True, "alertas": {}, "total_expedientes": 0,
            "expedientes_con_alertas": 0,
            "estadisticas_semaforo": {"verde": 0, "amarillo": 0, "rojo": 0, "vencido": 0},
        }, status_code=200)

    fecha_hoy = date.today()
    alertas_totales = {}
    estadisticas = {"verde": 0, "amarillo": 0, "rojo": 0, "vencido": 0}

    for exp_id, radicado in expedientes:
        alertas = await _calcular_alertas_expediente_infraccion(exp_id, db, fecha_hoy)
        if alertas:
            alertas_totales[radicado] = alertas
            for a in alertas.values():
                estadisticas[a["semaforo"]["estado"]] += 1

    return JSONResponse(content={
        "ok": True,
        "alertas": alertas_totales,
        "total_expedientes": len(expedientes),
        "expedientes_con_alertas": len(alertas_totales),
        "estadisticas_semaforo": estadisticas,
    }, status_code=200)


@router.get("/alerts/{expediente_id}")
async def obtener_alertas_expediente_infraccion(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = verify_gateway_token(request)["user_id"]

    row = (await db.execute(
        select(Expediente.radicado, Expediente.abogado_responsable_id)
        .where(Expediente.id == expediente_id)
    )).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    radicado, abogado_id = row
    if abogado_id != user_id:
        raise HTTPException(status_code=403, detail="Sin permisos")

    fecha_hoy = date.today()
    alertas = await _calcular_alertas_expediente_infraccion(expediente_id, db, fecha_hoy)

    estadisticas = {"verde": 0, "amarillo": 0, "rojo": 0, "vencido": 0}
    for a in alertas.values():
        estadisticas[a["semaforo"]["estado"]] += 1

    return JSONResponse(content={
        "ok": True,
        "radicado": radicado,
        "alertas": alertas,
        "total_alertas": len(alertas),
        "estadisticas_semaforo": estadisticas,
    }, status_code=200)


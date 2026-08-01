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


@router.get("/audit/logs")
async def obtener_logs_auditoria(
    request: Request,
    usuario_id: int = Query(None, description="ID del usuario"),
    nombre_usuario: str = Query(None, description="Nombre del usuario"),
    cedula: str = Query(None, description="Número de documento/cédula del usuario"),
    expediente_radicado: str = Query(None, description="Radicado del expediente"),
    tipo_operacion: str = Query(None, description="Tipo de operación: INSERT, UPDATE, DELETE"),
    tabla_afectada: str = Query(None, description="Tabla afectada"),
    id_registro: str = Query(None, description="ID del registro"),
    fecha_inicio: str = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Obtiene los logs de auditoría filtrados por diferentes criterios.
    Solo accesible para usuarios con rol Admin o permisos especiales.
    """
    try:
        token_data = verify_gateway_token(request)
        user_id = token_data["user_id"]
        if not await verify_permission(user_id, LOG_PERMISSION):
            raise HTTPException(status_code=403, detail="No tiene permisos para acceder a los logs de auditoría")
        
        # Consulta base (sin JOIN a Usuario porque está en otro servicio)
        query = select(
            Auditoria.id,
            Auditoria.usuario_id,
            Auditoria.tipo_evento,
            Auditoria.resultado,
            Auditoria.detalle,
            Auditoria.expediente_id,
            Auditoria.expediente_radicado,
            Auditoria.fecha,
            Auditoria.datos_anteriores,
            Auditoria.datos_nuevos
        )

        # Aplicar filtros
        conditions = []
        
        if usuario_id:
            conditions.append(Auditoria.usuario_id == usuario_id)
        
        if expediente_radicado:
            conditions.append(Auditoria.expediente_radicado == expediente_radicado)
        
        if tipo_operacion:
            conditions.append(Auditoria.tipo_evento.ilike(f"{tipo_operacion.upper()}%"))
        
        if tabla_afectada:
            conditions.append(Auditoria.tipo_evento.ilike(f"%{tabla_afectada.upper()}%"))
        
        if id_registro:
            if not id_registro.isdigit():
                raise HTTPException(status_code=400, detail="id_registro debe ser numérico")
            conditions.append(Auditoria.expediente_id == int(id_registro))
        
        if fecha_inicio:
            try:
                fecha_inicio_date = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                conditions.append(Auditoria.fecha >= fecha_inicio_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Formato de fecha_inicio inválido. Use YYYY-MM-DD"
                )
        
        if fecha_fin:
            try:
                fecha_fin_date = datetime.strptime(fecha_fin, "%Y-%m-%d")
                # Incluir todo el día final
                fecha_fin_date = fecha_fin_date.replace(hour=23, minute=59, second=59)
                conditions.append(Auditoria.fecha <= fecha_fin_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Formato de fecha_fin inválido. Use YYYY-MM-DD"
                )
        
        if conditions:
            query = query.where(and_(*conditions))

        has_post_filter = bool(cedula or nombre_usuario)

        # Contar total de registros (solo útil cuando no hay filtro post-procesamiento)
        count_query = select(func.count()).select_from(Auditoria)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await db.execute(count_query)
        total_records = total_result.scalar()

        # Cuando hay filtro post-procesamiento, traer todos para filtrar en memoria
        if has_post_filter:
            query = query.order_by(Auditoria.fecha.desc())
        else:
            query = query.order_by(Auditoria.fecha.desc()).limit(limit).offset(offset)

        result = await db.execute(query)
        logs = result.fetchall()
        
        # Obtener IDs únicos de usuarios (actor + relacionados en payloads)
        user_ids = set(log.usuario_id for log in logs if log.usuario_id)

        def collect_related_user_ids(payload):
            if not isinstance(payload, dict):
                return
            for key in ("abogado_responsable_id", "encargado_id"):
                value = payload.get(key)
                if isinstance(value, int):
                    user_ids.add(value)
                elif isinstance(value, str) and value.isdigit():
                    user_ids.add(int(value))

        for log in logs:
            collect_related_user_ids(log.datos_anteriores)
            collect_related_user_ids(log.datos_nuevos)

        user_ids = list(user_ids)
        
        # Obtener información de usuarios del servicio de usuarios
        users_info = {}
        if user_ids:
            try:
                users_info = await get_user_info(user_ids)
                logger.info(f"Usuarios obtenidos: {len(users_info)} de {len(user_ids)} solicitados")
            except Exception as e:
                logger.warning(f"No se pudo obtener información de usuarios: {e}")
                # Crear entradas por defecto para usuarios no encontrados
                users_info = {
                    uid: {
                        "nombre": f"Usuario {uid}",
                        "correo": "",
                        "numero_documento": "",
                        "documento": "",
                    }
                    for uid in user_ids
                }
        
        # Formatear respuesta
        logs_data = []
        def enrich_payload(payload):
            if not isinstance(payload, dict):
                return payload
            enriched = dict(payload)
            for key, prefix in (
                ("abogado_responsable_id", "abogado_responsable"),
                ("encargado_id", "encargado"),
            ):
                value = enriched.get(key)
                if isinstance(value, str) and value.isdigit():
                    value = int(value)
                if isinstance(value, int):
                    info = users_info.get(value, {})
                    if info.get("nombre"):
                        enriched[f"{prefix}_nombre"] = info.get("nombre")
                    documento = info.get("numero_documento") or info.get("documento")
                    if documento:
                        enriched[f"{prefix}_documento"] = documento
            return enriched

        _TIPO_EVENTO_MAP_INF = {
            "INSERT_EXPEDIENTE":                    ("INSERT", "Expediente"),
            "UPDATE_EXPEDIENTE_BASICO":             ("UPDATE", "Expediente"),
            "UPDATE_ENCARGADO_EXPEDIENTE":          ("UPDATE", "Expediente"),
            "UPDATE_BULK_ENCARGADO_EXPEDIENTE":     ("UPDATE", "Expediente"),
            "UPDATE_ARCHIVE_EXPEDIENTE":            ("UPDATE", "Expediente"),
            "CREAR_ETAPA_RESPUESTA":                ("INSERT", "Etapa Respuesta"),
            "ACTUALIZAR_ETAPA_RESPUESTA":           ("UPDATE", "Etapa Respuesta"),
            "CREAR_MEDIDA_PREVENTIVA":              ("INSERT", "Medida Preventiva"),
            "ACTUALIZAR_MEDIDA_PREVENTIVA":         ("UPDATE", "Medida Preventiva"),
            "CREAR_INFORME_TECNICO":                ("INSERT", "Informe Técnico"),
            "CREAR_INFORME_POLICIAL":               ("INSERT", "Informe Policial"),
            "CREAR_ETAPA_CONCEPTO":                 ("INSERT", "Acoger Concepto"),
            "ACTUALIZAR_ETAPA_CONCEPTO":            ("UPDATE", "Acoger Concepto"),
            "CREAR_OFICIO_REMITE":                  ("INSERT", "Oficio Remite"),
            "ACTUALIZAR_OFICIO_REMITE":             ("UPDATE", "Oficio Remite"),
            "CREAR_ETAPA_CIERRE":                   ("INSERT", "Etapa Cierre"),
            "CREAR_ACTO_ADMIN":                     ("INSERT", "Acto Administrativo"),
            "ACTUALIZAR_ACTO_ADMIN":                ("UPDATE", "Acto Administrativo"),
            "ELIMINAR_ACTO_ADMIN":                  ("DELETE", "Acto Administrativo"),
            "CREAR_NOTIFICACION":                   ("INSERT", "Notificación"),
            "ACTUALIZAR_NOTIFICACION":              ("UPDATE", "Notificación"),
            "ELIMINAR_NOTIFICACION":                ("DELETE", "Notificación"),
            "CREAR_COMUNICACION":                   ("INSERT", "Comunicación"),
            "ACTUALIZAR_COMUNICACION":              ("UPDATE", "Comunicación"),
            "ELIMINAR_COMUNICACION":                ("DELETE", "Comunicación"),
            "VINCULAR_INVOLUCRADO_EXPEDIENTE":      ("INSERT", "Involucrado"),
            "DESVINCULAR_INVOLUCRADO_EXPEDIENTE":   ("DELETE", "Involucrado"),
        }

        for log in logs:
            user_info = users_info.get(log.usuario_id, {})
            usuario_nombre = (
                user_info.get("nombre")
                or (f"Usuario {log.usuario_id}" if log.usuario_id else "Usuario no identificado")
            )
            usuario_documento = str(
                user_info.get("numero_documento")
                or user_info.get("documento")
                or ""
            )
            usuario_correo = user_info.get("correo", "")

            _tipo_ev = log.tipo_evento or ""
            tipo_operacion_log, tabla_afectada_log = _TIPO_EVENTO_MAP_INF.get(_tipo_ev, ("UPDATE", _tipo_ev))

            # Informe dinámico: CREAR_INFORME_{TIPO}
            if _tipo_ev.startswith("CREAR_INFORME_") and _tipo_ev not in _TIPO_EVENTO_MAP_INF:
                tipo_informe = _tipo_ev.replace("CREAR_INFORME_", "").replace("_", " ").title()
                tipo_operacion_log, tabla_afectada_log = "INSERT", f"Informe {tipo_informe}"

            # Filtrar por nombre si se proporcionó (post-procesamiento)
            if nombre_usuario:
                if nombre_usuario.lower() not in usuario_nombre.lower():
                    continue

            # Filtrar por cédula si se proporcionó (post-procesamiento)
            if cedula:
                if cedula.strip() not in usuario_documento:
                    continue

            logs_data.append({
                "id": log.id,
                "usuario_id": log.usuario_id,
                "usuario_nombre": usuario_nombre,
                "usuario_documento": usuario_documento,
                "usuario_correo": usuario_correo,
                "tabla_afectada": tabla_afectada_log,
                "tipo_operacion": tipo_operacion_log,
                "tipo_evento": log.tipo_evento,
                "resultado": log.resultado,
                "descripcion": log.detalle,
                "expediente_radicado": log.expediente_radicado,
                "id_registro": log.expediente_id,
                "fecha": log.fecha.isoformat() if log.fecha else None,
                "datos_anteriores": enrich_payload(log.datos_anteriores),
                "datos_nuevos": enrich_payload(log.datos_nuevos),
            })
        
        # Si hubo filtro post-procesamiento, paginar en memoria y recalcular total
        if has_post_filter:
            total_records = len(logs_data)
            logs_data = logs_data[offset:offset + limit]

        return JSONResponse(
            content={
                "ok": True,
                "data": logs_data,
                "pagination": {
                    "total": total_records,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total_records
                },
                "msg": f"Se encontraron {total_records} registros"
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo logs de auditoría: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error al obtener logs de auditoría"
        )

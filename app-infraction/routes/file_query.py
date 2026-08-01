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


@router.get("/get")
async def obtener_expedientes(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=200),
    radicado: str = Query(None),
    fecha_radicado: str = Query(None),
    fecha_creacion: str = Query(None),
    encargado_id: int = Query(None),
):
    verify_gateway_token(request)

    fecha = None
    if fecha_creacion:
        fecha = datetime.fromisoformat(fecha_creacion)

    fecha_radicado = None
    if fecha_radicado:
        fecha_radicado = datetime.fromisoformat(fecha_radicado)

    count_stmt = select(func.count()).select_from(Expediente)
    data_stmt = select(
        Expediente.id,
        Expediente.radicado,
        Expediente.fecha_radicado,
        Expediente.abogado_responsable_id,
        Expediente.fecha_creacion,
    )

    if radicado:
        count_stmt = count_stmt.where(Expediente.radicado.contains(radicado))
        data_stmt = data_stmt.where(Expediente.radicado.contains(radicado))

    if fecha:
        count_stmt = count_stmt.where(
            func.date(Expediente.fecha_creacion) == fecha.date()
        )
        data_stmt = data_stmt.where(
            func.date(Expediente.fecha_creacion) == fecha.date()
        )

    if encargado_id is not None:
        count_stmt = count_stmt.where(Expediente.abogado_responsable_id == encargado_id)
        data_stmt = data_stmt.where(Expediente.abogado_responsable_id == encargado_id)

    data_stmt = data_stmt.order_by(desc(Expediente.fecha_creacion))

    total = (await db.execute(count_stmt)).scalar() or 0
    data_stmt = data_stmt.offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(data_stmt)).all()

    usuarios_disponibles = await get_users_by_permission(FILE_MANAGE)

    payload = [
        {
            "id": r[0],
            "radicado": r[1],
            "fecha_radicado": r[2].isoformat() if r[2] else None,
            "encargado_id": r[3],
            "encargado_nombre": usuarios_disponibles.get(r[3], {}).get("nombre") if r[3] else None,
            "encargado_documento": (usuarios_disponibles.get(r[3], {}).get("numero_documento") or usuarios_disponibles.get(r[3], {}).get("documento")) if r[3] else None,
            "fecha_creacion": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]

    usuarios_disponibles_lista = [
        {
            "id": user_id,
            "nombre": info["nombre"],
            "numero_documento": info.get("numero_documento") or info.get("documento"),
        }
        for user_id, info in usuarios_disponibles.items()
    ]

    return {
        "ok": True,
        "data": payload,
        "usuarios_disponibles": usuarios_disponibles_lista,
        "page": page,
        "limit": limit,
        "totalCount": total,
    }


@router.post("/filter")
async def filtrar_expedientes(
    request: Request,
    filtros: FiltroAvanzado,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Filtrado avanzado de expedientes.
    Solo incluye filtros que NO están en quick filters: motivo, dirección, veredas, recursos, estado.
    
    """
    try:
        user_id = verify_gateway_token(request)["user_id"]

        # Consulta base con joins necesarios
        stmt = (
            select(
                Expediente.id,
                Expediente.radicado,
                Expediente.fecha_creacion,
                Expediente.direccion,
                Vereda.municipio_id,
                Expediente.vereda_id
            )
            .join(Vereda, Vereda.id == Expediente.vereda_id, isouter=True)
            .where(Expediente.abogado_responsable_id == user_id)
        )

        condiciones = []

        # Filtro: Dirección
        if filtros.direccion:
            expr = Expediente.direccion == filtros.direccion if filtros.valor_exacto \
                else Expediente.direccion.ilike(f"%{filtros.direccion}%")
            condiciones.append(expr)
            logger.info(f"Aplicando filtro direccion: {filtros.direccion}")

        # Filtro: Municipio
        if filtros.municipio_id:
            condiciones.append(Vereda.municipio_id == filtros.municipio_id)
            logger.info(f"Aplicando filtro municipio_id: {filtros.municipio_id}")

        # Filtro: Veredas (múltiples)
        if filtros.vereda_ids:
            condiciones.append(Expediente.vereda_id.in_(filtros.vereda_ids))
            logger.info(f"Aplicando filtro vereda_ids: {filtros.vereda_ids}")

        # Aplicar condiciones
        if condiciones:
            stmt = stmt.where(and_(*condiciones))

        # Ejecutar consulta base
        res = await db.execute(stmt)
        expedientes_raw = res.all()

        if not expedientes_raw:
            logger.info("No se encontraron expedientes con los filtros aplicados")
            return JSONResponse(content={"ok": True, "data": []}, status_code=200)

        ids = [r[0] for r in expedientes_raw]
        ids_filtrados = set(ids)

        # Filtro: Recursos afectados (múltiples)
        if filtros.recurso_ids:
            logger.info(f"Filtrando por recursos: {filtros.recurso_ids}")
            stmt_recursos = (
                select(ExpedienteRecurso.expediente_id)
                .where(
                    and_(
                        ExpedienteRecurso.expediente_id.in_(ids_filtrados),
                        ExpedienteRecurso.recurso_id.in_(filtros.recurso_ids)
                    )
                )
                .distinct()
            )
            res_rec = await db.execute(stmt_recursos)
            ids_con_recursos = {r[0] for r in res_rec.all()}
            ids_filtrados &= ids_con_recursos

            if not ids_filtrados:
                logger.info("No se encontraron expedientes con los recursos especificados")
                return JSONResponse(content={"ok": True, "data": []}, status_code=200)

        # Filtrar expedientes_raw según ids_filtrados
        expedientes_raw = [e for e in expedientes_raw if e[0] in ids_filtrados]

        # Obtener municipios
        municipio_ids = [r[5] for r in expedientes_raw if r[5] is not None]
        municipios_map = {}
        if municipio_ids:
            res_mun = await db.execute(
                select(Municipio.id, Municipio.nombre).where(Municipio.id.in_(municipio_ids))
            )
            municipios_map = {
                m_id: {"id": m_id, "nombre": m_nombre}
                for m_id, m_nombre in res_mun.all()
            }

        # Obtener involucrados
        involucrados_map = await get_involved_by_expedientes_ids(db, list(ids_filtrados))

        # Construir respuesta
        data = []
        for id, rad, fecha_crea, direccion, municipio_id, vereda_id in expedientes_raw:
            data.append({
                "id": id,
                "radicado": rad,
                "fecha_creacion": fecha_crea.isoformat() if fecha_crea else None,
                "direccion": direccion,
                "municipio": municipios_map.get(municipio_id),
                "involucrados": involucrados_map.get(rad, [])
            })

        logger.info(f"Se encontraron {len(data)} expedientes")
        return JSONResponse(content={"ok": True, "data": data}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en filtrar_expedientes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
@router.get("/affected-resource")
async def obtener_recurso_afectado(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    verify_gateway_token(request)
    stmr = select(RecursoAfectado)
    result = await db.execute(stmr)
    result = result.scalars().all()

    data = [
        {
            "id": ra.id,
            "nombre": ra.nombre,
        }
        for ra in result
    ]

    return JSONResponse(content={"ok": True, "data": data}, status_code=200)


@router.get("/tipos-afectacion")
async def obtener_tipos_afectacion(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    verify_gateway_token(request)
    stmt = select(TipoAfectacion)
    result = await db.execute(stmt)
    tipos = result.scalars().all()

    data = [
        {"id": t.id, "nombre": t.nombre, "recurso_id": t.recurso_id}
        for t in tipos
    ]

    return JSONResponse(content={"ok": True, "data": data}, status_code=200)


@router.get("/complainer/list")
async def obtener_quejosos(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    verify_gateway_token(request)
    stmr = select(Quejoso)
    result = await db.execute(stmr)
    result = result.scalars().all()

    data = [
        {
            "id": q.id,
            "nombre": q.nombre,
            "telefono": q.telefono,
            "correo": q.correo,
            "anonimo": q.anonimo,
        }
        for q in result
    ]

    return JSONResponse(content={"ok": True, "data": data}, status_code=200)




@router.get("/full/{expediente_id}")
async def obtener_expediente_completo_por_expediente_id(
    request: Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    db: AsyncSession = Depends(get_db_managed)
):
    verify_gateway_token(request)

    # Subquery con todas las fechas de etapas en un solo query
    concepto_q = select(
        EtapaAcogerConcepto.expediente_id,
        EtapaAcogerConcepto.fecha_creacion,
        literal("Etapa concepto").label("tipo")
    )

    cierre_q = select(
        EtapaCierre.expediente_id,
        EtapaCierre.fecha_creacion,
        literal("Etapa cierre").label("tipo")
    )

    visita_q = select(
        InformeTecnico.expediente_id,
        func.coalesce(
            InformeTecnico.fecha_aceptacion_informe,
            InformeTecnico.fecha_recibido_informe,
            InformeTecnico.fecha_programacion_visita,
        ).label("fecha_creacion"),
        literal("Etapa visita").label("tipo")
    ).where(InformeTecnico.tipo_informe == "VISITA")

    seguimiento_q = select(
        InformeTecnico.expediente_id,
        func.coalesce(
            InformeTecnico.fecha_aceptacion_informe,
            InformeTecnico.fecha_recibido_informe,
            InformeTecnico.fecha_programacion_visita,
        ).label("fecha_creacion"),
        literal("Etapa seguimiento").label("tipo")
    ).where(InformeTecnico.tipo_informe == "SEGUIMIENTO")

    etapas_union = union_all(concepto_q, cierre_q, visita_q, seguimiento_q).subquery()

    # Subquery con la etapa más reciente por expediente
    etapa_reciente = (
        select(
            etapas_union.c.expediente_id,
            etapas_union.c.tipo,
            func.row_number().over(
                partition_by=etapas_union.c.expediente_id,
                order_by=etapas_union.c.fecha_creacion.desc()
            ).label("rn")
        )
    ).subquery()

    etapa_actual = (
        select(etapa_reciente.c.expediente_id, etapa_reciente.c.tipo)
        .where(etapa_reciente.c.rn == 1)
    ).subquery()

    # Query principal
    stmt = (
        select(
            Expediente.id,
            Expediente.radicado,
            Expediente.fecha_radicado,
            Expediente.direccion,
            Expediente.descripcion,
            Expediente.vereda_id,
            etapa_actual.c.tipo.label("etapa_actual"),
        )
        .where(Expediente.id == expediente_id)
        .outerjoin(etapa_actual, etapa_actual.c.expediente_id == Expediente.id)
    )

    expediente = (await db.execute(stmt)).mappings().first()

    if not expediente:
        return JSONResponse(content={"ok": True, "data": []}, status_code=200)

    # Recursos afectados
    recursos_stmt = (
        select(RecursoAfectado.id, RecursoAfectado.nombre)
        .join(ExpedienteRecurso, ExpedienteRecurso.recurso_id == RecursoAfectado.id)
        .where(ExpedienteRecurso.expediente_id == expediente_id)
    )
    recursos_res = await db.execute(recursos_stmt)
    recursos = [
        {"id": row[0], "nombre": row[1]}
        for row in recursos_res.fetchall()
    ]

    # Quejosos
    quejosos_stmt = (
        select(Quejoso.id, Quejoso.nombre, Quejoso.anonimo)
        .join(QuejosoExpediente, QuejosoExpediente.quejoso_id == Quejoso.id)
        .where(QuejosoExpediente.expediente_id == expediente_id)
    )
    quejosos_res = await db.execute(quejosos_stmt)
    quejosos = [
        {"id": row[0], "nombre": row[1], "anonimo": row[2]}
        for row in quejosos_res.fetchall()
    ]

    # Radicados asociados
    radicados_stmt = select(RadicadoAsociado.radicado).where(
        RadicadoAsociado.expediente_id == expediente_id
    )
    radicados_res = await db.execute(radicados_stmt)
    radicados_asociados = [row[0] for row in radicados_res.fetchall()]

    # Involucrados
    involucrados_map = await get_involved_by_expedientes_ids(db, [expediente_id])
    involucrados = involucrados_map.get(expediente_id, [])

    # Vereda
    vereda = None
    if expediente["vereda_id"]:
        res_ver = await db.execute(
            select(Vereda.id, Vereda.nombre)
            .where(Vereda.id == expediente["vereda_id"])
        )
        ver_row = res_ver.first()
        if ver_row:
            vereda = {"id": ver_row[0], "nombre": ver_row[1]}

    # Tipos de afectación
    tipos_stmt = (
        select(TipoAfectacion.id, TipoAfectacion.nombre, TipoAfectacion.recurso_id)
        .join(ExpedienteTipoAfectacion, ExpedienteTipoAfectacion.tipo_afectacion_id == TipoAfectacion.id)
        .where(ExpedienteTipoAfectacion.expediente_id == expediente_id)
    )
    tipos_res = await db.execute(tipos_stmt)
    tipos_afectacion = [
        {"id": row[0], "nombre": row[1], "recurso_id": row[2]}
        for row in tipos_res.fetchall()
    ]

    # Etapas existentes (IDs numéricos alineados con tabToEtapaMap del frontend)
    etapas_existentes = []
    stage_checks = [
        (EtapaRespuesta, None, 1),
        (InformeTecnico, "VISITA", 2),
        (EtapaAcogerConcepto, None, 3),
        (InformeTecnico, "SEGUIMIENTO", 4),
        (EtapaCierre, None, 5),
    ]
    for ModelClass, tipo_informe, legacy_id in stage_checks:
        if tipo_informe:
            exists = await db.scalar(
                select(ModelClass.id).where(
                    and_(ModelClass.expediente_id == expediente_id, ModelClass.tipo_informe == tipo_informe)
                )
            )
        else:
            exists = await db.scalar(
                select(ModelClass.id).where(ModelClass.expediente_id == expediente_id)
            )
        if exists:
            etapas_existentes.append(legacy_id)

    # Armar respuesta con toda la data
    exp_dict = {
        "id": expediente["id"],
        "radicado": expediente["radicado"],
        "fecha_radicado": expediente["fecha_radicado"].isoformat() if expediente["fecha_radicado"] else None,
        "recurso_afectado": recursos,
        "direccion": expediente["direccion"],
        "descripcion": expediente["descripcion"],
        "vereda": vereda,
        "tipos_afectacion": tipos_afectacion,
        "quejosos": quejosos,
        "radicados_asociados": radicados_asociados,
        "ultima_etapa": expediente["etapa_actual"],
        "involucrados": involucrados,
    }

    return JSONResponse(
        content={
            "ok": True,
            "data": exp_dict,
            "etapas_existentes": sorted(etapas_existentes),
        },
        status_code=200
    )


@router.get("/get/all")
async def obtener_expedientes_para_vista(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    verify_gateway_token(request)

    # Subquery con todas las fechas de etapas en un solo query
    concepto_q = select(
        EtapaAcogerConcepto.expediente_id,
        EtapaAcogerConcepto.fecha_creacion,
        literal("Etapa concepto").label("tipo")
    )

    cierre_q = select(
        EtapaCierre.expediente_id,
        EtapaCierre.fecha_creacion,
        literal("Etapa cierre").label("tipo")
    )

    visita_q = select(
        InformeTecnico.expediente_id,
        InformeTecnico.fecha_creacion,
        literal("Etapa visita").label("tipo")
    ).where(InformeTecnico.tipo_informe == "VISITA")

    seguimiento_q = select(
        InformeTecnico.expediente_id,
        InformeTecnico.fecha_creacion,
        literal("Etapa seguimiento").label("tipo")
    ).where(InformeTecnico.tipo_informe == "SEGUIMIENTO")

    etapas_union = union_all(concepto_q, cierre_q, visita_q, seguimiento_q).subquery()

    # Subquery con la etapa más reciente por expediente
    etapa_reciente = (
        select(
            etapas_union.c.expediente_id,
            etapas_union.c.tipo,
            func.row_number().over(
                partition_by=etapas_union.c.expediente_id,
                order_by=etapas_union.c.fecha_creacion.desc()
            ).label("rn")
        )
    ).subquery()

    etapa_actual = (
        select(etapa_reciente.c.expediente_id, etapa_reciente.c.tipo)
        .where(etapa_reciente.c.rn == 1)
    ).subquery()

    # Query principal
    stmt = (
        select(
            Expediente.id,
            Expediente.radicado,
            Expediente.fecha_radicado,
            Expediente.descripcion,
            Expediente.direccion,
            Expediente.fecha_creacion,
            Expediente.archivado,
            Expediente.vereda_id,
            etapa_actual.c.tipo.label("etapa_actual")
        )
        .outerjoin(etapa_actual, etapa_actual.c.expediente_id == Expediente.id)
    )

    res = await db.execute(stmt)
    expedientes_raw = res.all()

    if not expedientes_raw:
        return JSONResponse(content={"ok": True, "data": []}, status_code=200)


    expediente_ids = [exp.id for exp in expedientes_raw]

    recursos_map = defaultdict(list)
    if expediente_ids:
        st_rec = (
            select(
                ExpedienteRecurso.expediente_id,
                ExpedienteRecurso.recurso_id,
            )
            .where(ExpedienteRecurso.expediente_id.in_(expediente_ids))
        )
        res_rec = await db.execute(st_rec)
        for exp_id, recurso_id in res_rec.all():
            recursos_map[exp_id].append(recurso_id)

    # Obtener involucrados
    involucrados_map = await get_involved_by_expedientes_ids(db, expediente_ids)

    vereda_ids = [exp.vereda_id for exp in expedientes_raw if exp.vereda_id]
    veredas_map = {}
    municipios_map = {}

    if vereda_ids:
        res_ver = await db.execute(
            select(Vereda.id, Vereda.nombre, Vereda.municipio_id)
            .where(Vereda.id.in_(vereda_ids))
        )
        veredas = res_ver.all()
        veredas_map = {
            v_id: {"id": v_id, "nombre": v_name, "municipio_id": m_id}
            for v_id, v_name, m_id in veredas
        }

        municipio_ids = [m_id for _, _, m_id in veredas if m_id]
        if municipio_ids:
            res_mun = await db.execute(
                select(Municipio.id, Municipio.nombre).where(Municipio.id.in_(municipio_ids))
            )
            municipios_map = {
                m_id: {"id": m_id, "nombre": m_name}
                for m_id, m_name in res_mun.all()
            }

    data = []
    for exp in expedientes_raw:
        vereda_obj = veredas_map.get(exp.vereda_id)
        municipio_obj = municipios_map.get(vereda_obj["municipio_id"]) if vereda_obj else None

        data.append({
            "id": exp.id,
            "radicado": exp.radicado,
            "fecha_radicado": exp.fecha_radicado.isoformat() if exp.fecha_radicado else None,
            "fecha_creacion": exp.fecha_creacion.isoformat() if exp.fecha_creacion else None,
            "archivado": exp.archivado,
            "municipio": municipio_obj,
            "involucrados": involucrados_map.get(exp.id, []),
            "etapa_actual": exp.etapa_actual,
        })

    return JSONResponse(content={"ok": True, "data": data}, status_code=200)


@router.get("/{encargado_id}")
async def obtener_expedientes_por_encargado(
    request: Request,
    encargado_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = verify_gateway_token(request)["user_id"]

    if user_id != encargado_id:
        raise HTTPException(status_code=400, detail="Sin permisos")

    concepto_q = select(
        EtapaAcogerConcepto.expediente_id,
        EtapaAcogerConcepto.fecha_creacion,
        literal("concepto").label("tipo")
    )
    cierre_q = select(
        EtapaCierre.expediente_id,
        EtapaCierre.fecha_creacion,
        literal("cierre").label("tipo")
    )
    visita_q = select(
        InformeTecnico.expediente_id,
        func.coalesce(
            InformeTecnico.fecha_aceptacion_informe,
            InformeTecnico.fecha_recibido_informe,
            InformeTecnico.fecha_programacion_visita,
        ).label("fecha_creacion"),
        literal("visita").label("tipo")
    ).where(InformeTecnico.tipo_informe == "VISITA")

    seguimiento_q = select(
        InformeTecnico.expediente_id,
        func.coalesce(
            InformeTecnico.fecha_aceptacion_informe,
            InformeTecnico.fecha_recibido_informe,
            InformeTecnico.fecha_programacion_visita,
        ).label("fecha_creacion"),
        literal("seguimiento").label("tipo")
    ).where(InformeTecnico.tipo_informe == "SEGUIMIENTO")

    etapas_union = union_all(
        concepto_q, cierre_q, visita_q, seguimiento_q
    ).subquery()

    etapa_reciente = select(
        etapas_union.c.expediente_id,
        etapas_union.c.tipo,
        func.row_number().over(
            partition_by=etapas_union.c.expediente_id,
            order_by=etapas_union.c.fecha_creacion.desc()
        ).label("rn")
    ).subquery()

    etapa_actual = select(
        etapa_reciente.c.expediente_id,
        etapa_reciente.c.tipo
    ).where(etapa_reciente.c.rn == 1).subquery()

    # Query principal trayendo Municipio directamente
    stmt = (
        select(
            Expediente.id,
            Expediente.radicado,
            Expediente.fecha_radicado,
            Expediente.fecha_creacion,
            Expediente.archivado,
            etapa_actual.c.tipo.label("etapa_actual"),
            Municipio.id.label("municipio_id"),
            Municipio.nombre.label("municipio_nombre"),
        )
        .join(Vereda, Vereda.id == Expediente.vereda_id, isouter=True)
        .join(Municipio, Municipio.id == Vereda.municipio_id, isouter=True)
        .outerjoin(etapa_actual, etapa_actual.c.expediente_id == Expediente.id)
        .where(Expediente.abogado_responsable_id == encargado_id)
    )

    res = await db.execute(stmt)
    expedientes_raw = res.mappings().all()

    if not expedientes_raw:
        return JSONResponse(content={"ok": True, "data": []}, status_code=200)

    expediente_ids = [r["id"] for r in expedientes_raw]
    involucrados_map = await get_involved_by_expedientes_ids(db, expediente_ids)

    data = [
        {
            "id": r["id"],
            "radicado": r["radicado"],
            "fecha_radicado": r["fecha_radicado"].isoformat() if r["fecha_radicado"] else None,
            "fecha_creacion": r["fecha_creacion"].isoformat() if r["fecha_creacion"] else None,
            "municipio": {"id": r["municipio_id"], "nombre": r["municipio_nombre"]} if r["municipio_id"] else None,
            "involucrados": involucrados_map.get(r["id"], []),
            "etapa_actual": r["etapa_actual"],
            "archivado": r["archivado"],
        }
        for r in expedientes_raw
    ]

    return JSONResponse(content={"ok": True, "data": data}, status_code=200)


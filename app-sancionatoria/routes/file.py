from fastapi import Request, APIRouter, Depends, HTTPException, Query,  Path as PathParam
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, desc, insert
from datetime import datetime, date
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
from typing import List, Optional
import logging
import os
import pytz

#----- DB -----

from db.deps import get_db
from db.models.recurso_afectado import RecursoAfectado
from db.models.expediente_recurso import ExpedienteRecurso
from db.models.expediente import Expediente
from db.models.vereda import Vereda
from db.models.municipio import Municipio
from db.models.etapa import Etapa
from db.models.tipo_etapa import TipoEtapa
from db.models.acto_admin import ActoAdministrativo
from db.models.comunicacion import Comunicacion
from db.models.notificacion import Notificacion
from db.models.documento_anexo import DocumentoAnexo
from db.models.tipo_notificacion import TipoNotificacion
from db.models.auditoria import Auditoria

from core.permission import Permission


router = APIRouter()
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_DAYS = os.getenv("JWT_EXP_DAYS")
GATEWAY_URL = os.getenv("API_GATEWAY_URL")

ASSIGN_PERMISSION = Permission.ASSIGN_PERMISSION
FILE_MANAGE = Permission.FILE_MANAGE
LOG_PERMISSION = Permission.LOG_PERMISSION

bogota_tz = pytz.timezone("America/Bogota")
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = BASE_DIR / "uploads" / "expedientes"

# ---------- LOGGER ------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- MODELOS ----------

class ExpedienteSchema(BaseModel):
    radicado : str
    expediente : str
    recurso: List[int]
    motivo: str
    encargado_id : int
    municipio: int
    vereda: int
    direccion: str

class FileUpdate(BaseModel):
    radicado : str
    expediente : str
    recurso: List[int]
    motivo: str
    vereda: int
    direccion: str

class BulkEncargadoRequest(BaseModel):
    expediente_id: List[int]
    encargado_id: int

class FiltroAvanzado(BaseModel):
    """Filtros avanzados que NO están en quick filters."""
    motivo_afectacion: Optional[str] = None
    direccion: Optional[str] = None
    municipio_id: Optional[int] = None
    vereda_ids: Optional[List[int]] = None
    recurso_ids: Optional[List[int]] = None
    valor_exacto: bool = False

#----------- FUNCIONES ------------

from utils.verify_token import verify_gateway_token
from utils.log import insert_log
from services.involved import get_involucrados_by_ids
from services.users import get_users_by_permission, get_user_info, verify_external_permission, create_user_notification
from services.alertas import calcular_alertas_expediente
from services.docs import download_unified_pdf

# ---------- ENDPOINTS ----------

@router.get("/get")
async def obtener_expedientes(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=200),
    radicado: str = Query(None),
    expediente: str = Query(None),
    fecha_creacion: str = Query(None),
    encargado_id: int = Query(None),
):
    try:
        verify_gateway_token(request)

        fecha = None
        if fecha_creacion:
            fecha = datetime.fromisoformat(fecha_creacion)

        count_stmt = select(func.count()).select_from(Expediente)
        data_stmt = select(
            Expediente.id,
            Expediente.radicado,
            Expediente.expediente,
            Expediente.fecha_creacion,
            Expediente.encargado_id,
        )

        if radicado:
            count_stmt = count_stmt.where(Expediente.radicado.contains(radicado))
            data_stmt = data_stmt.where(Expediente.radicado.contains(radicado))

        if expediente:
            count_stmt = count_stmt.where(
                Expediente.expediente.ilike(f"%{expediente}%")
            )
            data_stmt = data_stmt.where(
                Expediente.expediente.ilike(f"%{expediente}%")
            )

        if fecha:
            count_stmt = count_stmt.where(
                func.date(Expediente.fecha_creacion) == fecha.date()
            )
            data_stmt = data_stmt.where(
                func.date(Expediente.fecha_creacion) == fecha.date()
            )

        if encargado_id is not None:
            count_stmt = count_stmt.where(Expediente.encargado_id == encargado_id)
            data_stmt = data_stmt.where(Expediente.encargado_id == encargado_id)

        data_stmt = data_stmt.order_by(desc(Expediente.fecha_creacion))

        total = (await db.execute(count_stmt)).scalar() or 0
        data_stmt = data_stmt.offset((page - 1) * limit).limit(limit)
        rows = (await db.execute(data_stmt)).all()

        usuarios_disponibles = await get_users_by_permission(FILE_MANAGE)

        payload = [
            {
                "id": r[0],
                "radicado": r[1],
                "expediente": r[2],
                "fecha_creacion": r[3].isoformat() if r[3] else None,
                "encargado_id": r[4],
                "encargado_nombre": usuarios_disponibles.get(r[4], {}).get("nombre") if r[4] else None,
            }
            for r in rows
        ]

        usuarios_disponibles_lista = [
            {
                "id": user_id,
                "nombre": info["nombre"],
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

    except Exception as e:
        logger.error(f"Error en obtener_expedientes: {e}")
        raise HTTPException(status_code=500, detail="Error interno al consultar archivos")

@router.post("/filter")
async def filtrar_expedientes(
    request: Request,
    filtros: FiltroAvanzado,
    db: AsyncSession = Depends(get_db),
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
                Expediente.expediente,
                Expediente.fecha_creacion,
                Expediente.motivo_afectacion,
                Expediente.direccion,
                Vereda.municipio_id,
                Expediente.vereda_id
            )
            .join(Vereda, Vereda.id == Expediente.vereda_id, isouter=True)
            .where(Expediente.encargado_id == user_id)
        )

        condiciones = []

        # Filtro: Motivo de afectación
        if filtros.motivo_afectacion:
            expr = Expediente.motivo_afectacion == filtros.motivo_afectacion if filtros.valor_exacto \
                else Expediente.motivo_afectacion.ilike(f"%{filtros.motivo_afectacion}%")
            condiciones.append(expr)
            logger.info(f"Aplicando filtro motivo_afectacion: {filtros.motivo_afectacion}")

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

        expediente_ids = [r[0] for r in expedientes_raw]
        radicados = [r[1] for r in expedientes_raw]
        radicados_filtrados = set(radicados)

        # Filtro: Recursos afectados (múltiples)
        if filtros.recurso_ids:
            logger.info(f"Filtrando por recursos: {filtros.recurso_ids}")
            stmt_recursos = (
                select(ExpedienteRecurso.expediente_id)
                .where(
                    and_(
                        ExpedienteRecurso.expediente_id.in_(expediente_ids),
                        ExpedienteRecurso.recurso_id.in_(filtros.recurso_ids)
                    )
                )
                .distinct()
            )
            res_rec = await db.execute(stmt_recursos)
            radicados_con_recursos = {r[0] for r in res_rec.all()}
            radicados_filtrados &= radicados_con_recursos

            if not radicados_filtrados:
                logger.info("No se encontraron expedientes con los recursos especificados")
                return JSONResponse(content={"ok": True, "data": []}, status_code=200)

        # Filtrar expedientes_raw según radicados_filtrados
        expedientes_raw = [e for e in expedientes_raw if e[0] in radicados_filtrados]

        # Obtener municipios
        municipio_ids = [r[5] for r in expedientes_raw if r[5] is not None]
        municipios_map = {}
        if municipio_ids:
            res_mun = await db.execute(
                select(Municipio.id, Municipio.nombre).where(Municipio.id.in_(municipio_ids))
            )
            municipios_map = {m_id: {"id": m_id, "name": m_nombre} for m_id, m_nombre in res_mun.all()}

        # Obtener involucrados
        involucrados_map = await get_involucrados_by_ids(db, list(expediente_ids))

        # Construir respuesta
        data = []
        for id, rad, expe, fecha_crea, motivo, direccion, municipio_id, vereda_id in expedientes_raw:
            data.append({
                "id": id,
                "radicado": rad,
                "expediente": expe,
                "fecha_creacion": fecha_crea.isoformat() if fecha_crea else None,
                "motivo_afectacion": motivo,
                "direccion": direccion,
                "municipio": municipios_map.get(municipio_id),
                "involucrados": involucrados_map.get(rad, [])
            })

        logger.info(f"Se encontraron {len(data)} expedientes")
        return JSONResponse(content={"ok": True, "data": data}, status_code=200)

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Error en filtrar_expedientes: {e}\n{error_detail}")
        raise HTTPException(status_code=500, detail=f"Error al aplicar filtros.")

@router.get("/affected-resource")
async def obtener_recurso_afectado(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        verify_gateway_token(request)
        stmr = select(RecursoAfectado)
        result = await db.execute(stmr)
        result = result.scalars().all()

        data = [
            {
                "id": ra.id,
                "nombre": ra.nombre
            }
            for ra in result
        ]

        return JSONResponse(content={"ok": True, "data": data}, status_code=200)

    except Exception as e:
        logger.error(f"Error en obtener_recurso_afectado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

#Nuevos
@router.get("/full/{expediente_id}")
async def obtener_expediente_completo_por_expediente_id(
    request:Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = verify_gateway_token(request)["user_id"]

        # 1) Última etapa por expediente
        latest_etapa_subq = (
            select(
                Etapa.expediente_id,
                Etapa.tipo_etapa_id,
                func.row_number().over(
                    partition_by=Etapa.expediente_id,
                    order_by=Etapa.fecha_inicio.desc()
                ).label("rn")
            ).subquery()
        )

        # 2) Consulta principal 
        stmt = (
            select(
                Expediente.id,
                Expediente.radicado,
                Expediente.motivo_afectacion,
                Expediente.direccion,
                Expediente.vereda_id,
                Expediente.id_auxiliar,
                TipoEtapa.nombre.label("ultima_etapa")
            )
            .join(
                latest_etapa_subq,
                (latest_etapa_subq.c.expediente_id == Expediente.id)
                & (latest_etapa_subq.c.rn == 1),
                isouter=True
            )
            .join(TipoEtapa, TipoEtapa.id == latest_etapa_subq.c.tipo_etapa_id, isouter=True)
            .where(Expediente.id == expediente_id)
        )

        res = await db.execute(stmt)
        expedientes_raw = res.all()

        if not expedientes_raw:
            return JSONResponse(content={"ok": True, "data": []}, status_code=200)

        # 3) Verificar permisos
        stmt_check = select(Expediente.encargado_id).where(Expediente.id == expediente_id)
        res_check = await db.execute(stmt_check)
        current_encargado = res_check.scalar_one_or_none()

        if current_encargado is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if current_encargado != user_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        expediente_ids = [r[0] for r in expedientes_raw]
        vereda_ids = [r[4] for r in expedientes_raw if r[4]]

        # 4) Recursos afectados 
        recursos_map = defaultdict(list)
        if expediente_ids:
            stmr_rec = (
                select(
                    ExpedienteRecurso.expediente_id,
                    ExpedienteRecurso.recurso_id,
                )
                .where(ExpedienteRecurso.expediente_id.in_(expediente_ids))
            )
            res_rec = await db.execute(stmr_rec)
            for exp_id, recurso_id in res_rec.all():
                recursos_map[exp_id].append(recurso_id)

        # 5) Involucrados - TODA LA DATA (como en /file/{encargado_id})
        involucrados_map = await get_involucrados_by_ids(db, expediente_ids)

        # 6) Veredas (map id -> {id, name})
        veredas_map = {}
        if vereda_ids:
            res_ver = await db.execute(
                select(Vereda.id, Vereda.nombre)
                .where(Vereda.id.in_(vereda_ids))
            )
            veredas_map = {v_id: {"id": v_id, "name": v_name} for v_id, v_name in res_ver.all()}

        # 7) Armar respuesta con toda la data
        exp_dict = {}
        for expediente_id, radicado, motivo, direccion, vereda_id, id_auxiliar, ultima_etapa in expedientes_raw:
            exp_dict = {
                "radicado": radicado,
                "recurso_afectado": recursos_map.get(expediente_id, []),
                "motivo_afectacion": motivo,
                "direccion": direccion,
                "vereda": veredas_map.get(vereda_id),
                "id_auxiliar": id_auxiliar,
                "ultima_etapa": ultima_etapa,
                "involucrados": involucrados_map.get(expediente_id, []),
            }

        # 8) Obtener las etapas que tiene el expediente (tipo_etapa_id)
        stmt_etapas = (
            select(TipoEtapa.id)
            .join(Etapa, Etapa.tipo_etapa_id == TipoEtapa.id)
            .where(Etapa.expediente_id == expediente_id)
            .distinct()
        )
        res_etapas = await db.execute(stmt_etapas)
        etapas_existentes = [etapa_id for (etapa_id,) in res_etapas.all()]

        stmt = select(TipoNotificacion)
        res = await db.execute(stmt)
        tnotificaciones = res.scalars().all()
        tnotificaciones_list = [{"id": tn.id, "nombre": tn.nombre} for tn in tnotificaciones]

        return JSONResponse(
            content={
                "ok": True, 
                "data": exp_dict,
                "tipo_notificacion": tnotificaciones_list,
                "etapas_existentes": etapas_existentes
            }, 
            status_code=200
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en obtener_expediente_completo_por_expediente_id: {e}")
        raise HTTPException(status_code=500, detail="Error del servidor")

@router.put("/{expediente_id}/basic-data")
async def actualizar_informacion_expediente(
    request: Request,
    expediente_id: int,
    file: FileUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = verify_gateway_token(request)["user_id"]

        stmt_check = select(Expediente).where(Expediente.int == expediente_id)
        res_check = await db.execute(stmt_check)
        expediente_actual = res_check.scalar_one_or_none()

        if expediente_actual is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if expediente_actual.encargado_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para actualizar este expediente"
            )

        # Obtener recursos anteriores
        stmt_recursos = select(ExpedienteRecurso.recurso_id).where(
            ExpedienteRecurso.expediente_id == expediente_id
        )
        res_recursos = await db.execute(stmt_recursos)
        recursos_anteriores = [row[0] for row in res_recursos.fetchall()]

        datos_anteriores = {
            "radicado": expediente_actual.radicado,
            "nombre_expediente": expediente_actual.nombre_expediente,
            "motivo_afectacion": expediente_actual.motivo_afectacion,
            "direccion": expediente_actual.direccion,
            "vereda_id": expediente_actual.vereda_id,
            "recursos": recursos_anteriores
        }

        stmr = select(Expediente).where(Expediente.radicado == file.radicado)
        result = await db.execute(stmr)
        duplicate_rol = result.scalar_one_or_none()

        if duplicate_rol:
            raise HTTPException(status_code=409, detail="El radicado ya está en uso.")

        stmr = (
            update(Expediente)
            .where(Expediente.id == expediente_id)
            .values(
                radicado=file.radicado,
                nombre_expediente=file.expediente,
                motivo_afectacion=file.motivo,
                direccion=file.direccion,
                vereda_id=file.vereda,
            )
        )
        await db.execute(stmr)

        if file.recurso:
            for recurso_id in file.recurso:
                insert_stmt = insert(ExpedienteRecurso).values(
                    expediente_id=expediente_id,
                    recurso_id=recurso_id
                ).on_conflict_do_nothing()
                await db.execute(insert_stmt)

        datos_nuevos = {
            "radicado": file.radicado,
            "nombre_expediente": file.expediente,
            "motivo_afectacion": file.motivo,
            "direccion": file.direccion,
            "vereda_id": file.vereda,
            "recursos": file.recurso
        }

        audit_result = await insert_log(
            db=db,
            usuario_id=user_id,
            tabla_afectada="expediente",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de expediente '{file.radicado}'",
            expediente_radicado=file.radicado,
            id_registro=file.radicado,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()

        return JSONResponse(content={"ok": True}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en actualizar_informacion_expediente: {e}")
        raise HTTPException(status_code=500, detail="Error del servidor")


@router.get("/get/all")
async def obtener_expedientes_para_vista(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        verify_gateway_token(request)

        latest_etapa_subq = (
            select(
                Etapa.expediente_radicado,
                Etapa.tipo_etapa_id,
                func.row_number().over(
                    partition_by=Etapa.expediente_radicado,
                    order_by=Etapa.fecha_inicio.desc()
                ).label("rn")
            ).subquery()
        )

        stmt = (
            select(
                Expediente,
                TipoEtapa.nombre.label("nombre_tipo_etapa")
            )
            .join(
                latest_etapa_subq,
                (latest_etapa_subq.c.expediente_id == Expediente.id) &
                (latest_etapa_subq.c.rn == 1),
                isouter=True
            )
            .join(TipoEtapa, TipoEtapa.id == latest_etapa_subq.c.tipo_etapa_id, isouter=True)
            .order_by(Expediente.fecha_creacion.desc())
        )

        res = await db.execute(stmt)
        expedientes_raw = res.all()

        if not expedientes_raw:
            return JSONResponse(content={"ok": True, "data": []}, status_code=200)

        expedientes = []
        for exp, nombre_tipo_etapa in expedientes_raw:
            exp.nombre_tipo_etapa = nombre_tipo_etapa
            expedientes.append(exp)

        expediente_ids = [exp.id for exp in expedientes]

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
            for rad, recurso_id in res_rec.all():
                recursos_map[rad].append(recurso_id)

        # Obtener involucrados
        involucrados_map = await get_involucrados_by_ids(db, expediente_ids)

        vereda_ids = [exp.vereda_id for exp in expedientes if exp.vereda_id]
        veredas_map = {}
        municipios_map = {}

        if vereda_ids:
            res_ver = await db.execute(
                select(Vereda.id, Vereda.nombre, Vereda.municipio_id)
                .where(Vereda.id.in_(vereda_ids))
            )
            veredas = res_ver.all()
            veredas_map = {
                v_id: {"id": v_id, "name": v_name, "municipio_id": m_id}
                for v_id, v_name, m_id in veredas
            }

            municipio_ids = [m_id for _, _, m_id in veredas if m_id]
            if municipio_ids:
                res_mun = await db.execute(
                    select(Municipio.id, Municipio.nombre).where(Municipio.id.in_(municipio_ids))
                )
                municipios_map = {
                    m_id: {"id": m_id, "name": m_name}
                    for m_id, m_name in res_mun.all()
                }

        data = []
        for exp in expedientes:
            vereda_obj = veredas_map.get(exp.vereda_id)
            municipio_obj = municipios_map.get(vereda_obj["municipio_id"]) if vereda_obj else None

            data.append({
                "id": exp.id,
                "radicado": exp.radicado,
                "expediente": exp.expediente,
                "recurso_afectado": recursos_map.get(exp.radicado, []),
                "motivo_afectacion": exp.motivo_afectacion,
                "fecha_creacion": exp.fecha_creacion.isoformat() if exp.fecha_creacion else None,
                "direccion": exp.direccion,
                "municipio": municipio_obj,
                "vereda": {"id": vereda_obj["id"], "name": vereda_obj["name"]} if vereda_obj else None,
                "involucrados": involucrados_map.get(exp.radicado, []),
                "ultima_etapa": exp.nombre_tipo_etapa
            })

        return JSONResponse(content={"ok": True, "data": data}, status_code=200)

    except Exception as e:
        logger.error(f"Error en obtener_expedientes_para_vista: {e}")
        raise HTTPException(status_code=500, detail="Error del servidor")

@router.get("/{encargado_id}")
async def obtener_expedientes_por_encargado(
    request: Request,
    encargado_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        if usuario_id != encargado_id:
            raise HTTPException(status_code=400, detail="Sin permisos")

        # Subconsulta para obtener la última etapa por expediente
        latest_etapa_subq = (
            select(
                Etapa.expediente_radicado,
                Etapa.tipo_etapa_id,
                func.row_number().over(
                    partition_by=Etapa.expediente_radicado,
                    order_by=Etapa.fecha_inicio.desc()
                ).label("rn")
            ).subquery()
        )

        stmt = (
            select(
                Expediente.id,
                Expediente.radicado,
                Expediente.nombre_expediente,
                Expediente.fecha_creacion,
                Vereda.municipio_id,
                TipoEtapa.nombre.label("ultima_etapa")
            )
            .join(Vereda, Vereda.id == Expediente.vereda_id, isouter=True)
            .join(
                latest_etapa_subq,
                (latest_etapa_subq.c.expediente_radicado == Expediente.radicado)
                & (latest_etapa_subq.c.rn == 1),
                isouter=True
            )
            .join(TipoEtapa, TipoEtapa.id == latest_etapa_subq.c.tipo_etapa_id, isouter=True)
            .where(
                and_(
                    Expediente.encargado_id == encargado_id,
                    Expediente.archivado == False
                )
            )
        )

        res = await db.execute(stmt)
        expedientes_raw = res.all()

        if not expedientes_raw:
            return JSONResponse(content={"ok": True, "data": []}, status_code=200)

        expediente_ids = [r[0] for r in expedientes_raw]
        municipio_ids = [r[4] for r in expedientes_raw if r[4] is not None]

        municipios_map = {}
        if municipio_ids:
            res_mun = await db.execute(
                select(Municipio.id, Municipio.nombre)
                .where(Municipio.id.in_(municipio_ids))
            )
            municipios_map = {
                m_id: {"id": m_id, "nombre": m_nombre}
                for m_id, m_nombre in res_mun.all()
            }

        # Obtener involucrados
        involucrados_map = await get_involucrados_by_ids(db, expediente_ids)

        data = []
        for id, rad, exp, fecha_crea, municipio_id, ultima_etapa in expedientes_raw:
            data.append({
                "id": id,
                "radicado": rad,
                "expediente": exp,
                "fecha_creacion": fecha_crea.isoformat() if fecha_crea else None,
                "municipio": municipios_map.get(municipio_id),
                "involucrados": involucrados_map.get(id, []),
                "ultima_etapa": ultima_etapa
            })

        return JSONResponse(content={"ok": True, "data": data}, status_code=200)

    except Exception as e:
        logger.error(f"Error en obtener_expedientes_por_encargado: {e}")
        raise HTTPException(status_code=500, detail="Error del servidor")
#Revisado
@router.post("/add")
async def agregar_expediente(
    request: Request,
    expediente: ExpedienteSchema,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)["user_id"]

        stmt = select(Expediente).where(Expediente.radicado == expediente.radicado)
        result = await db.execute(stmt)
        existing_file = result.scalar_one_or_none()

        if existing_file:
            raise HTTPException(status_code=400, detail="El radicado ya existe")
        
        stmt = select(Expediente).where(Expediente.expediente == expediente.expediente)
        result = await db.execute(stmt)
        existing_file = result.scalar_one_or_none()
        if existing_file:
            raise HTTPException(status_code=400, detail="El número de expediente ya existe")

        nuevo_expediente = Expediente(
            radicado=expediente.radicado,
            expediente=expediente.expediente,
            motivo_afectacion=expediente.motivo,
            encargado_id=expediente.encargado_id,
            direccion=expediente.direccion,
            vereda_id=expediente.vereda,
        )

        db.add(nuevo_expediente)       
        await db.flush()                
        expediente_id = nuevo_expediente.id  

        for recurso_id in expediente.recurso:
            db.add(
                ExpedienteRecurso(
                    expediente_radicado=expediente.radicado,
                    recurso_id=recurso_id,
                )
            )

        datos_nuevos = {
            "radicado": expediente.radicado,
            "expediente": expediente.expediente,
            "motivo_afectacion": expediente.motivo,
            "encargado_id": expediente.encargado_id,
            "direccion": expediente.direccion,
            "vereda_id": expediente.vereda,
            "recursos": expediente.recurso
        }

        # Obtener información del usuario para auditoría
        user_info = await get_user_info([user_id])

        audit_result = await insert_log(
            db=db,
            usuario_id=user_id,
            documento_usuario=user_info[user_id]["documento"],
            nombre_usuario=user_info[user_id]["nombre"],
            tabla_afectada="expediente",
            tipo_operacion="INSERT",
            descripcion=f"Creación de expediente {expediente.radicado}",
            expediente_id=expediente_id,
            expediente_radicado=expediente.radicado,
            id_registro=expediente.id,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()
        await db.refresh(nuevo_expediente)

        return JSONResponse(
            content={"ok": True, "expediente_id": expediente_id},
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{expediente_id}/charge/{encargado_id}")
async def actualizar_encargado_de_expediente(
    request: Request,
    expediente_id: int,
    encargado_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)["user_id"]
        res = await verify_external_permission(user_id, ASSIGN_PERMISSION)

        if not res["ok"]:
            raise HTTPException(status_code=403, detail="No cuenta con permisos")

        # Obtener datos anteriores
        stmt_check = select(Expediente).where(Expediente.id == expediente_id)
        res_check = await db.execute(stmt_check)
        expediente = res_check.scalar_one_or_none()

        if expediente is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        datos_anteriores = {
            "radicado": expediente.radicado,
            "encargado_id": expediente.encargado_id
        }

        new_value = None if encargado_id == 0 else encargado_id

        # Actualizar encargado
        stmt = (
            update(Expediente)
            .where(Expediente.id == expediente_id)
            .values({Expediente.encargado_id: new_value})
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt)

        if result.rowcount == 0:
            raise HTTPException(status_code=400, detail="Expediente no encontrado")

        datos_nuevos = {
            "radicado": expediente.radicado,
            "encargado_id": new_value
        }

        # Obtener información del usuario para auditoría
        user_info = await get_user_info([user_id])

        # Guardar auditoría
        audit_result = await insert_log(
            db=db,
            usuario_id=user_id,
            documento_usuario=user_info[user_id]["documento"],
            nombre_usuario=user_info[user_id]["nombre"],
            tabla_afectada="expediente",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de encargado del expediente {expediente.radicado}",
            expediente_id=expediente.id,
            expediente_radicado=expediente.radicado,
            id_registro=expediente.id,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()

        # Crear notificación si se asignó un encargado
        if encargado_id != 0:
            notif_result = await create_user_notification(
                mensaje=f"Se te ha asignado el expediente {expediente.radicado}",
                ruta=f"/expedientes/{expediente_id}",
                usuario_id=encargado_id
            )
            
            # Solo loguear si falla, no interrumpir el flujo
            if not notif_result["ok"]:
                logger.warning(
                    f"No se pudo crear notificación para usuario {encargado_id}: {notif_result['message']}"
                )

        return JSONResponse(
            content={"ok": True, "message": "Encargado actualizado"},
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error actualizando encargado: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar encargado")

@router.patch("/charge/bulk")
async def actualizar_encargado_bulk(
    request: Request,
    data: BulkEncargadoRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)["user_id"]
        res = await verify_external_permission(user_id, ASSIGN_PERMISSION)

        if not res["ok"]:
            raise HTTPException(status_code=403, detail="No cuenta con permisos")

        # Obtener información del usuario para auditoría
        user_info_map = await get_user_info([user_id])
        user_info = user_info_map.get(user_id, {"documento": "N/A", "nombre": "N/A"})

        expediente_ids = list(dict.fromkeys(data.expediente_id or []))
        if not expediente_ids:
            raise HTTPException(status_code=400, detail="Debe enviar al menos un expediente_id")

        new_value = None if data.encargado_id == 0 else data.encargado_id
        updated = []

        # Cargar expedientes existentes en una sola consulta.
        res_check = await db.execute(
            select(Expediente).where(Expediente.id.in_(expediente_ids))
        )
        expedientes = res_check.scalars().all()

        if not expedientes:
            return JSONResponse(
                content={"ok": True, "updated": [], "msg": "No se encontraron expedientes para actualizar"},
                status_code=200,
            )

        ids_existentes = [exp.id for exp in expedientes]

        # Actualización masiva en una sola sentencia SQL.
        await db.execute(
            update(Expediente)
            .where(Expediente.id.in_(ids_existentes))
            .values({Expediente.encargado_id: new_value})
            .execution_options(synchronize_session=False)
        )

        # Se mantiene auditoría por cada expediente actualizado.
        for expediente in expedientes:
            datos_anteriores = {
                "radicado": expediente.radicado,
                "encargado_id": expediente.encargado_id,
            }

            await insert_log(
                db=db,
                usuario_id=user_id,
                documento_usuario=user_info["documento"],
                nombre_usuario=user_info["nombre"],
                tabla_afectada="expediente",
                tipo_operacion="UPDATE",
                descripcion=f"Actualización masiva de encargado del expediente {expediente.radicado}",
                expediente_id=expediente.id,
                expediente_radicado=expediente.radicado,
                id_registro=expediente.id,
                datos_anteriores=datos_anteriores,
                datos_nuevos={"radicado": expediente.radicado, "encargado_id": new_value},
            )
            updated.append({"id": expediente.id, "radicado": expediente.radicado})

        await db.commit()

        if new_value:
            for expediente_actualizado in updated:
                await create_user_notification(
                    mensaje=f"Se te ha asignado el expediente {expediente_actualizado['radicado']}",
                    ruta=f"/expedientes/{expediente_actualizado['id']}",
                    usuario_id=new_value
                )

        return JSONResponse(
            content={"ok": True, "updated": updated, "msg": f"Se actualizaron {len(updated)} expedientes"},
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error actualizando encargados bulk: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al actualizar encargados")

# Archivar expediente
@router.patch("/{expediente_id}/archive")
async def archivar_expediente(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Archiva un expediente. Solo disponible cuando se ha completado la etapa de Ejecución de la Sanción.
    Esta acción no se puede revertir.
    """
    try:
        user_id = verify_gateway_token(request)["user_id"]

        # Obtener datos anteriores
        stmt_check = select(Expediente).where(Expediente.id == expediente_id)
        res_check = await db.execute(stmt_check)
        expediente = res_check.scalar_one_or_none()

        if expediente is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        # Verificar que el usuario es el encargado
        if expediente.encargado_id != user_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para archivar este expediente")

        # Verificar si ya está archivado
        if expediente.archivado:
            raise HTTPException(status_code=400, detail="El expediente ya está archivado")

        datos_anteriores = {
            "radicado": expediente.radicado,
            "archivado": expediente.archivado
        }

        # Archivar expediente
        stmt = (
            update(Expediente)
            .where(Expediente.id == expediente_id)
            .values(archivado=True, fecha_archivado=datetime.now().replace(tzinfo=None))
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt)

        if result.rowcount == 0:
            raise HTTPException(status_code=400, detail="No se pudo archivar el expediente")

        datos_nuevos = {
            "radicado": expediente.radicado,
            "archivado": True
        }

        # Obtener información del usuario para auditoría
        user_info = await get_user_info([user_id])

        # Guardar auditoría
        audit_result = await insert_log(
            db=db,
            usuario_id=user_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="expediente",
            tipo_operacion="UPDATE",
            descripcion=f"Archivado del expediente {expediente.radicado}",
            expediente_id=expediente.id,
            expediente_radicado=expediente.radicado,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()

        return JSONResponse(
            content={"ok": True, "message": "Expediente archivado exitosamente"},
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error archivando expediente: {e}")
        raise HTTPException(status_code=500, detail="Error al archivar expediente")

#Log Auditoria
@router.get("/audit/logs")
async def obtener_logs_auditoria(
    request: Request,
    usuario_id: int = Query(None, description="ID del usuario"),
    nombre_usuario: str = Query(None, description="Nombre del usuario"),
    expediente_radicado: str = Query(None, description="Radicado del expediente"),
    tipo_operacion: str = Query(None, description="Tipo de operación: INSERT, UPDATE, DELETE"),
    tabla_afectada: str = Query(None, description="Tabla afectada"),
    id_registro: str = Query(None, description="ID del registro"),
    fecha_inicio: str = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene los logs de auditoría filtrados por diferentes criterios.
    Solo accesible para usuarios con rol Admin o permisos especiales.
    """
    try:
        user_id = verify_gateway_token(request)["user_id"]
        #Consultar permisos
        res = await verify_external_permission(user_id, LOG_PERMISSION)
        
        # Consulta base (sin JOIN a Usuario porque está en otro servicio)
        query = select(
            Auditoria.id,
            Auditoria.usuario_id,
            Auditoria.tabla_afectada,
            Auditoria.tipo_operacion,
            Auditoria.descripcion,
            Auditoria.expediente_radicado,
            Auditoria.id_registro,
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
            conditions.append(Auditoria.tipo_operacion == tipo_operacion.upper())
        
        if tabla_afectada:
            conditions.append(Auditoria.tabla_afectada.ilike(f"%{tabla_afectada}%"))
        
        if id_registro:
            conditions.append(Auditoria.id_registro == id_registro)
        
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
        
        # Contar total de registros
        count_query = select(func.count()).select_from(Auditoria)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await db.execute(count_query)
        total_records = total_result.scalar()
        
        # Ordenar por fecha descendente y aplicar paginación
        query = query.order_by(Auditoria.fecha.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        logs = result.fetchall()
        
        # Obtener IDs únicos de usuarios
        user_ids = list(set(log.usuario_id for log in logs if log.usuario_id))
        
        # Obtener información de usuarios del servicio de usuarios
        users_info = {}
        if user_ids:
            try:
                users_info = await get_user_info(user_ids)
                logger.info(f"Usuarios obtenidos: {len(users_info)} de {len(user_ids)} solicitados")
            except Exception as e:
                logger.warning(f"No se pudo obtener información de usuarios: {e}")
                # Crear entradas por defecto para usuarios no encontrados
                users_info = {uid: {"nombre": f"Usuario {uid}", "correo": ""} for uid in user_ids}
        
        # Formatear respuesta
        logs_data = []
        for log in logs:
            user_info = users_info.get(log.usuario_id, {})
            usuario_nombre = user_info.get("nombre", f"Usuario {log.usuario_id}")
            usuario_correo = user_info.get("correo", "")
            
            # Filtrar por nombre si se proporcionó (post-procesamiento)
            if nombre_usuario:
                if nombre_usuario.lower() not in usuario_nombre.lower():
                    continue
            
            logs_data.append({
                "id": log.id,
                "usuario_id": log.usuario_id,
                "usuario_nombre": usuario_nombre,
                "usuario_correo": usuario_correo,
                "tabla_afectada": log.tabla_afectada,
                "tipo_operacion": log.tipo_operacion,
                "descripcion": log.descripcion,
                "expediente_radicado": log.expediente_radicado,
                "id_registro": log.id_registro,
                "fecha": log.fecha.isoformat() if log.fecha else None,
                "datos_anteriores": log.datos_anteriores,
                "datos_nuevos": log.datos_nuevos
            })
        
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
                "msg": f"Se encontraron {len(logs_data)} registros"
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

#Alertas
@router.get("/alerts/all")
async def obtener_alertas_todos_expedientes(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene todas las alertas de todos los expedientes asignados al usuario autenticado.
    """
    try:
        user_id = verify_gateway_token(request)

        # Obtener todos los expedientes del usuario
        stmt = select(Expediente.radicado).where(Expediente.encargado_id == user_id)
        result = await db.execute(stmt)
        expedientes = result.scalars().all()

        if not expedientes:
            return JSONResponse(
                content={
                    "ok": True,
                    "alertas": {},
                    "total_expedientes": 0,
                    "expedientes_con_alertas": 0
                },
                status_code=200
            )

        alertas_totales = {}
        fecha_hoy = date.today()

        # Calcular alertas para cada expediente
        for radicado in expedientes:
            alertas = await calcular_alertas_expediente(radicado, db, fecha_hoy)
            if alertas:  # Solo incluir expedientes con alertas
                alertas_totales[radicado] = alertas

        # Calcular estadísticas de semáforo
        estadisticas = {
            "verde": 0,
            "amarillo": 0,
            "rojo": 0,
            "vencido": 0
        }
        
        for radicado, alertas_expediente in alertas_totales.items():
            for alerta in alertas_expediente.values():
                estado = alerta["semaforo"]["estado"]
                estadisticas[estado] += 1

        return JSONResponse(
            content={
                "ok": True,
                "alertas": alertas_totales,
                "total_expedientes": len(expedientes),
                "expedientes_con_alertas": len(alertas_totales),
                "estadisticas_semaforo": estadisticas
            },
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo alertas de expedientes: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al obtener alertas"
        )

@router.get("/alerts/{expediente_id}")
async def obtener_alertas_expediente(
    expediente_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene todas las alertas de un expediente específico.
    
    Args:
        expediente_id: ID del expediente
        
    Returns:
        JSONResponse con estructura:
        {
            "ok": True,
            "radicado": str,
            "alertas": {"alerta1": {...}, "alerta2": {...}},
            "total_alertas": int
        }
    """
    try:
        user_id = verify_gateway_token(request)

        # Verificar que el expediente existe y pertenece al usuario
        stmt = select(Expediente.radicado).where(
            Expediente.id == expediente_id,
            Expediente.encargado_id == user_id
        )
        result = await db.execute(stmt)
        expediente = result.scalar()

        if not expediente:
            raise HTTPException(
                status_code=404,
                detail=f"Expediente con ID {expediente_id} no encontrado o no tiene acceso"
            )

        fecha_hoy = date.today()
        alertas = await calcular_alertas_expediente(expediente.radicado, db, fecha_hoy)

        # Calcular estadísticas de semáforo
        estadisticas = {
            "verde": 0,
            "amarillo": 0,
            "rojo": 0,
            "vencido": 0
        }
        
        for alerta in alertas.values():
            estado = alerta["semaforo"]["estado"]
            estadisticas[estado] += 1

        return JSONResponse(
            content={
                "ok": True,
                "radicado": expediente.radicado,
                "alertas": alertas,
                "total_alertas": len(alertas),
                "estadisticas_semaforo": estadisticas
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo alertas del expediente con radicado {expediente.radicado}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor al obtener alertas del expediente {expediente.radicado}"
        )


#Descargar todo el doc
@router.get("/download-all/{radicado}")
async def descargar_todos_documentos(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Descarga todos los documentos de un expediente combinados en un único PDF.
    Los documentos se ordenan por etapa y se deduplican (documentos repetidos solo aparecen una vez).
    Delega la descarga y combinación de PDFs a app-docs.
    """
    try:
        usuario_id = verify_gateway_token(request)

        # Verificar que el expediente existe y obtener permisos
        stmt = select(Expediente.encargado_id, Expediente.id_auxiliar).where(
            Expediente.radicado == radicado
        )
        result = await db.execute(stmt)
        expediente = result.one_or_none()

        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        encargado_id, id_auxiliar = expediente
        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para acceder a este expediente"
            )

        logger.info(f"[DOWNLOAD-ALL] Iniciando descarga para expediente: {radicado}")

        # Orden de etapas según el frontend:
        # Indagación(2), Medida(1), Inicio(9), Cesación(10), Cargos(4),
        # Apertura(5), Cierre(11), Decisión(6), Recurso(12), Ejecución(7)
        orden_etapas = [2, 1, 9, 10, 4, 5, 11, 6, 12, 7]

        # Crear mapping de tipo_etapa_id a orden
        orden_map = {tipo_id: idx for idx, tipo_id in enumerate(orden_etapas)}

        # Obtener todas las etapas del expediente
        stmt = (
            select(Etapa.id, TipoEtapa.id.label("tipo_etapa_id"), TipoEtapa.nombre)
            .join(TipoEtapa, Etapa.tipo_etapa_id == TipoEtapa.id)
            .where(Etapa.expediente_radicado == radicado)
        )
        result = await db.execute(stmt)
        etapas_raw = result.all()

        # Ordenar etapas manualmente según el orden del frontend
        etapas = sorted(
            etapas_raw,
            key=lambda e: orden_map.get(e[1], 999)  # 999 para etapas no mapeadas al final
        )

        if not etapas:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron etapas para este expediente"
            )

        logger.info(f"[DOWNLOAD-ALL] Encontradas {len(etapas)} etapas")

        # Conjunto para rastrear IDs únicos (deduplicación)
        ids_vistos = set()
        documentos_ids = []  # Lista de IDs de documentos en orden

        # Recorrer etapas en orden y recolectar IDs de documentos
        for etapa_id, tipo_etapa_id, nombre_etapa in etapas:
            logger.info(f"[DOWNLOAD-ALL] Procesando etapa: {nombre_etapa} (ID: {etapa_id})")

            # 1. ACTO ADMINISTRATIVO
            stmt = select(ActoAdministrativo.id, ActoAdministrativo.url_acto, ActoAdministrativo.tipo_acto).where(
                ActoAdministrativo.etapa_id == etapa_id
            )
            result = await db.execute(stmt)
            actos = result.all()

            for acto_id, url_acto, tipo_acto in actos:
                if url_acto and url_acto not in ids_vistos:
                    ids_vistos.add(url_acto)
                    documentos_ids.append(url_acto)
                    logger.info(f"  ✓ Agregado acto administrativo: {tipo_acto} (ID: {url_acto})")

                # 2. COMUNICACIÓN O NOTIFICACIÓN (verificar cuál existe)

                # 2a. Verificar si tiene COMUNICACIÓN
                stmt_com = select(Comunicacion.documento_comunicacion_id).where(
                    Comunicacion.acto_admin_id == acto_id
                ).where(Comunicacion.acto_administrativo_id == acto_id)
                result_com = await db.execute(stmt_com)
                comunicacion_id = result_com.scalar_one_or_none()

                if comunicacion_id:
                    if comunicacion_id not in ids_vistos:
                        ids_vistos.add(comunicacion_id)
                        documentos_ids.append(comunicacion_id)
                        logger.info(f"  ✓ Agregado comunicación (ID: {comunicacion_id})")
                else:
                    # 2b. Si no hay comunicación, verificar NOTIFICACIONES
                    stmt_not_id = select(Notificacion.documento_notificacion_id,
                                        Notificacion.documento_citacion_id,
                                        Notificacion.involucrado_id).where(
                                        Notificacion.acto_administrativo_id == acto_id
                    )
                    result_not = await db.execute(stmt_not_id)
                    notificacion_id = result_not.scalar_one_or_none()

                    if notificacion_id:
                        for id_notificacion, id_citacion, involucrado_id in result_not.all():
                            # Primero citación
                            if id_citacion and id_citacion not in ids_vistos:
                                ids_vistos.add(id_citacion)
                                documentos_ids.append(id_citacion)
                                logger.info(f"  ✓ Agregado citación para {involucrado_id} (ID: {id_citacion})")

                            # Luego notificación
                            if id_notificacion and id_notificacion not in ids_vistos:
                                ids_vistos.add(id_notificacion)
                                documentos_ids.append(id_notificacion)
                                logger.info(f"  ✓ Agregado notificación para {involucrado_id} (ID: {id_notificacion})")

            # 3. DOCUMENTOS ANEXOS (ordenados por fecha de subida, más antigua primero)
            stmt = (
                select(DocumentoAnexo.documento_anexo_id)
                .where(DocumentoAnexo.etapa_id == etapa_id)
            )
            result = await db.execute(stmt)
            documentos_etapa = result.all()

            for doc_id, in documentos_etapa:
                if doc_id and doc_id not in ids_vistos:
                    ids_vistos.add(doc_id)
                    documentos_ids.append(doc_id)
                    logger.info(f"  ✓ Agregado documento anexo (ID: {doc_id})")

        if not documentos_ids:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron documentos para este expediente"
            )

        logger.info(
            f"[DOWNLOAD-ALL] Total documentos únicos a combinar: {len(documentos_ids)}"
        )

        # Convertir cookies del request a diccionario
        cookies_dict = {k: v for k, v in request.cookies.items()}

        resultado = await download_unified_pdf(
            gateway_url=GATEWAY_URL,
            file_ids=documentos_ids,
            cookies=cookies_dict
        )

        if not resultado.get("ok"):
            raise HTTPException(
                status_code=500,
                detail=f"Error generando PDF unificado: {resultado.get('message', 'Error desconocido')}"
            )

        # Nombre del archivo de salida
        filename = f"expediente_{radicado}_completo.pdf"

        logger.info(f"[DOWNLOAD-ALL] PDF generado exitosamente: {filename}")

        # Retornar PDF combinado desde app-docs
        from io import BytesIO
        return StreamingResponse(
            BytesIO(resultado["content"]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"[DOWNLOAD-ALL] Error al generar PDF combinado: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar PDF combinado: {str(e)}"
        )

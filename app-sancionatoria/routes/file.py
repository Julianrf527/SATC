from fastapi import UploadFile, File, Request, APIRouter, Depends, HTTPException, Form, Body, Query, Path as PathParam
from fastapi.responses import JSONResponse
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func, desc, cast, String
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
from typing import List, Optional
from zoneinfo import ZoneInfo
import shutil
import logging
import os
import pytz

#----- DB -----

from db.deps import get_db
from db.models.recurso_afectado import RecursoAfectado
from db.models.expediente_recurso import ExpedienteRecurso
from db.models.expediente import Expediente
from db.models.involucrado_expediente import InvolucradoExpediente
from db.models.involucrado import Involucrado
from db.models.vereda import Vereda
from db.models.municipio import Municipio
from db.models.involucrado_notificacion import InvolucradoNotificacion
from db.models.etapa import Etapa
from db.models.tipo_etapa import TipoEtapa
from db.models.medida_preventiva import MedidaPreventiva
from db.models.cesacion import Cesacion
from db.models.formulacion_cargos import FormulacionCargos
from db.models.decision_fondo import DecisionFondo
from db.models.ejecucion_sancion import EjecucionSancion
from db.models.acto_admin import ActoAdmin
from db.models.tipo_notificacion import TipoNotificacion
from db.models.comunicacion import Comunicacion
from db.models.notificacion import Notificacion
from db.models.log_auditoria import LogAuditoria
from db.models.documento import Documento


router = APIRouter()
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_DAYS = os.getenv("JWT_EXP_DAYS")
ENCARGADO_PERMISSION = os.getenv("ENCARGADO_PERMISSION")
FILE_PERMISSION = os.getenv("FILE_PERMISSION")
LOG_PERMISSION = os.getenv("LOG_PERMISSION")
GATEWAY_URL = os.getenv("API_GATEWAY_URL")


bogota_tz = pytz.timezone("America/Bogota")

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Subir a ApiCorp
DOCS_DIR = BASE_DIR / "uploads" / "expedientes"

# ---------- LOGGER ------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- MODELOS ----------

class FileModal(BaseModel):
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

class InvolucradoExpedienteLink(BaseModel):
    involucrado_id: int

class Procedure(BaseModel):
    radicado: str
    etapaId: int
    tipoNotificacion: int
    nombre: str

class Notification(BaseModel):
    involucrado_id: int
    proceso_id: int
    numero_envio: str
    fecha_envio: str | None = None
    fecha_constancia: str | None = None
    notificacion_exitosa: bool
    etapa_id: int

class Measure(BaseModel):
    tipo_medida_id: int
    cantidad: str
    especie: str
    estado_medida: bool | None
    etapa_id: int

class CesacionData(BaseModel):
    id: int | None = None
    tipo_cesacion_id: int
    etapa_id: int

class FormulationCharges(BaseModel):
    id: int | None = None
    descargos: bool | None = None
    etapa_id: int

class Decision(BaseModel):
    tipo_sancion_id: int
    detalle: str
    etapa_id: int

class Execution(BaseModel):
    cobro_coactivo: bool
    disposicion: bool
    ruia: bool
    act_admin: str
    fecha_act: date
    etapa_id: int

class ComunicacionCreate(BaseModel):
    acto_admin_id: int
    numerado: str = Field(..., min_length=4, max_length=4)
    fecha_numerado: date
    fecha_envio: date

class ComunicacionUpdate(BaseModel):
    numerado: str = Field(..., min_length=4, max_length=4)
    fecha_numerado: date
    fecha_envio: date
    
    @validator('numerado')
    def validate_numerado(cls, v):
        if not v.isdigit():
            raise ValueError('El numerado debe contener solo dígitos')
        return v

class FiltroAvanzado(BaseModel):
    """Filtros avanzados que NO están en quick filters."""
    motivo_afectacion: Optional[str] = None
    direccion: Optional[str] = None
    municipio_id: Optional[int] = None
    vereda_ids: Optional[List[int]] = None
    recurso_ids: Optional[List[int]] = None
    valor_exacto: bool = False
#----------- FUNCIONES ------------

from utils.verify_gateway_token import verify_gateway_token
from services.usuarios import obtener_info_usuarios, obtener_usuarios_por_permiso, crear_notificacion_usuario, verificar_permiso_externo
from services.alertas import calcular_alertas_expediente

from services.crud_file_operations import (
    get_indagacion_preliminar,
    get_medida_preventiva,
    get_inicio_proceso_sancionatorio,
    get_cesacion,
    get_formulacion_cargos,
    get_apertura_etapa_probatoria,
    get_cierre_etapa_probatoria,
    get_decision_fondo,
    get_recurso,
    insert_log_auditoria,
)


# ---------- ENDPOINTS ----------

@router.get("/get")
async def obtener_expedientes(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=200),
    radicado: str = Query(None),
    nombre_expediente: str = Query(None),
    fecha_creacion: str = Query(None),
    encargado_id: int = Query(None),
):
    try:
        usuario_id = verify_gateway_token(request)

        fecha = None
        if fecha_creacion:
            fecha = datetime.fromisoformat(fecha_creacion)

        count_stmt = select(func.count()).select_from(Expediente)
        data_stmt = select(
            Expediente.radicado,
            Expediente.nombre_expediente,
            Expediente.fecha_creacion,
            Expediente.encargado_id,
        )

        if radicado:
            count_stmt = count_stmt.where(Expediente.radicado.contains(radicado))
            data_stmt = data_stmt.where(Expediente.radicado.contains(radicado))

        if nombre_expediente:
            count_stmt = count_stmt.where(
                Expediente.nombre_expediente.ilike(f"%{nombre_expediente}%")
            )
            data_stmt = data_stmt.where(
                Expediente.nombre_expediente.ilike(f"%{nombre_expediente}%")
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

        usuarios_disponibles = await obtener_usuarios_por_permiso(FILE_PERMISSION)

        payload = [
            {
                "radicado": r[0],
                "nombre_expediente": r[1],
                "fecha_creacion": r[2].isoformat() if r[2] else None,
                "encargado_id": r[3],
                "encargado_nombre": usuarios_disponibles.get(r[3], {}).get("nombre") if r[3] else None,
            }
            for r in rows
        ]

        usuarios_disponibles_lista = [
            {
                "id": user_id,
                "name": info["nombre"],
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
        usuario_id = verify_gateway_token(request)
        
        logger.info(f"====== INICIO FILTRADO AVANZADO ======")
        logger.info(f"Usuario: {usuario_id}")
        logger.info(f"Filtros recibidos: {filtros.model_dump()}")
        print(f"\n[DEBUG] Filtros: {filtros.model_dump()}\n")

        # Consulta base con joins necesarios
        stmt = (
            select(
                Expediente.radicado,
                Expediente.nombre_expediente,
                Expediente.fecha_creacion,
                Expediente.motivo_afectacion,
                Expediente.direccion,
                Vereda.municipio_id,
                Expediente.vereda_id
            )
            .join(Vereda, Vereda.id == Expediente.vereda_id, isouter=True)
            .where(Expediente.encargado_id == usuario_id)
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

        radicados = [r[0] for r in expedientes_raw]
        radicados_filtrados = set(radicados)

        # Filtro: Recursos afectados (múltiples)
        if filtros.recurso_ids:
            logger.info(f"Filtrando por recursos: {filtros.recurso_ids}")
            stmt_recursos = (
                select(ExpedienteRecurso.expediente_radicado)
                .where(
                    and_(
                        ExpedienteRecurso.expediente_radicado.in_(radicados),
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
        involucrados_map = defaultdict(list)
        if radicados_filtrados:
            st_invo = (
                select(
                    InvolucradoExpediente.expediente_radicado,
                    Involucrado.numero_documento,
                    Involucrado.nombre,
                )
                .join(Involucrado, InvolucradoExpediente.involucrado_id == Involucrado.id)
                .where(InvolucradoExpediente.expediente_radicado.in_(radicados_filtrados))
            )
            res_invo = await db.execute(st_invo)

            for rad, doc, nombre in res_invo.all():
                involucrados_map[rad].append({"numero_documento": doc, "nombre": nombre})

        # Construir respuesta
        data = []
        for rad, nombre_exp, fecha_crea, motivo, direccion, municipio_id, vereda_id in expedientes_raw:
            data.append({
                "radicado": rad,
                "nombre": nombre_exp,
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
        logger.error(f"ERROR CRÍTICO en filtrado avanzado")
        logger.error(f"Tipo de error: {type(e).__name__}")
        logger.error(f"Mensaje: {str(e)}")
        logger.error(f"Traceback completo:\n{error_detail}")
        print(f"\n{'='*80}")
        print(f"ERROR EN ENDPOINT /filter")
        print(f"{'='*80}")
        print(error_detail)
        print(f"{'='*80}\n")
        raise HTTPException(status_code=500, detail=f"Error al aplicar filtros: {str(e)}")

@router.get("/affected-resource")
async def obtener_recurso_afectado(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        stmr = select(RecursoAfectado)
        result = await db.execute(stmr)
        result = result.scalars().all()

        data = [
            {
                "id": ra.id,
                "name": ra.nombre
            }
            for ra in result
        ]

        return JSONResponse(content={"ok": True, "data": data}, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/get/all")
async def obtener_expedientes_para_vista(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

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
                (latest_etapa_subq.c.expediente_radicado == Expediente.radicado) &
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

        radicados = [exp.radicado for exp in expedientes]

        recursos_map = defaultdict(list)
        if radicados:
            st_rec = (
                select(
                    ExpedienteRecurso.expediente_radicado,
                    ExpedienteRecurso.recurso_id,
                )
                .where(ExpedienteRecurso.expediente_radicado.in_(radicados))
            )
            res_rec = await db.execute(st_rec)
            for rad, recurso_id in res_rec.all():
                recursos_map[rad].append(recurso_id)

        involucrados_map = defaultdict(list)
        if radicados:
            st_invo = (
                select(
                    InvolucradoExpediente.expediente_radicado,
                    Involucrado.id,
                    Involucrado.numero_documento,
                    Involucrado.tipo_documento,
                    Involucrado.nombre,
                    Involucrado.celular,
                    Involucrado.correo,
                )
                .join(Involucrado, InvolucradoExpediente.involucrado_id == Involucrado.id)
                .where(InvolucradoExpediente.expediente_radicado.in_(radicados))
            )
            res_invo = await db.execute(st_invo)
            for row in res_invo.all():
                involucrados_map[row[0]].append({
                    "id": row[1],
                    "numero_documento": row[2],
                    "tipo_documento": row[3],
                    "nombre": row[4],
                    "celular": row[5],
                    "correo": row[6],
                })

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
                "radicado": exp.radicado,
                "nombre": exp.nombre_expediente,
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

    except Exception:
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

        radicados = [r[0] for r in expedientes_raw]
        municipio_ids = [r[3] for r in expedientes_raw if r[3] is not None]

        municipios_map = {}
        if municipio_ids:
            res_mun = await db.execute(
                select(Municipio.id, Municipio.nombre)
                .where(Municipio.id.in_(municipio_ids))
            )
            municipios_map = {
                m_id: {"id": m_id, "name": m_nombre}
                for m_id, m_nombre in res_mun.all()
            }

        involucrados_map = defaultdict(list)
        if radicados:
            st_invo = (
                select(
                    InvolucradoExpediente.expediente_radicado,
                    Involucrado.numero_documento,
                    Involucrado.nombre,
                )
                .join(Involucrado, InvolucradoExpediente.involucrado_id == Involucrado.id)
                .where(InvolucradoExpediente.expediente_radicado.in_(radicados))
            )
            res_invo = await db.execute(st_invo)
            for rad, doc, nombre in res_invo.all():
                involucrados_map[rad].append({
                    "numero_documento": doc,
                    "nombre": nombre
                })

        data = []
        for rad, nombre_exp, fecha_crea, municipio_id, ultima_etapa in expedientes_raw:
            data.append({
                "radicado": rad,
                "nombre": nombre_exp,
                "fecha_creacion": fecha_crea.isoformat() if fecha_crea else None,
                "municipio": municipios_map.get(municipio_id),
                "involucrados": involucrados_map.get(rad, []),
                "ultima_etapa": ultima_etapa
            })

        return JSONResponse(content={"ok": True, "data": data}, status_code=200)

    except Exception:
        raise HTTPException(status_code=500, detail="Error del servidor")

@router.post("/add")
async def agregar_expediente(
    request: Request,
    file: FileModal,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        stmt = select(Expediente).where(Expediente.radicado == file.radicado)
        result = await db.execute(stmt)
        existing_file = result.scalar_one_or_none()

        if existing_file:
            raise HTTPException(status_code=400, detail="El radicado ya existe")

        new_file = Expediente(
            radicado=file.radicado,
            nombre_expediente=file.expediente,
            motivo_afectacion=file.motivo,
            encargado_id=file.encargado_id,
            direccion=file.direccion,
            vereda_id=file.vereda,
        )

        db.add(new_file)
        await db.flush()

        for recurso_id in file.recurso:
            db.add(
                ExpedienteRecurso(
                    expediente_radicado=file.radicado,
                    recurso_id=recurso_id,
                )
            )

        datos_nuevos = {
            "radicado": file.radicado,
            "nombre_expediente": file.expediente,
            "motivo_afectacion": file.motivo,
            "encargado_id": file.encargado_id,
            "direccion": file.direccion,
            "vereda_id": file.vereda,
            "recursos": file.recurso
        }

        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="expediente",
            tipo_operacion="INSERT",
            descripcion=f"Creación de expediente {file.radicado}",
            expediente_radicado=file.radicado,
            id_registro=file.radicado,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()
        await db.refresh(new_file)

        return JSONResponse(
            content={"ok": True, "radicado": new_file.radicado},
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{radicado}/encargado/{encargado_id}")
async def actualizar_encargado_de_expediente(
    request: Request,
    radicado: str,
    encargado_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        res = await verificar_permiso_externo(usuario_id, ENCARGADO_PERMISSION)

        if not res["ok"]:
            raise HTTPException(status_code=403, detail="No cuenta con permisos")

        # Obtener datos anteriores
        stmt_check = select(Expediente).where(Expediente.radicado == radicado)
        res_check = await db.execute(stmt_check)
        expediente = res_check.scalar_one_or_none()

        if expediente is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        datos_anteriores = {
            "radicado": radicado,
            "encargado_id": expediente.encargado_id
        }

        new_value = None if encargado_id == 0 else encargado_id

        # Actualizar encargado
        stmt = (
            update(Expediente)
            .where(Expediente.radicado == radicado)
            .values({Expediente.encargado_id: new_value})
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt)

        if result.rowcount == 0:
            raise HTTPException(status_code=400, detail="Expediente no encontrado")

        datos_nuevos = {
            "radicado": radicado,
            "encargado_id": new_value
        }

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="expediente",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de encargado del expediente {radicado}",
            expediente_radicado=radicado,
            id_registro=radicado,
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
            notif_result = await crear_notificacion_usuario(
                mensaje=f"Se te ha asignado el expediente {radicado}",
                ruta=f"/expedientes/{radicado}",
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

# Archivar expediente
@router.patch("/{radicado}/archive")
async def archivar_expediente(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Archiva un expediente. Solo disponible cuando se ha completado la etapa de Ejecución de la Sanción.
    Esta acción no se puede revertir.
    """
    try:
        usuario_id = verify_gateway_token(request)

        # Obtener datos anteriores
        stmt_check = select(Expediente).where(Expediente.radicado == radicado)
        res_check = await db.execute(stmt_check)
        expediente = res_check.scalar_one_or_none()

        if expediente is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        # Verificar que el usuario es el encargado
        if expediente.encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para archivar este expediente")

        # Verificar si ya está archivado
        if expediente.archivado:
            raise HTTPException(status_code=400, detail="El expediente ya está archivado")

        datos_anteriores = {
            "radicado": radicado,
            "archivado": expediente.archivado
        }

        # Archivar expediente
        stmt = (
            update(Expediente)
            .where(Expediente.radicado == radicado)
            .values(archivado=True, fecha_archivado=datetime.now().replace(tzinfo=None))
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt)

        if result.rowcount == 0:
            raise HTTPException(status_code=400, detail="No se pudo archivar el expediente")

        datos_nuevos = {
            "radicado": radicado,
            "archivado": True
        }

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="expediente",
            tipo_operacion="UPDATE",
            descripcion=f"Archivado del expediente {radicado}",
            expediente_radicado=radicado,
            id_registro=radicado,
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

# -------- Etapas ----------
@router.post("/{radicado}/stage/{type}")
async def crear_etapa(
    request: Request,
    radicado: str = PathParam(..., description="Radicado del expediente"),
    type: int = PathParam(..., description="Tipo etapa a crear"),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        # Verificar permisos
        stmr = select(Expediente.radicado).where(
            Expediente.radicado == radicado, 
            Expediente.encargado_id == int(usuario_id)
        )
        res = await db.execute(stmr)
        expediente = res.scalar_one_or_none()

        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")

        # Crear nueva etapa
        stmt = (
            insert(Etapa)
            .values(
                expediente_radicado=radicado,
                tipo_etapa_id=type,
                fecha_inicio=datetime.now().replace(tzinfo=None)
            )
            .returning(Etapa.id)
        )
        etapa_id = await db.scalar(stmt)
        await db.flush()

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": etapa_id,
            "expediente_radicado": radicado,
            "tipo_etapa_id": type,
            "fecha_inicio": str(datetime.now().replace(tzinfo=None))
        }

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="etapa",
            tipo_operacion="INSERT",
            descripcion=f"Creación de etapa tipo {type}",
            expediente_radicado=radicado,
            id_registro=str(etapa_id),
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()

        return JSONResponse(content={"ok": True, "etapa_id": etapa_id}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al crear etapa: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

#File
@router.get("/full/{radicado}")
async def obtener_expedientes_completo_por_radicado(
    request:Request,
    radicado: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        usuario_id = verify_gateway_token(request)

        # 1) Última etapa por expediente
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

        # 2) Consulta principal 
        stmt = (
            select(
                Expediente.radicado,
                Expediente.motivo_afectacion,
                Expediente.direccion,
                Expediente.vereda_id,
                Expediente.id_auxiliar,
                TipoEtapa.nombre.label("ultima_etapa")
            )
            .join(
                latest_etapa_subq,
                (latest_etapa_subq.c.expediente_radicado == Expediente.radicado)
                & (latest_etapa_subq.c.rn == 1),
                isouter=True
            )
            .join(TipoEtapa, TipoEtapa.id == latest_etapa_subq.c.tipo_etapa_id, isouter=True)
            .where(Expediente.radicado == radicado)
        )

        res = await db.execute(stmt)
        expedientes_raw = res.all()

        if not expedientes_raw:
            return JSONResponse(content={"ok": True, "data": []}, status_code=200)

        # 3) Verificar permisos
        stmt_check = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        res_check = await db.execute(stmt_check)
        current_encargado = res_check.scalar_one_or_none()

        if current_encargado is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if current_encargado != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        radicados = [r[0] for r in expedientes_raw]
        vereda_ids = [r[3] for r in expedientes_raw if r[3]]

        # 4) Recursos afectados 
        recursos_map = defaultdict(list)
        if radicados:
            stmr_rec = (
                select(
                    ExpedienteRecurso.expediente_radicado,
                    ExpedienteRecurso.recurso_id,
                )
                .where(ExpedienteRecurso.expediente_radicado.in_(radicados))
            )
            res_rec = await db.execute(stmr_rec)
            for rad, recurso_id in res_rec.all():
                recursos_map[rad].append(recurso_id)

        # 5) Involucrados - TODA LA DATA (como en /file/{encargado_id})
        involucrados_map = defaultdict(list)
        if radicados:
            stmr_invo = (
                select(
                    InvolucradoExpediente.expediente_radicado,
                    Involucrado.id,
                    Involucrado.numero_documento,
                    Involucrado.digito_verificacion,
                    Involucrado.tipo_documento,
                    Involucrado.nombre,
                    Involucrado.celular,
                    Involucrado.correo,
                )
                .join(Involucrado, InvolucradoExpediente.involucrado_id == Involucrado.id)
                .where(InvolucradoExpediente.expediente_radicado.in_(radicados))
            )
            res_invo = await db.execute(stmr_invo)
            for row in res_invo.all():
                rad = row[0]
                involucrado = {
                    "id": row[1],
                    "numero_documento": row[2],
                    "digito_verificacion": row[3],
                    "tipo_documento": row[4],
                    "nombre": row[5],
                    "celular": row[6],
                    "correo": row[7],
                }
                involucrados_map[rad].append(involucrado)

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
        for radicado, motivo, direccion, vereda_id, id_auxiliar, ultima_etapa in expedientes_raw:
            exp_dict = {
                "radicado": radicado,
                "recurso_afectado": recursos_map.get(radicado, []),
                "motivo_afectacion": motivo,
                "direccion": direccion,
                "vereda": veredas_map.get(vereda_id),
                "id_auxiliar": id_auxiliar,
                "ultima_etapa": ultima_etapa,
                "involucrados": involucrados_map.get(radicado, []),
            }

        stmt = select(TipoNotificacion)
        res = await db.execute(stmt)
        tnotificaciones = res.scalars().all()
        tnotificaciones_list = [{"id": tn.id, "nombre": tn.nombre} for tn in tnotificaciones]

        return JSONResponse(
            content={
                "ok": True, 
                "data": exp_dict,
                "tipo_notificacion": tnotificaciones_list
            }, 
            status_code=200
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error en /file/full/{radicado}: {e}")
        raise HTTPException(status_code=500, detail="Error del servidor")

#Informacion
@router.put("/{radicado}/basic-data")
async def actualizar_informacion_expediente(
    request: Request,
    radicado: str,
    file: FileUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        usuario_id = verify_gateway_token(request)

        stmt_check = select(Expediente).where(Expediente.radicado == radicado)
        res_check = await db.execute(stmt_check)
        expediente_actual = res_check.scalar_one_or_none()

        if expediente_actual is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if expediente_actual.encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para actualizar este expediente"
            )

        # Obtener recursos anteriores
        stmt_recursos = select(ExpedienteRecurso.recurso_id).where(
            ExpedienteRecurso.expediente_radicado == radicado
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

        if radicado != file.radicado:
            stmr = select(Expediente).where(Expediente.radicado == file.radicado)
            result = await db.execute(stmr)
            duplicate_rol = result.scalar_one_or_none()

            if duplicate_rol:
                raise HTTPException(status_code=409, detail="El radicado ya está en uso.")

        stmr = (
            update(Expediente)
            .where(Expediente.radicado == radicado)
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
                    expediente_radicado=file.radicado,
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

        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="expediente",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de expediente '{radicado}' a '{file.radicado}'",
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
        raise HTTPException(status_code=500, detail=str(e))

#Indagacion Preliminar
@router.get("/investigation/{radicado}")
async def obtener_indagacion_preliminar(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)

        select_stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != user_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_indagacion_preliminar(radicado, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Indagación preliminar no encontrada")
        return JSONResponse(content={"ok": True, "indagacion": data["indagacion"]}, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#Medida Preventiva
@router.get("/measure/{radicado}")
async def obtener_medida_preventiva(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != user_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_medida_preventiva(radicado, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Medida preventiva no encontrada")
        return JSONResponse(content={"ok": True, "medida": data["medida"]}, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/measure")
async def create_measure(
    request:Request,
    data: Measure,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        stmr = (
            select(Etapa, Expediente.radicado)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                Etapa.id == data.etapa_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        row = res.first()

        if not row:
            raise HTTPException(
                status_code=404, 
                detail="Etapa no encontrada o sin permisos"
            )

        etapa, radicado = row

        stmt_check = select(MedidaPreventiva).where(
            MedidaPreventiva.etapa_id == data.etapa_id
        )
        existing = await db.scalar(stmt_check)
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Ya existe una medida preventiva para esta etapa"
            )

        nueva_medida = MedidaPreventiva(
            tipo_medida_id=data.tipo_medida_id,
            cantidad=data.cantidad,
            especie=data.especie,
            estado_medida=data.estado_medida,
            etapa_id=data.etapa_id
        )
        
        db.add(nueva_medida)
        await db.flush()

        datos_nuevos = {
            "id": nueva_medida.id,
            "tipo_medida_id": nueva_medida.tipo_medida_id,
            "cantidad": nueva_medida.cantidad,
            "especie": nueva_medida.especie,
            "estado_medida": nueva_medida.estado_medida,
            "etapa_id": nueva_medida.etapa_id
        }

        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="medida_preventiva",
            tipo_operacion="INSERT",
            descripcion=f"Creación de medida preventiva ID {nueva_medida.id}",
            expediente_radicado=radicado,
            id_registro=str(nueva_medida.id),
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
            content={
                "ok": True,
                "id": nueva_medida.id,
                "message": "Medida preventiva creada correctamente"
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/measure/{medida_id}")
async def update_measure(
    request: Request,
    medida_id: int,
    data: Measure,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        stmr = (
            select(MedidaPreventiva, Expediente.radicado)
            .join(Etapa, MedidaPreventiva.etapa_id == Etapa.id)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                MedidaPreventiva.id == medida_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        row = res.first()

        if not row:
            raise HTTPException(status_code=404, detail="Medida preventiva no encontrada o sin permisos")

        medida, radicado = row

        datos_anteriores = {
            "id": medida.id,
            "tipo_medida_id": medida.tipo_medida_id,
            "cantidad": medida.cantidad,
            "especie": medida.especie,
            "estado_medida": medida.estado_medida,
            "etapa_id": medida.etapa_id
        }

        stmt = (
            update(MedidaPreventiva)
            .where(MedidaPreventiva.id == medida_id)
            .values(
                tipo_medida_id=data.tipo_medida_id,
                cantidad=data.cantidad,
                especie=data.especie,
                estado_medida=data.estado_medida,
            )
        )
        await db.execute(stmt)

        datos_nuevos = {
            "id": medida_id,
            "tipo_medida_id": data.tipo_medida_id,
            "cantidad": data.cantidad,
            "especie": data.especie,
            "estado_medida": data.estado_medida,
            "etapa_id": medida.etapa_id
        }

        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="medida_preventiva",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de medida preventiva ID {medida_id}",
            expediente_radicado=radicado,
            id_registro=str(medida_id),
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
            content={
                "ok": True,
                "id": medida_id,
                "message": "Medida preventiva actualizada correctamente"
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

#Inicio de proceso sancionatorio
@router.get("/start-process/{radicado}")
async def obtener_inicio_proceso_sancionatorio(
    request :Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_inicio_proceso_sancionatorio(radicado, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Inicio proceso sancionatorio no encontrada")
        return JSONResponse(content={"ok": True, "inicio_proceso": data["inicio_proceso"]}, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#Cesacion
@router.get("/cessation/{radicado}")
async def obtener_cesacion(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != user_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_cesacion(radicado, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Cesacion no encontrada")
        return JSONResponse(content={"ok": True, "cesacion": data["cesacion"]}, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cessation")
async def create_law(
    request: Request,
    data: CesacionData,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        stmr = (
            select(Expediente.radicado)
            .join(Etapa, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                Etapa.id == data.etapa_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        radicado = res.scalar_one_or_none()

        if not radicado:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")

        stmt = (
            insert(Cesacion)
            .values(
                tipo_cesacion_id=data.tipo_cesacion_id,
                etapa_id=data.etapa_id
            )
            .returning(Cesacion.id)
        )
        result = await db.execute(stmt)
        cesacion_id = result.scalar_one()

        datos_nuevos = {
            "id": cesacion_id,
            "tipo_cesacion_id": data.tipo_cesacion_id,
            "etapa_id": data.etapa_id
        }

        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="cesacion",
            tipo_operacion="INSERT",
            descripcion=f"Creación de cesación ID {cesacion_id}",
            expediente_radicado=radicado,
            id_registro=str(cesacion_id),
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
            content={
                "ok": True,
                "id": cesacion_id,
                "message": "Ley 1333/2009 creada correctamente"
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/cessation/{cessation_id}")
async def update_law(
    request:Request,
    cessation_id: int,
    data: CesacionData,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        stmr = (
            select(Cesacion, Etapa.expediente_radicado)
            .join(Etapa, Cesacion.etapa_id == Etapa.id)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                Cesacion.id == cessation_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        row = res.first()

        if not row:
            raise HTTPException(status_code=404, detail="Ley no encontrada o sin permisos")

        cesacion, radicado = row

        datos_anteriores = {
            "id": cesacion.id,
            "tipo_cesacion_id": cesacion.tipo_cesacion_id,
            "etapa_id": cesacion.etapa_id
        }

        stmt = (
            update(Cesacion)
            .where(Cesacion.id == cessation_id)
            .values(tipo_cesacion_id=data.tipo_cesacion_id)
        )
        await db.execute(stmt)

        datos_nuevos = {
            "id": cessation_id,
            "tipo_cesacion_id": data.tipo_cesacion_id,
            "etapa_id": cesacion.etapa_id
        }

        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="cesacion",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de cesación ID {cessation_id}",
            expediente_radicado=radicado,
            id_registro=str(cessation_id),
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
            content={
                "ok": True,
                "id": cessation_id,
                "message": "Ley 1333/2009 actualizada correctamente"
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Formulacion de cargos
@router.get("/formulation/{radicado}")
async def obtener_formulacion_cargos(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_formulacion_cargos(radicado, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Formulacion de cargos no encontrada")
        return JSONResponse(content={"ok": True, "formulacion": data["formulacion_cargos"]}, status_code=200)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al obtener formulacion de cargos para radicado '{radicado}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al consultar formulacion de cargos")

@router.post("/formulation")
async def create_formulation(
    request: Request,
    etapa_id: int = Form(...),
    descargos: str = Form(...),
    id_auxiliar: int = Form(...),
    tipo_etapa: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),

):
    try:
        usuario_id = verify_gateway_token(request)
        
        # Convertir string a boolean o None
        descargos_bool: bool | None = None
        if descargos == "true":
            descargos_bool = True
        elif descargos == "false":
            descargos_bool = False
        elif descargos == "null":
            descargos_bool = None

        # Validar que el expediente corresponde al usuario y etapa
        stmr = (
            select(Expediente.radicado)
            .join(Etapa, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                Etapa.id == etapa_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        expediente = res.scalar_one_or_none()

        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")

        # Variable para la URL del documento
        url_documento = None

        # Guardar archivo si existe
        if file and file.filename:
            if file.content_type != "application/pdf":
                raise HTTPException(status_code=400, detail="El archivo debe ser PDF")
            
            # Validar tamaño del archivo (10MB máximo)
            file.file.seek(0, 2)  # Mover al final del archivo
            file_size = file.file.tell()  # Obtener posición (tamaño)
            file.file.seek(0)  # Volver al inicio
            
            if file_size > 10 * 1024 * 1024:  # 10MB en bytes
                raise HTTPException(status_code=400, detail="El archivo no debe superar los 10MB")
            
            # Crear directorio usando ruta absoluta
            expediente_path = DOCS_DIR / str(id_auxiliar)
            etapa_path = expediente_path / tipo_etapa
            etapa_path.mkdir(parents=True, exist_ok=True)
            
            # Generar nombre de archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"FormulacionCargos_{timestamp}.pdf"
            file_path = etapa_path / file_name
            
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            url_documento = f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/{file_name}"

        # Insertar formulación
        stmt = (
            insert(FormulacionCargos)
            .values(
                descargos=descargos_bool,
                url_documento=url_documento,
                etapa_id=etapa_id
            )
            .returning(FormulacionCargos.id)
        )
        result = await db.execute(stmt)
        formulacion_id = result.scalar_one()

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": formulacion_id,
            "descargos": descargos_bool,
            "url_documento": url_documento,
            "etapa_id": etapa_id
        }

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="FormulacionCargos",
            tipo_operacion="INSERT",
            descripcion=f"Creación de formulación de cargos ID {formulacion_id}",
            expediente_radicado=expediente,
            id_registro=str(formulacion_id),
            datos_anteriores=None,
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
            content={
                "ok": True,
                "id": formulacion_id,
                "message": "Formulación de cargos creada correctamente"
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando Formulación de cargos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/formulation/{formulation_id}")
async def update_formulation(
    request: Request,
    formulation_id: int,
    etapa_id: int = Form(...),
    descargos: str = Form(...),
    id_auxiliar: int = Form(...),
    tipo_etapa: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        
        # Convertir string a boolean o None
        descargos_bool: bool | None = None
        if descargos == "true":
            descargos_bool = True
        elif descargos == "false":
            descargos_bool = False
        elif descargos == "null":
            descargos_bool = None

        # Obtener datos anteriores y validar permisos
        stmr = (
            select(
                FormulacionCargos.id,
                FormulacionCargos.descargos,
                FormulacionCargos.url_documento,
                FormulacionCargos.etapa_id,
                Expediente.radicado
            )
            .join(Etapa, FormulacionCargos.etapa_id == Etapa.id)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                FormulacionCargos.id == formulation_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        registro = res.first()

        if not registro:
            raise HTTPException(status_code=404, detail="Formulación de cargos no encontrada o sin permisos")

        # Preparar datos anteriores
        datos_anteriores = {
            "id": registro.id,
            "descargos": registro.descargos,
            "url_documento": registro.url_documento,
            "etapa_id": registro.etapa_id
        }

        # Mantener URL anterior por defecto
        url_documento = registro.url_documento

        # Si se envió un nuevo archivo, procesarlo
        if file and file.filename:
            if file.content_type != "application/pdf":
                raise HTTPException(status_code=400, detail="El archivo debe ser PDF")
            
            # Validar tamaño del archivo (10MB máximo)
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
            
            if file_size > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="El archivo no debe superar los 10MB")
            
            # Crear directorio usando ruta absoluta
            expediente_path = DOCS_DIR / str(id_auxiliar)
            etapa_path = expediente_path / tipo_etapa
            etapa_path.mkdir(parents=True, exist_ok=True)
            
            # Eliminar archivo anterior si existe
            if registro.url_documento:
                old_file_path = DOCS_DIR.parent / registro.url_documento
                if old_file_path.exists():
                    try:
                        old_file_path.unlink()
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar el archivo anterior: {e}")
            
            # Generar nombre de archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"FormulacionCargos_{timestamp}.pdf"
            file_path = etapa_path / file_name
            
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            url_documento = f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/{file_name}"

        # Actualizar registro
        stmt = (
            update(FormulacionCargos)
            .where(FormulacionCargos.id == formulation_id)
            .values(
                descargos=descargos_bool,
                url_documento=url_documento
            )
        )
        await db.execute(stmt)

        # Preparar datos nuevos
        datos_nuevos = {
            "id": formulation_id,
            "descargos": descargos_bool,
            "url_documento": url_documento,
            "etapa_id": registro.etapa_id
        }

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="FormulacionCargos",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de formulación de cargos ID {formulation_id}",
            expediente_radicado=registro.radicado,
            id_registro=str(formulation_id),
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
            content={
                "ok": True,
                "id": formulation_id,
                "message": "Formulación de cargos actualizada correctamente"
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error actualizando Formulación de cargos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# Apertura Etapa Probatoria
@router.get("/opening/{radicado}")
async def obtener_apertura_etapa_probatoria(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_apertura_etapa_probatoria(radicado, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Apertura etapa probatoria no encontrada")
        return JSONResponse(content={"ok": True, "apertura_etapa_probatoria": data["apertura_etapa_probatoria"]}, status_code=200)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al obtener apertura etapa probatoria para radicado '{radicado}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al consultar apertura etapa probatoria")

# Cierre Etapa Probatoria
@router.get("/closing/{radicado}")
async def obtener_cierre_etapa_probatoria(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_cierre_etapa_probatoria(radicado, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Cierre etapa probatoria no encontrada")
        return JSONResponse(content={"ok": True, "cierre_etapa_probatoria": data["cierre_etapa_probatoria"]}, status_code=200)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al obtener cierre etapa probatoria para radicado '{radicado}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al consultar cierre etapa probatoria")

# Decision de Fondo
@router.get("/decision/{radicado}")
async def obtener_decision(
    request:Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        logger.info(f"[DECISION] Iniciando consulta para radicado: {radicado}")
        usuario_id = verify_gateway_token(request)
        logger.info(f"[DECISION] Usuario autenticado: {usuario_id}")
        
        select_stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(select_stmt)
        logger.info(f"[DECISION] Encargado del expediente: {encargado_id}")
        
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        logger.info(f"[DECISION] Llamando a get_decision_fondo...")
        data = await get_decision_fondo(radicado, db)
        logger.info(f"[DECISION] Respuesta de get_decision_fondo: ok={data.get('ok')}, tiene decision_fondo={('decision_fondo' in data)}")
        
        # Verificar si hubo un error interno
        if not data.get("ok", False):
            logger.error(f"[DECISION] Error en get_decision_fondo: {data.get('error', 'Sin mensaje de error')}")
            raise HTTPException(status_code=500, detail="Error al consultar decisión de fondo")
        
        # Siempre devolver la respuesta, incluso si no hay decisión de fondo todavía
        logger.info(f"[DECISION] Devolviendo respuesta exitosa")
        return JSONResponse(content={"ok": True, "decision_fondo": data.get("decision_fondo", {})}, status_code=200)
    except HTTPException as he:
        logger.error(f"[DECISION] HTTPException: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Error al obtener decision de fondo para radicado '{radicado}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al consultar decision de fondo")

@router.post("/decision")
async def crear_decision(
    request:Request,
    data: Decision,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        # Validar que el expediente corresponde al usuario y etapa
        stmr = (
            select(Expediente.radicado)
            .join(Etapa, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                Etapa.id == data.etapa_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        expediente = res.scalar_one_or_none()

        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")

        # Insertar Decision de Fondo
        stmt = (
            insert(DecisionFondo)
            .values(
                tipo_sancion_id=data.tipo_sancion_id,
                detalle=data.detalle,
                etapa_id=data.etapa_id
            )
            .returning(DecisionFondo.id)
        )
        result = await db.execute(stmt)
        de_id = result.scalar_one()

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": de_id,
            "tipo_sancion_id": data.tipo_sancion_id,
            "detalle": data.detalle,
            "etapa_id": data.etapa_id
        }

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="DecisionFondo",
            tipo_operacion="INSERT",
            descripcion=f"Creación de decisión de fondo ID {de_id}",
            expediente_radicado=expediente,
            id_registro=str(de_id),
            datos_anteriores=None,
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
            content={
                "ok": True,
                "id": de_id,
                "message": "Decisión de fondo creada correctamente"
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando Decisión de fondo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/decision/{decision_id}")
async def update_decision(
    request: Request,
    decision_id: int,
    data: Decision,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        # Obtener datos anteriores y validar permisos
        stmr = (
            select(
                DecisionFondo.id,
                DecisionFondo.tipo_sancion_id,
                DecisionFondo.detalle,
                DecisionFondo.etapa_id,
                Expediente.radicado
            )
            .join(Etapa, DecisionFondo.etapa_id == Etapa.id)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                DecisionFondo.id == decision_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        row = res.first()

        if not row:
            raise HTTPException(status_code=404, detail="Decisión de fondo no encontrada o sin permisos")

        # Preparar datos anteriores
        datos_anteriores = {
            "id": row.id,
            "tipo_sancion_id": row.tipo_sancion_id,
            "detalle": row.detalle,
            "etapa_id": row.etapa_id
        }

        # Actualizar registro
        stmt = (
            update(DecisionFondo)
            .where(DecisionFondo.id == decision_id)
            .values(
                tipo_sancion_id=data.tipo_sancion_id,
                detalle=data.detalle
            )
        )
        await db.execute(stmt)

        # Preparar datos nuevos
        datos_nuevos = {
            "id": decision_id,
            "tipo_sancion_id": data.tipo_sancion_id,
            "detalle": data.detalle,
            "etapa_id": row.etapa_id
        }

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="DecisionFondo",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de decisión de fondo ID {decision_id}",
            expediente_radicado=row.radicado,
            id_registro=str(decision_id),
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
            content={
                "ok": True,
                "id": decision_id,
                "message": "Decisión de fondo actualizada correctamente"
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error actualizando Decisión de fondo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# Recurso
@router.get("/resource/{radicado}")
async def obtener_formulacion_cargos(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_recurso(radicado, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Recurso no encontrada")
        return JSONResponse(content={"ok": True, "recurso": data["recurso"]}, status_code=200)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al obtener recurso para radicado '{radicado}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al consultar recurso")

# Ejecucion Sancion
@router.get("/execution/{radicado}")
async def get_ejecucion_sancion(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        usuario_id = verify_gateway_token(request)
        stmr = select(Expediente.radicado).where(Expediente.radicado == radicado)
        res = await db.execute(stmr)
        expediente = res.scalar_one_or_none()

        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        # Buscar etapa "EJECUCION DE LA SANCION"
        stmt = select(TipoEtapa.id).where(TipoEtapa.nombre == "EJECUCION DE LA SANCION")
        tipo_etapa = await db.scalar(stmt)

        if not tipo_etapa:
            raise HTTPException(status_code=500, detail="Tipo de etapa 'EJECUCION DE LA SANCION' no configurado")
        
        stmt = select(Etapa.id).where(
            Etapa.tipo_etapa_id == tipo_etapa,
            Etapa.expediente_radicado == radicado
        )
        etapa_id = await db.execute(stmt)
        etapa_id = etapa_id.scalar_one_or_none()
        
        # Permisos de creacion
        stmt = (
            select(Etapa.id)
            .join(TipoEtapa, Etapa.tipo_etapa_id == TipoEtapa.id)
            .where(
                Etapa.expediente_radicado == radicado,
                TipoEtapa.nombre == "DECISION DE FONDO"
            )
        )
        decision_id = await db.scalar(stmt)

        stmt = select(ActoAdmin.id).where(ActoAdmin.etapa_id == decision_id, ActoAdmin.nivel_auxiliar == False)
        ad_id = await db.scalar(stmt)

        if ad_id:
            # Consultar documentos
            stmt = select(Documento.id).where(Documento.etapa_id == decision_id, Documento.nombre == "Recurso")
            doc_id = (await db.execute(stmt)).scalars().all()

            if doc_id:
                stmt = select(ActoAdmin.id).where(ActoAdmin.etapa_id == decision_id, ActoAdmin.nivel_auxiliar == True)
                ad_recurso_id = await db.scalar(stmt)

                if ad_recurso_id:
                    stmt = (
                        select(Etapa.id)
                        .join(TipoEtapa, Etapa.tipo_etapa_id == TipoEtapa.id)
                        .where(
                            Etapa.expediente_radicado == radicado,
                            TipoEtapa.nombre == "PROBATORIA DE RECURSO"
                        )
                    )
                    recurso_id = await db.scalar(stmt)
                    if recurso_id:
                        stmt = select(ActoAdmin.id).where(ActoAdmin.etapa_id == recurso_id, ActoAdmin.nivel_auxiliar == True)
                        ad_decision_id = await db.scalar(stmt)
                        if ad_decision_id:
                            stmt = (
                                select(InvolucradoNotificacion.notificacion_exitosa)
                                .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                                .where(Notificacion.acto_admin_id == ad_decision_id)
                            )
                            result = await db.execute(stmt)
                            notificaciones = result.scalars().all()

                            if not notificaciones or not any(notificaciones):
                                creable = {
                                    "status": False,
                                    "msg":
                                    f'No se ha notificado exitosamente a ningún involucrado del acto administrativa de decision de la etapa: "Probatoria del Recurso".'
                                }
                            else:
                                creable = {"status": True}

                        else:
                            creable = {
                                "status": False,
                                "msg":
                                f'No se ha creado un acto administrativa de decision para la etapa: "Probatoria del Recurso".'
                            }
                        
                    else:
                        stmt = (
                            select(InvolucradoNotificacion.notificacion_exitosa)
                            .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                            .where(Notificacion.acto_admin_id == ad_recurso_id)
                        )
                        result = await db.execute(stmt)
                        notificaciones = result.scalars().all()

                        if not notificaciones or not any(notificaciones):
                            creable = {
                                "status": False,
                                "msg":
                                f'No se ha notificado exitosamente a ningún involucrado del acto administrativa de recurso en la etapa: "Decision de Fondo".'
                            }
                        else:
                            creable = {"status": True}

                        stmt = (
                            select(InvolucradoNotificacion.notificacion_exitosa)
                            .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                            .where(Notificacion.acto_admin_id == ad_id)
                        )
                        result = await db.execute(stmt)
                        notificaciones = result.scalars().all()
                        if not notificaciones or not any(notificaciones):
                            creable = {
                                "status": False,
                                "msg":
                                f'No se ha notificado exitosamente a ningún involucrado del acto administrativa de la etapa: "Decision de Fondo".'
                            }
                        else:
                            creable = {"status": True}

                else:
                    creable = {
                        "status": False,
                        "msg":
                        f'No se ha creado un acto administrativa de recurso para la etapa: "Decision de Fondo".'
                    }

            else:
                stmt = (
                    select(InvolucradoNotificacion.notificacion_exitosa)
                    .join(Notificacion, InvolucradoNotificacion.notificacion_id == Notificacion.id)
                    .where(Notificacion.acto_admin_id == ad_id)
                )
                result = await db.execute(stmt)
                notificaciones = result.scalars().all()

                if not notificaciones or not any(notificaciones):
                    creable = {
                        "status": False,
                        "msg":
                        f'No se ha notificado exitosamente a ningún involucrado del acto administrativa de la etapa: "Decision de Fondo".'
                    }
                else:
                    creable = {"status": True}
        else:
            creable = {
                    "status": False,
                    "msg":
                    f'No se ha creado un acto administrativa para la etapa: "Decision de fondo".'
                }

        # EJECUCION DE LA SANCION (puede no existir)
        stmr = select(EjecucionSancion).where(EjecucionSancion.etapa_id == etapa_id)
        result = await db.execute(stmr)
        es = result.scalar_one_or_none()

        decision = {}
        if es:
            decision = {
                "id": es.id,
                "cobro_coactivo": es.cobro_coactivo,
                "cobro_coactivo_doc_url": es.cobro_coactivo_doc_url,
                "disposicion": es.disposicion,
                "ruia": es.ruia,
                "ruia_doc_url": es.ruia_doc_url,
                "memorando": es.memorando,
                "memorando_doc_url": es.memorando_doc_url,
                "auto_admin": es.auto_admin,
                "fecha_auto": es.fecha_auto.isoformat() if es.fecha_auto else None,
                "auto_doc_url": es.auto_doc_url,
            }
        decision["creable"] = creable
        decision["tipo_etapa_id"] = tipo_etapa

        return JSONResponse(
            content={
                "ok": True,
                "etapa_id": etapa_id,
                "ejecucion_sancion": decision,
            },
            status_code=200
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error obteniendo ejecucion de la sancion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/execution")
async def crear_ejecucion(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # Campos requeridos
    etapa_id: int = Form(...),
    auto_admin: str = Form(...),
    fecha_auto: str = Form(...),
    id_auxiliar: int = Form(...),
    tipo_etapa: str = Form(...),
    
    # Campos booleanos
    cobro_coactivo: str = Form("false"),
    disposicion: str = Form("false"),
    ruia: str = Form("false"),
    memorando: str = Form("false"),
    
    # Archivos opcionales
    cobro_coactivo_doc: Optional[UploadFile] = File(None),
    ruia_doc: Optional[UploadFile] = File(None),
    memorando_doc: Optional[UploadFile] = File(None),
    auto_doc: Optional[UploadFile] = File(None),
):
    """
    Crea un nuevo registro de ejecución de la sanción.
    """
    try:
        usuario_id = verify_gateway_token(request)
        
        # Convertir strings de booleanos
        cobro_coactivo_bool = cobro_coactivo.lower() == "true"
        disposicion_bool = disposicion.lower() == "true"
        ruia_bool = ruia.lower() == "true"
        memorando_bool = memorando.lower() == "true"
        
        # Validar que el expediente corresponde al usuario y etapa
        stmr = (
            select(Expediente.radicado)
            .join(Etapa, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                Etapa.id == etapa_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        expediente = res.scalar_one_or_none()

        if not expediente:
            raise HTTPException(
                status_code=404,
                detail="Expediente no encontrado o sin permisos"
            )
        
        # Validar que no exista ya una ejecución para esta etapa
        stmt = select(EjecucionSancion.id).where(EjecucionSancion.etapa_id == etapa_id)
        existe = await db.scalar(stmt)
        
        if existe:
            raise HTTPException(
                status_code=400, 
                detail="Ya existe una ejecución registrada para esta etapa"
            )
        
        # Validaciones de archivos requeridos según checkboxes
        if cobro_coactivo_bool and (not cobro_coactivo_doc or not cobro_coactivo_doc.filename):
            raise HTTPException(
                status_code=400,
                detail="Debe adjuntar el documento de Cobro Coactivo"
            )
        
        if ruia_bool and (not ruia_doc or not ruia_doc.filename):
            raise HTTPException(
                status_code=400,
                detail="Debe adjuntar el documento RUIA"
            )
        
        if memorando_bool and (not memorando_doc or not memorando_doc.filename):
            raise HTTPException(
                status_code=400,
                detail="Debe adjuntar el documento de Memorando"
            )
        
        if not auto_doc or not auto_doc.filename:
            raise HTTPException(
                status_code=400,
                detail="El documento del Acto Administrativo es requerido"
            )
        
        # Parsear fecha
        try:
            fecha_auto_date = date.fromisoformat(fecha_auto)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )
        
        # Variables para URLs de documentos
        cobro_coactivo_url = None
        ruia_url = None
        memorando_url = None
        auto_url = None
        
        # Crear directorio base
        expediente_path = DOCS_DIR / str(id_auxiliar)
        etapa_path = expediente_path / tipo_etapa
        etapa_path.mkdir(parents=True, exist_ok=True)
        
        # Función auxiliar para guardar archivos
        async def save_pdf(file: UploadFile, prefix: str) -> str:
            if file.content_type != "application/pdf":
                raise HTTPException(
                    status_code=400,
                    detail=f"El archivo {prefix} debe ser PDF"
                )
            
            # Validar tamaño del archivo (10MB máximo)
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
            
            if file_size > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"El archivo {prefix} no debe superar los 10MB"
                )
            
            # Generar nombre de archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{prefix}_{timestamp}.pdf"
            file_path = etapa_path / file_name
            
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            return f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/{file_name}"
        
        # Guardar archivos si existen
        if cobro_coactivo_doc and cobro_coactivo_doc.filename:
            cobro_coactivo_url = await save_pdf(cobro_coactivo_doc, "CobroCoactivo")
        
        if ruia_doc and ruia_doc.filename:
            ruia_url = await save_pdf(ruia_doc, "RUIA")
        
        if memorando_doc and memorando_doc.filename:
            memorando_url = await save_pdf(memorando_doc, "Memorando")
        
        if auto_doc and auto_doc.filename:
            auto_url = await save_pdf(auto_doc, "Auto")
        
        # Insertar ejecución
        stmt = (
            insert(EjecucionSancion)
            .values(
                etapa_id=etapa_id,
                cobro_coactivo=cobro_coactivo_bool,
                cobro_coactivo_doc_url=cobro_coactivo_url,
                disposicion=disposicion_bool,
                ruia=ruia_bool,
                ruia_doc_url=ruia_url,
                memorando=memorando_bool,
                memorando_doc_url=memorando_url,
                auto_admin=auto_admin,
                fecha_auto=fecha_auto_date,
                auto_doc_url=auto_url,
            )
            .returning(EjecucionSancion.id)
        )
        result = await db.execute(stmt)
        ejecucion_id = result.scalar_one()
        
        # Preparar datos para auditoría
        datos_nuevos = {
            "id": ejecucion_id,
            "etapa_id": etapa_id,
            "cobro_coactivo": cobro_coactivo_bool,
            "cobro_coactivo_doc_url": cobro_coactivo_url,
            "disposicion": disposicion_bool,
            "ruia": ruia_bool,
            "ruia_doc_url": ruia_url,
            "memorando": memorando_bool,
            "memorando_doc_url": memorando_url,
            "auto_admin": auto_admin,
            "fecha_auto": fecha_auto,
            "auto_doc_url": auto_url,
        }
        
        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="EjecucionSancion",
            tipo_operacion="INSERT",
            descripcion=f"Creación de ejecución de sanción ID {ejecucion_id}",
            expediente_radicado=expediente,
            id_registro=str(ejecucion_id),
            datos_anteriores=None,
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
            content={
                "ok": True,
                "id": ejecucion_id,
                "message": "Ejecución de la sanción creada correctamente"
            },
            status_code=201
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando ejecución de sanción: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.put("/execution/{execution_id}")
async def actualizar_ejecucion(
    request: Request,
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    # Campos requeridos
    etapa_id: int = Form(...),
    auto_admin: str = Form(...),
    fecha_auto: str = Form(...),
    id_auxiliar: int = Form(...),
    tipo_etapa: str = Form(...),
    
    # Campos booleanos
    cobro_coactivo: str = Form("false"),
    disposicion: str = Form("false"),
    ruia: str = Form("false"),
    memorando: str = Form("false"),
    
    # Archivos opcionales (solo si se están actualizando)
    cobro_coactivo_doc: Optional[UploadFile] = File(None),
    ruia_doc: Optional[UploadFile] = File(None),
    memorando_doc: Optional[UploadFile] = File(None),
    auto_doc: Optional[UploadFile] = File(None),
):
    """
    Actualiza un registro existente de ejecución de la sanción.
    """
    try:
        usuario_id = verify_gateway_token(request)
        
        # Convertir strings de booleanos
        cobro_coactivo_bool = cobro_coactivo.lower() == "true"
        disposicion_bool = disposicion.lower() == "true"
        ruia_bool = ruia.lower() == "true"
        memorando_bool = memorando.lower() == "true"
        
        # Obtener datos anteriores y validar permisos
        stmr = (
            select(
                EjecucionSancion.id,
                EjecucionSancion.etapa_id,
                EjecucionSancion.cobro_coactivo,
                EjecucionSancion.cobro_coactivo_doc_url,
                EjecucionSancion.disposicion,
                EjecucionSancion.ruia,
                EjecucionSancion.ruia_doc_url,
                EjecucionSancion.memorando,
                EjecucionSancion.memorando_doc_url,
                EjecucionSancion.auto_admin,
                EjecucionSancion.fecha_auto,
                EjecucionSancion.auto_doc_url,
                Expediente.radicado
            )
            .join(Etapa, EjecucionSancion.etapa_id == Etapa.id)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                EjecucionSancion.id == execution_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        registro = res.first()
        
        if not registro:
            raise HTTPException(
                status_code=404,
                detail="Ejecución no encontrada o sin permisos"
            )
        
        # Preparar datos anteriores
        datos_anteriores = {
            "id": registro.id,
            "etapa_id": registro.etapa_id,
            "cobro_coactivo": registro.cobro_coactivo,
            "cobro_coactivo_doc_url": registro.cobro_coactivo_doc_url,
            "disposicion": registro.disposicion,
            "ruia": registro.ruia,
            "ruia_doc_url": registro.ruia_doc_url,
            "memorando": registro.memorando,
            "memorando_doc_url": registro.memorando_doc_url,
            "auto_admin": registro.auto_admin,
            "fecha_auto": registro.fecha_auto.isoformat() if registro.fecha_auto else None,
            "auto_doc_url": registro.auto_doc_url,
        }
        
        # Validaciones de archivos requeridos según checkboxes
        if cobro_coactivo_bool and (not cobro_coactivo_doc or not cobro_coactivo_doc.filename) and not registro.cobro_coactivo_doc_url:
            raise HTTPException(
                status_code=400,
                detail="Debe adjuntar el documento de Cobro Coactivo"
            )
        
        if ruia_bool and (not ruia_doc or not ruia_doc.filename) and not registro.ruia_doc_url:
            raise HTTPException(
                status_code=400,
                detail="Debe adjuntar el documento RUIA"
            )
        
        if memorando_bool and (not memorando_doc or not memorando_doc.filename) and not registro.memorando_doc_url:
            raise HTTPException(
                status_code=400,
                detail="Debe adjuntar el documento de Memorando"
            )
        
        if (not auto_doc or not auto_doc.filename) and not registro.auto_doc_url:
            raise HTTPException(
                status_code=400,
                detail="El documento del Acto Administrativo es requerido"
            )
        
        # Parsear fecha
        try:
            fecha_auto_date = date.fromisoformat(fecha_auto)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )
        
        # Mantener URLs anteriores por defecto
        cobro_coactivo_url = registro.cobro_coactivo_doc_url
        ruia_url = registro.ruia_doc_url
        memorando_url = registro.memorando_doc_url
        auto_url = registro.auto_doc_url
        
        # Crear directorio base
        expediente_path = DOCS_DIR / str(id_auxiliar)
        etapa_path = expediente_path / tipo_etapa
        etapa_path.mkdir(parents=True, exist_ok=True)
        
        # Función auxiliar para actualizar archivos
        async def update_pdf(file: UploadFile, prefix: str, old_url: str | None) -> str:
            if file.content_type != "application/pdf":
                raise HTTPException(
                    status_code=400,
                    detail=f"El archivo {prefix} debe ser PDF"
                )
            
            # Validar tamaño del archivo (10MB máximo)
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
            
            if file_size > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"El archivo {prefix} no debe superar los 10MB"
                )
            
            # Eliminar archivo anterior si existe
            if old_url:
                old_file_path = DOCS_DIR.parent / old_url
                if old_file_path.exists():
                    try:
                        old_file_path.unlink()
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar el archivo anterior: {e}")
            
            # Generar nombre de archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{prefix}_{timestamp}.pdf"
            file_path = etapa_path / file_name
            
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            return f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/{file_name}"
        
        # Actualizar archivos solo si se enviaron nuevos
        if cobro_coactivo_doc and cobro_coactivo_doc.filename:
            cobro_coactivo_url = await update_pdf(
                cobro_coactivo_doc,
                "CobroCoactivo",
                registro.cobro_coactivo_doc_url
            )
        
        if ruia_doc and ruia_doc.filename:
            ruia_url = await update_pdf(
                ruia_doc,
                "RUIA",
                registro.ruia_doc_url
            )
        
        if memorando_doc and memorando_doc.filename:
            memorando_url = await update_pdf(
                memorando_doc,
                "Memorando",
                registro.memorando_doc_url
            )
        
        if auto_doc and auto_doc.filename:
            auto_url = await update_pdf(
                auto_doc,
                "Auto",
                registro.auto_doc_url
            )
        
        # Actualizar registro
        stmt = (
            update(EjecucionSancion)
            .where(EjecucionSancion.id == execution_id)
            .values(
                cobro_coactivo=cobro_coactivo_bool,
                cobro_coactivo_doc_url=cobro_coactivo_url,
                disposicion=disposicion_bool,
                ruia=ruia_bool,
                ruia_doc_url=ruia_url,
                memorando=memorando_bool,
                memorando_doc_url=memorando_url,
                auto_admin=auto_admin,
                fecha_auto=fecha_auto_date,
                auto_doc_url=auto_url,
            )
        )
        await db.execute(stmt)
        
        # Preparar datos nuevos
        datos_nuevos = {
            "id": execution_id,
            "etapa_id": registro.etapa_id,
            "cobro_coactivo": cobro_coactivo_bool,
            "cobro_coactivo_doc_url": cobro_coactivo_url,
            "disposicion": disposicion_bool,
            "ruia": ruia_bool,
            "ruia_doc_url": ruia_url,
            "memorando": memorando_bool,
            "memorando_doc_url": memorando_url,
            "auto_admin": auto_admin,
            "fecha_auto": fecha_auto,
            "auto_doc_url": auto_url,
        }
        
        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="EjecucionSancion",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de ejecución de sanción ID {execution_id}",
            expediente_radicado=registro.radicado,
            id_registro=str(execution_id),
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
            content={
                "ok": True,
                "id": execution_id,
                "message": "Ejecución de la sanción actualizada correctamente"
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error actualizando ejecución de sanción: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )



# Acto Admin
@router.post("/acto-admin")
async def crear_acto_admin(
    request: Request,
    radicado_expediente: str = Form(...),
    etapa_id: int = Form(...),
    tipo_acto: str = Form(...),
    id_auxiliar: int = Form(...),
    numerado: int= Form(...),
    fecha_numerado: str = Form(...),
    tipo_etapa: str = Form(...),
    nivel_auxiliar: bool = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()

        if not numerado or len(str(numerado)) > 4:
            raise HTTPException(status_code=400, detail="El numerado debe tener como maximo 4 numeros")

        if tipo_acto not in ["AUTO", "RES"]:
            raise HTTPException(status_code=400, detail="El tipo de acto debe ser AUTO o RES")

        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado_expediente)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para modificar este expediente")

        if nivel_auxiliar:
            stmt = select(ActoAdmin.id).where(ActoAdmin.etapa_id == etapa_id, ActoAdmin.nivel_auxiliar == nivel_auxiliar)
        else:
            stmt = select(ActoAdmin.id).where(ActoAdmin.etapa_id == etapa_id, ActoAdmin.nivel_auxiliar == False)
        
        if await db.scalar(stmt):
            raise HTTPException(status_code=400, detail="El acto administrativo ya existe")

        # Validación de numerado + fecha_numerado según año
        año_numerado = fecha_numerado_date.year
        
        if año_numerado > 2012:
            # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
            stmt = (
                select(Expediente.radicado)
                .join(Etapa, Etapa.expediente_radicado == Expediente.radicado)
                .join(ActoAdmin, ActoAdmin.etapa_id == Etapa.id)
                .where(
                    ActoAdmin.numerado == numerado,
                    ActoAdmin.fecha_numerado == fecha_numerado_date
                )
            )
            radicado_existente = await db.scalar(stmt)
            
            if radicado_existente:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en el expediente {radicado_existente}"
                )
        else:
            # Para años ≤ 2012: solo verificar en OTROS expedientes (permitir duplicados en mismo expediente)
            stmt = (
                select(Expediente.radicado)
                .join(Etapa, Etapa.expediente_radicado == Expediente.radicado)
                .join(ActoAdmin, ActoAdmin.etapa_id == Etapa.id)
                .where(
                    ActoAdmin.numerado == numerado,
                    ActoAdmin.fecha_numerado == fecha_numerado_date,
                    Expediente.radicado != radicado_expediente
                )
            )
            radicado_expediente_existente = await db.scalar(stmt)
            
            if radicado_expediente_existente:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en el expediente {radicado_expediente_existente}"
                )

        if nivel_auxiliar:
            acto_etapa = await db.scalar(
                select(ActoAdmin).where(
                    ActoAdmin.etapa_id == etapa_id,
                    ActoAdmin.nivel_auxiliar == False
                )
            )
            if not acto_etapa:
                raise HTTPException(
                    status_code=400,
                    detail="Debe crear primero el acto administrativo de etapa antes de crear el acto de recurso"
                )

        expediente_path = DOCS_DIR / str(id_auxiliar)
        etapa_path = expediente_path / tipo_etapa 
        etapa_path.mkdir(parents=True, exist_ok=True)

        file_name = f"{tipo_acto}_{numerado}_{fecha_numerado.replace('-', '')}.pdf"
        file_path = etapa_path / file_name

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        url_acto_normalizada = f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/{file_name}"

        nuevo_acto = ActoAdmin(
            etapa_id=etapa_id,
            tipo_acto=tipo_acto,
            numerado=numerado,
            fecha_numerado=fecha_numerado_date,
            url_acto=url_acto_normalizada,
            nivel_auxiliar=nivel_auxiliar
        )

        db.add(nuevo_acto)
        await db.flush()

        datos_nuevos = {
            "id": nuevo_acto.id,
            "etapa_id": etapa_id,
            "tipo_acto": tipo_acto,
            "numerado": numerado,
            "fecha_radicado": fecha_numerado,
            "url_acto": url_acto_normalizada,
            "fecha_creacion": str(nuevo_acto.fecha_creacion),
            "nivel_auxiliar": nivel_auxiliar
        }

        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="acto_admin",
            tipo_operacion="INSERT",
            descripcion=f"Creación de acto administrativo {tipo_acto} {numerado}{nivel_auxiliar}",
            expediente_radicado=radicado_expediente,
            id_registro=str(nuevo_acto.id),
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
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
                    "url_acto": nuevo_acto.url_acto,
                    "tipo_acto": nuevo_acto.tipo_acto,
                    "fecha_creacion": str(nuevo_acto.fecha_creacion),
                    "etapa_id": nuevo_acto.etapa_id,
                    "nivel_auxiliar": nuevo_acto.nivel_auxiliar
                }
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error creando acto admin: {e}")
        raise HTTPException(status_code=500, detail="Error al crear acto administrativo")

@router.put("/acto-admin/{acto_id}")
async def actualizar_acto_admin(
    request: Request,
    acto_id: int,
    radicado_expediente: str = Form(...),
    etapa_id: int = Form(...),
    id_auxiliar: int = Form(...),
    tipo_acto: str = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    tipo_etapa: str = Form(...),
    nivel_auxiliar: bool = Form(None), 
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()

        if not numerado or len(str(numerado)) > 4:
            raise HTTPException(status_code=400, detail="El numerado debe tener como maximo 4 numeros")

        if tipo_acto not in ["AUTO", "RES"]:
            raise HTTPException(status_code=400, detail="El tipo de acto debe ser AUTO o RES")

        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado_expediente)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para modificar este expediente")

        acto_admin = await db.scalar(select(ActoAdmin).where(ActoAdmin.id == acto_id))
        if not acto_admin:
            raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

        datos_anteriores = {
            "id": acto_admin.id,
            "tipo_acto": acto_admin.tipo_acto,
            "numerado": acto_admin.numerado,
            "fecha_numerado": str(acto_admin.fecha_numerado) if acto_admin.fecha_numerado else None,
            "url_acto": acto_admin.url_acto,
            "etapa_id": acto_admin.etapa_id,
            "fecha_creacion": str(acto_admin.fecha_creacion) if acto_admin.fecha_creacion else None,
            "nivel_auxiliar": acto_admin.nivel_auxiliar
        }

        # Validación de numerado + fecha_numerado según año
        año_numerado = fecha_numerado_date.year
        
        if año_numerado > 2012:
            # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
            stmt = (
                select(Expediente.radicado)
                .join(Etapa, Etapa.expediente_radicado == Expediente.radicado)
                .join(ActoAdmin, ActoAdmin.etapa_id == Etapa.id)
                .where(
                    ActoAdmin.numerado == int(numerado),
                    ActoAdmin.fecha_numerado == fecha_numerado_date,
                    ActoAdmin.id != acto_id
                )
            )
            radicado_existente = await db.scalar(stmt)

            if radicado_existente:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en el expediente {radicado_existente}"
                )
        else:
            # Para años ≤ 2012: solo verificar en OTROS expedientes (permitir duplicados en mismo expediente)
            stmt = (
                select(Expediente.radicado)
                .join(Etapa, Etapa.expediente_radicado == Expediente.radicado)
                .join(ActoAdmin, ActoAdmin.etapa_id == Etapa.id)
                .where(
                    ActoAdmin.numerado == int(numerado),
                    ActoAdmin.fecha_numerado == fecha_numerado_date,
                    ActoAdmin.id != acto_id,
                    Expediente.radicado != radicado_expediente
                )
            )
            radicado_expediente_existente = await db.scalar(stmt)

            if radicado_expediente_existente:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en el expediente {radicado_expediente_existente}"
                )

        if nivel_auxiliar:
            acto_etapa = await db.scalar(
                select(ActoAdmin).where(
                    ActoAdmin.etapa_id == etapa_id,
                    ActoAdmin.nivel_auxiliar == False,
                    ActoAdmin.id != acto_id
                )
            )
            if not acto_etapa:
                raise HTTPException(
                    status_code=400,
                    detail="Debe existir un acto administrativo de etapa antes de modificar el acto de recurso"
                )

        url_acto = acto_admin.url_acto
        if file:
            if file.content_type != "application/pdf":
                raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

            old_file_path = BASE_DIR / acto_admin.url_acto
            if old_file_path.exists():
                old_file_path.unlink()

            expediente_path = DOCS_DIR / str(id_auxiliar)
            etapa_path = expediente_path / tipo_etapa  
            etapa_path.mkdir(parents=True, exist_ok=True)

            file_name = f"{tipo_acto}_{numerado}_{fecha_numerado.replace('-', '')}.pdf"
            file_path = etapa_path / file_name

            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            url_acto = f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/{file_name}"

        acto_admin.tipo_acto = tipo_acto
        acto_admin.numerado = int(numerado)
        acto_admin.fecha_numerado = fecha_numerado_date
        acto_admin.url_acto = url_acto
        acto_admin.nivel_auxiliar = nivel_auxiliar

        await db.flush()

        datos_nuevos = {
            "id": acto_admin.id,
            "tipo_acto": acto_admin.tipo_acto,
            "numerado": acto_admin.numerado,
            "fecha_numerado": str(acto_admin.fecha_numerado),
            "url_acto": acto_admin.url_acto,
            "etapa_id": acto_admin.etapa_id,
            "fecha_creacion": str(acto_admin.fecha_creacion) if acto_admin.fecha_creacion else None,
            "nivel_auxiliar": acto_admin.nivel_auxiliar
        }

        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="acto_admin",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de acto administrativo {tipo_acto} {numerado}{nivel_auxiliar}",
            expediente_radicado=radicado_expediente,
            id_registro=str(acto_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

        await db.commit()
        await db.refresh(acto_admin)

        stmt = select(Comunicacion).where(Comunicacion.acto_admin_id == acto_admin.id)
        comunicacion = await db.scalar(stmt)

        comunicacion_data = None
        if comunicacion:
            comunicacion_data = {
                "id": comunicacion.id,
                "numerado": comunicacion.numerado,
                "fecha_numerado": str(comunicacion.fecha_numerado),
                "fecha_envio": str(comunicacion.fecha_envio),
                "fecha_creacion": str(comunicacion.fecha_creacion)
            }

        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": acto_admin.id,
                    "numerado": acto_admin.numerado,
                    "fecha_numerado": str(acto_admin.fecha_numerado),
                    "url_acto": acto_admin.url_acto,
                    "tipo_acto": acto_admin.tipo_acto,
                    "fecha_creacion": str(acto_admin.fecha_creacion),
                    "etapa_id": acto_admin.etapa_id,
                    "nivel_auxiliar": acto_admin.nivel_auxiliar,
                    "comunicacion": comunicacion_data
                }
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error al actualizar acto administrativo: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar acto administrativo")

@router.delete("/acto-admin/{acto_id}")
async def delete_acto_admin(
    request: Request,
    acto_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        stmr = (
            select(ActoAdmin, Expediente.radicado)
            .join(Etapa, ActoAdmin.etapa_id == Etapa.id)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(ActoAdmin.id == acto_id, Expediente.encargado_id == usuario_id)
        )
        res = await db.execute(stmr)
        row = res.first()

        if not row:
            raise HTTPException(status_code=404, detail="Acto administrativo no encontrado o sin permisos")

        acto_admin, radicado_expediente = row

        datos_acto = {
            "id": acto_admin.id,
            "numerado": acto_admin.numerado,
            "fecha_numerado": str(acto_admin.fecha_numerado) if acto_admin.fecha_numerado else None,
            "url_acto": acto_admin.url_acto,
            "tipo_acto": acto_admin.tipo_acto,
            "etapa_id": acto_admin.etapa_id,
            "fecha_creacion": str(acto_admin.fecha_creacion) if acto_admin.fecha_creacion else None
        }

        comunicacion = await db.scalar(
            select(Comunicacion).where(Comunicacion.acto_admin_id == acto_id)
        )

        datos_comunicacion = None
        notificaciones_eliminadas = []
        involucrados_notificacion_eliminados = []

        if comunicacion:
            datos_comunicacion = {
                "id": comunicacion.id,
                "numerado": comunicacion.numerado,
                "fecha_numerado": str(comunicacion.fecha_numerado) if comunicacion.fecha_numerado else None,
                "fecha_envio": str(comunicacion.fecha_envio) if comunicacion.fecha_envio else None,
                "acto_admin_id": comunicacion.acto_admin_id,
                "fecha_creacion": str(comunicacion.fecha_creacion) if comunicacion.fecha_creacion else None
            }

            notificaciones = (await db.execute(
                select(Notificacion).where(Notificacion.comunicacion_id == comunicacion.id)
            )).scalars().all()

            for notificacion in notificaciones:
                notificaciones_eliminadas.append({
                    "id": notificacion.id,
                    "tipo_notificacion_id": notificacion.tipo_notificacion_id,
                    "comunicacion_id": notificacion.comunicacion_id,
                })

                involucrados_not = (await db.execute(
                    select(InvolucradoNotificacion).where(
                        InvolucradoNotificacion.notificacion_id == notificacion.id
                    )
                )).scalars().all()

                for inv_not in involucrados_not:
                    involucrados_notificacion_eliminados.append({
                        "id": inv_not.id,
                        "involucrado_id": inv_not.involucrado_id,
                        "notificacion_id": inv_not.notificacion_id,
                        "fecha_notificacion": str(inv_not.fecha_notificacion) if inv_not.fecha_notificacion else None,
                        "url_constancia": inv_not.url_constancia,
                    })

                    await db.execute(
                        delete(InvolucradoNotificacion).where(InvolucradoNotificacion.id == inv_not.id)
                    )

                await db.execute(delete(Notificacion).where(Notificacion.id == notificacion.id))

            await db.execute(delete(Comunicacion).where(Comunicacion.id == comunicacion.id))

        if acto_admin.url_acto:
            file_path = BASE_DIR / acto_admin.url_acto
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"No se pudo eliminar el archivo: {e}")

        await db.execute(delete(ActoAdmin).where(ActoAdmin.id == acto_id))
        await db.flush()

        descripcion_partes = [
            f"Eliminación de acto administrativo {datos_acto['tipo_acto']} {datos_acto['numerado']}"
        ]
        
        if datos_comunicacion:
            descripcion_partes.append(f"con comunicación (ID: {datos_comunicacion['id']})")
        
        if notificaciones_eliminadas:
            descripcion_partes.append(f"{len(notificaciones_eliminadas)} notificación(es)")
        
        if involucrados_notificacion_eliminados:
            descripcion_partes.append(f"{len(involucrados_notificacion_eliminados)} involucrado(s) en notificaciones")

        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="acto_admin",
            tipo_operacion="DELETE",
            descripcion=" - ".join(descripcion_partes),
            expediente_radicado=radicado_expediente,
            id_registro=str(acto_id),
            datos_anteriores={
                "acto_admin": datos_acto,
                "comunicacion": datos_comunicacion,
                "notificaciones": notificaciones_eliminadas,
                "involucrados_notificacion": involucrados_notificacion_eliminados,
            },
            datos_nuevos={}
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "message": "Acto administrativo y registros relacionados eliminados correctamente",
                "deleted": {
                    "acto_admin": 1,
                    "comunicacion": 1 if datos_comunicacion else 0,
                    "notificaciones": len(notificaciones_eliminadas),
                    "involucrados_notificacion": len(involucrados_notificacion_eliminados),
                }
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error eliminando acto administrativo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# Comunicacion
@router.post("/comunicacion")
async def crear_comunicacion(
    request:Request,
    radicado: str = Form(...),
    acto_admin_id: int = Form(...),
    id_auxiliar: int = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio: str = Form(...),
    tipo_etapa: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
        fecha_envio_date = datetime.strptime(fecha_envio, "%Y-%m-%d").date()

        # Validar numerado
        if not numerado.isdigit() or len(numerado) != 4:
            raise HTTPException(
                status_code=400,
                detail="El numerado debe tener exactamente 4 dígitos"
            )

        # Validar tipo de archivo
        allowed_types = ["application/pdf", "image/jpeg", "image/png"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Solo se permiten archivos PDF, JPG o PNG"
            )

        # Verificar que el acto admin existe
        stmt = select(ActoAdmin).where(ActoAdmin.id == acto_admin_id)
        acto_admin = await db.scalar(stmt)
        if not acto_admin:
            raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

        # Verificar permisos
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para crear comunicación en este expediente"
            )

        # Validación de numerado + fecha_numerado según año
        año_numerado = fecha_numerado_date.year
        
        if año_numerado > 2012:
            # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
            stmt = (
                select(Comunicacion.id)
                .where(
                    Comunicacion.numerado == int(numerado),
                    Comunicacion.fecha_numerado == fecha_numerado_date
                )
            )
            existe_comunicacion = await db.scalar(stmt)
            
            if existe_comunicacion:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra comunicación"
                )
        # Para años ≤ 2012: se permite duplicados en el mismo expediente, no validar

        # Crear directorio y guardar archivo
        expediente_path = DOCS_DIR / str(id_auxiliar)
        etapa_path = expediente_path / tipo_etapa
        etapa_path.mkdir(parents=True, exist_ok=True)

        # Determinar extensión del archivo
        extension = ""
        if file.content_type == "application/pdf":
            extension = "pdf"
        elif file.content_type == "image/jpeg":
            extension = "jpg"
        elif file.content_type == "image/png":
            extension = "png"

        file_name = f"COMUNICACION_{numerado}_{fecha_numerado.replace('-', '')}.{extension}"
        file_path = etapa_path / file_name

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        url_documento_normalizada = f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/{file_name}"

        # Crear comunicación
        nueva_comunicacion = Comunicacion(
            acto_admin_id=acto_admin_id,
            numerado=int(numerado),
            fecha_numerado=fecha_numerado_date,
            fecha_envio=fecha_envio_date,
            fecha_creacion=datetime.now().date(),
            url_documento=url_documento_normalizada,
        )

        db.add(nueva_comunicacion)
        await db.flush()

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": nueva_comunicacion.id,
            "acto_admin_id": acto_admin_id,
            "numerado": int(numerado),
            "fecha_numerado": fecha_numerado,
            "fecha_envio": fecha_envio,
            "url_documento": url_documento_normalizada,
            "fecha_creacion": str(nueva_comunicacion.fecha_creacion)
        }

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="comunicacion",
            tipo_operacion="INSERT",
            descripcion=f"Creación de comunicación {numerado} para acto admin {acto_admin_id}",
            expediente_radicado=radicado,
            id_registro=str(nueva_comunicacion.id),
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        await db.refresh(nueva_comunicacion)

        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": nueva_comunicacion.id,
                    "numerado": nueva_comunicacion.numerado,
                    "fecha_numerado": str(nueva_comunicacion.fecha_numerado),
                    "fecha_envio": str(nueva_comunicacion.fecha_envio),
                    "fecha_creacion": str(nueva_comunicacion.fecha_creacion),
                    "url_documento": nueva_comunicacion.url_documento,
                },
            },
            status_code=201,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error creando comunicación: {e}")
        raise HTTPException(status_code=500, detail="Error al crear comunicación")

@router.put("/comunicacion/{comunicacion_id}")
async def actualizar_comunicacion(
    request:Request,
    comunicacion_id: int,
    radicado: str = Form(...),
    id_auxiliar: int = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio: str = Form(...),
    tipo_etapa: str = Form(...),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
        fecha_envio_date = datetime.strptime(fecha_envio, "%Y-%m-%d").date()

        # Validar numerado
        if not numerado.isdigit() or len(numerado) != 4:
            raise HTTPException(
                status_code=400,
                detail="El numerado debe tener exactamente 4 dígitos"
            )

        # Buscar la comunicación existente
        stmt = select(Comunicacion).where(Comunicacion.id == comunicacion_id)
        comunicacion = await db.scalar(stmt)
        
        if not comunicacion:
            raise HTTPException(status_code=404, detail="Comunicación no encontrada")
        
        # Guardar datos anteriores para auditoría
        datos_anteriores = {
            "id": comunicacion.id,
            "acto_admin_id": comunicacion.acto_admin_id,
            "numerado": comunicacion.numerado,
            "fecha_numerado": str(comunicacion.fecha_numerado) if comunicacion.fecha_numerado else None,
            "fecha_envio": str(comunicacion.fecha_envio) if comunicacion.fecha_envio else None,
            "url_documento": comunicacion.url_documento,
            "fecha_creacion": str(comunicacion.fecha_creacion) if comunicacion.fecha_creacion else None
        }
        
        # Obtener el acto admin asociado
        stmt = select(ActoAdmin).where(ActoAdmin.id == comunicacion.acto_admin_id)
        acto_admin = await db.scalar(stmt)
        
        if not acto_admin:
            raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")
        
        # Verificar permisos
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        
        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para editar esta comunicación"
            )
        
        # Validación de numerado + fecha_numerado según año
        año_numerado = fecha_numerado_date.year
        
        if año_numerado > 2012:
            # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
            stmt = (
                select(Comunicacion.id)
                .where(
                    Comunicacion.numerado == int(numerado),
                    Comunicacion.fecha_numerado == fecha_numerado_date,
                    Comunicacion.id != comunicacion_id
                )
            )
            existe_comunicacion = await db.scalar(stmt)
            
            if existe_comunicacion:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra comunicación"
                )
        # Para años ≤ 2012: se permite duplicados en el mismo expediente, no validar
        
        url_documento = comunicacion.url_documento
        if file:
            # Validar tipo de archivo
            allowed_types = ["application/pdf", "image/jpeg", "image/png"]
            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail="Solo se permiten archivos PDF, JPG o PNG"
                )

            # Eliminar archivo antiguo
            if comunicacion.url_documento:
                old_file_path = BASE_DIR / comunicacion.url_documento
                if old_file_path.exists():
                    old_file_path.unlink()

            # Crear directorio y guardar nuevo archivo
            expediente_path = DOCS_DIR / str(id_auxiliar)
            etapa_path = expediente_path / tipo_etapa
            etapa_path.mkdir(parents=True, exist_ok=True)

            # Determinar extensión del archivo
            extension = ""
            if file.content_type == "application/pdf":
                extension = "pdf"
            elif file.content_type == "image/jpeg":
                extension = "jpg"
            elif file.content_type == "image/png":
                extension = "png"

            file_name = f"COMUNICACION_{numerado}_{fecha_numerado.replace('-', '')}.{extension}"
            file_path = etapa_path / file_name

            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            url_documento = f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/{file_name}"

        # Actualizar comunicación
        comunicacion.numerado = int(numerado)
        comunicacion.fecha_numerado = fecha_numerado_date
        comunicacion.fecha_envio = fecha_envio_date
        comunicacion.url_documento = url_documento
        
        await db.flush()

        # Preparar datos nuevos para auditoría
        datos_nuevos = {
            "id": comunicacion.id,
            "acto_admin_id": comunicacion.acto_admin_id,
            "numerado": comunicacion.numerado,
            "fecha_numerado": str(comunicacion.fecha_numerado),
            "fecha_envio": str(comunicacion.fecha_envio),
            "url_documento": comunicacion.url_documento,
            "fecha_creacion": str(comunicacion.fecha_creacion) if comunicacion.fecha_creacion else None
        }

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="comunicacion",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de comunicación {numerado}",
            expediente_radicado=radicado,
            id_registro=str(comunicacion_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        await db.refresh(comunicacion)
        
        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": comunicacion.id,
                    "numerado": comunicacion.numerado,
                    "fecha_numerado": str(comunicacion.fecha_numerado),
                    "fecha_envio": str(comunicacion.fecha_envio),
                    "fecha_creacion": str(comunicacion.fecha_creacion),
                    "url_documento": comunicacion.url_documento,
                },
            },
            status_code=200,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error actualizando comunicación: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar comunicación")

@router.delete("/comunicacion/{comunicacion_id}")
async def eliminar_comunicacion(
    request:Request,
    comunicacion_id: int,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        radicado = data.get("radicado")

        # Buscar la comunicación existente
        stmt = select(Comunicacion).where(Comunicacion.id == comunicacion_id)
        comunicacion = await db.scalar(stmt)
        
        if not comunicacion:
            raise HTTPException(status_code=404, detail="Comunicación no encontrada")
        
        # Guardar datos anteriores para auditoría
        datos_anteriores = {
            "id": comunicacion.id,
            "acto_admin_id": comunicacion.acto_admin_id,
            "numerado": comunicacion.numerado,
            "fecha_numerado": str(comunicacion.fecha_numerado) if comunicacion.fecha_numerado else None,
            "fecha_envio": str(comunicacion.fecha_envio) if comunicacion.fecha_envio else None,
            "url_documento": comunicacion.url_documento,
            "fecha_creacion": str(comunicacion.fecha_creacion) if comunicacion.fecha_creacion else None
        }
        
        # Obtener el acto admin asociado
        stmt = select(ActoAdmin).where(ActoAdmin.id == comunicacion.acto_admin_id)
        acto_admin = await db.scalar(stmt)
        
        if not acto_admin:
            raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")
        
        # Verificar permisos
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        
        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para eliminar esta comunicación"
            )
        
        # Eliminar archivo físico si existe
        if comunicacion.url_documento:
            file_path = BASE_DIR / comunicacion.url_documento
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"No se pudo eliminar el archivo: {e}")
        
        # Eliminar comunicación de la base de datos
        await db.delete(comunicacion)
        await db.flush()

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="comunicacion",
            tipo_operacion="DELETE",
            descripcion=f"Eliminación de comunicación {datos_anteriores['numerado']}",
            expediente_radicado=radicado,
            id_registro=str(comunicacion_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos={}
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        
        return JSONResponse(
            content={
                "ok": True,
                "message": "Comunicación eliminada exitosamente"
            },
            status_code=200,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error eliminando comunicación: {e}")
        raise HTTPException(status_code=500, detail="Error al eliminar comunicación")


# Notificacion
@router.post("/notificacion")
async def crear_notificacion(
    request:Request,
    radicado: str = Form(...),
    acto_admin_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        # Verificar permisos
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )

        # Verificar que el acto admin existe
        stmt = select(ActoAdmin).where(ActoAdmin.id == acto_admin_id)
        acto_admin = await db.scalar(stmt)

        if not acto_admin:
            raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

        # Verificar que no exista ya una notificación para este acto admin
        stmt = select(Notificacion.id).where(Notificacion.acto_admin_id == acto_admin_id)
        existe = await db.scalar(stmt)

        if existe:
            raise HTTPException(
                status_code=400,
                detail="Ya existe una notificación para este acto administrativo"
            )

        # Crear notificación
        nueva_notificacion = Notificacion(
            acto_admin_id=acto_admin_id,
            fecha_creacion=datetime.now().date()
        )

        db.add(nueva_notificacion)
        await db.flush()

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": nueva_notificacion.id,
            "acto_admin_id": acto_admin_id,
            "fecha_creacion": str(nueva_notificacion.fecha_creacion)
        }

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="notificacion",
            tipo_operacion="INSERT",
            descripcion=f"Creación de notificación para acto admin {acto_admin_id}",
            expediente_radicado=radicado,
            id_registro=str(nueva_notificacion.id),
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        await db.refresh(nueva_notificacion)

        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": nueva_notificacion.id,
                    "acto_admin_id": nueva_notificacion.acto_admin_id,
                    "fecha_creacion": str(nueva_notificacion.fecha_creacion),
                    "involucrados": []
                }
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error creando notificación: {e}")
        raise HTTPException(status_code=500, detail="Error al crear notificación")

@router.put("/involucrado-notificacion/{involucrado_notificacion_id}")
async def actualizar_involucrado_notificacion(
    request: Request,
    involucrado_notificacion_id: int,
    radicado: str = Form(...),
    numerado: int = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio_citacion: str = Form(...),
    id_auxiliar: int = Form(...),
    tipo_etapa: str = Form(...),
    fecha_constancia_citacion: str = Form(None),
    notificacion_exitosa: bool = Form(False),
    tipo_notificacion_id: int = Form(None),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        usuario_id = verify_gateway_token(request)
        fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
        fecha_envio_date = datetime.strptime(fecha_envio_citacion, "%Y-%m-%d").date()
        fecha_constancia_date = None
        
        # Validar fecha_constancia_citacion
        if fecha_constancia_citacion and fecha_constancia_citacion.strip() and fecha_constancia_citacion != "None":
            fecha_constancia_date = datetime.strptime(fecha_constancia_citacion, "%Y-%m-%d").date()

        # Validar numerado
        numerado_str = str(numerado).strip()
        if not numerado_str.isdigit() or len(numerado_str) > 4:
            raise HTTPException(
                status_code=400,
                detail="El numerado debe tener como maximo 4 dígitos"
            )

        # Validar notificacion_exitosa
        if notificacion_exitosa and not tipo_notificacion_id:
            raise HTTPException(
                status_code=400,
                detail="Debe seleccionar un tipo de notificación si marca como exitosa"
            )

        # Verificar permisos
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )

        # Buscar InvolucradoNotificacion existente
        stmt = select(InvolucradoNotificacion).where(
            InvolucradoNotificacion.id == involucrado_notificacion_id
        )
        inv_not = await db.scalar(stmt)

        if not inv_not:
            raise HTTPException(
                status_code=404,
                detail="Notificación del involucrado no encontrada"
            )

        # Guardar datos anteriores para auditoría
        datos_anteriores = {
            "id": inv_not.id,
            "involucrado_id": inv_not.involucrado_id,
            "notificacion_id": inv_not.notificacion_id,
            "numerado": inv_not.numerado,
            "fecha_numerado": str(inv_not.fecha_numerado) if inv_not.fecha_numerado else None,
            "fecha_envio_citacion": str(inv_not.fecha_envio_citacion) if inv_not.fecha_envio_citacion else None,
            "fecha_constancia_citacion": str(inv_not.fecha_constancia_citacion) if inv_not.fecha_constancia_citacion else None,
            "notificacion_exitosa": inv_not.notificacion_exitosa,
            "fecha_notificacion": str(inv_not.fecha_notificacion) if inv_not.fecha_notificacion else None,
            "tipo_notificacion_id": inv_not.tipo_notificacion_id,
            "url_documento": inv_not.url_documento
        }

        # Validación de numerado + fecha_numerado según año
        año_numerado = fecha_numerado_date.year
        
        if año_numerado > 2012:
            # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
            stmt = (
                select(InvolucradoNotificacion.id)
                .where(
                    InvolucradoNotificacion.numerado == numerado,
                    InvolucradoNotificacion.fecha_numerado == fecha_numerado_date,
                    InvolucradoNotificacion.id != involucrado_notificacion_id
                )
            )
            existe_notificacion = await db.scalar(stmt)
            
            if existe_notificacion:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra notificación"
                )
        # Para años ≤ 2012: se permite duplicados en el mismo expediente, no validar

        url_documento = inv_not.url_documento

        # Si se proporciona nuevo archivo
        if file and file.filename:
            valid_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
            if file.content_type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail="Solo se permiten archivos PDF, JPG o PNG"
                )

            # Validar tamaño
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
            
            if file_size > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail="El archivo no debe superar los 10MB"
                )

            # Eliminar archivo antiguo si existe
            if inv_not.url_documento:
                old_file_path = BASE_DIR / inv_not.url_documento
                if old_file_path.exists():
                    try:
                        old_file_path.unlink()
                    except Exception as e:
                        print(f"Error al eliminar archivo antiguo: {e}")

            # Guardar nuevo archivo
            expediente_path = DOCS_DIR / str(id_auxiliar)
            etapa_path = expediente_path / tipo_etapa / "notificaciones"
            etapa_path.mkdir(parents=True, exist_ok=True)

            extension = "pdf"
            if file.content_type in ["image/jpeg", "image/jpg"]:
                extension = "jpg"
            elif file.content_type == "image/png":
                extension = "png"

            file_name = f"NOT_{numerado}_{fecha_numerado.replace('-', '')}_{inv_not.involucrado_id}.{extension}"
            file_path = etapa_path / file_name

            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            url_documento = f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/notificaciones/{file_name}"

        # Actualizar campos
        inv_not.numerado = numerado
        inv_not.fecha_numerado = fecha_numerado_date
        inv_not.fecha_envio_citacion = fecha_envio_date
        inv_not.fecha_constancia_citacion = fecha_constancia_date
        inv_not.notificacion_exitosa = notificacion_exitosa
        inv_not.tipo_notificacion_id = tipo_notificacion_id if tipo_notificacion_id else None
        inv_not.url_documento = url_documento
        if notificacion_exitosa:
            inv_not.fecha_notificacion = datetime.now(ZoneInfo("America/Bogota")).date()

        await db.flush()

        # Preparar datos nuevos para auditoría
        datos_nuevos = {
            "id": inv_not.id,
            "involucrado_id": inv_not.involucrado_id,
            "notificacion_id": inv_not.notificacion_id,
            "numerado": inv_not.numerado,
            "fecha_numerado": str(inv_not.fecha_numerado),
            "fecha_envio_citacion": str(inv_not.fecha_envio_citacion),
            "fecha_constancia_citacion": str(inv_not.fecha_constancia_citacion) if inv_not.fecha_constancia_citacion else None,
            "notificacion_exitosa": inv_not.notificacion_exitosa,
            "tipo_notificacion_id": inv_not.tipo_notificacion_id,
            "url_documento": inv_not.url_documento
        }

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="involucrado_notificacion",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de notificación {numerado} para involucrado {inv_not.involucrado_id}",
            expediente_radicado=radicado,
            id_registro=str(involucrado_notificacion_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        await db.refresh(inv_not)

        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": inv_not.id,
                    "involucrado_id": inv_not.involucrado_id,
                    "numerado": inv_not.numerado,
                    "fecha_numerado": str(inv_not.fecha_numerado),
                    "fecha_envio_citacion": str(inv_not.fecha_envio_citacion),
                    "fecha_constancia_citacion": str(inv_not.fecha_constancia_citacion) if inv_not.fecha_constancia_citacion else None,
                    "notificacion_exitosa": inv_not.notificacion_exitosa,
                    "url_documento": inv_not.url_documento,
                    "tipo_notificacion_id": inv_not.tipo_notificacion_id
                }
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error actualizando involucrado notificación: {e}")
        raise HTTPException(status_code=500, detail=f"Error al actualizar notificación del involucrado: {str(e)}")

@router.delete("/notificacion/{notificacion_id}")
async def eliminar_notificacion(
    request: Request,
    notificacion_id: int,
    radicado: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        # Verificar permisos
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )

        # Buscar notificación
        stmt = select(Notificacion).where(Notificacion.id == notificacion_id)
        notificacion = await db.scalar(stmt)

        if not notificacion:
            raise HTTPException(status_code=404, detail="Notificación no encontrada")

        # Guardar datos de la notificación para auditoría
        datos_notificacion = {
            "id": notificacion.id,
            "acto_admin_id": notificacion.acto_admin_id,
            "fecha_creacion": str(notificacion.fecha_creacion) if notificacion.fecha_creacion else None
        }

        # Buscar todos los InvolucradoNotificacion
        stmt = select(InvolucradoNotificacion).where(
            InvolucradoNotificacion.notificacion_id == notificacion_id
        )
        involucrados_not = (await db.execute(stmt)).scalars().all()

        # Guardar datos de involucrados para auditoría
        datos_involucrados = []
        for inv_not in involucrados_not:
            datos_involucrados.append({
                "id": inv_not.id,
                "involucrado_id": inv_not.involucrado_id,
                "notificacion_id": inv_not.notificacion_id,
                "numerado": inv_not.numerado,
                "fecha_numerado": str(inv_not.fecha_numerado) if inv_not.fecha_numerado else None,
                "fecha_envio_citacion": str(inv_not.fecha_envio_citacion) if inv_not.fecha_envio_citacion else None,
                "fecha_constancia_citacion": str(inv_not.fecha_constancia_citacion) if inv_not.fecha_constancia_citacion else None,
                "notificacion_exitosa": inv_not.notificacion_exitosa,
                "tipo_notificacion_id": inv_not.tipo_notificacion_id,
                "url_documento": inv_not.url_documento
            })

            # Eliminar archivo físico si existe
            if inv_not.url_documento:
                file_path = BASE_DIR / inv_not.url_documento
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar el archivo: {e}")

            # Eliminar InvolucradoNotificacion
            await db.execute(
                delete(InvolucradoNotificacion).where(
                    InvolucradoNotificacion.id == inv_not.id
                )
            )

        # Eliminar notificación
        await db.execute(
            delete(Notificacion).where(Notificacion.id == notificacion_id)
        )

        await db.flush()

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="notificacion",
            tipo_operacion="DELETE",
            descripcion=f"Eliminación de notificación (ID: {notificacion_id}) con {len(involucrados_not)} involucrado(s)",
            expediente_radicado=radicado,
            id_registro=str(notificacion_id),
            datos_anteriores={
                "notificacion": datos_notificacion,
                "involucrados_notificacion": datos_involucrados
            },
            datos_nuevos={}
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "message": "Notificación y sus registros relacionados eliminados correctamente",
                "deleted": {
                    "notificacion": 1,
                    "involucrados_notificacion": len(involucrados_not)
                }
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error eliminando notificación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/involucrado-notificacion")
async def crear_involucrado_notificacion(
    request:Request,
    radicado: str = Form(...),
    notificacion_id: int = Form(...),
    involucrado_id: int = Form(...),
    numerado: int = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio_citacion: str = Form(...),
    id_auxiliar: int = Form(...),
    tipo_etapa: str = Form(...),
    fecha_constancia_citacion: str = Form(None),
    notificacion_exitosa: bool = Form(False),
    tipo_notificacion_id: int = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):

    try:
        usuario_id = verify_gateway_token(request)

        # Convertir fechas
        fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
        fecha_envio_date = datetime.strptime(fecha_envio_citacion, "%Y-%m-%d").date()
        fecha_constancia_date = None
        if fecha_constancia_citacion:
            fecha_constancia_date = datetime.strptime(fecha_constancia_citacion, "%Y-%m-%d").date()
        logger.info("Fechas convertidas correctamente")

        # Validación numerado
        if not str(numerado).isdigit() or len(str(numerado)) > 4:
            logger.warning("Error validando numerado")
            raise HTTPException(status_code=400, detail="El numerado debe tener como maximo 4 dígitos")

        # Validación tipo archivo
        valid_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
        if file.content_type not in valid_types:
            logger.warning("Archivo con tipo inválido")
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF, JPG o PNG")

        # Tamaño archivo
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        logger.info(f"Tamaño archivo: {file_size} bytes")

        if file_size > 10 * 1024 * 1024:
            logger.warning("Archivo excede 10MB")
            raise HTTPException(status_code=400, detail="El archivo no debe superar los 10MB")

        # Verificar encargado
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)
        logger.info(f"Encargado del expediente: {encargado_id}")

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para modificar este expediente")

        # Verificar notificación
        stmt = select(Notificacion).where(Notificacion.id == notificacion_id)
        notificacion = await db.scalar(stmt)
        logger.info(f"Notificación encontrada: {bool(notificacion)}")

        if not notificacion:
            raise HTTPException(status_code=404, detail="Notificación no encontrada")

        # Verificar involucrado en expediente
        stmt = select(InvolucradoExpediente).where(
            and_(
                InvolucradoExpediente.involucrado_id == involucrado_id,
                InvolucradoExpediente.expediente_radicado == radicado
            )
        )
        inv_exp = await db.scalar(stmt)
        logger.info(f"Involucrado pertenece al expediente: {bool(inv_exp)}")

        if not inv_exp:
            raise HTTPException(status_code=404, detail="El involucrado no pertenece a este expediente")

        # Verificar duplicado
        stmt = select(InvolucradoNotificacion.id).where(
            and_(
                InvolucradoNotificacion.notificacion_id == notificacion_id,
                InvolucradoNotificacion.involucrado_id == involucrado_id
            )
        )
        existe = await db.scalar(stmt)
        logger.info(f"Ya existe notificación previa: {existe}")

        if existe:
            raise HTTPException(status_code=400, detail="Ya existe una notificación para este involucrado")

        # Validación de numerado + fecha_numerado según año
        año_numerado = fecha_numerado_date.year
        logger.info(f"Validando numerado para año: {año_numerado}")
        
        if año_numerado > 2012:
            # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
            stmt = (
                select(InvolucradoNotificacion.id)
                .where(
                    InvolucradoNotificacion.numerado == numerado,
                    InvolucradoNotificacion.fecha_numerado == fecha_numerado_date
                )
            )
            existe_notificacion = await db.scalar(stmt)
            
            if existe_notificacion:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra notificación"
                )
            logger.info("Numerado+fecha validado - único globalmente")
        else:
            logger.info("Año ≤ 2012 - se permite duplicado en mismo expediente")

        # Guardar archivo
        logger.info("Guardando archivo...")

        expediente_path = DOCS_DIR / str(id_auxiliar)
        etapa_path = expediente_path / tipo_etapa / "notificaciones"
        etapa_path.mkdir(parents=True, exist_ok=True)

        extension = "pdf"
        if file.content_type in ["image/jpeg", "image/jpg"]:
            extension = "jpg"
        elif file.content_type == "image/png":
            extension = "png"

        file_name = f"NOT_{numerado}_{fecha_numerado.replace('-', '')}_{involucrado_id}.{extension}"
        file_path = etapa_path / file_name

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Archivo guardado en: {file_path}")

        url_documento = f"uploads/expedientes/{id_auxiliar}/{tipo_etapa}/notificaciones/{file_name}"

        # Crear registro
        nuevo_inv_not = InvolucradoNotificacion(
            notificacion_id=notificacion_id,
            involucrado_id=involucrado_id,
            numerado=numerado,
            fecha_numerado=fecha_numerado_date,
            fecha_envio_citacion=fecha_envio_date,
            fecha_constancia_citacion=fecha_constancia_date,
            notificacion_exitosa=notificacion_exitosa,
            fecha_notificacion=datetime.now(ZoneInfo("America/Bogota")).date() if notificacion_exitosa else None,
            tipo_notificacion_id=tipo_notificacion_id,
            url_documento=url_documento
        )

        db.add(nuevo_inv_not)
        await db.flush()

        logger.info(f"ID generado: {nuevo_inv_not.id}")

        await db.commit()
        await db.refresh(nuevo_inv_not)

        logger.info("---- FIN EXITOSO ----")

        # Retornar el objeto completo en el formato consistente con PUT
        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": nuevo_inv_not.id,
                    "involucrado_id": nuevo_inv_not.involucrado_id,
                    "numerado": nuevo_inv_not.numerado,
                    "fecha_numerado": str(nuevo_inv_not.fecha_numerado),
                    "fecha_envio_citacion": str(nuevo_inv_not.fecha_envio_citacion),
                    "fecha_constancia_citacion": str(nuevo_inv_not.fecha_constancia_citacion) if nuevo_inv_not.fecha_constancia_citacion else None,
                    "notificacion_exitosa": nuevo_inv_not.notificacion_exitosa,
                    "url_documento": nuevo_inv_not.url_documento,
                    "tipo_notificacion_id": nuevo_inv_not.tipo_notificacion_id
                }
            },
            status_code=201
        )

    except Exception as e:
        logger.error(f"ERROR GENERAL: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/involucrado-notificacion/{involucrado_notificacion_id}")
async def eliminar_involucrado_notificacion(
    request:Request,
    involucrado_notificacion_id: int,
    radicado: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        # Verificar permisos
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )

        # Buscar InvolucradoNotificacion
        stmt = select(InvolucradoNotificacion).where(
            InvolucradoNotificacion.id == involucrado_notificacion_id
        )
        inv_not = await db.scalar(stmt)

        if not inv_not:
            raise HTTPException(
                status_code=404,
                detail="Notificación del involucrado no encontrada"
            )

        # Guardar datos anteriores para auditoría
        datos_anteriores = {
            "id": inv_not.id,
            "notificacion_id": inv_not.notificacion_id,
            "involucrado_id": inv_not.involucrado_id,
            "numerado": inv_not.numerado,
            "fecha_numerado": str(inv_not.fecha_numerado) if inv_not.fecha_numerado else None,
            "fecha_envio_citacion": str(inv_not.fecha_envio_citacion) if inv_not.fecha_envio_citacion else None,
            "fecha_constancia_citacion": str(inv_not.fecha_constancia_citacion) if inv_not.fecha_constancia_citacion else None,
            "notificacion_exitosa": inv_not.notificacion_exitosa,
            "tipo_notificacion_id": inv_not.tipo_notificacion_id,
            "url_documento": inv_not.url_documento
        }

        # Eliminar archivo físico
        if inv_not.url_documento:
            file_path = BASE_DIR / inv_not.url_documento
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"No se pudo eliminar el archivo: {e}")

        # Eliminar registro
        await db.execute(
            delete(InvolucradoNotificacion).where(
                InvolucradoNotificacion.id == involucrado_notificacion_id
            )
        )

        await db.flush()

        # Guardar auditoría
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="involucrado_notificacion",
            tipo_operacion="DELETE",
            descripcion=f"Eliminación de notificación {datos_anteriores['numerado']} para involucrado {datos_anteriores['involucrado_id']}",
            expediente_radicado=radicado,
            id_registro=str(involucrado_notificacion_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos={}
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "message": "Notificación del involucrado eliminada correctamente"
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error eliminando involucrado notificación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

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
        user_id = verify_gateway_token(request) 
        #Consultar permisos
        res = verificar_permiso_externo(user_id, LOG_PERMISSION)
        
        # Consulta base (sin JOIN a Usuario porque está en otro servicio)
        query = select(
            LogAuditoria.id,
            LogAuditoria.usuario_id,
            LogAuditoria.tabla_afectada,
            LogAuditoria.tipo_operacion,
            LogAuditoria.descripcion,
            LogAuditoria.expediente_radicado,
            LogAuditoria.id_registro,
            LogAuditoria.fecha,
            LogAuditoria.datos_anteriores,
            LogAuditoria.datos_nuevos
        )

        # Aplicar filtros
        conditions = []
        
        if usuario_id:
            conditions.append(LogAuditoria.usuario_id == usuario_id)
        
        if expediente_radicado:
            conditions.append(LogAuditoria.expediente_radicado == expediente_radicado)
        
        if tipo_operacion:
            conditions.append(LogAuditoria.tipo_operacion == tipo_operacion.upper())
        
        if tabla_afectada:
            conditions.append(LogAuditoria.tabla_afectada.ilike(f"%{tabla_afectada}%"))
        
        if id_registro:
            conditions.append(LogAuditoria.id_registro == id_registro)
        
        if fecha_inicio:
            try:
                fecha_inicio_date = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                conditions.append(LogAuditoria.fecha >= fecha_inicio_date)
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
                conditions.append(LogAuditoria.fecha <= fecha_fin_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Formato de fecha_fin inválido. Use YYYY-MM-DD"
                )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Contar total de registros
        count_query = select(func.count()).select_from(LogAuditoria)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await db.execute(count_query)
        total_records = total_result.scalar()
        
        # Ordenar por fecha descendente y aplicar paginación
        query = query.order_by(LogAuditoria.fecha.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        logs = result.fetchall()
        
        # Obtener IDs únicos de usuarios
        user_ids = list(set(log.usuario_id for log in logs if log.usuario_id))
        
        # Obtener información de usuarios del servicio de usuarios
        users_info = {}
        if user_ids:
            try:
                users_info = await obtener_info_usuarios(user_ids)
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

# Endpoint para obtener información de etapas por IDs (para auditoría)
@router.post("/audit/etapas/batch")
async def obtener_etapas_batch(
    request: Request,
    etapa_ids: list[int],
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene información de múltiples etapas por sus IDs.
    Retorna {etapa_id: nombre_tipo_etapa}
    """
    try:
        verify_gateway_token(request)
        
        if not etapa_ids or len(etapa_ids) == 0:
            return JSONResponse(
                content={"ok": True, "data": {}},
                status_code=200
            )
        
        if len(etapa_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="Máximo 100 etapas por solicitud"
            )
        
        # Consultar etapas con su tipo
        stmt = select(
            Etapa.id,
            TipoEtapa.nombre
        ).join(
            TipoEtapa, Etapa.tipo_etapa_id == TipoEtapa.id, isouter=True
        ).where(Etapa.id.in_(etapa_ids))
        
        result = await db.execute(stmt)
        etapas = result.fetchall()
        
        etapas_map = {
            etapa.id: etapa.nombre or f"Etapa {etapa.id}"
            for etapa in etapas
        }
        
        return JSONResponse(
            content={"ok": True, "data": etapas_map},
            status_code=200
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo etapas batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error al obtener información de etapas"
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

@router.get("/alerts/{radicado}")
async def obtener_alertas_expediente(
    radicado: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene todas las alertas de un expediente específico.
    
    Args:
        radicado: Número de radicado del expediente
        
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
            Expediente.radicado == radicado,
            Expediente.encargado_id == user_id
        )
        result = await db.execute(stmt)
        expediente = result.scalar()

        if not expediente:
            raise HTTPException(
                status_code=404,
                detail=f"Expediente con radicado {radicado} no encontrado o no tiene acceso"
            )

        fecha_hoy = date.today()
        alertas = await calcular_alertas_expediente(radicado, db, fecha_hoy)

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
                "radicado": radicado,
                "alertas": alertas,
                "total_alertas": len(alertas),
                "estadisticas_semaforo": estadisticas
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo alertas del expediente {radicado}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor al obtener alertas del expediente {radicado}"
        )


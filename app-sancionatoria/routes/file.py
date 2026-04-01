from fastapi import Request, APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, desc
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

class Procedure(BaseModel):
    radicado: str
    etapaId: int
    tipoNotificacion: int
    nombre: str

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

class BulkEncargadoRequest(BaseModel):
    radicados: List[str]
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

from utils.verify_gateway_token import verify_gateway_token
from utils.involved_client import get_involucrados_por_radicados
from services.usuarios import obtener_info_usuarios, obtener_usuarios_por_permiso, crear_notificacion_usuario, verificar_permiso_externo
# from services.alertas import calcular_alertas_expediente  # Importar dinámicamente para evitar errores de carga

from services.crud_file_operations import insert_auditoria

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
        usuario_id = verify_gateway_token(request)

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

        usuarios_disponibles = await obtener_usuarios_por_permiso(FILE_PERMISSION)

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
        involucrados_map = await get_involucrados_por_radicados(db, list(radicados_filtrados), GATEWAY_URL)

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

        # Obtener involucrados
        involucrados_map = await get_involucrados_por_radicados(db, radicados, GATEWAY_URL)

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

        # Obtener involucrados
        involucrados_map = await get_involucrados_por_radicados(db, radicados, GATEWAY_URL)

        data = []
        for id, rad, exp, fecha_crea, municipio_id, ultima_etapa in expedientes_raw:
            data.append({
                "id": id,
                "radicado": rad,
                "expediente": exp,
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
        
        stmt = select(Expediente).where(Expediente.expediente == file.expediente)
        result = await db.execute(stmt)
        existing_file = result.scalar_one_or_none()
        if existing_file:
            raise HTTPException(status_code=400, detail="El número de expediente ya existe")

        new_file = Expediente(
            radicado=file.radicado,
            expediente=file.expediente,
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
            "expediente": file.expediente,
            "motivo_afectacion": file.motivo,
            "encargado_id": file.encargado_id,
            "direccion": file.direccion,
            "vereda_id": file.vereda,
            "recursos": file.recurso
        }

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="expediente",
            tipo_operacion="INSERT",
            descripcion=f"Creación de expediente {file.radicado}",
            expediente_id=new_file.id,
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

@router.patch("/{expediente_id}/charge/{encargado_id}")
async def actualizar_encargado_de_expediente(
    request: Request,
    expediente_id: int,
    encargado_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        res = await verificar_permiso_externo(usuario_id, ENCARGADO_PERMISSION)

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
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
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
            notif_result = await crear_notificacion_usuario(
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
        usuario_id = verify_gateway_token(request)
        res = await verificar_permiso_externo(usuario_id, ENCARGADO_PERMISSION)

        if not res["ok"]:
            raise HTTPException(status_code=403, detail="No cuenta con permisos")

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        new_value = None if data.encargado_id == 0 else data.encargado_id
        updated = []

        for radicado in data.radicados:
            stmt_check = select(Expediente).where(Expediente.radicado == radicado)
            res_check = await db.execute(stmt_check)
            expediente = res_check.scalar_one_or_none()
            if expediente is None:
                continue

            datos_anteriores = {"radicado": radicado, "encargado_id": expediente.encargado_id}

            await db.execute(
                update(Expediente)
                .where(Expediente.radicado == radicado)
                .values({Expediente.encargado_id: new_value})
                .execution_options(synchronize_session=False)
            )

            await insert_auditoria(
                db=db,
                usuario_id=usuario_id,
                documento_usuario=user_info["documento"],
                nombre_usuario=user_info["nombre"],
                tabla_afectada="expediente",
                tipo_operacion="UPDATE",
                descripcion=f"Actualización masiva de encargado del expediente {radicado}",
                expediente_id=expediente.id,
                expediente_radicado=radicado,
                id_registro=radicado,
                datos_anteriores=datos_anteriores,
                datos_nuevos={"radicado": radicado, "encargado_id": new_value}
            )
            updated.append(radicado)

        await db.commit()

        if new_value:
            for radicado in updated:
                await crear_notificacion_usuario(
                    mensaje=f"Se te ha asignado el expediente {radicado}",
                    ruta=f"/expedientes/{radicado}",
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
    expediente_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Archiva un expediente. Solo disponible cuando se ha completado la etapa de Ejecución de la Sanción.
    Esta acción no se puede revertir.
    """
    try:
        usuario_id = verify_gateway_token(request)

        # Obtener datos anteriores
        stmt_check = select(Expediente).where(Expediente.id == expediente_id)
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
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
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
    expediente_id: str,
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

        # Llamar a app-docs para generar el PDF unificado
        from utils.docs_client import download_unified_pdf

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

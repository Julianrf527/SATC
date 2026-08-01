from fastapi import Request, APIRouter, Depends, HTTPException, Query, Path as PathParam
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, desc, union_all, literal, delete
from sqlalchemy.dialects.postgresql import insert
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from collections import defaultdict
import logging

from db.deps import get_db_managed
from db.models.recurso_afectado import RecursoAfectado
from db.models.expediente_recurso import ExpedienteRecurso
from db.models.expediente import Expediente
from db.models.vereda import Vereda
from db.models.municipio import Municipio
from db.models.tipo_notificacion import TipoNotificacion

from utils.verify_token import verify_gateway_token
from services.auditoria import insert_log
from services.involucrado import get_involucrados_by_expedientes_ids
from services.users import get_users_by_permission, get_user_info
from services.etapas import ETAPA_MODELS, ETAPA_LABELS, get_expediente_con_permiso
from core.permission import Permission

router = APIRouter()
FILE_MANAGE = Permission.FILE_MANAGE
logger = logging.getLogger(__name__)


class ExpedienteSchema(BaseModel):
    radicado: str
    expediente: str
    recurso: List[int]
    motivo: str
    encargado_id: int
    municipio: int
    vereda: int
    direccion: str

class FileUpdate(BaseModel):
    radicado: str
    expediente: str
    recurso: List[int]
    motivo: str
    vereda: int
    direccion: str

class FiltroAvanzado(BaseModel):
    """Filtros avanzados que NO están en quick filters."""
    motivo_afectacion: Optional[str] = None
    direccion: Optional[str] = None
    municipio_id: Optional[int] = None
    vereda_ids: Optional[List[int]] = None
    recurso_ids: Optional[List[int]] = None
    valor_exacto: bool = False


def _etapa_union_subq():
    """UNION of all stage tables to get (expediente_id, fecha_creacion, nombre_etapa)."""
    queries = [
        select(
            Model.expediente_id,
            Model.fecha_creacion,
            literal(ETAPA_LABELS[Model]).label("nombre_etapa")
        )
        for Model in ETAPA_MODELS.values()
    ]
    return union_all(*queries).subquery()


@router.get("/get")
async def obtener_expedientes(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=200),
    radicado: str = Query(None),
    expediente: str = Query(None),
    fecha_creacion: str = Query(None),
    encargado_id: int = Query(None),
):
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
            "nombre_expediente": r[2],
            "fecha_creacion": r[3].isoformat() if r[3] else None,
            "encargado_id": r[4],
            "encargado_nombre": usuarios_disponibles.get(r[4], {}).get("nombre") if r[4] else None,
            "encargado_documento": (usuarios_disponibles.get(r[4], {}).get("numero_documento") or usuarios_disponibles.get(r[4], {}).get("documento")) if r[4] else None,
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
    """Filtrado avanzado de expedientes (complemento a los quick filters)."""
    user_id = verify_gateway_token(request)["user_id"]

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

    if filtros.motivo_afectacion:
        expr = Expediente.motivo_afectacion == filtros.motivo_afectacion if filtros.valor_exacto \
            else Expediente.motivo_afectacion.ilike(f"%{filtros.motivo_afectacion}%")
        condiciones.append(expr)
        logger.info(f"Aplicando filtro motivo_afectacion: {filtros.motivo_afectacion}")

    if filtros.direccion:
        expr = Expediente.direccion == filtros.direccion if filtros.valor_exacto \
            else Expediente.direccion.ilike(f"%{filtros.direccion}%")
        condiciones.append(expr)
        logger.info(f"Aplicando filtro direccion: {filtros.direccion}")

    if filtros.municipio_id:
        condiciones.append(Vereda.municipio_id == filtros.municipio_id)
        logger.info(f"Aplicando filtro municipio_id: {filtros.municipio_id}")

    if filtros.vereda_ids:
        condiciones.append(Expediente.vereda_id.in_(filtros.vereda_ids))
        logger.info(f"Aplicando filtro vereda_ids: {filtros.vereda_ids}")

    if condiciones:
        stmt = stmt.where(and_(*condiciones))

    res = await db.execute(stmt)
    expedientes_raw = res.all()

    if not expedientes_raw:
        logger.info("No se encontraron expedientes con los filtros aplicados")
        return JSONResponse(content={"ok": True, "data": []}, status_code=200)

    ids_filtrados = set(r[0] for r in expedientes_raw)

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

    expedientes_raw = [e for e in expedientes_raw if e[0] in ids_filtrados]

    # r[6] = Vereda.municipio_id, ver orden de columnas en el select() de arriba
    municipio_ids = [r[6] for r in expedientes_raw if r[6] is not None]
    municipios_map = {}
    if municipio_ids:
        res_mun = await db.execute(
            select(Municipio.id, Municipio.nombre).where(Municipio.id.in_(municipio_ids))
        )
        municipios_map = {
            m_id: {"id": m_id, "nombre": m_nombre}
            for m_id, m_nombre in res_mun.all()
        }

    expediente_ids_filtrados = [e[0] for e in expedientes_raw]
    involucrados_map = await get_involucrados_by_expedientes_ids(db, expediente_ids_filtrados)

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
            "involucrados": involucrados_map.get(id, [])
        })

    logger.info(f"Se encontraron {len(data)} expedientes")
    return JSONResponse(content={"ok": True, "data": data}, status_code=200)

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
            "nombre": ra.nombre
        }
        for ra in result
    ]

    return JSONResponse(content={"ok": True, "data": data}, status_code=200)

@router.get("/full/{expediente_id}")
async def obtener_expediente_completo_por_expediente_id(
    request:Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    db: AsyncSession = Depends(get_db_managed)
):
    verify_gateway_token(request)

    all_etapas_sq = _etapa_union_subq()
    latest_etapa_subq = (
        select(
            all_etapas_sq.c.expediente_id,
            all_etapas_sq.c.nombre_etapa,
            func.row_number().over(
                partition_by=all_etapas_sq.c.expediente_id,
                order_by=all_etapas_sq.c.fecha_creacion.desc()
            ).label("rn")
        )
    ).subquery()

    stmt = (
        select(
            Expediente.id,
            Expediente.radicado,
            Expediente.motivo_afectacion,
            Expediente.direccion,
            Expediente.vereda_id,
            latest_etapa_subq.c.nombre_etapa.label("ultima_etapa")
        )
        .join(
            latest_etapa_subq,
            (latest_etapa_subq.c.expediente_id == Expediente.id)
            & (latest_etapa_subq.c.rn == 1),
            isouter=True
        )
        .where(Expediente.id == expediente_id)
    )

    res = await db.execute(stmt)
    expedientes_raw = res.all()

    if not expedientes_raw:
        return JSONResponse(content={"ok": True, "data": []}, status_code=200)

    expediente_ids = [r[0] for r in expedientes_raw]
    vereda_ids = [r[4] for r in expedientes_raw if r[4]]

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

    involucrados_map = await get_involucrados_by_expedientes_ids(db, expediente_ids)

    veredas_map = {}
    if vereda_ids:
        res_ver = await db.execute(
            select(Vereda.id, Vereda.nombre)
            .where(Vereda.id.in_(vereda_ids))
        )
        veredas_map = {
            v_id: {"id": v_id, "nombre": v_name}
            for v_id, v_name in res_ver.all()
        }

    exp_dict = {}
    for expediente_id, radicado, motivo, direccion, vereda_id, ultima_etapa in expedientes_raw:
        exp_dict = {
            "radicado": radicado,
            "recurso_afectado": recursos_map.get(expediente_id, []),
            "motivo_afectacion": motivo,
            "direccion": direccion,
            "vereda": veredas_map.get(vereda_id),
            "ultima_etapa": ultima_etapa,
            "involucrados": involucrados_map.get(expediente_id, []),
        }

    all_sq = _etapa_union_subq()
    stmt_etapas = (
        select(all_sq.c.nombre_etapa)
        .where(all_sq.c.expediente_id == expediente_id)
    )
    res_etapas = await db.execute(stmt_etapas)
    etapas_existentes = [nombre for (nombre,) in res_etapas.all()]

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

@router.put("/{expediente_id}/basic-data")
async def actualizar_informacion_expediente(
    request: Request,
    expediente_id: int,
    file: FileUpdate,
    db: AsyncSession = Depends(get_db_managed)
):
    """Actualiza la información básica de un expediente."""
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    await get_expediente_con_permiso(db, expediente_id, user_id)

    stmt_check = select(Expediente).where(Expediente.id == expediente_id)
    res_check = await db.execute(stmt_check)
    expediente_actual = res_check.scalar_one_or_none()

    stmt_recursos = select(ExpedienteRecurso.recurso_id).where(
        ExpedienteRecurso.expediente_id == expediente_id
    )
    res_recursos = await db.execute(stmt_recursos)
    recursos_anteriores = [row[0] for row in res_recursos.fetchall()]

    vereda_ant_nombre = await db.scalar(select(Vereda.nombre).where(Vereda.id == expediente_actual.vereda_id)) if expediente_actual.vereda_id else None
    recursos_ant_nombres = list((await db.execute(select(RecursoAfectado.nombre).where(RecursoAfectado.id.in_(recursos_anteriores)))).scalars().all()) if recursos_anteriores else []
    datos_anteriores = {
        "radicado": expediente_actual.radicado,
        "nombre_expediente": expediente_actual.expediente,
        "motivo_afectacion": expediente_actual.motivo_afectacion,
        "direccion": expediente_actual.direccion,
        "vereda": vereda_ant_nombre,
        "recursos": recursos_ant_nombres,
    }

    if file.radicado != expediente_actual.radicado:
        stmt_radicado = select(Expediente).where(
            and_(
                Expediente.radicado == file.radicado,
                Expediente.id != expediente_id
            )
        )
        result = await db.execute(stmt_radicado)
        duplicate_radicado = result.scalar_one_or_none()

        if duplicate_radicado:
            raise HTTPException(
                status_code=409,
                detail="El radicado ya está en uso por otro expediente"
            )

    stmt_update = (
        update(Expediente)
        .where(Expediente.id == expediente_id)
        .values(
            radicado=file.radicado,
            expediente=file.expediente,
            motivo_afectacion=file.motivo,
            direccion=file.direccion,
            vereda_id=file.vereda,
        )
    )
    await db.execute(stmt_update)

    # Diff por sets contra lo existente: solo se tocan las filas que cambiaron
    nuevos_recursos = set(file.recurso or [])
    anteriores_set = set(recursos_anteriores)
    a_borrar = anteriores_set - nuevos_recursos
    a_insertar = nuevos_recursos - anteriores_set

    if a_borrar:
        await db.execute(
            delete(ExpedienteRecurso).where(
                and_(
                    ExpedienteRecurso.expediente_id == expediente_id,
                    ExpedienteRecurso.recurso_id.in_(a_borrar)
                )
            )
        )
    for recurso_id in a_insertar:
        insert_stmt = insert(ExpedienteRecurso).values(
            expediente_id=expediente_id,
            recurso_id=recurso_id
        ).on_conflict_do_nothing()
        await db.execute(insert_stmt)

    vereda_nueva_nombre = await db.scalar(select(Vereda.nombre).where(Vereda.id == file.vereda)) if file.vereda else None
    recursos_nuevos_nombres = list((await db.execute(select(RecursoAfectado.nombre).where(RecursoAfectado.id.in_(file.recurso or [])))).scalars().all()) if file.recurso else []
    datos_nuevos = {
        "radicado": file.radicado,
        "nombre_expediente": file.expediente,
        "motivo_afectacion": file.motivo,
        "direccion": file.direccion,
        "vereda": vereda_nueva_nombre,
        "recursos": recursos_nuevos_nombres,
    }

    await insert_log(
        db=db,
        tipo_evento="ACTUALIZAR_EXPEDIENTE",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Actualización de expediente '{file.radicado}'",
        expediente_id=expediente_id,
        expediente_radicado=file.radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos
    )

    await db.commit()

    logger.info(f"Expediente {file.radicado} actualizado exitosamente (ID: {expediente_id})")

    return JSONResponse(
        content={
            "ok": True,
            "msg": "Expediente actualizado exitosamente"
        },
        status_code=200
    )

@router.get("/get/all")
async def obtener_expedientes_para_vista(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    verify_gateway_token(request)

    all_etapas_sq = _etapa_union_subq()
    latest_etapa_subq = (
        select(
            all_etapas_sq.c.expediente_id,
            all_etapas_sq.c.nombre_etapa,
            func.row_number().over(
                partition_by=all_etapas_sq.c.expediente_id,
                order_by=all_etapas_sq.c.fecha_creacion.desc()
            ).label("rn")
        )
    ).subquery()

    stmt = (
        select(
            Expediente,
            latest_etapa_subq.c.nombre_etapa.label("nombre_tipo_etapa")
        )
        .join(
            latest_etapa_subq,
            (latest_etapa_subq.c.expediente_id == Expediente.id) &
            (latest_etapa_subq.c.rn == 1),
            isouter=True
        )
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

    involucrados_map = await get_involucrados_by_expedientes_ids(db, expediente_ids)

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
    for exp in expedientes:
        vereda_obj = veredas_map.get(exp.vereda_id)
        municipio_obj = municipios_map.get(vereda_obj["municipio_id"]) if vereda_obj else None

        data.append({
            "id": exp.id,
            "radicado": exp.radicado,
            "expediente": exp.expediente,
            "recurso_afectado": recursos_map.get(exp.id, []),
            "motivo_afectacion": exp.motivo_afectacion,
            "fecha_creacion": exp.fecha_creacion.isoformat() if exp.fecha_creacion else None,
            "direccion": exp.direccion,
            "municipio": municipio_obj,
            "vereda": {"id": vereda_obj["id"], "nombre": vereda_obj["nombre"]} if vereda_obj else None,
            "involucrados": involucrados_map.get(exp.id, []),
            "ultima_etapa": exp.nombre_tipo_etapa
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
        raise HTTPException(status_code=403, detail="Sin permisos para consultar los expedientes de este usuario")

    all_etapas_sq = _etapa_union_subq()
    latest_etapa_subq = (
        select(
            all_etapas_sq.c.expediente_id,
            all_etapas_sq.c.nombre_etapa,
            func.row_number().over(
                partition_by=all_etapas_sq.c.expediente_id,
                order_by=all_etapas_sq.c.fecha_creacion.desc()
            ).label("rn")
        )
    ).subquery()

    stmt = (
        select(
            Expediente.id,
            Expediente.radicado,
            Expediente.expediente,
            Expediente.fecha_creacion,
            Vereda.municipio_id,
            latest_etapa_subq.c.nombre_etapa.label("ultima_etapa")
        )
        .join(Vereda, Vereda.id == Expediente.vereda_id, isouter=True)
        .join(
            latest_etapa_subq,
            (latest_etapa_subq.c.expediente_id == Expediente.id)
            & (latest_etapa_subq.c.rn == 1),
            isouter=True
        )
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

    involucrados_map = await get_involucrados_by_expedientes_ids(db, expediente_ids)

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

@router.post("/add")
async def agregar_expediente(
    request: Request,
    expediente: ExpedienteSchema,
    db: AsyncSession = Depends(get_db_managed),
):
    """Crea un nuevo expediente en el sistema."""
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
    await db.flush()  # Obtener el ID sin hacer commit
    expediente_id = nuevo_expediente.id

    for recurso_id in expediente.recurso:
        db.add(
            ExpedienteRecurso(
                expediente_id=expediente_id,
                recurso_id=recurso_id,
            )
        )

    vereda_nombre_crear = await db.scalar(select(Vereda.nombre).where(Vereda.id == expediente.vereda)) if expediente.vereda else None
    recursos_nombres_crear = list((await db.execute(select(RecursoAfectado.nombre).where(RecursoAfectado.id.in_(expediente.recurso)))).scalars().all()) if expediente.recurso else []
    encargado_info_crear = (await get_user_info([expediente.encargado_id])).get(expediente.encargado_id, {}) if expediente.encargado_id else {}
    datos_nuevos = {
        "radicado": expediente.radicado,
        "expediente": expediente.expediente,
        "motivo_afectacion": expediente.motivo,
        "encargado": encargado_info_crear.get("nombre", f"ID {expediente.encargado_id}") if expediente.encargado_id else None,
        "direccion": expediente.direccion,
        "vereda": vereda_nombre_crear,
        "recursos": recursos_nombres_crear,
    }

    await insert_log(
        db=db,
        tipo_evento="CREAR_EXPEDIENTE",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Creación de expediente {expediente.radicado}",
        expediente_id=expediente_id,
        expediente_radicado=expediente.radicado,
        datos_nuevos=datos_nuevos
    )

    await db.commit()
    await db.refresh(nuevo_expediente)

    logger.info(f"Expediente creado exitosamente: {expediente.radicado} (ID: {expediente_id})")

    return JSONResponse(
        content={
            "ok": True,
            "expediente_id": expediente_id,
            "radicado": expediente.radicado,
            "msg": "Expediente creado exitosamente"
        },
        status_code=201  # Usar 201 Created en lugar de 200
    )

@router.patch("/{expediente_id}/archive")
async def archivar_expediente(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """Archiva un expediente. Acción irreversible."""
    user_id = verify_gateway_token(request)["user_id"]

    await get_expediente_con_permiso(db, expediente_id, user_id)

    stmt_check = select(Expediente).where(Expediente.id == expediente_id)
    res_check = await db.execute(stmt_check)
    expediente = res_check.scalar_one_or_none()

    if expediente.archivado:
        raise HTTPException(status_code=400, detail="El expediente ya está archivado")

    datos_anteriores = {
        "radicado": expediente.radicado,
        "archivado": expediente.archivado
    }

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

    await insert_log(
        db=db,
        tipo_evento="ARCHIVAR_EXPEDIENTE",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Archivado del expediente {expediente.radicado}",
        expediente_id=expediente.id,
        expediente_radicado=expediente.radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos
    )

    await db.commit()

    return JSONResponse(
        content={"ok": True, "message": "Expediente archivado exitosamente"},
        status_code=200
    )

"""Consulta de expedientes (pestañas Gestionar y Consulta). Solo lectura.

Prefijo en main.py: ``/expedientes``.
- ``GET /expedientes``: listado paginado con filtros.
- ``GET /expedientes/{id}``: información base completa + ``etapas`` (hook del
  agente C en ``services/etapas_lectura.py``) + ``acciones_disponibles``.
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_lectura, tiene_permiso
from core.permission import Permission
from db.deps import get_db_managed
from db.models import Expediente, ExpedienteInvolucrado, Municipio, TipoFuente, Vereda
from services.etapas_lectura import leer_etapas
from services.expediente import cargar_expediente, serializar_expediente
from services.involved import get_involucrados_by_ids

router = APIRouter()


@router.get("")
async def listar_expedientes(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=200),
    radicado: str | None = Query(None, description="Contiene (sin distinguir mayúsculas)"),
    expediente: str | None = Query(None, description='Número de expediente, p. ej. "CA 001-26" (contiene)'),
    numero_vital: str | None = Query(None, description="Contiene"),
    municipio_id: int | None = Query(None),
    vereda_id: int | None = Query(None),
    involucrado_id: int | None = Query(None, description="id de app-involved (solicitante o tercero)"),
):
    await requiere_lectura(request)

    condiciones = []
    if radicado and radicado.strip():
        condiciones.append(Expediente.radicado.ilike(f"%{radicado.strip()}%"))
    if expediente and expediente.strip():
        condiciones.append(Expediente.expediente.ilike(f"%{expediente.strip()}%"))
    if numero_vital and numero_vital.strip():
        condiciones.append(Expediente.numero_vital.ilike(f"%{numero_vital.strip()}%"))
    if vereda_id is not None:
        condiciones.append(Expediente.vereda_id == vereda_id)
    if municipio_id is not None:
        condiciones.append(Vereda.municipio_id == municipio_id)
    if involucrado_id is not None:
        condiciones.append(Expediente.id.in_(
            select(ExpedienteInvolucrado.expediente_id)
            .where(ExpedienteInvolucrado.involucrado_id == involucrado_id)
        ))
    filtro = and_(*condiciones) if condiciones else None

    count_stmt = select(func.count(Expediente.id)).join(Vereda, Vereda.id == Expediente.vereda_id)
    data_stmt = (
        select(
            Expediente.id,
            Expediente.version,
            Expediente.radicado,
            Expediente.fecha_radicado,
            Expediente.expediente,
            Expediente.numero_vital,
            Expediente.nombre_predio,
            Expediente.nombre_fuente,
            Expediente.fecha_creacion,
            Vereda.id.label("vereda_id"),
            Vereda.nombre.label("vereda_nombre"),
            Municipio.id.label("municipio_id"),
            Municipio.nombre.label("municipio_nombre"),
            TipoFuente.id.label("tipo_fuente_id"),
            TipoFuente.nombre.label("tipo_fuente_nombre"),
        )
        .join(Vereda, Vereda.id == Expediente.vereda_id)
        .join(Municipio, Municipio.id == Vereda.municipio_id)
        .join(TipoFuente, TipoFuente.id == Expediente.tipo_fuente_id)
    )
    if filtro is not None:
        count_stmt = count_stmt.where(filtro)
        data_stmt = data_stmt.where(filtro)

    total = await db.scalar(count_stmt) or 0
    rows = (await db.execute(
        data_stmt.order_by(desc(Expediente.fecha_creacion), desc(Expediente.id))
        .offset((page - 1) * limit).limit(limit)
    )).mappings().all()

    # Involucrados de la página resueltos en una sola llamada a app-involved.
    ids = [r["id"] for r in rows]
    vinculos = (await db.execute(
        select(
            ExpedienteInvolucrado.expediente_id,
            ExpedienteInvolucrado.involucrado_id,
            ExpedienteInvolucrado.tipo_vinculo,
        )
        .where(ExpedienteInvolucrado.expediente_id.in_(ids))
        .order_by(ExpedienteInvolucrado.fecha_vinculacion, ExpedienteInvolucrado.id)
    )).all() if ids else []
    personas = await get_involucrados_by_ids(db, sorted({v.involucrado_id for v in vinculos}))
    mapa = {p["id"]: p for p in personas if isinstance(p, dict) and "id" in p}
    por_expediente: dict[int, list[dict]] = {}
    for v in vinculos:
        info = mapa.get(v.involucrado_id) or {"id": v.involucrado_id}
        por_expediente.setdefault(v.expediente_id, []).append({
            "involucrado_id": v.involucrado_id,
            "tipo_vinculo": v.tipo_vinculo.value,
            "nombre": info.get("nombre"),
            "tipo_documento": info.get("tipo_documento"),
            "numero_documento": info.get("numero_documento"),
        })

    data = [
        {
            "id": r["id"],
            "version": r["version"],
            "radicado": r["radicado"],
            "fecha_radicado": r["fecha_radicado"].isoformat() if r["fecha_radicado"] else None,
            "expediente": r["expediente"],
            "numero_vital": r["numero_vital"],
            "nombre_predio": r["nombre_predio"],
            "nombre_fuente": r["nombre_fuente"],
            "fecha_creacion": r["fecha_creacion"].isoformat() if r["fecha_creacion"] else None,
            "vereda": {"id": r["vereda_id"], "nombre": r["vereda_nombre"]},
            "municipio": {"id": r["municipio_id"], "nombre": r["municipio_nombre"]},
            "tipo_fuente": {"id": r["tipo_fuente_id"], "nombre": r["tipo_fuente_nombre"]},
            "involucrados": por_expediente.get(r["id"], []),
        }
        for r in rows
    ]
    return {"ok": True, "data": data, "page": page, "limit": limit, "totalCount": total}


@router.get("/{expediente_id}")
async def obtener_expediente(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_lectura(request)
    expediente = await cargar_expediente(db, expediente_id)

    puede_gestionar = usuario.super_gestion or await tiene_permiso(usuario.user_id, Permission.MANAGE)
    data = await serializar_expediente(db, expediente, puede_gestionar)

    acciones = ["descargar_expediente"]
    if puede_gestionar:
        acciones = ["editar_informacion_base", "vincular_solicitante", *acciones]
    data["acciones_disponibles"] = acciones
    data["etapas"] = await leer_etapas(db, expediente, usuario)
    return {"ok": True, "data": data}

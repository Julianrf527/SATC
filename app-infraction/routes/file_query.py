from fastapi import Request, APIRouter, Depends, HTTPException, Query, Path as PathParam
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, union_all, literal
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv
import logging
import os
import pytz

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
from db.models.vereda import Vereda
from db.models.municipio import Municipio
from db.models.radicado_asociado import RadicadoAsociado
from db.models.quejoso import Quejoso

from core.permission import Permission
ASSIGN_PERMISSION = Permission.ASSIGN_PERMISSION
FILE_MANAGE = Permission.FILE_MANAGE
FILE_CONSULT = Permission.FILE_CONSULT
LOG_PERMISSION = Permission.LOG_PERMISSION

router = APIRouter()
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_DAYS = os.getenv("JWT_EXP_DAYS")

bogota_tz = pytz.timezone("America/Bogota")
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = BASE_DIR / "uploads" / "expedientes"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from .models.file_models import (
    FiltroAvanzado,
)

from utils.verify_token import verify_gateway_token
from services.users import get_users_by_permission, verify_permission
from services.involved import get_involved_by_expedientes_ids
from services.estado_expediente import calcular_estados, calcular_estado_uno


# ─── Permisos de lectura ─────────────────────────────────────────────────────
# El gateway solo autentica; los permisos se verifican aquí. Cada endpoint
# exige lo mismo que la pantalla del frontend que lo consume (App.tsx):
#   - /infraction/consult       -> infraccion_consultar (ve todos)
#   - /infraction/manage        -> infraccion_gestionar (solo los suyos)
#   - /infraction/assign_manage -> infraccion_asignar
#   - /audit/infractions        -> auditoria_infracciones

async def _tiene_alguno(user_id: int, *permisos: str) -> bool:
    for permiso in permisos:
        if await verify_permission(user_id, permiso):
            return True
    return False


async def _exigir_alguno(user_id: int, *permisos: str) -> None:
    if not await _tiene_alguno(user_id, *permisos):
        raise HTTPException(status_code=403, detail="Sin permisos")


@router.get("")
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
    # Lista TODOS los expedientes + usuarios con documento: solo la pantalla
    # de asignación de encargados (/infraction/assign_manage).
    user_id = verify_gateway_token(request)["user_id"]
    await _exigir_alguno(user_id, ASSIGN_PERMISSION)

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
        Expediente.archivado,
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

    estados_map = await calcular_estados(
        db, [r[0] for r in rows], {r[0]: r[5] for r in rows}
    )

    payload = [
        {
            "id": r[0],
            "radicado": r[1],
            "fecha_radicado": r[2].isoformat() if r[2] else None,
            "encargado_id": r[3],
            "encargado_nombre": usuarios_disponibles.get(r[3], {}).get("nombre") if r[3] else None,
            "encargado_documento": (usuarios_disponibles.get(r[3], {}).get("numero_documento") or usuarios_disponibles.get(r[3], {}).get("documento")) if r[3] else None,
            "fecha_creacion": r[4].isoformat() if r[4] else None,
            "archivado": r[5],
            "estado": estados_map.get(r[0]),
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


# ─── Listados de expedientes (forma compartida) ─────────────────────────────
# GET /todos (vista de consulta), GET /encargado/{id} (vista de gestión) y
# POST /filtrar devuelven items con la MISMA forma; los tres pasan por
# _listar_expedientes. Lo único que cambia entre vistas es cómo se calcula
# etapa_actual (etiquetas y fecha de referencia), que se conserva tal cual
# estaba en cada endpoint.

def _etapa_actual_vista_todos():
    """Etapa más reciente por expediente, como la calcula GET /todos."""
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
    return _etapa_mas_reciente(concepto_q, cierre_q, visita_q, seguimiento_q)


def _etapa_actual_vista_encargado():
    """Etapa más reciente por expediente, como la calcula GET /encargado/{id}."""
    def fecha_informe():
        return func.coalesce(
            InformeTecnico.fecha_aceptacion_informe,
            InformeTecnico.fecha_recibido_informe,
            InformeTecnico.fecha_programacion_visita,
        ).label("fecha_creacion")

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
        fecha_informe(),
        literal("visita").label("tipo")
    ).where(InformeTecnico.tipo_informe == "VISITA")
    seguimiento_q = select(
        InformeTecnico.expediente_id,
        fecha_informe(),
        literal("seguimiento").label("tipo")
    ).where(InformeTecnico.tipo_informe == "SEGUIMIENTO")
    return _etapa_mas_reciente(concepto_q, cierre_q, visita_q, seguimiento_q)


def _etapa_mas_reciente(*selects):
    etapas_union = union_all(*selects).subquery()
    etapa_reciente = select(
        etapas_union.c.expediente_id,
        etapas_union.c.tipo,
        func.row_number().over(
            partition_by=etapas_union.c.expediente_id,
            order_by=etapas_union.c.fecha_creacion.desc()
        ).label("rn")
    ).subquery()
    return select(
        etapa_reciente.c.expediente_id,
        etapa_reciente.c.tipo
    ).where(etapa_reciente.c.rn == 1).subquery()


async def _listar_expedientes(db: AsyncSession, etapa_actual, condiciones=()) -> list[dict]:
    """
    Ejecuta el listado de expedientes y lo serializa con la forma común:
    id, radicado, fecha_radicado, fecha_creacion, archivado, municipio,
    involucrados, etapa_actual, estado.

    `condiciones` se aplican sobre Expediente/Vereda (Vereda va por outer
    join, así que se puede filtrar por Vereda.municipio_id).
    """
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
    )
    if condiciones:
        stmt = stmt.where(and_(*condiciones))

    rows = (await db.execute(stmt)).mappings().all()
    if not rows:
        return []

    expediente_ids = [r["id"] for r in rows]
    involucrados_map = await get_involved_by_expedientes_ids(db, expediente_ids)
    estados_map = await calcular_estados(
        db, expediente_ids, {r["id"]: r["archivado"] for r in rows}
    )

    return [
        {
            "id": r["id"],
            "radicado": r["radicado"],
            "fecha_radicado": r["fecha_radicado"].isoformat() if r["fecha_radicado"] else None,
            "fecha_creacion": r["fecha_creacion"].isoformat() if r["fecha_creacion"] else None,
            "archivado": r["archivado"],
            "municipio": {"id": r["municipio_id"], "nombre": r["municipio_nombre"]} if r["municipio_id"] else None,
            "involucrados": involucrados_map.get(r["id"], []),
            "etapa_actual": r["etapa_actual"],
            "estado": estados_map.get(r["id"]),
        }
        for r in rows
    ]


@router.post("/filtrar")
async def filtrar_expedientes(
    request: Request,
    filtros: FiltroAvanzado,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Filtrado avanzado de expedientes (dirección, municipio, veredas, recursos,
    tipos de afectación). Cada item tiene la misma forma que GET /todos y
    GET /encargado/{id} (ver _listar_expedientes).

    Alcance:
      - alcance="propios" (por defecto): solo expedientes con
        abogado_responsable_id == usuario, como la vista de gestión.
      - alcance="todos": todos los expedientes, como la vista de consulta
        (GET /todos), solo si el usuario tiene infraccion_consultar; si no lo
        tiene, se limita a los suyos.
      - Los "propios" exigen infraccion_gestionar (vista de gestión); sin
        ninguno de los dos permisos responde 403.

    Sin try/except propio: get_db_managed convierte los errores inesperados en
    500 (con rollback) y deja pasar las HTTPException y los 422 tal cual.
    """
    user_id = verify_gateway_token(request)["user_id"]

    ver_todos = filtros.alcance == "todos" and await verify_permission(user_id, FILE_CONSULT)
    if not ver_todos:
        await _exigir_alguno(user_id, FILE_MANAGE)

    condiciones = []
    if ver_todos:
        etapa_actual = _etapa_actual_vista_todos()
    else:
        etapa_actual = _etapa_actual_vista_encargado()
        condiciones.append(Expediente.abogado_responsable_id == user_id)

    if filtros.direccion:
        condiciones.append(
            Expediente.direccion == filtros.direccion if filtros.valor_exacto
            else Expediente.direccion.ilike(f"%{filtros.direccion}%")
        )

    if filtros.municipio_id:
        condiciones.append(Vereda.municipio_id == filtros.municipio_id)

    if filtros.vereda_ids:
        condiciones.append(Expediente.vereda_id.in_(filtros.vereda_ids))

    # Recursos y tipos de afectación: basta con que el expediente tenga alguno
    # de los seleccionados (OR dentro de cada filtro, AND entre filtros).
    if filtros.recurso_ids:
        condiciones.append(Expediente.id.in_(
            select(ExpedienteRecurso.expediente_id)
            .where(ExpedienteRecurso.recurso_id.in_(filtros.recurso_ids))
        ))

    if filtros.tipo_afectacion_ids:
        condiciones.append(Expediente.id.in_(
            select(ExpedienteTipoAfectacion.expediente_id)
            .where(ExpedienteTipoAfectacion.tipo_afectacion_id.in_(filtros.tipo_afectacion_ids))
        ))

    data = await _listar_expedientes(db, etapa_actual, condiciones)

    logger.info(
        f"filtrar_expedientes: usuario {user_id}, alcance {'todos' if ver_todos else 'propios'}, "
        f"{len(data)} resultados"
    )
    return JSONResponse(content={"ok": True, "data": data}, status_code=200)


@router.get("/recursos-afectados")
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


@router.get("/denunciantes")
async def obtener_quejosos(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    # Datos personales (teléfono, correo) de los quejosos: catálogo de las
    # vistas de consulta/gestión y de la auditoría de infracciones.
    user_id = verify_gateway_token(request)["user_id"]
    await _exigir_alguno(user_id, FILE_CONSULT, FILE_MANAGE, LOG_PERMISSION)
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




@router.get("/completo/{expediente_id}")
async def obtener_expediente_completo_por_expediente_id(
    request: Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    db: AsyncSession = Depends(get_db_managed)
):
    # Consulta (infraccion_consultar) abre cualquier expediente; gestión
    # (infraccion_gestionar) solo los que tiene a cargo. 403 (no 404) cuando
    # no es suyo, para no revelar si el expediente existe.
    user_id = verify_gateway_token(request)["user_id"]
    if not await verify_permission(user_id, FILE_CONSULT):
        await _exigir_alguno(user_id, FILE_MANAGE)
        encargado = await db.scalar(
            select(Expediente.abogado_responsable_id).where(Expediente.id == expediente_id)
        )
        if encargado is None or encargado != user_id:
            raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

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
            Expediente.archivado,
            etapa_actual.c.tipo.label("etapa_actual"),
        )
        .where(Expediente.id == expediente_id)
        .outerjoin(etapa_actual, etapa_actual.c.expediente_id == Expediente.id)
    )

    expediente = (await db.execute(stmt)).mappings().first()

    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")

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
    estado = await calcular_estado_uno(db, expediente_id, expediente["archivado"])

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
        "archivado": expediente["archivado"],
        "estado": estado,
    }

    return JSONResponse(
        content={
            "ok": True,
            "data": exp_dict,
            "etapas_existentes": sorted(etapas_existentes),
        },
        status_code=200
    )


@router.get("/todos")
async def obtener_expedientes_para_vista(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = verify_gateway_token(request)["user_id"]
    await _exigir_alguno(user_id, FILE_CONSULT)
    data = await _listar_expedientes(db, _etapa_actual_vista_todos())
    return JSONResponse(content={"ok": True, "data": data}, status_code=200)


@router.get("/encargado/{encargado_id}")
async def obtener_expedientes_por_encargado(
    request: Request,
    encargado_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = verify_gateway_token(request)["user_id"]

    if user_id != encargado_id:
        raise HTTPException(status_code=403, detail="Sin permisos")
    await _exigir_alguno(user_id, FILE_MANAGE)

    data = await _listar_expedientes(
        db,
        _etapa_actual_vista_encargado(),
        [Expediente.abogado_responsable_id == encargado_id],
    )
    return JSONResponse(content={"ok": True, "data": data}, status_code=200)

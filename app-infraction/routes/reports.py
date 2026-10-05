from fastapi import Request, APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_, func
from datetime import datetime, date
from pydantic import BaseModel
from typing import Optional
import logging

from satc_shared.review_process import FINALIZADO, ReviewError

from db.deps import get_db_managed
from db.models.informe_tecnico import InformeTecnico
from db.models.informe_recurso_afectado import InformeRecursoAfectado, RECURSOS_MATRIZ
from db.models.expediente import Expediente

from core.permission import Permission
ASSIGN_REPORTS = Permission.ASSIGN_REPORTS
UPLOAD_REPORTS = Permission.UPLOAD_REPORTS
REVIEW_REPORTS = Permission.REVIEW_REPORTS
MANUAL_UPLOAD = Permission.MANUAL_UPLOAD

router = APIRouter()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from utils.verify_token import verify_gateway_token
from services.users import get_users_by_permission, verify_permission
from services.docs import increment_file_usage, decrement_file_usage, get_file_info
from services.revision_informes import (
    Avisos,
    cerrar_proceso_vigente,
    crear_proceso_informe,
    es_final,
    proceso_vigente,
    procesos_vigentes,
    resumen_proceso,
)


# ─── SCHEMAS ────────────────────────────────────────────────────────────────

class AsignarProfesionalRequest(BaseModel):
    profesional_id: int
    revisor_id: int
    fecha_programacion_visita: Optional[str] = None  # ISO date string


class CambiarModoRequest(BaseModel):
    modo: str  # 'FLUJO' | 'MANUAL'


class CargueManualRequest(BaseModel):
    file_id: int
    fecha_recibido: str  # ISO date string
    fecha_aceptacion: str  # ISO date string
    fecha_programacion_visita: Optional[str] = None  # ISO date string
    profesional_id: Optional[int] = None
    revisor_id: Optional[int] = None


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _format_date(d) -> Optional[str]:
    if d is None:
        return None
    if isinstance(d, (date, datetime)):
        return d.isoformat()
    return str(d)


async def _radicado(db: AsyncSession, expediente_id: int) -> str:
    radicado = await db.scalar(select(Expediente.radicado).where(Expediente.id == expediente_id))
    return radicado or str(expediente_id)


async def _validar_asignacion(informe: Optional[InformeTecnico], body: AsignarProfesionalRequest) -> None:
    if not informe:
        raise HTTPException(status_code=404, detail="Informe técnico no encontrado")
    if informe.modo != "FLUJO":
        raise HTTPException(status_code=400, detail="El informe está en modo de cargue manual, cambia el modo primero")
    if informe.fecha_aceptacion_informe is not None:
        raise HTTPException(status_code=400, detail="El informe ya fue aceptado, no se puede reasignar")
    if body.revisor_id == body.profesional_id:
        raise HTTPException(status_code=400, detail="El profesional y el revisor deben ser personas distintas")
    if not await verify_permission(body.profesional_id, UPLOAD_REPORTS):
        raise HTTPException(status_code=400, detail="El usuario no tiene permiso de infraccion_informes_subir")
    if not await verify_permission(body.revisor_id, REVIEW_REPORTS):
        raise HTTPException(status_code=400, detail="El usuario seleccionado no tiene permiso de infraccion_informes_revisar")


def _aplicar_datos_asignacion(informe: InformeTecnico, body: AsignarProfesionalRequest) -> None:
    informe.profesional_asignado_id = body.profesional_id
    informe.revisor_asignado_id = body.revisor_id
    if body.fecha_programacion_visita:
        try:
            informe.fecha_programacion_visita = date.fromisoformat(body.fecha_programacion_visita)
        except ValueError:
            pass


async def _commit_asignacion(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError:
        # Índice único parcial: otra asignación simultánea ya creó el proceso vigente.
        await db.rollback()
        raise HTTPException(status_code=409, detail="El informe ya tiene un proceso activo")


# ─── GET /informes ───────────────────────────────────────────────────────────

@router.get("/disponibles", status_code=200)
async def obtener_profesionales_revisores_disponibles(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Lista de usuarios con permiso de subir/revisar informes, para el
    selector opcional de profesional/revisor en el cargue manual.
    """
    user_id = verify_gateway_token(request)["user_id"]
    permisos = await verify_permission(user_id, MANUAL_UPLOAD)
    if not permisos:
        raise HTTPException(status_code=403, detail="No tienes permiso para cargar informes manualmente")

    profesionales = await get_users_by_permission(UPLOAD_REPORTS)
    revisores = await get_users_by_permission(REVIEW_REPORTS)

    return JSONResponse(content={
        "ok": True,
        "profesionales_disponibles": [
            {"id": uid, "nombre": info["nombre"]} for uid, info in profesionales.items()
        ],
        "revisores_disponibles": [
            {"id": uid, "nombre": info["nombre"]} for uid, info in revisores.items()
        ],
    })


@router.get("", status_code=200)
async def obtener_informes_tecnicos(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
    # Filtros
    fecha_desde: Optional[str] = Query(None, description="Fecha inicio creación (ISO date)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha fin creación (ISO date)"),
    aceptado: Optional[bool] = Query(None, description="True=con fecha_aceptacion, False=sin ella"),
    profesional_id: Optional[int] = Query(None, description="ID del profesional asignado"),
    expediente_radicado: Optional[str] = Query(None, description="Radicado del expediente (búsqueda parcial)"),
    tipo_informe: Optional[str] = Query(None, description="VISITA | SEGUIMIENTO"),
    # Paginación
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    user_id = int(verify_gateway_token(request)["user_id"])
    permisos = await verify_permission(user_id, ASSIGN_REPORTS)
    if not permisos:
        raise HTTPException(status_code=403, detail="No tienes permiso para gestionar informes técnicos")

    # Cargar usuarios con UPLOAD_REPORTS/REVIEW_REPORTS para enriquecer respuesta
    users = await get_users_by_permission(UPLOAD_REPORTS)
    revisores = await get_users_by_permission(REVIEW_REPORTS)

    # Los informes en modo MANUAL no pasan por asignación/revisión — no
    # pertenecen a esta tabla, se gestionan desde la etapa del expediente.
    stmt = select(InformeTecnico).where(InformeTecnico.modo == "FLUJO")

    if fecha_desde:
        try:
            stmt = stmt.where(InformeTecnico.fecha_creacion >= datetime.fromisoformat(fecha_desde))
        except ValueError:
            pass
    if fecha_hasta:
        try:
            stmt = stmt.where(InformeTecnico.fecha_creacion <= datetime.fromisoformat(fecha_hasta + "T23:59:59"))
        except ValueError:
            pass
    if aceptado is True:
        stmt = stmt.where(InformeTecnico.fecha_aceptacion_informe.isnot(None))
    elif aceptado is False:
        stmt = stmt.where(InformeTecnico.fecha_aceptacion_informe.is_(None))
    if profesional_id is not None:
        stmt = stmt.where(InformeTecnico.profesional_asignado_id == profesional_id)
    if expediente_radicado:
        subq = select(Expediente.id).where(Expediente.radicado.ilike(f"%{expediente_radicado}%"))
        stmt = stmt.where(InformeTecnico.expediente_id.in_(subq))
    if tipo_informe:
        stmt = stmt.where(InformeTecnico.tipo_informe == tipo_informe.upper())

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()

    offset = (page - 1) * limit
    stmt = stmt.order_by(InformeTecnico.fecha_creacion.desc()).limit(limit).offset(offset)
    informes = (await db.execute(stmt)).scalars().all()

    expediente_ids = list({inf.expediente_id for inf in informes})
    radicados_map: dict[int, str] = {}
    if expediente_ids:
        exp_result = await db.execute(
            select(Expediente.id, Expediente.radicado).where(Expediente.id.in_(expediente_ids))
        )
        radicados_map = {row.id: row.radicado for row in exp_result.all()}

    # Estado del proceso de revisión: tabla local, una sola consulta.
    procesos = await procesos_vigentes(db, [inf.id for inf in informes])

    data = []
    for inf in informes:
        profesional_info = users.get(inf.profesional_asignado_id) if inf.profesional_asignado_id else None
        revisor_info = revisores.get(inf.revisor_asignado_id) if inf.revisor_asignado_id else None
        data.append({
            "id": inf.id,
            "expediente_id": inf.expediente_id,
            "expediente_radicado": radicados_map.get(inf.expediente_id),
            "profesional_asignado_id": inf.profesional_asignado_id,
            "profesional_nombre": profesional_info["nombre"] if profesional_info else None,
            "revisor_asignado_id": inf.revisor_asignado_id,
            "revisor_nombre": revisor_info["nombre"] if revisor_info else None,
            "modo": inf.modo,
            "fecha_programacion_visita": _format_date(inf.fecha_programacion_visita),
            "fecha_recibido_informe": _format_date(inf.fecha_recibido_informe),
            "fecha_aceptacion_informe": _format_date(inf.fecha_aceptacion_informe),
            "documento_informe_id": inf.documento_informe_id,
            "tipo_informe": inf.tipo_informe,
            "fecha_creacion": _format_date(inf.fecha_creacion),
            "aceptado": inf.fecha_aceptacion_informe is not None,
            **resumen_proceso(procesos.get(inf.id), user_id, inf.revisor_asignado_id),
        })

    return JSONResponse(content={
        "ok": True,
        "data": data,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": max(1, -(-total // limit)),  # ceil division
        "profesionales_disponibles": [
            {"id": uid, "nombre": info["nombre"]}
            for uid, info in users.items()
        ],
        "revisores_disponibles": [
            {"id": uid, "nombre": info["nombre"]}
            for uid, info in revisores.items()
        ],
    })


# ─── POST /informes/{informe_id}/asignar ─────────────────────────────────────

@router.post("/{informe_id}/asignar", status_code=200)
async def asignar_profesional(
    request: Request,
    informe_id: int,
    body: AsignarProfesionalRequest,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Asigna profesional + revisor y crea el proceso de revisión propio
    (sin archivo -> pendiente_carga). Si ya hay un proceso vigente sin
    terminar devuelve 409 (usar PUT para reasignar). Si el vigente quedó
    finalizado (3 devoluciones) se archiva y se crea uno nuevo desde cero.
    """
    user_id = int(verify_gateway_token(request)["user_id"])
    if not await verify_permission(user_id, ASSIGN_REPORTS):
        raise HTTPException(status_code=403, detail="No tienes permiso para asignar informes técnicos")

    informe = await db.scalar(select(InformeTecnico).where(InformeTecnico.id == informe_id).with_for_update())
    await _validar_asignacion(informe, body)

    vigente = await proceso_vigente(db, informe_id, para_actualizar=True)
    if vigente is not None and not es_final(vigente):
        raise HTTPException(status_code=409, detail="Ya existe un proceso activo. Usa el endpoint de reasignación.")
    if vigente is not None and vigente.estado == FINALIZADO:
        vigente.activo = False
        await db.flush()

    radicado = await _radicado(db, informe.expediente_id)
    avisos = Avisos(informe_id)
    try:
        proceso = await crear_proceso_informe(
            db, informe,
            profesional_id=body.profesional_id, revisor_id=body.revisor_id,
            asignador_id=user_id, radicado=radicado, avisos=avisos,
        )
    except ReviewError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    _aplicar_datos_asignacion(informe, body)
    await _commit_asignacion(db)
    await avisos.enviar()

    logger.info(f"Informe {informe_id} asignado a profesional {body.profesional_id}, proceso={proceso.id}")
    return JSONResponse(content={
        "ok": True,
        "informe_id": informe_id,
        "proceso_id": proceso.id,
        "message": "Profesional asignado y proceso de revisión creado exitosamente",
    })


# ─── PUT /informes/{informe_id}/asignar ──────────────────────────────────────

@router.put("/{informe_id}/asignar", status_code=200)
async def reasignar_profesional(
    request: Request,
    informe_id: int,
    body: AsignarProfesionalRequest,
    db: AsyncSession = Depends(get_db_managed),
):
    """Reasigna: finaliza el proceso vigente (si lo hay) y crea uno nuevo, en la misma transacción."""
    user_id = int(verify_gateway_token(request)["user_id"])
    if not await verify_permission(user_id, ASSIGN_REPORTS):
        raise HTTPException(status_code=403, detail="No tienes permiso para asignar informes técnicos")

    informe = await db.scalar(select(InformeTecnico).where(InformeTecnico.id == informe_id).with_for_update())
    await _validar_asignacion(informe, body)

    radicado = await _radicado(db, informe.expediente_id)
    avisos = Avisos(informe_id)
    profesional_anterior = informe.profesional_asignado_id
    try:
        anterior = await cerrar_proceso_vigente(
            db, informe_id, usuario_id=user_id,
            descripcion=f"Proceso cerrado por reasignación a profesional {body.profesional_id}",
        )
        if anterior is not None and profesional_anterior and profesional_anterior != body.profesional_id:
            avisos.agregar(
                profesional_anterior,
                f"Expediente {radicado}\nInforme técnico reasignado, ya no eres responsable",
            )
        proceso = await crear_proceso_informe(
            db, informe,
            profesional_id=body.profesional_id, revisor_id=body.revisor_id,
            asignador_id=user_id, radicado=radicado, avisos=avisos, reasignacion=True,
        )
    except ReviewError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    _aplicar_datos_asignacion(informe, body)
    await _commit_asignacion(db)
    await avisos.enviar()

    logger.info(f"Informe {informe_id} reasignado a profesional {body.profesional_id}, nuevo proceso={proceso.id}")
    return JSONResponse(content={
        "ok": True,
        "informe_id": informe_id,
        "proceso_id": proceso.id,
        "message": "Profesional reasignado y nuevo proceso de revisión creado",
    })


# ─── PUT /informes/{informe_id}/cambiar-modo ─────────────────────────────────

@router.put("/{informe_id}/cambiar-modo", status_code=200)
async def cambiar_modo_informe(
    request: Request,
    informe_id: int,
    body: CambiarModoRequest,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Alterna el informe entre modo FLUJO (asignar profesional/revisor + ciclo
    de revisión) y modo MANUAL (cargue directo de un informe ya aceptado
    previamente, ej. expedientes históricos). Cambiar de modo borra por
    completo la información del modo anterior (archivo, fechas,
    profesional/revisor) — el frontend debe confirmarlo con el usuario antes
    de llamar este endpoint.
    """
    user_id = int(verify_gateway_token(request)["user_id"])
    if not await verify_permission(user_id, MANUAL_UPLOAD):
        raise HTTPException(status_code=403, detail="No tienes permiso para cambiar el modo de cargue")

    if body.modo not in ("FLUJO", "MANUAL"):
        raise HTTPException(status_code=400, detail="Modo inválido, debe ser FLUJO o MANUAL")

    informe = await db.scalar(select(InformeTecnico).where(InformeTecnico.id == informe_id).with_for_update())
    if not informe:
        raise HTTPException(status_code=404, detail="Informe técnico no encontrado")

    if informe.modo == body.modo:
        return JSONResponse(content={"ok": True, "informe_id": informe_id, "modo": informe.modo, "message": "Ya estaba en ese modo"})

    if body.modo == "MANUAL":
        # Viene de FLUJO: cerrar el proceso de revisión vigente. Sus versiones
        # conservan su uso de archivo (el historial no se borra); aquí solo se
        # libera el uso propio del informe más abajo.
        try:
            await cerrar_proceso_vigente(db, informe_id, usuario_id=user_id, descripcion="Informe cambiado a modo MANUAL")
        except ReviewError as e:
            await db.rollback()
            raise HTTPException(status_code=e.status_code, detail=e.detail)

    if informe.documento_informe_id:
        try:
            await decrement_file_usage([informe.documento_informe_id])
        except Exception as e:
            logger.warning(f"Error decrementando uso de archivo {informe.documento_informe_id}: {e}")

    informe.profesional_asignado_id = None
    informe.revisor_asignado_id = None
    informe.documento_informe_id = None
    informe.fecha_recibido_informe = None
    informe.fecha_aceptacion_informe = None
    informe.fecha_programacion_visita = None
    informe.modo = body.modo
    await db.execute(delete(InformeRecursoAfectado).where(InformeRecursoAfectado.informe_id == informe_id))

    await db.commit()

    logger.info(f"Informe {informe_id} cambiado a modo {informe.modo}")
    return JSONResponse(content={"ok": True, "informe_id": informe_id, "modo": informe.modo, "message": "Modo actualizado"})


# ─── POST /informes/{informe_id}/cargue-manual ───────────────────────────────

@router.post("/{informe_id}/cargue-manual", status_code=200)
async def cargue_manual_informe(
    request: Request,
    informe_id: int,
    body: CargueManualRequest,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Registra el cargue manual (histórico) de un informe técnico ya aceptado
    previamente fuera del sistema. El archivo ya debe estar subido en
    app-docs (vía /files/upload) — aquí solo se vincula su file_id.
    """
    user_id = verify_gateway_token(request)["user_id"]
    permisos = await verify_permission(user_id, MANUAL_UPLOAD)
    if not permisos:
        raise HTTPException(status_code=403, detail="No tienes permiso para cargar informes manualmente")

    result = await db.execute(select(InformeTecnico).where(InformeTecnico.id == informe_id))
    informe = result.scalar_one_or_none()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe técnico no encontrado")

    if informe.modo != "MANUAL":
        raise HTTPException(status_code=400, detail="El informe no está en modo de cargue manual. Cambia el modo primero.")

    try:
        fecha_recibido = date.fromisoformat(body.fecha_recibido)
        fecha_aceptacion = date.fromisoformat(body.fecha_aceptacion)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido, debe ser YYYY-MM-DD")

    if fecha_aceptacion < fecha_recibido:
        raise HTTPException(status_code=400, detail="La fecha de aceptación no puede ser anterior a la fecha de recibido")

    if body.profesional_id is not None and body.profesional_id == body.revisor_id:
        raise HTTPException(status_code=400, detail="El profesional y el revisor deben ser personas distintas")

    fecha_programacion = None
    if body.fecha_programacion_visita:
        try:
            fecha_programacion = date.fromisoformat(body.fecha_programacion_visita)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha de programación inválido")

    if body.profesional_id is not None:
        if not await verify_permission(body.profesional_id, UPLOAD_REPORTS):
            raise HTTPException(status_code=400, detail="El usuario seleccionado no tiene permiso de infraccion_informes_subir")

    if body.revisor_id is not None:
        if not await verify_permission(body.revisor_id, REVIEW_REPORTS):
            raise HTTPException(status_code=400, detail="El usuario seleccionado no tiene permiso de infraccion_informes_revisar")

    # Solo tocar el contador de uso si el archivo realmente cambió — reenviar
    # el mismo file_id (ej. edición que solo cambia fechas) no debe inflar el
    # contador ni decrementarlo de más.
    if informe.documento_informe_id != body.file_id:
        # El informe aceptado se une al PDF del expediente: debe ser PDF.
        file_info = await get_file_info(body.file_id)
        if not file_info.get("ok"):
            raise HTTPException(status_code=400, detail="No se encontró el archivo cargado")
        if file_info["data"].get("content_type") != "application/pdf":
            raise HTTPException(status_code=400, detail="El informe técnico debe cargarse en PDF")
        if informe.documento_informe_id:
            try:
                await decrement_file_usage([informe.documento_informe_id])
            except Exception as e:
                logger.warning(f"Error decrementando uso de archivo previo {informe.documento_informe_id}: {e}")
        await increment_file_usage([body.file_id])

    informe.documento_informe_id = body.file_id
    informe.fecha_recibido_informe = fecha_recibido
    informe.fecha_aceptacion_informe = fecha_aceptacion
    informe.fecha_programacion_visita = fecha_programacion
    informe.profesional_asignado_id = body.profesional_id
    informe.revisor_asignado_id = body.revisor_id

    await db.commit()

    logger.info(f"Informe {informe_id} cargado manualmente por usuario {user_id}, file_id={body.file_id}")
    return JSONResponse(content={
        "ok": True,
        "informe_id": informe_id,
        "message": "Informe técnico cargado y aceptado correctamente",
    })


# ─── GET /informes/mios ──────────────────────────────────────────────────────

@router.get("/mios", status_code=200)
async def obtener_mis_informes(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Informes técnicos donde el usuario actual es el profesional asignado y/o
    el revisor asignado — para la pestaña "Mis Informes" (sin necesidad de
    ASSIGN_REPORTS, que es del líder que asigna, no de quien sube/revisa).
    El estado del proceso sale de la tabla local (sin llamar a app-docs).
    """
    user_id = int(verify_gateway_token(request)["user_id"])

    puede_subir = await verify_permission(user_id, UPLOAD_REPORTS)
    puede_revisar = await verify_permission(user_id, REVIEW_REPORTS)
    if not (puede_subir or puede_revisar):
        raise HTTPException(status_code=403, detail="No tienes permiso para ver esta sección")

    condiciones = []
    if puede_subir:
        condiciones.append(InformeTecnico.profesional_asignado_id == user_id)
    if puede_revisar:
        condiciones.append(InformeTecnico.revisor_asignado_id == user_id)

    stmt = (
        select(InformeTecnico)
        .where(or_(*condiciones))
        .order_by(InformeTecnico.fecha_creacion.desc())
    )
    informes = (await db.execute(stmt)).scalars().all()

    expediente_ids = list({inf.expediente_id for inf in informes})
    radicados_map: dict[int, str] = {}
    if expediente_ids:
        exp_result = await db.execute(
            select(Expediente.id, Expediente.radicado).where(Expediente.id.in_(expediente_ids))
        )
        radicados_map = {row.id: row.radicado for row in exp_result.all()}

    informe_ids = [inf.id for inf in informes]
    informes_con_matriz: set = set()
    if informe_ids:
        filas_result = await db.execute(
            select(InformeRecursoAfectado.informe_id)
            .where(InformeRecursoAfectado.informe_id.in_(informe_ids))
            .distinct()
        )
        informes_con_matriz = {row[0] for row in filas_result.all()}

    procesos = await procesos_vigentes(db, informe_ids)

    data = []
    for inf in informes:
        data.append({
            "id": inf.id,
            "expediente_id": inf.expediente_id,
            "expediente_radicado": radicados_map.get(inf.expediente_id),
            "tipo_informe": inf.tipo_informe,
            "modo": inf.modo,
            "soy_profesional": inf.profesional_asignado_id == user_id,
            "soy_revisor": inf.revisor_asignado_id == user_id,
            "fecha_programacion_visita": _format_date(inf.fecha_programacion_visita),
            "fecha_recibido_informe": _format_date(inf.fecha_recibido_informe),
            "fecha_aceptacion_informe": _format_date(inf.fecha_aceptacion_informe),
            "documento_informe_id": inf.documento_informe_id,
            "aceptado": inf.fecha_aceptacion_informe is not None,
            "puede_diligenciar_matriz": (
                inf.tipo_informe == "VISITA"
                and inf.fecha_aceptacion_informe is not None
                and inf.profesional_asignado_id == user_id
            ),
            "tiene_matriz": inf.id in informes_con_matriz,
            **resumen_proceso(procesos.get(inf.id), user_id, inf.revisor_asignado_id),
        })

    return JSONResponse(content={"ok": True, "data": data})


# ─── Matriz de recursos afectados ─────────────────────────────────────────────

async def _validar_permiso_matriz(informe: InformeTecnico, user_id: int) -> None:
    if informe.tipo_informe != "VISITA":
        raise HTTPException(status_code=400, detail="La matriz de recursos afectados solo aplica a informes de VISITA")
    if informe.fecha_aceptacion_informe is None:
        raise HTTPException(status_code=400, detail="El informe aún no ha sido aceptado")

    if informe.profesional_asignado_id == user_id:
        return

    # El rol de cargue manual (infraccion_cargue) puede diligenciar la matriz
    # directamente desde la etapa del expediente, pero solo si el informe
    # también se cargó en modo manual — si fue por flujo, solo el profesional
    # asignado la diligencia (desde "Mis Informes").
    if informe.modo == "MANUAL" and await verify_permission(user_id, MANUAL_UPLOAD):
        return

    raise HTTPException(status_code=403, detail="No tienes permiso para diligenciar esta matriz")


@router.get("/{informe_id}/recursos", status_code=200)
async def obtener_matriz_recursos(
    request: Request,
    informe_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = verify_gateway_token(request)["user_id"]

    informe = await db.scalar(select(InformeTecnico).where(InformeTecnico.id == informe_id))
    if not informe:
        raise HTTPException(status_code=404, detail="Informe técnico no encontrado")

    if informe.tipo_informe != "VISITA" or informe.fecha_aceptacion_informe is None:
        raise HTTPException(status_code=400, detail="La matriz de recursos afectados solo aplica a informes de VISITA ya aceptados")

    if informe.profesional_asignado_id != user_id and informe.revisor_asignado_id != user_id:
        es_asignador = await verify_permission(user_id, ASSIGN_REPORTS)
        expediente = await db.scalar(select(Expediente).where(Expediente.id == informe.expediente_id))
        es_responsable = expediente is not None and expediente.abogado_responsable_id == user_id
        if not (es_asignador or es_responsable):
            raise HTTPException(status_code=403, detail="Sin permiso para consultar esta matriz")

    filas = (await db.execute(
        select(InformeRecursoAfectado).where(InformeRecursoAfectado.informe_id == informe_id)
    )).scalars().all()
    filas_map = {f.recurso: f for f in filas}

    data = [
        {
            "recurso": recurso,
            "magnitud": filas_map[recurso].magnitud if recurso in filas_map else None,
            "reversibilidad": filas_map[recurso].reversibilidad if recurso in filas_map else None,
            "no_existe": filas_map[recurso].no_existe if recurso in filas_map else False,
        }
        for recurso in RECURSOS_MATRIZ
    ]

    return JSONResponse(content={"ok": True, "data": data})


class FilaRecursoRequest(BaseModel):
    recurso: str
    magnitud: Optional[str] = None
    reversibilidad: Optional[str] = None
    no_existe: bool = False


class MatrizRecursosRequest(BaseModel):
    filas: list[FilaRecursoRequest]


@router.put("/{informe_id}/recursos", status_code=200)
async def actualizar_matriz_recursos(
    request: Request,
    informe_id: int,
    body: MatrizRecursosRequest,
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = verify_gateway_token(request)["user_id"]

    informe = await db.scalar(select(InformeTecnico).where(InformeTecnico.id == informe_id))
    if not informe:
        raise HTTPException(status_code=404, detail="Informe técnico no encontrado")

    await _validar_permiso_matriz(informe, user_id)

    for fila in body.filas:
        if fila.recurso not in RECURSOS_MATRIZ:
            raise HTTPException(status_code=400, detail=f"Recurso inválido: {fila.recurso}")
        if fila.magnitud and fila.magnitud not in ("LEVE", "MODERADO", "GRAVE"):
            raise HTTPException(status_code=400, detail=f"Magnitud inválida: {fila.magnitud}")
        if fila.reversibilidad and fila.reversibilidad not in ("REVERSIBLE", "IRREVERSIBLE"):
            raise HTTPException(status_code=400, detail=f"Reversibilidad inválida: {fila.reversibilidad}")
        if not fila.no_existe and not (fila.magnitud and fila.reversibilidad):
            raise HTTPException(
                status_code=400,
                detail=f"El recurso {fila.recurso} debe marcar 'no existe' o tener magnitud y reversibilidad",
            )

    existentes = (await db.execute(
        select(InformeRecursoAfectado).where(InformeRecursoAfectado.informe_id == informe_id)
    )).scalars().all()
    existentes_map = {f.recurso: f for f in existentes}

    for fila in body.filas:
        actual = existentes_map.get(fila.recurso)
        if actual:
            actual.magnitud = None if fila.no_existe else fila.magnitud
            actual.reversibilidad = None if fila.no_existe else fila.reversibilidad
            actual.no_existe = fila.no_existe
        else:
            db.add(InformeRecursoAfectado(
                informe_id=informe_id,
                recurso=fila.recurso,
                magnitud=None if fila.no_existe else fila.magnitud,
                reversibilidad=None if fila.no_existe else fila.reversibilidad,
                no_existe=fila.no_existe,
            ))

    await db.commit()

    logger.info(f"Matriz de recursos afectados actualizada para informe {informe_id} por usuario {user_id}")
    return JSONResponse(content={"ok": True, "message": "Matriz de recursos afectados guardada correctamente"})

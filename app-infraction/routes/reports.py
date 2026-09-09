from fastapi import Request, APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo

_BOGOTA = ZoneInfo("America/Bogota")
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional
import logging
import os

from db.deps import get_db_managed
from db.models.informe_tecnico import InformeTecnico
from db.models.informe_documento import InformeDocumento
from db.models.informe_recurso_afectado import InformeRecursoAfectado, RECURSOS_MATRIZ
from db.models.expediente import Expediente

from core.permission import Permission
ASSIGN_REPORTS = Permission.ASSIGN_REPORTS
UPLOAD_REPORTS = Permission.UPLOAD_REPORTS
REVIEW_REPORTS = Permission.REVIEW_REPORTS
MANUAL_UPLOAD = Permission.MANUAL_UPLOAD

# UTILIDADES
router = APIRouter()
load_dotenv()
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://api-gateway:8000")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from utils.verify_token import verify_gateway_token
from utils.log import insert_log
from services.notification import create_notification
from services.users import get_users_by_permission, get_user_info, verify_permission
from services.docs_service import create_doc_for_professional, finalize_doc_as_rejected, get_doc_detail
from services.docs import increment_file_usage, decrement_file_usage


# ─── SCHEMAS ────────────────────────────────────────────────────────────────

class AsignarProfesionalRequest(BaseModel):
    profesional_id: int
    revisor_id: int
    fecha_programacion_visita: Optional[str] = None  # ISO date string


class SyncDocRequest(BaseModel):
    pass  # vacío — el sync lo hace el backend consultando app-docs


class SwitchModeRequest(BaseModel):
    modo: str  # 'FLUJO' | 'MANUAL'


class ManualUploadRequest(BaseModel):
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


async def _get_active_informe_documento(db: AsyncSession, informe_id: int) -> Optional[InformeDocumento]:
    stmt = select(InformeDocumento).where(
        and_(InformeDocumento.informe_id == informe_id, InformeDocumento.activo == True)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ─── GET /reports ─────────────────────────────────────────────────────────────

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
    user_id = verify_gateway_token(request)["user_id"]
    permisos = await verify_permission(user_id, ASSIGN_REPORTS)
    if not permisos:
        raise HTTPException(status_code=403, detail="No tienes permiso para gestionar informes técnicos")

    # Cargar usuarios con UPLOAD_REPORTS/REVIEW_REPORTS para enriquecer respuesta
    users = await get_users_by_permission(UPLOAD_REPORTS)
    revisores = await get_users_by_permission(REVIEW_REPORTS)

    # Los informes en modo MANUAL no pasan por asignación/revisión — no
    # pertenecen a esta tabla, se gestionan desde la etapa del expediente.
    stmt = select(InformeTecnico).where(InformeTecnico.modo == "FLUJO")

    # Filtros
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

    # Conteo total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Paginación
    offset = (page - 1) * limit
    stmt = stmt.order_by(InformeTecnico.fecha_creacion.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    informes = result.scalars().all()

    # Cargar radicados de expedientes en batch
    expediente_ids = list({inf.expediente_id for inf in informes})
    radicados_map: dict[int, str] = {}
    if expediente_ids:
        exp_result = await db.execute(
            select(Expediente.id, Expediente.radicado).where(Expediente.id.in_(expediente_ids))
        )
        radicados_map = {row.id: row.radicado for row in exp_result.all()}

    # Enriquecer con estado del proceso docs y nombre del profesional
    data = []
    for inf in informes:
        profesional_info = users.get(inf.profesional_asignado_id) if inf.profesional_asignado_id else None
        revisor_info = revisores.get(inf.revisor_asignado_id) if inf.revisor_asignado_id else None

        # Proceso activo en app-docs
        informe_doc = await _get_active_informe_documento(db, inf.id)

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
            "docs_documento_id": informe_doc.docs_documento_id if informe_doc else None,
            "proceso_activo": informe_doc is not None,
            "aceptado": inf.fecha_aceptacion_informe is not None,
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


# ─── POST /reports/{informe_id}/assign ───────────────────────────────────────

@router.post("/{informe_id}/assign", status_code=200)
async def asignar_profesional(
    request: Request,
    informe_id: int,
    body: AsignarProfesionalRequest,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Asigna un profesional al informe técnico y crea el proceso de documentos en app-docs.
    Si ya hay un proceso activo, devuelve error (usar PUT para reasignar).
    """
    user_id = verify_gateway_token(request)["user_id"]
    permisos = await verify_permission(user_id, ASSIGN_REPORTS)
    if not permisos:
        raise HTTPException(status_code=403, detail="No tienes permiso para asignar informes técnicos")

    # Obtener informe
    result = await db.execute(select(InformeTecnico).where(InformeTecnico.id == informe_id))
    informe = result.scalar_one_or_none()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe técnico no encontrado")

    if informe.modo != "FLUJO":
        raise HTTPException(status_code=400, detail="El informe está en modo de cargue manual, cambia el modo primero")

    # No permitir si ya fue aceptado
    if informe.fecha_aceptacion_informe is not None:
        raise HTTPException(status_code=400, detail="El informe ya fue aceptado, no se puede reasignar")

    # Verificar que no haya proceso activo
    informe_doc_activo = await _get_active_informe_documento(db, informe_id)
    if informe_doc_activo:
        raise HTTPException(status_code=409, detail="Ya existe un proceso activo. Usa el endpoint de reasignación.")

    # Verificar que el profesional tiene el permiso correcto
    perm_profesional = await verify_permission(body.profesional_id, UPLOAD_REPORTS)
    if not perm_profesional:
        raise HTTPException(status_code=400, detail="El usuario no tiene permiso de infraccion_informes_subir")

    # Verificar que el revisor tiene el permiso correcto
    perm_revisor = await verify_permission(body.revisor_id, REVIEW_REPORTS)
    if not perm_revisor:
        raise HTTPException(status_code=400, detail="El usuario seleccionado no tiene permiso de infraccion_informes_revisar")

    if body.revisor_id == body.profesional_id:
        raise HTTPException(status_code=400, detail="El profesional y el revisor deben ser personas distintas")

    # Obtener nombre del expediente para el nombre del documento
    result_exp = await db.execute(select(Expediente).where(Expediente.id == informe.expediente_id))
    expediente = result_exp.scalar_one_or_none()
    nombre_doc = f"Informe {informe.tipo_informe or 'Técnico'} - Expediente {expediente.radicado if expediente else informe.expediente_id}"

    # Crear proceso en app-docs (service-to-service)
    create_result = await create_doc_for_professional(
        nombre=nombre_doc,
        descripcion=f"Informe técnico de {informe.tipo_informe or 'VISITA'} para el expediente. Profesional responsable del cargue.",
        creador_id=body.profesional_id,
        revisor_id=body.revisor_id,
    )

    if not create_result["ok"]:
        raise HTTPException(status_code=502, detail=f"Error creando proceso en app-docs: {create_result.get('message')}")

    docs_documento_id = create_result["documento_id"]

    # Actualizar informe
    informe.profesional_asignado_id = body.profesional_id
    informe.revisor_asignado_id = body.revisor_id
    if body.fecha_programacion_visita:
        try:
            informe.fecha_programacion_visita = date.fromisoformat(body.fecha_programacion_visita)
        except ValueError:
            pass

    # Crear registro en tabla bridge
    informe_doc = InformeDocumento(
        informe_id=informe_id,
        docs_documento_id=docs_documento_id,
        activo=True,
    )
    db.add(informe_doc)
    await db.commit()

    # Notificar al profesional — tipo "documento" para que el botón navegue directo al doc
    try:
        await create_notification(
            mensaje=f"Informe técnico de {informe.tipo_informe or 'VISITA'} asignado — expediente {expediente.radicado if expediente else informe.expediente_id}",
            id_vinculada=str(docs_documento_id),
            tipo="documento",
            usuario_id=body.profesional_id,
        )
    except Exception as e:
        logger.warning(f"Error enviando notificación al profesional: {e}")

    logger.info(f"Informe {informe_id} asignado a profesional {body.profesional_id}, docs_id={docs_documento_id}")
    return JSONResponse(content={
        "ok": True,
        "informe_id": informe_id,
        "docs_documento_id": docs_documento_id,
        "message": "Profesional asignado y proceso de documentos creado exitosamente",
    })


# ─── PUT /reports/{informe_id}/assign ────────────────────────────────────────

@router.put("/{informe_id}/assign", status_code=200)
async def reasignar_profesional(
    request: Request,
    informe_id: int,
    body: AsignarProfesionalRequest,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Reasigna el profesional: finaliza el proceso activo en app-docs y crea uno nuevo.
    """
    user_id = verify_gateway_token(request)["user_id"]
    permisos = await verify_permission(user_id, ASSIGN_REPORTS)
    if not permisos:
        raise HTTPException(status_code=403, detail="No tienes permiso para asignar informes técnicos")

    result = await db.execute(select(InformeTecnico).where(InformeTecnico.id == informe_id))
    informe = result.scalar_one_or_none()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe técnico no encontrado")

    if informe.modo != "FLUJO":
        raise HTTPException(status_code=400, detail="El informe está en modo de cargue manual, cambia el modo primero")

    if informe.fecha_aceptacion_informe is not None:
        raise HTTPException(status_code=400, detail="El informe ya fue aceptado, no se puede reasignar")

    # Verificar permiso del nuevo profesional
    perm_profesional = await verify_permission(body.profesional_id, UPLOAD_REPORTS)
    if not perm_profesional:
        raise HTTPException(status_code=400, detail="El usuario no tiene permiso de infraccion_informes_subir")

    # Verificar permiso del nuevo revisor
    perm_revisor = await verify_permission(body.revisor_id, REVIEW_REPORTS)
    if not perm_revisor:
        raise HTTPException(status_code=400, detail="El usuario seleccionado no tiene permiso de infraccion_informes_revisar")

    if body.revisor_id == body.profesional_id:
        raise HTTPException(status_code=400, detail="El profesional y el revisor deben ser personas distintas")

    # Finalizar proceso activo anterior
    informe_doc_activo = await _get_active_informe_documento(db, informe_id)
    if informe_doc_activo:
        finalize_result = await finalize_doc_as_rejected(informe_doc_activo.docs_documento_id)
        if not finalize_result["ok"]:
            logger.warning(f"No se pudo finalizar proceso anterior {informe_doc_activo.docs_documento_id}: {finalize_result.get('message')}")
        informe_doc_activo.activo = False

        # Notificar al profesional anterior que fue reasignado
        if informe.profesional_asignado_id and informe.profesional_asignado_id != body.profesional_id:
            try:
                result_exp = await db.execute(select(Expediente).where(Expediente.id == informe.expediente_id))
                expediente_prev = result_exp.scalar_one_or_none()
                await create_notification(
                    mensaje=f"Informe técnico reasignado — ya no eres responsable del expediente {expediente_prev.radicado if expediente_prev else informe.expediente_id}",
                    id_vinculada=str(informe_id),
                    tipo="informe_tecnico",
                    usuario_id=informe.profesional_asignado_id,
                )
            except Exception as e:
                logger.warning(f"Error notificando al profesional anterior: {e}")

    # Obtener expediente para el nombre del documento
    result_exp = await db.execute(select(Expediente).where(Expediente.id == informe.expediente_id))
    expediente = result_exp.scalar_one_or_none()
    nombre_doc = f"Informe {informe.tipo_informe or 'Técnico'} - Expediente {expediente.radicado if expediente else informe.expediente_id}"

    # Crear nuevo proceso en app-docs
    create_result = await create_doc_for_professional(
        nombre=nombre_doc,
        descripcion=f"Informe técnico de {informe.tipo_informe or 'VISITA'} (reasignación). Profesional responsable del cargue.",
        creador_id=body.profesional_id,
        revisor_id=body.revisor_id,
    )

    if not create_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=502, detail=f"Error creando proceso en app-docs: {create_result.get('message')}")

    docs_documento_id = create_result["documento_id"]

    # Actualizar informe
    informe.profesional_asignado_id = body.profesional_id
    informe.revisor_asignado_id = body.revisor_id
    if body.fecha_programacion_visita:
        try:
            informe.fecha_programacion_visita = date.fromisoformat(body.fecha_programacion_visita)
        except ValueError:
            pass

    # Nuevo registro en bridge
    nuevo_informe_doc = InformeDocumento(
        informe_id=informe_id,
        docs_documento_id=docs_documento_id,
        activo=True,
    )
    db.add(nuevo_informe_doc)
    await db.commit()

    # Notificar al nuevo profesional — tipo "documento" para navegar directo al doc
    try:
        await create_notification(
            mensaje=f"Informe técnico de {informe.tipo_informe or 'VISITA'} asignado — expediente {expediente.radicado if expediente else informe.expediente_id}",
            id_vinculada=str(docs_documento_id),
            tipo="documento",
            usuario_id=body.profesional_id,
        )
    except Exception as e:
        logger.warning(f"Error enviando notificación al nuevo profesional: {e}")

    logger.info(f"Informe {informe_id} reasignado a profesional {body.profesional_id}, nuevo docs_id={docs_documento_id}")
    return JSONResponse(content={
        "ok": True,
        "informe_id": informe_id,
        "docs_documento_id": docs_documento_id,
        "message": "Profesional reasignado y nuevo proceso de documentos creado",
    })


# ─── SYNC (compartido) ────────────────────────────────────────────────────────

def _parse_date_bogota(iso_str: str) -> date | None:
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_BOGOTA).date()
    except (ValueError, TypeError):
        return None


async def _sincronizar_informe(
    db: AsyncSession,
    informe: InformeTecnico,
    informe_doc: InformeDocumento,
) -> dict:
    """
    Consulta el estado del documento en app-docs y actualiza el InformeTecnico
    si ya fue aprobado o rechazado. Devuelve el payload de respuesta.
    Nota: el estado de "devuelto" en app-docs se llama 'rechazado' (ver
    app-docs/routes/revision.py) — antes se comparaba mal contra 'devuelto'
    y esta rama nunca se ejecutaba.
    """
    doc_detail = await get_doc_detail(informe_doc.docs_documento_id)
    if not doc_detail.get("ok"):
        return {"ok": False, "message": f"Error consultando app-docs: {doc_detail.get('message')}", "estado": None}

    estado_doc = doc_detail.get("estado")

    result_exp = await db.execute(select(Expediente).where(Expediente.id == informe.expediente_id))
    expediente = result_exp.scalar_one_or_none()
    radicado = expediente.radicado if expediente else str(informe.expediente_id)

    if estado_doc == "rechazado":
        try:
            await create_notification(
                mensaje=f"Informe técnico devuelto — expediente {radicado}, revisa observaciones",
                id_vinculada=str(informe.id),
                tipo="informe_tecnico",
                usuario_id=informe.profesional_asignado_id,
            )
        except Exception as e:
            logger.warning(f"Error notificando devolución al profesional: {e}")
        return {
            "ok": False,
            "message": "El documento fue devuelto. Se notificó al profesional.",
            "estado": estado_doc,
        }

    if estado_doc == "finalizado":
        # 3 devoluciones seguidas: app-docs cierra el proceso solo. Se marca
        # inactivo en app-infraction para que se pueda reasignar de cero.
        informe_doc.activo = False
        await db.commit()
        try:
            await create_notification(
                mensaje=f"Informe técnico rechazado 3 veces — expediente {radicado}, reasignar",
                id_vinculada=str(informe.id),
                tipo="informe_tecnico",
                usuario_id=informe.revisor_asignado_id or informe.profesional_asignado_id,
            )
        except Exception as e:
            logger.warning(f"Error notificando finalización: {e}")
        return {
            "ok": False,
            "message": "El documento fue rechazado 3 veces y el proceso se cerró. Reasigna el informe.",
            "estado": estado_doc,
        }

    if estado_doc != "aprobado":
        return {
            "ok": False,
            "message": f"El documento aún no está aprobado. Estado actual: {estado_doc}",
            "estado": estado_doc,
        }

    ultima_version = doc_detail.get("ultima_version")
    fecha_subida = _parse_date_bogota(ultima_version["fecha_subida"]) if ultima_version and ultima_version.get("fecha_subida") else None
    fecha_aprobacion = _parse_date_bogota(doc_detail["fecha_ultima_actualizacion"]) if doc_detail.get("fecha_ultima_actualizacion") else None

    informe.fecha_aceptacion_informe = fecha_aprobacion or date.today()
    informe.fecha_recibido_informe = fecha_subida or fecha_aprobacion or date.today()
    file_hash_id = ultima_version.get("file_hash_id") if ultima_version else None
    informe.documento_informe_id = file_hash_id or informe_doc.docs_documento_id

    informe_doc.activo = False
    await db.commit()

    try:
        await create_notification(
            mensaje=f"Informe técnico aceptado — expediente {radicado}",
            id_vinculada=str(informe.id),
            tipo="informe_tecnico",
            usuario_id=informe.profesional_asignado_id,
        )
        if expediente and expediente.abogado_responsable_id:
            await create_notification(
                mensaje=f"Informe técnico aceptado — expediente {radicado}, disponible para revisión",
                id_vinculada=str(informe.id),
                tipo="informe_tecnico",
                usuario_id=expediente.abogado_responsable_id,
            )
    except Exception as e:
        logger.warning(f"Error notificando aprobación: {e}")

    logger.info(f"Informe {informe.id} sincronizado como aprobado")
    return {
        "ok": True,
        "informe_id": informe.id,
        "fecha_aceptacion": _format_date(informe.fecha_aceptacion_informe),
        "fecha_recibido": _format_date(informe.fecha_recibido_informe),
        "message": "Informe técnico actualizado como aceptado",
    }


# ─── PUT /reports/{informe_id}/sync ──────────────────────────────────────────

@router.put("/{informe_id}/sync", status_code=200)
async def sincronizar_informe_aprobado(
    request: Request,
    informe_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Sincroniza el InformeTecnico con el documento aprobado/rechazado en app-docs.
    Se llama desde el frontend luego de que se revisa el documento.
    """
    user_id = verify_gateway_token(request)["user_id"]
    permisos = await verify_permission(user_id, ASSIGN_REPORTS)
    if not permisos:
        raise HTTPException(status_code=403, detail="No tienes permiso para sincronizar informes")

    result = await db.execute(select(InformeTecnico).where(InformeTecnico.id == informe_id))
    informe = result.scalar_one_or_none()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe técnico no encontrado")

    informe_doc = await _get_active_informe_documento(db, informe_id)
    if not informe_doc:
        raise HTTPException(status_code=404, detail="No hay proceso de documento activo para este informe")

    payload = await _sincronizar_informe(db, informe, informe_doc)
    return JSONResponse(content=payload)


# ─── PUT /reports/sync-by-doc/{docs_documento_id} ────────────────────────────

@router.put("/sync-by-doc/{docs_documento_id}", status_code=200)
async def sincronizar_informe_por_documento(
    request: Request,
    docs_documento_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Igual que /sync pero identificando el informe por el id del documento en
    app-docs. Pensado para llamarse best-effort desde el módulo genérico de
    Documentos (app-documentos) justo después de revisar cualquier documento:
    si ese documento no corresponde a un informe técnico, responde ok=False
    sin error, ya que la mayoría de documentos no lo son.

    Necesario porque el revisor de un informe técnico ya no es siempre quien
    lo asignó — puede revisar desde el módulo de Documentos, donde antes
    nunca se disparaba esta sincronización.
    """
    user_id = verify_gateway_token(request)["user_id"]

    result = await db.execute(
        select(InformeDocumento).where(
            and_(InformeDocumento.docs_documento_id == docs_documento_id, InformeDocumento.activo == True)
        )
    )
    informe_doc = result.scalar_one_or_none()
    if not informe_doc:
        return JSONResponse(content={"ok": False, "message": "No es un informe técnico o ya fue sincronizado"})

    result_inf = await db.execute(select(InformeTecnico).where(InformeTecnico.id == informe_doc.informe_id))
    informe = result_inf.scalar_one_or_none()
    if not informe:
        return JSONResponse(content={"ok": False, "message": "Informe técnico no encontrado"})

    es_asignador = await verify_permission(user_id, ASSIGN_REPORTS)
    es_revisor_asignado = informe.revisor_asignado_id is not None and int(informe.revisor_asignado_id) == int(user_id)
    if not (es_asignador or es_revisor_asignado):
        raise HTTPException(status_code=403, detail="No tienes permiso para sincronizar este informe")

    payload = await _sincronizar_informe(db, informe, informe_doc)
    return JSONResponse(content=payload)


# ─── PUT /reports/{informe_id}/switch-mode ───────────────────────────────────

@router.put("/{informe_id}/switch-mode", status_code=200)
async def cambiar_modo_informe(
    request: Request,
    informe_id: int,
    body: SwitchModeRequest,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Alterna el informe entre modo FLUJO (asignar profesional/revisor + ciclo
    de revisión en app-docs) y modo MANUAL (cargue directo de un informe ya
    aceptado previamente, ej. expedientes históricos). Cambiar de modo borra
    por completo la información del modo anterior (archivo, fechas,
    profesional/revisor) — el frontend debe confirmarlo con el usuario antes
    de llamar este endpoint.
    """
    user_id = verify_gateway_token(request)["user_id"]
    permisos = await verify_permission(user_id, MANUAL_UPLOAD)
    if not permisos:
        raise HTTPException(status_code=403, detail="No tienes permiso para cambiar el modo de cargue")

    if body.modo not in ("FLUJO", "MANUAL"):
        raise HTTPException(status_code=400, detail="Modo inválido, debe ser FLUJO o MANUAL")

    result = await db.execute(select(InformeTecnico).where(InformeTecnico.id == informe_id))
    informe = result.scalar_one_or_none()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe técnico no encontrado")

    if informe.modo == body.modo:
        return JSONResponse(content={"ok": True, "informe_id": informe_id, "modo": informe.modo, "message": "Ya estaba en ese modo"})

    if body.modo == "MANUAL":
        # Viene de FLUJO: cerrar cualquier proceso de app-docs y liberar el archivo si ya se había subido.
        informe_doc = await _get_active_informe_documento(db, informe_id)
        if informe_doc:
            doc_detail = await get_doc_detail(informe_doc.docs_documento_id)
            if doc_detail.get("ok"):
                ultima_version = doc_detail.get("ultima_version")
                file_hash_id = ultima_version.get("file_hash_id") if ultima_version else None
                if file_hash_id:
                    try:
                        await decrement_file_usage([file_hash_id])
                    except Exception as e:
                        logger.warning(f"Error decrementando uso de archivo {file_hash_id}: {e}")
            finalize_result = await finalize_doc_as_rejected(informe_doc.docs_documento_id)
            if not finalize_result["ok"]:
                logger.warning(f"No se pudo finalizar proceso {informe_doc.docs_documento_id}: {finalize_result.get('message')}")
            informe_doc.activo = False

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
        informe.modo = "MANUAL"
    else:
        # Viene de MANUAL: liberar el archivo cargado a mano, si lo hay.
        if informe.documento_informe_id:
            try:
                await decrement_file_usage([informe.documento_informe_id])
            except Exception as e:
                logger.warning(f"Error decrementando uso de archivo {informe.documento_informe_id}: {e}")

        informe.documento_informe_id = None
        informe.fecha_recibido_informe = None
        informe.fecha_aceptacion_informe = None
        informe.fecha_programacion_visita = None
        informe.profesional_asignado_id = None
        informe.revisor_asignado_id = None
        informe.modo = "FLUJO"

    await db.commit()

    logger.info(f"Informe {informe_id} cambiado a modo {informe.modo}")
    return JSONResponse(content={"ok": True, "informe_id": informe_id, "modo": informe.modo, "message": "Modo actualizado"})


# ─── POST /reports/{informe_id}/manual-upload ────────────────────────────────

@router.post("/{informe_id}/manual-upload", status_code=200)
async def cargue_manual_informe(
    request: Request,
    informe_id: int,
    body: ManualUploadRequest,
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


@router.get("/{informe_id}/doc-process", status_code=200)
async def obtener_proceso_documento(
    request: Request,
    informe_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Devuelve el ID del proceso de app-docs activo para el informe.
    El frontend usa este ID para abrir DocumentoDetalleModal.
    """
    user_id = verify_gateway_token(request)["user_id"]

    informe = await db.scalar(select(InformeTecnico).where(InformeTecnico.id == informe_id))
    if not informe:
        raise HTTPException(status_code=404, detail="Informe técnico no encontrado")

    es_asignador = await verify_permission(user_id, ASSIGN_REPORTS)
    es_involucrado = int(user_id) in (informe.profesional_asignado_id, informe.revisor_asignado_id)
    if not (es_asignador or es_involucrado):
        raise HTTPException(status_code=403, detail="Sin permiso")

    informe_doc = await _get_active_informe_documento(db, informe_id)
    if not informe_doc:
        return JSONResponse(content={"ok": True, "proceso_activo": False, "docs_documento_id": None})

    return JSONResponse(content={
        "ok": True,
        "proceso_activo": True,
        "docs_documento_id": informe_doc.docs_documento_id,
        "informe_doc_id": informe_doc.id,
    })


# ─── GET /reports/mios ────────────────────────────────────────────────────────

@router.get("/mios", status_code=200)
async def obtener_mis_informes(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Informes técnicos donde el usuario actual es el profesional asignado y/o
    el revisor asignado — para la pestaña "Mis Informes" (sin necesidad de
    ASSIGN_REPORTS, que es del líder que asigna, no de quien sube/revisa).
    """
    user_id = verify_gateway_token(request)["user_id"]

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

    data = []
    for inf in informes:
        informe_doc = await _get_active_informe_documento(db, inf.id)
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
            "docs_documento_id": informe_doc.docs_documento_id if informe_doc else None,
            "proceso_activo": informe_doc is not None,
            "aceptado": inf.fecha_aceptacion_informe is not None,
            "puede_diligenciar_matriz": (
                inf.tipo_informe == "VISITA"
                and inf.fecha_aceptacion_informe is not None
                and inf.profesional_asignado_id == user_id
            ),
            "tiene_matriz": inf.id in informes_con_matriz,
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

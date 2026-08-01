from fastapi import Request, APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
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
from db.models.expediente import Expediente

from core.permission import Permission
ASSIGN_REPORTS = Permission.ASSIGN_REPORTS
UPLOAD_REPORTS = Permission.UPLOAD_REPORTS

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


# ─── SCHEMAS ────────────────────────────────────────────────────────────────

class AsignarProfesionalRequest(BaseModel):
    profesional_id: int
    fecha_programacion_visita: Optional[str] = None  # ISO date string


class SyncDocRequest(BaseModel):
    pass  # vacío — el sync lo hace el backend consultando app-docs


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

    # Cargar usuarios con UPLOAD_REPORTS para enriquecer respuesta
    users = await get_users_by_permission(UPLOAD_REPORTS)

    stmt = select(InformeTecnico)

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

        # Proceso activo en app-docs
        informe_doc = await _get_active_informe_documento(db, inf.id)

        data.append({
            "id": inf.id,
            "expediente_id": inf.expediente_id,
            "expediente_radicado": radicados_map.get(inf.expediente_id),
            "profesional_asignado_id": inf.profesional_asignado_id,
            "profesional_nombre": profesional_info["nombre"] if profesional_info else None,
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
        raise HTTPException(status_code=400, detail="El usuario no tiene permiso de subir_informes")

    # Obtener nombre del expediente para el nombre del documento
    result_exp = await db.execute(select(Expediente).where(Expediente.id == informe.expediente_id))
    expediente = result_exp.scalar_one_or_none()
    nombre_doc = f"Informe {informe.tipo_informe or 'Técnico'} - Expediente {expediente.radicado if expediente else informe.expediente_id}"

    # Crear proceso en app-docs (service-to-service)
    create_result = await create_doc_for_professional(
        nombre=nombre_doc,
        descripcion=f"Informe técnico de {informe.tipo_informe or 'VISITA'} para el expediente. Profesional responsable del cargue.",
        creador_id=body.profesional_id,
        revisor_id=user_id,  # la ingeniera líder que asigna es la revisora
    )

    if not create_result["ok"]:
        raise HTTPException(status_code=502, detail=f"Error creando proceso en app-docs: {create_result.get('message')}")

    docs_documento_id = create_result["documento_id"]

    # Actualizar informe
    informe.profesional_asignado_id = body.profesional_id
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
            mensaje=f"Se te ha asignado el informe técnico de {informe.tipo_informe or 'VISITA'} para el expediente {expediente.radicado if expediente else informe.expediente_id}. Debes subir el documento en el módulo de documentos.",
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

    if informe.fecha_aceptacion_informe is not None:
        raise HTTPException(status_code=400, detail="El informe ya fue aceptado, no se puede reasignar")

    # Verificar permiso del nuevo profesional
    perm_profesional = await verify_permission(body.profesional_id, UPLOAD_REPORTS)
    if not perm_profesional:
        raise HTTPException(status_code=400, detail="El usuario no tiene permiso de subir_informes")

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
                    mensaje=f"Se ha reasignado el informe técnico del expediente {expediente_prev.radicado if expediente_prev else informe.expediente_id}. Ya no eres el profesional responsable.",
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
        revisor_id=user_id,
    )

    if not create_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=502, detail=f"Error creando proceso en app-docs: {create_result.get('message')}")

    docs_documento_id = create_result["documento_id"]

    # Actualizar informe
    informe.profesional_asignado_id = body.profesional_id
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
            mensaje=f"Se te ha asignado el informe técnico de {informe.tipo_informe or 'VISITA'} para el expediente {expediente.radicado if expediente else informe.expediente_id}. Debes subir el documento en el módulo de documentos.",
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


# ─── PUT /reports/{informe_id}/sync ──────────────────────────────────────────

@router.put("/{informe_id}/sync", status_code=200)
async def sincronizar_informe_aprobado(
    request: Request,
    informe_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Sincroniza el InformeTecnico con el documento aprobado en app-docs.
    Se llama desde el frontend luego de que la líder aprueba en el modal de revisión.
    Consulta app-docs vía service-to-service y actualiza los campos del informe.
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

    # Obtener detalle desde app-docs (service-to-service)
    doc_detail = await get_doc_detail(informe_doc.docs_documento_id)
    if not doc_detail.get("ok"):
        raise HTTPException(status_code=502, detail=f"Error consultando app-docs: {doc_detail.get('message')}")

    estado_doc = doc_detail.get("estado")

    if estado_doc == "devuelto":
        # Notificar al profesional que el documento fue rechazado
        try:
            result_exp = await db.execute(select(Expediente).where(Expediente.id == informe.expediente_id))
            expediente_dev = result_exp.scalar_one_or_none()
            radicado_dev = expediente_dev.radicado if expediente_dev else str(informe.expediente_id)
            await create_notification(
                mensaje=f"Tu informe técnico para el expediente {radicado_dev} fue devuelto. Por favor revisa las observaciones y sube una nueva versión.",
                id_vinculada=str(informe_id),
                tipo="informe_tecnico",
                usuario_id=informe.profesional_asignado_id,
            )
        except Exception as e:
            logger.warning(f"Error notificando devolución al profesional: {e}")
        return JSONResponse(content={
            "ok": False,
            "message": "El documento fue devuelto. Se notificó al profesional.",
            "estado": estado_doc,
        })

    if estado_doc != "aprobado":
        return JSONResponse(content={
            "ok": False,
            "message": f"El documento aún no está aprobado. Estado actual: {estado_doc}",
            "estado": estado_doc,
        })

    def _parse_date_bogota(iso_str: str) -> date | None:
        try:
            dt = datetime.fromisoformat(iso_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(_BOGOTA).date()
        except (ValueError, TypeError):
            return None

    ultima_version = doc_detail.get("ultima_version")
    fecha_subida = _parse_date_bogota(ultima_version["fecha_subida"]) if ultima_version and ultima_version.get("fecha_subida") else None
    fecha_aprobacion = _parse_date_bogota(doc_detail["fecha_ultima_actualizacion"]) if doc_detail.get("fecha_ultima_actualizacion") else None

    # Actualizar InformeTecnico
    informe.fecha_aceptacion_informe = fecha_aprobacion or date.today()
    informe.fecha_recibido_informe = fecha_subida or fecha_aprobacion or date.today()
    file_hash_id = ultima_version.get("file_hash_id") if ultima_version else None
    informe.documento_informe_id = file_hash_id or informe_doc.docs_documento_id

    # Desactivar el proceso en la tabla bridge (ya terminó)
    informe_doc.activo = False

    await db.commit()

    # Notificar al profesional y al abogado del expediente
    try:
        result_exp = await db.execute(select(Expediente).where(Expediente.id == informe.expediente_id))
        expediente = result_exp.scalar_one_or_none()
        radicado = expediente.radicado if expediente else str(informe.expediente_id)

        # Notificar profesional: su informe fue aceptado
        await create_notification(
            mensaje=f"Tu informe técnico para el expediente {radicado} ha sido aceptado.",
            id_vinculada=str(informe_id),
            tipo="informe_tecnico",
            usuario_id=informe.profesional_asignado_id,
        )

        # Notificar abogado responsable del expediente
        if expediente and expediente.abogado_responsable_id:
            await create_notification(
                mensaje=f"El informe técnico del expediente {radicado} fue aceptado y está disponible para revisión.",
                id_vinculada=str(informe_id),
                tipo="informe_tecnico",
                usuario_id=expediente.abogado_responsable_id,
            )
    except Exception as e:
        logger.warning(f"Error notificando aprobación: {e}")

    logger.info(f"Informe {informe_id} sincronizado como aprobado")
    return JSONResponse(content={
        "ok": True,
        "informe_id": informe_id,
        "fecha_aceptacion": _format_date(informe.fecha_aceptacion_informe),
        "fecha_recibido": _format_date(informe.fecha_recibido_informe),
        "message": "Informe técnico actualizado como aceptado",
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
    permisos = await verify_permission(user_id, ASSIGN_REPORTS)
    if not permisos:
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

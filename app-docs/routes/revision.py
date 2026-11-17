"""Revisión de documentos (/review), estadísticas (/stats) y revisores (/reviewers).

/review delega las reglas en el flujo fijo del módulo (services/revision_documentos.py):
aprobado | devuelto (adjunto opcional pdf/doc/docx solo al devolver); a la 3ª
devolución el documento queda 'finalizado'.
"""
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from satc_shared.review_process import APROBADO, FINALIZADO, ReviewError

from core.permission import permission
from db.deps import get_db_managed
from db.models.asignaciones_revisores import AsignacionRevisor
from db.models.documentos import Documento
from db.models.revisiones import Revision
from routes.documentos import subir_archivo
from services.notification import (
    notify_document_approved,
    notify_document_finalized,
    notify_document_rejected,
)
from services.revision_documentos import FLUJO, http_error, prevalidar_revision, servicio
from services.users import get_users_by_permission, verify_permission
from utils.verify_token import verify_gateway_token

PERMISO_CREADOR = permission.PERMISO_CREADOR
PERMISO_REVISOR = permission.PERMISO_REVISOR

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/review/{documento_id}")
async def revisar_documento(
    request: Request,
    documento_id: int,
    accion: str = Form(...),            # 'aprobado' | 'devuelto'
    comentario: str | None = Form(None),
    adjunto: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Un revisor asignado aprueba o devuelve el documento (al devolver puede
    adjuntar un documento de observaciones pdf/doc/docx). A la 3ª devolución
    pasa a 'finalizado'. Requiere PERMISO_REVISOR.
    """
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    if not await verify_permission(user_id, PERMISO_REVISOR):
        raise HTTPException(status_code=403, detail="No tienes permiso para revisar documentos")

    tiene_adjunto = adjunto is not None and bool(adjunto.filename)
    svc = servicio(db)
    try:
        await prevalidar_revision(svc, db, documento_id, user_id, accion, adjunto.filename if tiene_adjunto else None)
    except ReviewError as e:
        raise http_error(e)

    ref = (await subir_archivo(db, adjunto))[0] if tiene_adjunto else None

    try:
        resultado = await svc.revisar(
            db, documento_id, user_id=user_id, accion=accion, comentario=comentario, adjunto=ref
        )
        await db.commit()
    except ReviewError as e:
        await db.rollback()
        raise http_error(e)

    documento = resultado.proceso
    if resultado.estado_nuevo == APROBADO:
        await notify_document_approved(
            documento_id=documento_id, documento_nombre=documento.nombre, creador_id=documento.creador_id,
        )
    elif resultado.estado_nuevo == FINALIZADO:
        await notify_document_finalized(
            documento_id=documento_id, documento_nombre=documento.nombre, creador_id=documento.creador_id,
            max_devoluciones=FLUJO.max_devoluciones,
        )
    else:
        await notify_document_rejected(
            documento_id=documento_id, documento_nombre=documento.nombre, creador_id=documento.creador_id,
            numero_devoluciones=documento.numero_devoluciones, max_devoluciones=FLUJO.max_devoluciones,
            con_adjunto=ref is not None,
        )

    return {
        "ok": True,
        "estado": FLUJO.estado_info(resultado.estado_nuevo).model_dump(),
        "numero_devoluciones": documento.numero_devoluciones,
        "message": resultado.descripcion,
    }


@router.get("/stats")
async def obtener_estadisticas(
    request: Request,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Estadísticas del usuario según sus permisos:
    - CREADOR: documentos creados por estado.
    - REVISOR: documentos asignados/pendientes y revisiones realizadas.
    """
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    stats = {}

    tiene_permiso_creador = await verify_permission(user_id, PERMISO_CREADOR)
    tiene_permiso_revisor = await verify_permission(user_id, PERMISO_REVISOR)

    if tiene_permiso_creador:
        stmt = select(
            func.count(Documento.id).label('total_creados'),
            func.sum(case((Documento.estado == 'en_revision', 1), else_=0)).label('en_revision'),
            func.sum(case((Documento.estado == 'aprobado', 1), else_=0)).label('aprobados'),
            func.sum(case((Documento.estado == 'rechazado', 1), else_=0)).label('rechazados'),
            func.sum(case((Documento.estado == 'finalizado', 1), else_=0)).label('finalizados')
        ).where(Documento.creador_id == user_id)
        row = (await db.execute(stmt)).one()
        stats["creador"] = {
            "total_creados": row.total_creados or 0,
            "en_revision": row.en_revision or 0,
            "aprobados": row.aprobados or 0,
            "rechazados": row.rechazados or 0,
            "finalizados": row.finalizados or 0
        }

    if tiene_permiso_revisor:
        docs_asignados = select(AsignacionRevisor.proceso_id).where(
            AsignacionRevisor.revisor_id == user_id
        ).scalar_subquery()

        stmt_docs = select(
            func.count(Documento.id).label('total_asignados'),
            func.sum(case((Documento.estado == 'en_revision', 1), else_=0)).label('pendientes')
        ).where(Documento.id.in_(docs_asignados))
        row_docs = (await db.execute(stmt_docs)).one()

        stmt_rev = select(
            func.count(Revision.id).label('total_revisiones'),
            func.sum(case((Revision.accion == 'aprobado', 1), else_=0)).label('aprobados'),
            func.sum(case((Revision.accion == 'devuelto', 1), else_=0)).label('devueltos')
        ).where(Revision.revisor_id == user_id)
        row_rev = (await db.execute(stmt_rev)).one()

        stats["revisor"] = {
            "total_asignados": row_docs.total_asignados or 0,
            "pendientes": row_docs.pendientes or 0,
            "total_revisiones": row_rev.total_revisiones or 0,
            "aprobados": row_rev.aprobados or 0,
            "devueltos": row_rev.devueltos or 0
        }

    if not stats:
        raise HTTPException(status_code=403, detail="No tienes permisos en este módulo")

    return {"ok": True, "stats": stats}


@router.get("/reviewers")
async def listar_revisores_disponibles(
    request: Request,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Lista los usuarios con permiso de revisor (excluye al propio solicitante).
    Requiere PERMISO_CREADOR o PERMISO_REVISOR.
    """
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    tiene_acceso = await verify_permission(user_id, PERMISO_CREADOR) or await verify_permission(user_id, PERMISO_REVISOR)
    if not tiene_acceso:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para consultar revisores. Se requiere permiso de creador o revisor."
        )

    revisores_dict = await get_users_by_permission(PERMISO_REVISOR)
    revisores_list = [
        {"id": id, "nombre_completo": info["nombre"], "email": info["correo"]}
        for id, info in revisores_dict.items() if id != user_id
    ]

    return {"ok": True, "usuarios": revisores_list, "total": len(revisores_list)}

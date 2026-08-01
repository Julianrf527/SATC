from fastapi import APIRouter, Depends, HTTPException, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from datetime import datetime
import logging

from db.deps import get_db_managed
from services.notification import (
    notify_document_rejected,
    notify_document_approved,
    notify_document_finalized,
)
from services.users import get_users_by_permission, verify_permission
from utils.verify_token import verify_gateway_token

from db.models.documentos import Documento
from db.models.asignaciones_revisores import AsignacionRevisor
from db.models.revisiones import Revision
from db.models.auditoria_documentos import AuditoriaDocumento

from core.permission import permission

PERMISO_CREADOR = permission.PERMISO_CREADOR
PERMISO_REVISOR = permission.PERMISO_REVISOR

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/review/{documento_id}")
async def revisar_documento(
    request: Request,
    documento_id: int,
    estado_revision: str = Form(...),  # 'aprobado' o 'devuelto'
    comentarios: str = Form(None),
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Permite a un revisor asignado aprobar o devolver un documento.
    A la 3ª devolución el documento pasa a 'finalizado'. Requiere PERMISO_REVISOR.
    """
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    if not await verify_permission(user_id, PERMISO_REVISOR):
        raise HTTPException(status_code=403, detail="No tienes permiso para revisar documentos")

    stmt_asignacion = select(AsignacionRevisor).where(
        and_(
            AsignacionRevisor.documento_id == documento_id,
            AsignacionRevisor.revisor_id == user_id
        )
    )
    asignacion = (await db.execute(stmt_asignacion)).scalar_one_or_none()
    if not asignacion:
        raise HTTPException(status_code=403, detail="No estás asignado como revisor de este documento")

    documento = (await db.execute(
        select(Documento).where(Documento.id == documento_id)
    )).scalar_one_or_none()

    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if documento.estado != 'en_revision':
        raise HTTPException(status_code=400, detail="El documento no está en revisión")

    if estado_revision not in ['aprobado', 'devuelto']:
        raise HTTPException(status_code=400, detail="Estado de revisión inválido")

    db.add(Revision(
        documento_id=documento_id,
        version_revisada=documento.version_actual,
        revisor_id=user_id,
        estado_revision=estado_revision,
        comentarios=comentarios
    ))

    if estado_revision == 'aprobado':
        documento.estado = 'aprobado'
        accion_auditoria = 'aprobar'
        mensaje = "Documento aprobado exitosamente"
        await notify_document_approved(
            documento_id=documento_id,
            documento_nombre=documento.nombre,
            creador_id=documento.usuario_creador_id
        )
    else:  # devuelto
        documento.numero_devoluciones += 1
        if documento.numero_devoluciones >= 3:
            documento.estado = 'finalizado'
            accion_auditoria = 'finalizar'
            mensaje = "Documento finalizado tras 3 devoluciones"
            await notify_document_finalized(
                documento_id=documento_id,
                documento_nombre=documento.nombre,
                creador_id=documento.usuario_creador_id
            )
        else:
            documento.estado = 'rechazado'
            accion_auditoria = 'devolver'
            mensaje = f"Estado cambiado de en_revision a rechazado, rechazos {documento.numero_devoluciones}/3"
            await notify_document_rejected(
                documento_id=documento_id,
                documento_nombre=documento.nombre,
                creador_id=documento.usuario_creador_id,
                numero_devoluciones=documento.numero_devoluciones
            )

    documento.fecha_ultima_actualizacion = datetime.now()

    db.add(AuditoriaDocumento(
        documento_id=documento_id,
        usuario_id=user_id,
        accion=accion_auditoria,
        descripcion=mensaje,
        datos_adicionales={'comentarios': comentarios, 'version': documento.version_actual}
    ))

    await db.commit()

    return {
        "ok": True,
        "estado": documento.estado,
        "numero_devoluciones": documento.numero_devoluciones,
        "message": mensaje
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
        ).where(Documento.usuario_creador_id == user_id)
        row = (await db.execute(stmt)).one()
        stats["creador"] = {
            "total_creados": row.total_creados or 0,
            "en_revision": row.en_revision or 0,
            "aprobados": row.aprobados or 0,
            "rechazados": row.rechazados or 0,
            "finalizados": row.finalizados or 0
        }

    if tiene_permiso_revisor:
        docs_asignados = select(AsignacionRevisor.documento_id).where(
            AsignacionRevisor.revisor_id == user_id
        ).scalar_subquery()

        stmt_docs = select(
            func.count(Documento.id).label('total_asignados'),
            func.sum(case((Documento.estado == 'en_revision', 1), else_=0)).label('pendientes')
        ).where(Documento.id.in_(docs_asignados))
        row_docs = (await db.execute(stmt_docs)).one()

        stmt_rev = select(
            func.count(Revision.id).label('total_revisiones'),
            func.sum(case((Revision.estado_revision == 'aprobado', 1), else_=0)).label('aprobados'),
            func.sum(case((Revision.estado_revision == 'devuelto', 1), else_=0)).label('devueltos')
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

"""
Endpoints service-to-service (autenticados con x-service-token, sin usuario).
Consumidos por app-infraction / app-sancionatoria.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from datetime import datetime
import logging

from db.deps import get_db_managed
from services.notification import notify_assignment
from utils.verify_token import verify_service_token

from db.models.documentos import Documento
from db.models.asignaciones_revisores import AsignacionRevisor
from db.models.auditoria_documentos import AuditoriaDocumento
from db.models.file_hash import FileHash

router = APIRouter()
logger = logging.getLogger(__name__)


class CreateServiceRequest(BaseModel):
    nombre: str
    descripcion: str
    tipo_archivo: str = "pdf"
    creador_id: int
    revisores_ids: list[int]


@router.post("/create-service")
async def crear_documento_service(
    request: Request,
    body: CreateServiceRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Crea un documento en nombre de un usuario externo. El creador_id y
    revisores_ids se pasan explícitamente. Requiere x-service-token.
    """
    verify_service_token(request)

    if body.tipo_archivo not in ['pdf', 'docx', 'doc']:
        raise HTTPException(status_code=400, detail="Tipo de archivo no válido (pdf, docx, doc)")

    if not body.revisores_ids:
        raise HTTPException(status_code=400, detail="Debe asignar al menos un revisor")

    nuevo_documento = Documento(
        nombre=body.nombre,
        descripcion=body.descripcion,
        tipo_archivo=body.tipo_archivo,
        usuario_creador_id=body.creador_id,
        estado='en_revision',
        version_actual=1
    )
    db.add(nuevo_documento)
    await db.flush()

    for revisor_id in body.revisores_ids:
        db.add(AsignacionRevisor(
            documento_id=nuevo_documento.id,
            revisor_id=revisor_id,
            notificado=True
        ))
        try:
            await notify_assignment(
                documento_id=nuevo_documento.id,
                documento_nombre=body.nombre,
                revisor_id=revisor_id,
                version_actual=1
            )
        except Exception as e:
            logger.error(f"Error notificando revisor {revisor_id}: {e}")

    db.add(AuditoriaDocumento(
        documento_id=nuevo_documento.id,
        usuario_id=body.creador_id,
        accion='crear',
        descripcion=f'Documento creado por servicio externo con {len(body.revisores_ids)} revisor(es)',
        datos_adicionales={'revisores': body.revisores_ids, 'creado_por_servicio': True}
    ))
    await db.commit()

    logger.info(f"Documento creado por servicio: {nuevo_documento.id}")
    return {"ok": True, "documento_id": nuevo_documento.id}


@router.put("/finalize-service/{documento_id}")
async def finalizar_documento_service(
    request: Request,
    documento_id: int,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Fuerza el estado del documento a 'finalizado' (usado al reasignar un
    profesional: el proceso anterior se cancela). Requiere x-service-token.
    """
    verify_service_token(request)

    documento = (await db.execute(
        select(Documento).where(Documento.id == documento_id)
    )).scalar_one_or_none()

    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if documento.estado in ('aprobado', 'finalizado'):
        return {"ok": True, "message": "Documento ya está en estado terminal", "estado": documento.estado}

    documento.estado = 'finalizado'
    documento.fecha_ultima_actualizacion = datetime.now()

    db.add(AuditoriaDocumento(
        documento_id=documento_id,
        usuario_id=0,  # sistema
        accion='finalizar',
        descripcion='Documento finalizado por reasignación de profesional (servicio externo)',
        datos_adicionales={'finalizado_por_servicio': True}
    ))
    await db.commit()

    logger.info(f"Documento {documento_id} finalizado por servicio externo")
    return {"ok": True, "estado": "finalizado"}


@router.get("/detail-service/{documento_id}")
async def obtener_documento_service(
    request: Request,
    documento_id: int,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Devuelve estado y última versión de un documento. Requiere x-service-token.
    """
    verify_service_token(request)

    documento = (await db.execute(
        select(Documento)
        .options(selectinload(Documento.versiones))
        .where(Documento.id == documento_id)
    )).scalar_one_or_none()

    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    versiones_ordenadas = sorted(documento.versiones, key=lambda v: v.numero_version, reverse=True)
    ultima_version = versiones_ordenadas[0] if versiones_ordenadas else None

    # FileHash.id de la última versión: lo necesita el consumidor para descargar.
    file_hash_id = None
    if ultima_version and ultima_version.archivo_url:
        fh = (await db.execute(
            select(FileHash).where(FileHash.file_url == ultima_version.archivo_url)
        )).scalar_one_or_none()
        if fh:
            file_hash_id = fh.id

    return {
        "ok": True,
        "documento_id": documento.id,
        "estado": documento.estado,
        "version_actual": documento.version_actual,
        "numero_devoluciones": documento.numero_devoluciones,
        "fecha_ultima_actualizacion": documento.fecha_ultima_actualizacion.isoformat() if documento.fecha_ultima_actualizacion else None,
        "ultima_version": {
            "version_id": ultima_version.id,
            "numero_version": ultima_version.numero_version,
            "archivo_url": ultima_version.archivo_url,
            "archivo_nombre": ultima_version.archivo_nombre_original,
            "archivo_size": ultima_version.archivo_size or 0,
            "fecha_subida": ultima_version.fecha_subida.isoformat() if ultima_version.fecha_subida else None,
            "file_hash_id": file_hash_id,
        } if ultima_version else None,
    }

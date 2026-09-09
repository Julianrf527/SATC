from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic import BaseModel
import os
import logging
import asyncio
import json
import math
from collections import defaultdict

from db.deps import get_db_managed
from services.notification import notify_assignment, notify_new_version
from services.users import get_users_by_permission, verify_permission
from utils.verify_token import verify_gateway_token
from utils.minio_client import (
    upload_file_with_deduplication,
    get_file_from_minio,
    init_minio,
    MINIO_BUCKET,
)
from utils.hash_utils import calcular_hash_uploadfile
from utils.antivirus import escanear_archivo
from utils.file_validator import validate_file_complete

from db.models.documentos import Documento
from db.models.versiones_documento import VersionDocumento
from db.models.asignaciones_revisores import AsignacionRevisor
from db.models.auditoria_documentos import AuditoriaDocumento
from db.models.v_documentos_detalle import VDocumentoDetalle
from db.models.file_hash import FileHash

from core.permission import permission

PERMISO_CREADOR = permission.PERMISO_CREADOR
PERMISO_REVISOR = permission.PERMISO_REVISOR

_BOGOTA = ZoneInfo("America/Bogota")

router = APIRouter()
logger = logging.getLogger(__name__)

init_minio()


class DocumentoResumen(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    estado: str
    fecha_creacion: datetime
    fecha_ultima_actualizacion: datetime
    version_actual: Optional[int] = None
    numero_devoluciones: int
    usuario_creador_id: int
    total_revisiones: int
    total_revisores: int

    class Config:
        from_attributes = True


@router.get("/list")
async def listar_documentos(
    request: Request,
    estado: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db_managed)
):
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    tiene_permiso_creador = await verify_permission(user_id, PERMISO_CREADOR)
    tiene_permiso_revisor = await verify_permission(user_id, PERMISO_REVISOR)

    if not tiene_permiso_creador and not tiene_permiso_revisor:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver documentos")

    # Los documentos del flujo de informes técnicos (app-infraction) no se
    # listan acá — se gestionan desde "Mis Informes".
    stmt = select(VDocumentoDetalle).where(VDocumentoDetalle.origen.is_(None))

    if tiene_permiso_creador and tiene_permiso_revisor:
        subquery = select(AsignacionRevisor.documento_id).where(AsignacionRevisor.revisor_id == user_id)
        stmt = stmt.where(or_(VDocumentoDetalle.usuario_creador_id == user_id, VDocumentoDetalle.id.in_(subquery)))
    elif tiene_permiso_creador:
        stmt = stmt.where(VDocumentoDetalle.usuario_creador_id == user_id)
    elif tiene_permiso_revisor:
        subquery = select(AsignacionRevisor.documento_id).where(AsignacionRevisor.revisor_id == user_id)
        stmt = stmt.where(VDocumentoDetalle.id.in_(subquery))

    if estado:
        stmt = stmt.where(VDocumentoDetalle.estado == estado)
    if fecha_desde:
        stmt = stmt.where(VDocumentoDetalle.fecha_creacion >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(VDocumentoDetalle.fecha_creacion <= fecha_hasta)

    count_subq = stmt.with_only_columns(VDocumentoDetalle.id).distinct().subquery()
    count_result = await db.execute(select(func.count()).select_from(count_subq))
    total = count_result.scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    offset = (page - 1) * page_size
    data_stmt = stmt.order_by(VDocumentoDetalle.fecha_creacion.desc()).offset(offset).limit(page_size)
    result = await db.execute(data_stmt)
    documentos = result.scalars().all()

    documentos_unicos = {}
    for doc in documentos:
        if doc.id not in documentos_unicos:
            documentos_unicos[doc.id] = doc

    docs_list = [
        DocumentoResumen.model_validate(doc).model_dump(mode='json')
        for doc in documentos_unicos.values()
    ]

    return {
        "ok": True,
        "total": total,
        "total_pages": total_pages,
        "page": page,
        "page_size": page_size,
        "documentos": docs_list,
    }


@router.get("/detail/{documento_id}")
async def obtener_documento_completo(
    request: Request,
    documento_id: int,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Obtiene toda la información del documento: versiones, revisiones,
    revisores asignados y auditoría.
    """
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    tiene_permiso_creador = await verify_permission(user_id, PERMISO_CREADOR)
    tiene_permiso_revisor = await verify_permission(user_id, PERMISO_REVISOR)

    if not tiene_permiso_creador and not tiene_permiso_revisor:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver documentos")

    stmt = (
        select(Documento)
        .options(
            selectinload(Documento.versiones),
            selectinload(Documento.revisiones),
            selectinload(Documento.asignaciones_revisores),
            selectinload(Documento.auditoria)
        )
        .where(Documento.id == documento_id)
    )
    result = await db.execute(stmt)
    documento = result.scalar_one_or_none()

    # Se responde 403 tanto si el documento no existe como si existe pero no
    # pertenece al usuario: distinguir 404/403 revelaría qué IDs existen.
    es_creador = documento is not None and documento.usuario_creador_id == user_id
    es_revisor = documento is not None and any(
        a.revisor_id == user_id for a in documento.asignaciones_revisores
    )

    if not es_creador and not es_revisor:
        raise HTTPException(status_code=403, detail="No tienes acceso a este documento")

    versiones = sorted(documento.versiones, key=lambda v: v.numero_version, reverse=True)
    revisiones = sorted(documento.revisiones, key=lambda r: r.fecha_revision, reverse=True)
    revisores_asignados = sorted(documento.asignaciones_revisores, key=lambda a: a.fecha_asignacion)
    auditoria_raw = sorted(documento.auditoria, key=lambda a: a.fecha_accion)

    revisores_ids = set([r.revisor_id for r in revisiones])
    revisores_info = {}
    if revisores_ids:
        revisores_data = await get_users_by_permission(PERMISO_REVISOR)
        revisores_info = {uid: info for uid, info in revisores_data.items() if uid in revisores_ids}

    # Consolidar auditoría: agrupar por acción + minuto y quedarse con la
    # descripción más completa (varios pasos de una acción escriben filas casi iguales).
    eventos_agrupados = defaultdict(list)
    for a in auditoria_raw:
        fecha_minuto = a.fecha_accion.replace(second=0, microsecond=0)
        eventos_agrupados[(a.accion, fecha_minuto)].append(a)

    auditoria_consolidada = []
    for eventos in eventos_agrupados.values():
        eventos_ordenados = sorted(
            eventos,
            key=lambda e: (len(e.descripcion or ""), e.fecha_accion),
            reverse=True
        )
        auditoria_consolidada.append(eventos_ordenados[0])

    auditoria = sorted(auditoria_consolidada, key=lambda x: x.fecha_accion)

    return {
        "ok": True,
        "documento_id": documento.id,
        "nombre": documento.nombre,
        "descripcion": documento.descripcion or "",
        "tipo_archivo": documento.tipo_archivo,
        "estado": documento.estado,
        "version_actual": documento.version_actual or 1,
        "numero_devoluciones": documento.numero_devoluciones or 0,
        "fecha_creacion": documento.fecha_creacion.isoformat() if documento.fecha_creacion else None,
        "usuario_creador_id": documento.usuario_creador_id,
        "versiones": [
            {
                "version_id": v.id,
                "numero_version": v.numero_version,
                "archivo_url": v.archivo_url,
                "archivo_nombre": v.archivo_nombre_original,
                "archivo_size": v.archivo_size or 0,
                "fecha_subida": v.fecha_subida.isoformat() if v.fecha_subida else None,
                "comentario": v.comentario or ""
            }
            for v in versiones
        ],
        "revisiones": [
            {
                "revision_id": r.id,
                "revisor_id": r.revisor_id,
                "revisor_nombre": revisores_info.get(r.revisor_id, {}).get("nombre", f"Usuario {r.revisor_id}"),
                "estado": r.estado_revision,
                "comentarios": r.comentarios or "",
                "fecha_revision": r.fecha_revision.isoformat() if r.fecha_revision else None,
                "version_revisada": r.version_revisada
            }
            for r in revisiones
        ],
        "revisores_asignados": [
            {
                "revisor_id": ra.revisor_id,
                "fecha_asignacion": ra.fecha_asignacion.isoformat() if ra.fecha_asignacion else None,
                "notificado": ra.notificado if ra.notificado is not None else False
            }
            for ra in revisores_asignados
        ],
        "auditoria": [
            {
                "auditoria_id": a.id,
                "usuario_id": a.usuario_id,
                "accion": a.accion,
                "descripcion": a.descripcion or "",
                "fecha_accion": a.fecha_accion.isoformat() if a.fecha_accion else None
            }
            for a in auditoria
        ]
    }


@router.post("/create")
async def crear_documento(
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(None),
    tipo_archivo: str = Form(...),
    revisores_ids: str = Form(...),  # JSON string: "[1,2,3]"
    archivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_managed)
):
    """Crea un nuevo documento y lo asigna a revisores. Requiere PERMISO_CREADOR."""
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    if not await verify_permission(user_id, PERMISO_CREADOR):
        raise HTTPException(status_code=403, detail="No tienes permiso para crear documentos")

    if tipo_archivo not in ['pdf', 'docx', 'doc']:
        raise HTTPException(status_code=400, detail="Tipo de archivo no válido (pdf, docx, doc)")

    try:
        revisores_list = json.loads(revisores_ids)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="Formato de revisores inválido")

    if not revisores_list:
        raise HTTPException(status_code=400, detail="Debe asignar al menos un revisor")

    for revisor_id in revisores_list:
        if not await verify_permission(revisor_id, PERMISO_REVISOR):
            raise HTTPException(
                status_code=400,
                detail=f"El usuario {revisor_id} no tiene permiso de revisor"
            )

    file_hash, sanitized_filename, mime_type, archivo_size, file_data = await _procesar_archivo_seguro(archivo)

    resultado_upload = await upload_file_with_deduplication(
        db=db,
        file_data=file_data,
        original_filename=sanitized_filename,
        content_type=mime_type
    )
    if not resultado_upload["ok"]:
        raise HTTPException(
            status_code=500,
            detail=f"Error subiendo archivo: {resultado_upload.get('message', 'Error desconocido')}"
        )

    archivo_url = resultado_upload["url"]
    if resultado_upload.get("deduplicated"):
        file_hash_id = resultado_upload.get("id")
        if file_hash_id:
            file_record = await db.get(FileHash, file_hash_id)
            if file_record:
                file_record.numero_usos += 1

    nuevo_documento = Documento(
        nombre=nombre,
        descripcion=descripcion,
        tipo_archivo=tipo_archivo,
        usuario_creador_id=user_id,
        estado='en_revision',
        version_actual=1
    )
    db.add(nuevo_documento)
    await db.flush()

    nueva_version = VersionDocumento(
        documento_id=nuevo_documento.id,
        numero_version=1,
        archivo_url=archivo_url,
        archivo_nombre_original=archivo.filename,
        archivo_size=archivo_size,
        usuario_subida_id=user_id,
        comentario="Versión inicial"
    )
    db.add(nueva_version)

    for revisor_id in revisores_list:
        asignacion = AsignacionRevisor(
            documento_id=nuevo_documento.id,
            revisor_id=revisor_id,
            notificado=True
        )
        db.add(asignacion)
        try:
            await notify_assignment(
                documento_id=nuevo_documento.id,
                documento_nombre=nombre,
                revisor_id=revisor_id,
                version_actual=1
            )
        except Exception as e:
            logger.error(f"Error al notificar revisor {revisor_id}: {e}")

    auditoria = AuditoriaDocumento(
        documento_id=nuevo_documento.id,
        usuario_id=user_id,
        accion='crear',
        descripcion=f'Documento creado con {len(revisores_list)} revisor(es)',
        datos_adicionales={'revisores': revisores_list, 'hash': file_hash[:16]}
    )
    db.add(auditoria)

    await db.commit()
    logger.info(f"Documento creado exitosamente: {nuevo_documento.id}")

    return {
        "ok": True,
        "documento_id": nuevo_documento.id,
        "hash": file_hash,
        "message": "Documento creado exitosamente"
    }


@router.post("/upload-version/{documento_id}")
async def subir_nueva_version(
    request: Request,
    documento_id: int,
    comentario: str = Form(None),
    archivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_managed)
):
    """Sube una nueva versión del documento tras una devolución. Requiere PERMISO_CREADOR."""
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    if not await verify_permission(user_id, PERMISO_CREADOR):
        raise HTTPException(status_code=403, detail="No tienes permiso para subir documentos")

    stmt = select(Documento).where(Documento.id == documento_id)
    result = await db.execute(stmt)
    documento = result.scalar_one_or_none()

    # 403 tanto si no existe como si no es del usuario: no revelar qué IDs existen.
    if documento is None or documento.usuario_creador_id != user_id:
        raise HTTPException(status_code=403, detail="No eres el creador de este documento")

    stmt_ver_count = select(func.count()).select_from(VersionDocumento).where(
        VersionDocumento.documento_id == documento_id
    )
    versions_count = (await db.execute(stmt_ver_count)).scalar() or 0
    is_initial_upload = versions_count == 0

    # Permitir upload inicial (sin versiones) o re-subida tras rechazo.
    if not is_initial_upload and documento.estado != 'rechazado':
        raise HTTPException(
            status_code=400,
            detail="Solo puedes subir una nueva versión cuando el documento ha sido devuelto"
        )

    file_hash, sanitized_filename, mime_type, archivo_size, file_data = await _procesar_archivo_seguro(archivo)

    # Rechazar si el mismo contenido ya está en alguna versión del documento.
    stmt_hash = select(VersionDocumento).where(VersionDocumento.documento_id == documento_id)
    versiones_existentes = (await db.execute(stmt_hash)).scalars().all()
    for version_existente in versiones_existentes:
        if file_hash in version_existente.archivo_url:
            raise HTTPException(
                status_code=409,
                detail="Esta versión del archivo ya existe en el documento"
            )

    resultado_upload = await upload_file_with_deduplication(
        db=db,
        file_data=file_data,
        original_filename=sanitized_filename,
        content_type=mime_type
    )
    if not resultado_upload["ok"]:
        raise HTTPException(
            status_code=500,
            detail=f"Error subiendo archivo: {resultado_upload.get('message', 'Error desconocido')}"
        )

    archivo_url = resultado_upload["url"]

    nueva_version_num = documento.version_actual if is_initial_upload else documento.version_actual + 1
    nueva_version = VersionDocumento(
        documento_id=documento_id,
        numero_version=nueva_version_num,
        archivo_url=archivo_url,
        archivo_nombre_original=archivo.filename,
        archivo_size=archivo_size,
        usuario_subida_id=user_id,
        comentario=comentario
    )
    db.add(nueva_version)

    documento.version_actual = nueva_version_num
    documento.estado = 'en_revision'
    documento.fecha_ultima_actualizacion = datetime.now(_BOGOTA)

    stmt_revisores = select(AsignacionRevisor).where(AsignacionRevisor.documento_id == documento_id)
    revisores = (await db.execute(stmt_revisores)).scalars().all()
    await notify_new_version(
        documento_id=documento_id,
        documento_nombre=documento.nombre,
        version_numero=nueva_version_num,
        revisores_ids=[r.revisor_id for r in revisores]
    )

    accion_version = 'subir_version_inicial' if is_initial_upload else 'subir_version'
    descripcion_version = (
        f'Documento cargado por primera vez (v{nueva_version_num})'
        if is_initial_upload
        else f'Nueva versión subida (v{nueva_version_num}) tras devolución'
    )
    db.add(AuditoriaDocumento(
        documento_id=documento_id,
        usuario_id=user_id,
        accion=accion_version,
        descripcion=descripcion_version,
        datos_adicionales={'version': nueva_version_num, 'hash': file_hash[:16], 'comentario': comentario}
    ))

    await db.commit()
    logger.info(f"Nueva version subida exitosamente: v{nueva_version_num}")

    return {
        "ok": True,
        "version": nueva_version_num,
        "hash": file_hash,
        "message": "Versión subida exitosamente"
    }


@router.get("/download/{version_id}")
async def descargar_archivo(
    request: Request,
    version_id: int,
    db: AsyncSession = Depends(get_db_managed)
):
    """Descarga el archivo de una versión específica desde MinIO, validando permisos."""
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    stmt = select(VersionDocumento).where(VersionDocumento.id == version_id)
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()

    documento = None
    if version is not None:
        result_doc = await db.execute(select(Documento).where(Documento.id == version.documento_id))
        documento = result_doc.scalar_one_or_none()

    es_creador = documento is not None and documento.usuario_creador_id == user_id

    es_revisor = False
    if version is not None:
        stmt_revisor = select(AsignacionRevisor).where(
            and_(
                AsignacionRevisor.documento_id == version.documento_id,
                AsignacionRevisor.revisor_id == user_id
            )
        )
        es_revisor = (await db.execute(stmt_revisor)).scalar_one_or_none() is not None

    # 403 tanto si la versión no existe como si el archivo no es del usuario:
    # no revelar por version_id qué archivos existen.
    if not (es_creador or es_revisor):
        raise HTTPException(status_code=403, detail="No tienes permiso para descargar este archivo")

    file_path = version.archivo_url
    if file_path.startswith(MINIO_BUCKET + "/"):
        file_path = file_path.replace(MINIO_BUCKET + "/", "", 1)

    resultado = await asyncio.to_thread(get_file_from_minio, file_path)
    if not resultado["ok"]:
        raise HTTPException(status_code=404, detail="Archivo no encontrado en MinIO")

    file_data = resultado["data"]
    content_types = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword'
    }
    content_type = content_types.get(documento.tipo_archivo, 'application/octet-stream')

    return StreamingResponse(
        iter([file_data]),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{version.archivo_nombre_original}"'}
    )


async def _procesar_archivo_seguro(archivo: UploadFile):
    """
    Pipeline de seguridad compartido por /create y /upload-version:
    calcula el hash, valida (5 capas), sanea el nombre y escanea con antivirus.
    Devuelve (file_hash, sanitized_filename, mime_type, archivo_size, file_data).
    Lanza HTTPException si la validación o el antivirus rechazan el archivo.
    """
    file_hash, file_data = calcular_hash_uploadfile(archivo)
    archivo_size = len(file_data)
    max_size = int(os.getenv("MAX_FILE_SIZE_MB", "10"))

    validation_result = await validate_file_complete(
        file_data=file_data,
        filename=archivo.filename,
        max_size_mb=max_size
    )
    sanitized_filename = validation_result["sanitized_filename"]
    mime_type = validation_result["mime_type"]

    resultado_escaneo = escanear_archivo(file_data, archivo.filename)
    if not resultado_escaneo["ok"]:
        raise HTTPException(
            status_code=400,
            detail=f"Archivo rechazado: {resultado_escaneo['mensaje']}"
        )

    return file_hash, sanitized_filename, mime_type, archivo_size, file_data

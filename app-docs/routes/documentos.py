"""Módulo Documentos: flujo FIJO genérico de revisión (ver services/revision_documentos.py).

Las reglas del proceso (estados, acciones, devoluciones, versiones, numero_usos)
las aplica ``satc_shared.review_process.ProcesoRevisionService``; este router
hace auth/permisos del módulo, el pipeline de seguridad de archivos, el commit
y las notificaciones.
"""
import asyncio
import json
import logging
import math
import os
import re
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from satc_shared.review_process import (
    EN_REVISION,
    PENDIENTE_CARGA,
    EXTENSIONES_DOCUMENTO,
    ArchivoRef,
    EstadoInfo,
    ProcesoDetalle,
    ReviewError,
)

from core.permission import permission
from db.deps import get_db_managed
from db.models.asignaciones_revisores import AsignacionRevisor
from db.models.documentos import Documento
from db.models.revisiones import Revision
from db.models.v_documentos_detalle import VDocumentoDetalle
from db.models.versiones_documento import VersionDocumento
from services.notification import notify_assignment, notify_new_version
from services.revision_documentos import FLUJO, http_error, prevalidar_subida, servicio
from services.users import get_user_names, verify_permission
from utils.antivirus import escanear_archivo
from utils.file_validator import validate_file_complete
from utils.hash_utils import calcular_hash_uploadfile
from utils.minio_client import (
    MINIO_BUCKET,
    get_file_from_minio,
    init_minio,
    upload_file_with_deduplication,
)
from utils.verify_token import verify_gateway_token

PERMISO_CREADOR = permission.PERMISO_CREADOR
PERMISO_REVISOR = permission.PERMISO_REVISOR

router = APIRouter()
logger = logging.getLogger(__name__)

init_minio()

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
}


# ============================================================ archivos

def nombre_visible(filename: Optional[str]) -> str:
    """Nombre original para mostrar/descargar: sin ruta ni caracteres que rompan
    el header Content-Disposition."""
    nombre = os.path.basename((filename or "").replace("\\", "/"))
    return re.sub(r'[\x00-\x1f"]', "", nombre).strip() or "archivo"


async def _procesar_archivo_seguro(archivo: UploadFile):
    """
    Pipeline de seguridad compartido por /create, /upload-version y /review:
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


async def subir_archivo(db: AsyncSession, archivo: UploadFile) -> tuple[ArchivoRef, str]:
    """Pipeline de seguridad + subida deduplicada. Devuelve (ArchivoRef, sha256).

    No registra el uso: lo hace el servicio de revisión (UsoArchivosLocal) en la
    misma transacción que la versión/revisión que referencia el archivo."""
    file_hash, sanitized_filename, mime_type, archivo_size, file_data = await _procesar_archivo_seguro(archivo)
    resultado = await upload_file_with_deduplication(
        db=db, file_data=file_data, original_filename=sanitized_filename, content_type=mime_type
    )
    if not resultado["ok"]:
        raise HTTPException(
            status_code=500,
            detail=f"Error subiendo archivo: {resultado.get('message', 'Error desconocido')}"
        )
    ref = ArchivoRef(
        file_id=resultado.get("id"),
        url=resultado["url"],
        nombre=nombre_visible(archivo.filename),
        size=archivo_size,
    )
    return ref, file_hash


def _validar_extension(nombre: Optional[str], extensiones=EXTENSIONES_DOCUMENTO) -> None:
    if not (nombre or "").lower().endswith(tuple(extensiones)):
        raise HTTPException(status_code=400, detail=f"Formato no permitido. Permitidos: {', '.join(extensiones)}")


def _streaming(data: bytes, nombre: str) -> StreamingResponse:
    extension = os.path.splitext(nombre.lower())[1]
    return StreamingResponse(
        iter([data]),
        media_type=CONTENT_TYPES.get(extension, "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{nombre_visible(nombre)}"'},
    )


def _leer_minio(url: str):
    file_path = url
    if file_path.startswith(MINIO_BUCKET + "/"):
        file_path = file_path.replace(MINIO_BUCKET + "/", "", 1)
    return get_file_from_minio(file_path)


async def _es_participante(db: AsyncSession, documento_id: int, user_id: int) -> bool:
    """Creador o revisor asignado del documento."""
    creador = await db.scalar(select(Documento.creador_id).where(Documento.id == documento_id))
    if creador is not None and creador == user_id:
        return True
    return await db.scalar(
        select(AsignacionRevisor.id).where(
            AsignacionRevisor.proceso_id == documento_id,
            AsignacionRevisor.revisor_id == user_id,
        ).limit(1)
    ) is not None


# ============================================================== /list

class DocumentoResumen(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    estado: EstadoInfo
    fecha_creacion: datetime
    fecha_ultima_actualizacion: datetime
    version_actual: Optional[int] = None
    numero_devoluciones: int
    creador_id: int
    total_revisiones: int
    total_revisores: int


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

    stmt = select(VDocumentoDetalle)
    asignados = select(AsignacionRevisor.proceso_id).where(AsignacionRevisor.revisor_id == user_id)
    if tiene_permiso_creador and tiene_permiso_revisor:
        stmt = stmt.where(or_(VDocumentoDetalle.creador_id == user_id, VDocumentoDetalle.id.in_(asignados)))
    elif tiene_permiso_creador:
        stmt = stmt.where(VDocumentoDetalle.creador_id == user_id)
    else:
        stmt = stmt.where(VDocumentoDetalle.id.in_(asignados))

    if estado:
        stmt = stmt.where(VDocumentoDetalle.estado == estado)
    if fecha_desde:
        stmt = stmt.where(VDocumentoDetalle.fecha_creacion >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(VDocumentoDetalle.fecha_creacion <= fecha_hasta)

    count_subq = stmt.with_only_columns(VDocumentoDetalle.id).distinct().subquery()
    total = (await db.execute(select(func.count()).select_from(count_subq))).scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    offset = (page - 1) * page_size
    data_stmt = stmt.order_by(VDocumentoDetalle.fecha_creacion.desc()).offset(offset).limit(page_size)
    documentos = (await db.execute(data_stmt)).scalars().all()

    documentos_unicos = {}
    for doc in documentos:
        documentos_unicos.setdefault(doc.id, doc)

    return {
        "ok": True,
        "total": total,
        "total_pages": total_pages,
        "page": page,
        "page_size": page_size,
        # Catálogo de estados del flujo para el filtro (pendiente_carga no aplica:
        # en este módulo el documento siempre se crea con su versión 1).
        "estados": [e.info().model_dump() for e in FLUJO.estados.values() if e.codigo != PENDIENTE_CARGA],
        "documentos": [
            DocumentoResumen(
                id=doc.id,
                nombre=doc.nombre,
                descripcion=doc.descripcion,
                estado=FLUJO.estado_info(doc.estado),
                fecha_creacion=doc.fecha_creacion,
                fecha_ultima_actualizacion=doc.fecha_ultima_actualizacion,
                version_actual=doc.version_actual,
                numero_devoluciones=doc.numero_devoluciones or 0,
                creador_id=doc.creador_id,
                total_revisiones=doc.total_revisiones or 0,
                total_revisores=doc.total_revisores or 0,
            ).model_dump(mode="json")
            for doc in documentos_unicos.values()
        ],
    }


# ============================================================ /detail

@router.get("/detail/{documento_id}", response_model=ProcesoDetalle)
async def obtener_documento_completo(
    request: Request,
    documento_id: int,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Detalle completo del documento (contrato ``ProcesoDetalle`` de
    satc_shared): versiones, revisiones, revisores, auditoría y, POR USUARIO,
    ``acciones_disponibles`` (revisor asignado en ``en_revision``) y
    ``subida_version`` (creador). Solo creador y revisores asignados; 403 si
    no existe (no revelar qué IDs existen).
    """
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    tiene_permiso_creador = await verify_permission(user_id, PERMISO_CREADOR)
    tiene_permiso_revisor = await verify_permission(user_id, PERMISO_REVISOR)
    if not tiene_permiso_creador and not tiene_permiso_revisor:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver documentos")

    # Nombres por id (no por permiso): un revisor que perdió el permiso
    # sigue apareciendo con su nombre en revisores y en el historial.
    ids_usuarios = [r for (r,) in (await db.execute(
        select(AsignacionRevisor.revisor_id).where(AsignacionRevisor.proceso_id == documento_id)
        .union(select(Revision.revisor_id).where(Revision.proceso_id == documento_id))
    )).all()]
    nombres = await get_user_names(ids_usuarios)

    try:
        return await servicio(db).detalle(db, documento_id, user_id=user_id, nombres_usuarios=nombres)
    except ReviewError as e:
        raise http_error(e)


# ============================================================ /create

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
    """Crea un documento con su versión 1 (queda en_revision) y lo asigna a revisores. Requiere PERMISO_CREADOR."""
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    if not await verify_permission(user_id, PERMISO_CREADOR):
        raise HTTPException(status_code=403, detail="No tienes permiso para crear documentos")

    if tipo_archivo not in ("pdf", "docx", "doc"):
        raise HTTPException(status_code=400, detail="Tipo de archivo no válido (pdf, docx, doc)")

    try:
        revisores_list = [int(r) for r in json.loads(revisores_ids)]
    except (json.JSONDecodeError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Formato de revisores inválido")
    revisores_list = list(dict.fromkeys(revisores_list))
    if not revisores_list:
        raise HTTPException(status_code=400, detail="Debe asignar al menos un revisor")

    for revisor_id in revisores_list:
        if not await verify_permission(revisor_id, PERMISO_REVISOR):
            raise HTTPException(status_code=400, detail=f"El usuario {revisor_id} no tiene permiso de revisor")

    _validar_extension(archivo.filename)
    ref, file_hash = await subir_archivo(db, archivo)

    try:
        documento = await servicio(db).crear_proceso(
            db,
            nombre=nombre,
            descripcion=descripcion,
            creador_id=user_id,
            revisores_ids=revisores_list,
            archivo=ref,
            comentario="Versión inicial",
            campos={"tipo_archivo": tipo_archivo},
        )
        await db.commit()
    except ReviewError as e:
        await db.rollback()
        raise http_error(e)

    # Notificar tras el commit: si falla una notificación el documento ya existe.
    asignaciones = (await db.execute(
        select(AsignacionRevisor).where(AsignacionRevisor.proceso_id == documento.id)
    )).scalars().all()
    for asignacion in asignaciones:
        resultado = await notify_assignment(
            documento_id=documento.id,
            documento_nombre=nombre,
            revisor_id=asignacion.revisor_id,
            version_actual=documento.version_actual,
        )
        asignacion.notificado = bool(resultado and resultado.get("ok"))
    await db.commit()

    logger.info(f"Documento creado exitosamente: {documento.id}")
    return {
        "ok": True,
        "documento_id": documento.id,
        "hash": file_hash,
        "message": "Documento creado exitosamente",
    }


# ===================================================== /upload-version

@router.post("/upload-version/{documento_id}")
async def subir_nueva_version(
    request: Request,
    documento_id: int,
    comentario: str = Form(None),
    archivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_managed)
):
    """Sube una nueva versión tras una devolución (estado 'rechazado'). Requiere PERMISO_CREADOR y ser el creador."""
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    if not await verify_permission(user_id, PERMISO_CREADOR):
        raise HTTPException(status_code=403, detail="No tienes permiso para subir documentos")

    svc = servicio(db)
    try:
        await prevalidar_subida(svc, db, documento_id, user_id, archivo.filename or "")
    except ReviewError as e:
        raise http_error(e)

    ref, file_hash = await subir_archivo(db, archivo)

    try:
        resultado = await svc.subir_version(db, documento_id, user_id=user_id, archivo=ref, comentario=comentario)
        await db.commit()
    except ReviewError as e:
        await db.rollback()
        raise http_error(e)

    documento = resultado.proceso
    if resultado.estado_nuevo == EN_REVISION:
        revisores_ids = (await db.execute(
            select(AsignacionRevisor.revisor_id).where(AsignacionRevisor.proceso_id == documento_id)
        )).scalars().all()
        await notify_new_version(
            documento_id=documento_id,
            documento_nombre=documento.nombre,
            version_numero=resultado.version.numero_version,
            revisores_ids=list(revisores_ids),
        )

    logger.info(f"Nueva version subida exitosamente: v{resultado.version.numero_version}")
    return {
        "ok": True,
        "version": resultado.version.numero_version,
        "estado": FLUJO.estado_info(resultado.estado_nuevo).model_dump(),
        "hash": file_hash,
        "message": "Versión subida exitosamente",
    }


# ========================================================== descargas

@router.get("/download/{version_id}")
async def descargar_archivo(
    request: Request,
    version_id: int,
    db: AsyncSession = Depends(get_db_managed)
):
    """Descarga el archivo de una versión. Solo creador y revisores del documento."""
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    version = await db.scalar(select(VersionDocumento).where(VersionDocumento.id == version_id))
    # 403 tanto si no existe como si no es del usuario: no revelar qué IDs existen.
    if version is None or not await _es_participante(db, version.proceso_id, user_id):
        raise HTTPException(status_code=403, detail="No tienes permiso para descargar este archivo")

    resultado = await asyncio.to_thread(_leer_minio, version.archivo_url)
    if not resultado["ok"]:
        raise HTTPException(status_code=404, detail="Archivo no encontrado en MinIO")
    return _streaming(resultado["data"], version.archivo_nombre or "documento")


@router.get("/download-revision/{revision_id}")
async def descargar_adjunto_revision(
    request: Request,
    revision_id: int,
    db: AsyncSession = Depends(get_db_managed)
):
    """Descarga el archivo de observaciones adjunto a una devolución. Solo creador y revisores del documento."""
    token_data = verify_gateway_token(request)
    user_id = int(token_data["user_id"])

    revision = await db.scalar(select(Revision).where(Revision.id == revision_id))
    # 403 también si no existe o no tiene adjunto: no revelar qué IDs existen.
    if (
        revision is None
        or not revision.adjunto_url
        or not await _es_participante(db, revision.proceso_id, user_id)
    ):
        raise HTTPException(status_code=403, detail="No tienes permiso para descargar este archivo")

    resultado = await asyncio.to_thread(_leer_minio, revision.adjunto_url)
    if not resultado["ok"]:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return _streaming(resultado["data"], revision.adjunto_nombre or "observaciones")

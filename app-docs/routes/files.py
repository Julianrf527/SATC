from utils.verify_token import verify_gateway_token, verify_service_token
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel
import asyncio
import logging
import os
import io

from db.deps import get_db_managed
from db.models.file_hash import FileHash
from utils.minio_client import upload_file_with_deduplication, get_file_from_minio
from utils.file_validator import validate_file_complete
from utils.antivirus import escanear_archivo

router = APIRouter()
logger = logging.getLogger(__name__)

class FilesBatchRequest(BaseModel):
    file_ids: List[int]

class FileStateUpdateRequest(BaseModel):
    file_ids: List[int]

def verify_internal_access(request: Request) -> None:
    service_token = request.headers.get("x-service-token")
    gateway_token = request.headers.get("x-gateway-token")

    if service_token:
        verify_service_token(request)
    elif gateway_token:
        verify_gateway_token(request)
    else:
        raise HTTPException(status_code=401, detail="No se proporcionó token de autenticación")

def verify_service_only_access(request: Request) -> None:
    """
    Para endpoints exclusivamente service-to-service (nunca llamados desde el
    frontend vía gateway): exige X-Service-Token estricto, sin fallback a
    X-Gateway-Token. El gateway inyecta X-Gateway-Token en toda petición que
    reenvía, incluidas las que no exigen sesión de usuario — aceptarlo acá
    permitiría a cualquiera con acceso a la red interna suplantar un servicio.
    """
    verify_service_token(request)

@router.post("/upload")
async def upload_file(
    archivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Sube un archivo con deduplicación por hash. Devuelve su ID y numero_usos
    actual (0 si es nuevo): quien lo asocie a un recurso debe incrementarlo.
    """
    file_data = await archivo.read()

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
        logger.error(f"Archivo rechazado por antivirus: {resultado_escaneo['mensaje']}")
        raise HTTPException(
            status_code=400,
            detail=f"Archivo rechazado: {resultado_escaneo['mensaje']}"
        )

    resultado_upload = await upload_file_with_deduplication(
        db=db,
        file_data=file_data,
        original_filename=sanitized_filename,
        content_type=mime_type
    )
    if not resultado_upload.get("ok"):
        raise HTTPException(
            status_code=500,
            detail=f"Error subiendo archivo: {resultado_upload.get('message', 'Error desconocido')}"
        )

    return JSONResponse(
        content={
            "ok": True,
            "file_id": resultado_upload["id"],
            "file_url": resultado_upload["url"],
            "file_hash": resultado_upload["file_hash"],
            "message": resultado_upload["message"],
            "deduplicated": resultado_upload.get("deduplicated", False),
            "numero_usos": resultado_upload.get("numero_usos", 0)
        }
    )

@router.get("/{file_id}")
async def get_file_by_id(
    request: Request,
    file_id: int,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Retorna la información de un documento por su ID unico.
    """
    verify_internal_access(request)

    stmt = select(FileHash).where(FileHash.id == file_id)
    result = await db.execute(stmt)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": file_record.id,
                "file_url": file_record.file_url,
                "content_type": file_record.content_type,
                "file_size": file_record.file_size,
                "numero_usos": file_record.numero_usos
            }
        }
    )

@router.post("/batch")
async def get_files_batch(
    request: Request,
    file_request: FilesBatchRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Retorna las URLs de múltiples documentos dados sus IDs.
    """
    verify_service_only_access(request)

    if not file_request.file_ids:
        return JSONResponse(content={"ok": True, "data": []})

    stmt = select(FileHash).where(FileHash.id.in_(file_request.file_ids))
    result = await db.execute(stmt)
    files = result.scalars().all()

    data = []
    for file_record in files:
        data.append({
            "id": file_record.id,
            "file_url": file_record.file_url,
            "content_type": file_record.content_type,
            "file_size": file_record.file_size,
            "numero_usos": file_record.numero_usos
        })

    return JSONResponse(content={"ok": True, "data": data})

@router.get("/download/{file_id}")
async def download_file_by_id(
    request: Request,
    file_id: int,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Descarga o visualiza un archivo desde MinIO dado su ID.
    """
    verify_internal_access(request)

    file_record = (await db.execute(
        select(FileHash).where(FileHash.id == file_id)
    )).scalar_one_or_none()

    if not file_record:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    object_name = file_record.file_url
    result_minio = await asyncio.to_thread(get_file_from_minio, object_name)

    if not result_minio.get("ok"):
        raise HTTPException(status_code=404, detail="Archivo no encontrado en almacenamiento")

    file_data = result_minio["data"]
    content_type = file_record.content_type or "application/octet-stream"
    filename = object_name.split('/')[-1] if '/' in object_name else object_name

    return StreamingResponse(
        io.BytesIO(file_data),
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

@router.put("/increment-usage")
async def increment_file_usage(
    request: Request,
    file_request: FileStateUpdateRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Incrementa numero_usos al asociar archivos a un recurso. Mientras el
    contador sea > 0, el cleanup no los borra.
    """
    verify_service_only_access(request)

    if not file_request.file_ids:
        return JSONResponse(status_code=400, content={"ok": False, "message": "No file_ids provided."})

    files = (await db.execute(
        select(FileHash).where(FileHash.id.in_(file_request.file_ids))
    )).scalars().all()

    for file_record in files:
        file_record.numero_usos += 1

    await db.commit()

    return JSONResponse(content={"ok": True, "message": f"Uso incrementado para {len(files)} archivo(s)"})

@router.put("/decrement-usage")
async def decrement_file_usage(
    request: Request,
    file_request: FileStateUpdateRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Decrementa numero_usos al desvincular archivos de un recurso (nunca por
    debajo de 0). Al llegar a 0 quedan elegibles para el cleanup.
    """
    verify_service_only_access(request)

    if not file_request.file_ids:
        return JSONResponse(status_code=400, content={"ok": False, "message": "No file_ids provided."})

    files = (await db.execute(
        select(FileHash).where(FileHash.id.in_(file_request.file_ids))
    )).scalars().all()

    decremented_count = 0
    for file_record in files:
        if file_record.numero_usos > 0:
            file_record.numero_usos -= 1
            decremented_count += 1

    await db.commit()

    return JSONResponse(content={"ok": True, "message": f"Uso decrementado para {decremented_count} archivo(s)"})

@router.post("/download-unified")
async def download_unified_pdf(
    request: Request,
    file_request: FilesBatchRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Combina varios archivos en un único PDF, en el orden de file_ids.
    """
    verify_service_only_access(request)

    if not file_request.file_ids:
        raise HTTPException(status_code=400, detail="No se proporcionaron IDs de archivos")

    result = await db.execute(select(FileHash).where(FileHash.id.in_(file_request.file_ids)))
    files_dict = {f.id: f for f in result.scalars().all()}

    # Mantener el orden solicitado en file_ids (el consumidor decide el orden del PDF).
    files_ordered = []
    for file_id in file_request.file_ids:
        if file_id in files_dict:
            files_ordered.append(files_dict[file_id])
        else:
            logger.warning(f"[DOWNLOAD-UNIFIED] Archivo {file_id} no encontrado en BD")

    if not files_ordered:
        raise HTTPException(status_code=404, detail="No se encontraron archivos válidos")

    from pypdf import PdfWriter, PdfReader

    pdf_writer = PdfWriter()
    documentos_procesados = 0

    for file_record in files_ordered:
        # Un archivo dañado o ausente en MinIO no debe abortar el PDF completo.
        try:
            resultado = await asyncio.to_thread(get_file_from_minio, file_record.file_url)
            if not resultado["ok"]:
                logger.warning(f"[DOWNLOAD-UNIFIED] No se pudo descargar archivo ID {file_record.id}")
                continue

            pdf_reader = PdfReader(io.BytesIO(resultado["data"]))
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)
            documentos_procesados += 1
        except Exception as e:
            logger.warning(f"[DOWNLOAD-UNIFIED] Error procesando archivo ID {file_record.id}: {e}")
            continue

    if documentos_procesados == 0:
        raise HTTPException(status_code=500, detail="No se pudo procesar ningún documento")

    output_buffer = io.BytesIO()
    pdf_writer.write(output_buffer)
    output_buffer.seek(0)

    return StreamingResponse(
        output_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="documentos_unificados.pdf"'}
    )

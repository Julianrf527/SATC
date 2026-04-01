from utils.verify_token import verify_gateway_token
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel
import logging
import os
import io

from db.deps import get_db
from db.models.file_hash import FileHash
from utils.minio_client import upload_file_with_deduplication, get_file_from_minio
from utils.file_validator import validate_file_complete

router = APIRouter()
logger = logging.getLogger(__name__)

class FilesBatchRequest(BaseModel):
    file_ids: List[int]

class FileStateUpdateRequest(BaseModel):
    file_ids: List[int]

@router.post("/upload")
async def upload_file(
    archivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Sube un archivo con deduplicación por hash.
    Retorna el ID del archivo y su numero_usos actual. Si es nuevo, numero_usos será 0.
    """
    try:
        # 1. Leer archivo
        file_data = await archivo.read()

        # 2. Validacion de seguridad
        max_size = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
        try:
            validation_result = await validate_file_complete(
                file_data=file_data,
                filename=archivo.filename,
                max_size_mb=max_size
            )
            sanitized_filename = validation_result["sanitized_filename"]
            mime_type = validation_result["mime_type"]
        except HTTPException as e:
            raise e

        # 3. Subir con deduplicación
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /upload: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor al subir documento")

@router.get("/{file_id}")
async def get_file_by_id(file_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retorna la información de un documento por su ID unico.
    """
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
async def get_files_batch(request: FilesBatchRequest, db: AsyncSession = Depends(get_db)):
    """
    Retorna las URLs de múltiples documentos dados sus IDs.
    """
    if not request.file_ids:
        return JSONResponse(content={"ok": True, "data": []})

    stmt = select(FileHash).where(FileHash.id.in_(request.file_ids))
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
    db: AsyncSession = Depends(get_db)
):
    """
    Descarga o visualiza un archivo desde MinIO dado su ID.
    """
    try:
        verify_gateway_token(request)
        # Obtener el registro de la base de datos
        stmt = select(FileHash).where(FileHash.id == file_id)
        result = await db.execute(stmt)
        file_record = result.scalar_one_or_none()

        if not file_record:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")

        # El file_url generalmente tiene el formato 'bucket/path/to/file'
        # o solo 'path/to/file'. Necesitamos extraer el object_name para MinIO.
        # Si la url empieza con el bucket, lo removemos para el object_name
        # Pero get_file_from_minio asume el object_name dentro del MINIO_BUCKET por defecto,
        # O quiza get_file_from_minio espera todo el path.
        
        object_name = file_record.file_url

        # Obtener archivo de MinIO
        result_minio = get_file_from_minio(object_name)
        
        if not result_minio.get("ok"):
            raise HTTPException(status_code=404, detail="Archivo no encontrado en almacenamiento")
        
        file_data = result_minio["data"]
        content_type = file_record.content_type or "application/octet-stream"
        
        # Extraer el nombre del archivo de la ruta
        filename = object_name.split('/')[-1] if '/' in object_name else object_name
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error descargando archivo {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Error descargando archivo")

# servicios internos

@router.put("/increment-usage")
async def increment_file_usage(request: FileStateUpdateRequest, db: AsyncSession = Depends(get_db)):
    """
    Incrementa el contador de uso (numero_usos) de uno o varios archivos.
    Se utiliza cuando un archivo se asocia/vincula a un recurso.
    """
    if not request.file_ids:
        return JSONResponse(status_code=400, content={"ok": False, "message": "No file_ids provided."})

    try:
        # Incrementar numero_usos en 1 para cada archivo
        stmt = select(FileHash).where(FileHash.id.in_(request.file_ids))
        result = await db.execute(stmt)
        files = result.scalars().all()

        for file_record in files:
            file_record.numero_usos += 1

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "message": f"Uso incrementado para {len(files)} archivo(s)"
            }
        )
    except Exception as e:
        logger.error(f"Error en /increment-usage: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al incrementar uso de archivos")

@router.put("/decrement-usage")
async def decrement_file_usage(request: FileStateUpdateRequest, db: AsyncSession = Depends(get_db)):
    """
    Decrementa el contador de uso (numero_usos) de uno o varios archivos.
    Solo decrementa si numero_usos > 0.
    Se utiliza cuando un archivo se desvincula de un recurso.
    """
    if not request.file_ids:
        return JSONResponse(status_code=400, content={"ok": False, "message": "No file_ids provided."})

    try:
        # Decrementar numero_usos en 1 para cada archivo (solo si > 0)
        stmt = select(FileHash).where(FileHash.id.in_(request.file_ids))
        result = await db.execute(stmt)
        files = result.scalars().all()

        decremented_count = 0
        for file_record in files:
            if file_record.numero_usos > 0:
                file_record.numero_usos -= 1
                decremented_count += 1

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "message": f"Uso decrementado para {decremented_count} archivo(s)"
            }
        )
    except Exception as e:
        logger.error(f"Error en /decrement-usage: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al decrementar uso de archivos")

@router.post("/download-unified")
async def download_unified_pdf(
    request: Request,
    file_request: FilesBatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Descarga múltiples archivos y los combina en un único PDF.
    Los archivos se ordenan según el orden de file_ids recibido.

    Args:
        file_request: Lista de IDs de archivos a combinar

    Returns:
        PDF unificado con todos los documentos
    """
    try:
        verify_gateway_token(request)

        if not file_request.file_ids:
            raise HTTPException(
                status_code=400,
                detail="No se proporcionaron IDs de archivos"
            )

        logger.info(f"[DOWNLOAD-UNIFIED] Iniciando descarga unificada de {len(file_request.file_ids)} archivos")

        # Obtener información de los archivos en el orden recibido
        stmt = select(FileHash).where(FileHash.id.in_(file_request.file_ids))
        result = await db.execute(stmt)
        files_dict = {f.id: f for f in result.scalars().all()}

        # Mantener el orden de file_ids
        files_ordered = []
        for file_id in file_request.file_ids:
            if file_id in files_dict:
                files_ordered.append(files_dict[file_id])
            else:
                logger.warning(f"[DOWNLOAD-UNIFIED] Archivo {file_id} no encontrado en BD")

        if not files_ordered:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron archivos válidos"
            )

        # Importar PyPDF2 para combinar PDFs
        from pypdf import PdfWriter, PdfReader

        pdf_writer = PdfWriter()
        documentos_procesados = 0

        # Descargar y combinar cada PDF
        for file_record in files_ordered:
            try:
                object_name = file_record.file_url

                logger.info(f"  [DOWNLOAD-UNIFIED] Descargando: {object_name}")

                # Descargar de MinIO
                resultado = get_file_from_minio(object_name)

                if not resultado["ok"]:
                    logger.warning(f"  ⚠ [DOWNLOAD-UNIFIED] No se pudo descargar archivo ID {file_record.id}")
                    continue

                file_data = resultado["data"]

                # Agregar al PDF combinado
                pdf_reader = PdfReader(io.BytesIO(file_data))

                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)

                documentos_procesados += 1
                logger.info(f"  ✓ [DOWNLOAD-UNIFIED] Agregado ID {file_record.id} ({len(pdf_reader.pages)} páginas)")

            except Exception as e:
                logger.warning(f"[DOWNLOAD-UNIFIED] Error procesando archivo ID {file_record.id}: {e}")
                continue

        if documentos_procesados == 0:
            raise HTTPException(
                status_code=500,
                detail="No se pudo procesar ningún documento"
            )

        logger.info(f"[DOWNLOAD-UNIFIED] Documentos procesados: {documentos_procesados}/{len(files_ordered)}")

        # Generar PDF final en memoria
        output_buffer = io.BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)

        filename = "documentos_unificados.pdf"

        logger.info(f"[DOWNLOAD-UNIFIED] PDF generado exitosamente: {filename}")

        # Retornar PDF combinado
        return StreamingResponse(
            output_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"[DOWNLOAD-UNIFIED] Error al generar PDF combinado: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar PDF combinado: {str(e)}"
        )

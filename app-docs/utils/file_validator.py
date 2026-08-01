"""Validación de archivos subidos: extensión, MIME real por magic bytes y
sanitización del nombre. El antivirus vive aparte, en utils/antivirus.py."""
import os
import re
import magic
import hashlib
import unicodedata
from datetime import datetime
from typing import Dict, Tuple, Optional
from fastapi import HTTPException, UploadFile
import logging

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.txt', '.jpg', '.jpeg', '.png', '.gif',
    '.zip', '.rar', '.7z'
}

DANGEROUS_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.com', '.pif', '.scr',
    '.vbs', '.vbe', '.js', '.jse', '.wsf', '.wsh',
    '.msi', '.msp', '.ps1', '.jar', '.app', '.deb',
    '.rpm', '.dmg', '.pkg', '.sh', '.bash', '.dll',
    '.so', '.dylib', '.sys', '.drv'
}

def validate_extension(filename: str) -> str:
    """
    Valida la extensión del archivo y la devuelve normalizada en minúsculas.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if not ext:
        raise HTTPException(
            status_code=400,
            detail="El archivo debe tener una extensión"
        )
    
    if ext in DANGEROUS_EXTENSIONS:
        logger.error(f"Extension peligrosa detectada: {ext} en {filename}")
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido por seguridad: {ext}"
        )
    
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"Extension no permitida: {ext} en {filename}")
        raise HTTPException(
            status_code=400,
            detail=f"Extensión {ext} no está permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    logger.info(f"Extension valida: {ext}")
    return ext


ALLOWED_MIMES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'image/jpeg',
    'image/png',
    'image/gif',
    'text/plain',
    'application/zip',
    'application/x-rar-compressed',
    'application/x-7z-compressed',
    'application/octet-stream'  # Para algunos binarios legítimos
}

MIME_TO_EXTENSIONS = {
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'text/plain': ['.txt'],
    'application/zip': ['.zip'],
    'application/x-rar-compressed': ['.rar'],
    'application/x-7z-compressed': ['.7z'],
    'application/octet-stream': ['.zip', '.rar', '.7z']  # Binarios genéricos
}

async def validate_file_type(file_data: bytes, filename: str, declared_extension: str) -> str:
    """
    MIME real del archivo según sus magic bytes, no según lo que declare el
    cliente. Además exige que coincida con `declared_extension`: un .pdf cuyo
    contenido real es otra cosa se rechaza.
    """
    try:
        mime = magic.from_buffer(file_data[:2048], mime=True)

        logger.info(f"MIME detectado: {mime} para {filename}")

        if mime not in ALLOWED_MIMES:
            logger.error(f"MIME no permitido: {mime} en {filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido. Detectado: {mime}"
            )
        
        expected_extensions = MIME_TO_EXTENSIONS.get(mime, [])
        
        if expected_extensions and declared_extension not in expected_extensions:
            logger.error(
                f"Mismatch: Extension {declared_extension} no coincide con MIME {mime} en {filename}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"La extensión del archivo no coincide con su contenido real"
            )
        
        logger.info(f"MIME valido y coincide con extension: {mime}")
        return mime
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error detectando MIME: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error al validar el tipo de archivo"
        )


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Nombre de archivo seguro para almacenar: sin acentos, sin path, sin
    caracteres fuera de [a-zA-Z0-9._-] y con longitud acotada.

    Se prefija timestamp + hash corto porque sanitizar es ambiguo: dos nombres
    distintos pueden colapsar en el mismo resultado.
    """
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    filename = os.path.basename(filename)
    filename = filename.replace('..', '')
    filename = filename.replace('/', '')
    filename = filename.replace('\\', '')
    
    name, ext = os.path.splitext(filename)

    name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    ext = ext.lower()
    
    if len(name) > max_length:
        name = name[:max_length]
    
    if not name:
        name = "archivo"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hash_short = hashlib.md5(filename.encode()).hexdigest()[:6]
    
    sanitized = f"{timestamp}_{hash_short}_{name}{ext}"
    
    logger.info(f"Nombre sanitizado: {filename} -> {sanitized}")
    return sanitized


async def validate_file_complete(
    file_data: bytes,
    filename: str,
    max_size_mb: int = 10
) -> Dict[str, any]:
    """
    Corre todas las validaciones sobre un archivo subido y devuelve sus datos
    ya normalizados. Cualquier fallo se lanza como HTTPException.
    """
    logger.info(f"Iniciando validacion completa: {filename}")

    size_mb = len(file_data) / (1024 * 1024)
    if size_mb > max_size_mb:
        logger.error(f"Archivo muy grande: {size_mb:.2f}MB (max: {max_size_mb}MB)")
        raise HTTPException(
            status_code=413,
            detail=f"Archivo muy grande ({size_mb:.2f}MB). Máximo permitido: {max_size_mb}MB"
        )
    
    extension = validate_extension(filename)
    mime_type = await validate_file_type(file_data, filename, extension)
    sanitized_filename = sanitize_filename(filename)
    
    logger.info(f"Validacion completa exitosa para: {filename}")
    
    return {
        "ok": True,
        "sanitized_filename": sanitized_filename,
        "mime_type": mime_type,
        "size_mb": round(size_mb, 2),
        "extension": extension,
        "original_filename": filename
    }


def get_safe_content_type(mime_type: str) -> str:
    """
    Content-Type con el que se sirve cualquier archivo. Siempre
    'application/octet-stream': fuerza descarga y evita que el navegador
    renderice o ejecute el contenido en el origen de la app.
    """
    return "application/octet-stream"

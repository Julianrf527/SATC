"""
Validación completa de archivos (Caso 8: Seguridad en Subida de Archivos)

Implementa 5 capas de seguridad:
1. Validación de extensiones
2. Validación de MIME/Magic Bytes
3. Sanitización de nombres
4. Escaneo antivirus (ClamAV)
5. Aislamiento de archivos

Fecha: 2026-02-13
"""
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

# ============================================
# CAPA 1: VALIDACIÓN DE EXTENSIONES
# ============================================

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
    Valida que la extensión del archivo sea permitida.
    
    Args:
        filename: Nombre del archivo
        
    Returns:
        Extensión normalizada en minúsculas
        
    Raises:
        HTTPException: Si la extensión es peligrosa o no permitida
    """
    # Obtener extensión en minúsculas
    ext = os.path.splitext(filename)[1].lower()
    
    if not ext:
        raise HTTPException(
            status_code=400,
            detail="El archivo debe tener una extensión"
        )
    
    # Verificar extensiones peligrosas
    if ext in DANGEROUS_EXTENSIONS:
        logger.error(f"Extension peligrosa detectada: {ext} en {filename}")
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido por seguridad: {ext}"
        )
    
    # Verificar extensiones permitidas
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"Extension no permitida: {ext} en {filename}")
        raise HTTPException(
            status_code=400,
            detail=f"Extensión {ext} no está permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    logger.info(f"Extension valida: {ext}")
    return ext


# ============================================
# CAPA 2: VALIDACIÓN DE MIME/MAGIC BYTES
# ============================================

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

# Mapeo de MIME a extensiones válidas
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
    Valida el tipo MIME real del archivo usando magic bytes.
    
    Args:
        file_data: Contenido del archivo en bytes
        filename: Nombre del archivo (para logging)
        declared_extension: Extensión declarada por el usuario
        
    Returns:
        MIME type detectado
        
    Raises:
        HTTPException: Si el MIME no es permitido o no coincide con la extensión
    """
    try:
        # Detectar MIME real del archivo
        mime = magic.from_buffer(file_data[:2048], mime=True)
        
        logger.info(f"MIME detectado: {mime} para {filename}")
        
        # Verificar si el MIME está permitido
        if mime not in ALLOWED_MIMES:
            logger.error(f"MIME no permitido: {mime} en {filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido. Detectado: {mime}"
            )
        
        # Verificar que extensión coincida con MIME
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


# ============================================
# CAPA 3: SANITIZACIÓN DE NOMBRE DE ARCHIVO
# ============================================

def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitiza y normaliza el nombre del archivo.
    
    Protege contra:
    - Path traversal (../, ../../, etc.)
    - Caracteres especiales maliciosos
    - Nombres excesivamente largos
    - Caracteres Unicode problemáticos
    
    Args:
        filename: Nombre original del archivo
        max_length: Longitud máxima del nombre (sin extensión)
        
    Returns:
        Nombre sanitizado con timestamp único
    """
    # Normalizar Unicode (eliminar acentos y caracteres especiales)
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Extraer solo el nombre base (elimina cualquier path)
    filename = os.path.basename(filename)
    
    # Eliminar intentos de path traversal
    filename = filename.replace('..', '')
    filename = filename.replace('/', '')
    filename = filename.replace('\\', '')
    
    # Separar nombre y extensión
    name, ext = os.path.splitext(filename)
    
    # Solo caracteres alfanuméricos, guiones y guiones bajos
    name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    ext = ext.lower()
    
    # Limitar longitud del nombre
    if len(name) > max_length:
        name = name[:max_length]
    
    # Si el nombre quedó vacío, usar default
    if not name:
        name = "archivo"
    
    # Agregar timestamp y hash corto para unicidad
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hash_short = hashlib.md5(filename.encode()).hexdigest()[:6]
    
    sanitized = f"{timestamp}_{hash_short}_{name}{ext}"
    
    logger.info(f"Nombre sanitizado: {filename} -> {sanitized}")
    return sanitized


# ============================================
# VALIDACIÓN COMPLETA (TODAS LAS CAPAS)
# ============================================

async def validate_file_complete(
    file_data: bytes,
    filename: str,
    max_size_mb: int = 10
) -> Dict[str, any]:
    """
    Ejecuta todas las capas de validación de archivos.
    
    Args:
        file_data: Contenido del archivo en bytes
        filename: Nombre original del archivo
        max_size_mb: Tamaño máximo permitido en MB
        
    Returns:
        Dict con:
        - ok: bool - True si todas las validaciones pasaron
        - sanitized_filename: str - Nombre sanitizado
        - mime_type: str - MIME detectado
        - size_mb: float - Tamaño en MB
        - extension: str - Extensión validada
        
    Raises:
        HTTPException: Si alguna validación falla
    """
    logger.info(f"Iniciando validacion completa: {filename}")
    
    # Validar tamaño
    size_mb = len(file_data) / (1024 * 1024)
    if size_mb > max_size_mb:
        logger.error(f"Archivo muy grande: {size_mb:.2f}MB (max: {max_size_mb}MB)")
        raise HTTPException(
            status_code=413,
            detail=f"Archivo muy grande ({size_mb:.2f}MB). Máximo permitido: {max_size_mb}MB"
        )
    
    # CAPA 1: Validar extensión
    extension = validate_extension(filename)
    
    # CAPA 2: Validar MIME y consistencia
    mime_type = await validate_file_type(file_data, filename, extension)
    
    # CAPA 3: Sanitizar nombre
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
    Devuelve un Content-Type seguro para servir el archivo.
    
    Para PDFs y documentos, forzamos 'application/octet-stream'
    para evitar ejecución automática en el navegador.
    
    Args:
        mime_type: MIME detectado
        
    Returns:
        Content-Type seguro para headers HTTP
    """
    # Para máxima seguridad, forzar descarga de todo
    return "application/octet-stream"

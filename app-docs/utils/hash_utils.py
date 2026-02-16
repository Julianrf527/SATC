"""
Utilidad para calcular hashes SHA256 de archivos y detectar duplicados
"""
import hashlib
import logging
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def calcular_hash_archivo(file_data: bytes) -> str:
    """
    Calcula el hash SHA256 de un archivo.
    
    Args:
        file_data: Contenido del archivo en bytes
        
    Returns:
        Hash SHA256 en formato hexadecimal
    """
    try:
        sha256_hash = hashlib.sha256()
        sha256_hash.update(file_data)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error calculando hash: {e}")
        raise


def calcular_hash_uploadfile(file) -> tuple[str, bytes]:
    """
    Calcula el hash SHA256 de un UploadFile de FastAPI.
    
    Args:
        file: UploadFile de FastAPI
        
    Returns:
        Tupla (hash_str, file_data) - El hash y los datos del archivo
    """
    try:
        # Leer todo el archivo
        file_data = file.file.read()
        
        # Resetear el puntero del archivo por si se necesita leer después
        file.file.seek(0)
        
        # Calcular hash
        hash_str = calcular_hash_archivo(file_data)
        
        logger.info(f"Hash calculado para {file.filename}: {hash_str}")
        
        return hash_str, file_data
        
    except Exception as e:
        logger.error(f"Error calculando hash de UploadFile: {e}")
        raise


def verificar_duplicado_por_hash(
    file_hash: str, 
    archivos_existentes: Dict[str, str]
) -> Optional[str]:
    """
    Verifica si un archivo con el mismo hash ya existe.
    
    Args:
        file_hash: Hash SHA256 del archivo
        archivos_existentes: Diccionario {hash: url} de archivos existentes
        
    Returns:
        URL del archivo duplicado si existe, None si no existe
    """
    if file_hash in archivos_existentes:
        logger.warning(f"Archivo duplicado detectado. Hash: {file_hash}")
        return archivos_existentes[file_hash]
    
    return None


def generar_metadata_hash(file_hash: str, filename: str, size: int) -> dict:
    """
    Genera metadata que incluye el hash del archivo.
    
    Args:
        file_hash: Hash SHA256 del archivo
        filename: Nombre original del archivo
        size: Tamaño del archivo en bytes
        
    Returns:
        Diccionario con metadata
    """
    return {
        "sha256": file_hash,
        "original_filename": filename,
        "size_bytes": str(size),
        "timestamp": str(Path(__file__).stat().st_mtime)
    }


# Cache en memoria para hashes de archivos (opcional)
# Para uso en producción, considerar Redis o base de datos
_hash_cache: Dict[str, str] = {}


def agregar_a_cache(file_hash: str, url: str):
    """Agrega un hash a la cache en memoria"""
    _hash_cache[file_hash] = url
    logger.debug(f"Hash agregado a cache: {file_hash} -> {url}")


def obtener_de_cache(file_hash: str) -> Optional[str]:
    """Obtiene una URL desde la cache de hashes"""
    return _hash_cache.get(file_hash)


def limpiar_cache():
    """Limpia la cache de hashes"""
    global _hash_cache
    _hash_cache.clear()
    logger.info("Cache de hashes limpiada")

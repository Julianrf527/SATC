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
    Hash SHA256 de un UploadFile de FastAPI, como (hash_str, file_data).

    Deja el puntero del archivo en 0 para que el llamador pueda releerlo.
    """
    try:
        file_data = file.file.read()
        file.file.seek(0)
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
    URL del archivo con este hash si ya existe, None si no.
    """
    if file_hash in archivos_existentes:
        logger.warning(f"Archivo duplicado detectado. Hash: {file_hash}")
        return archivos_existentes[file_hash]
    
    return None


def generar_metadata_hash(file_hash: str, filename: str, size: int) -> dict:
    """
    Genera la metadata del objeto, incluyendo el hash del archivo.
    """
    return {
        "sha256": file_hash,
        "original_filename": filename,
        "size_bytes": str(size),
        "timestamp": str(Path(__file__).stat().st_mtime)
    }


# Cache local al proceso: con varios workers cada uno tiene el suyo, así que
# es solo un atajo, no la fuente de verdad de la deduplicación.
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

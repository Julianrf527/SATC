"""Gestión de archivos en app-docs (/files) vía satc_shared.clients.FilesClient.

Las funciones conservan sus firmas y el formato de respuesta dict
({'ok': bool, ...}) que esperan las rutas: nunca lanzan.
"""
from dotenv import load_dotenv
from typing import List, Dict, Any
import logging

from satc_shared.clients import FilesClient, NotFoundError, ServiceClientError

load_dotenv()
logger = logging.getLogger(__name__)

# Directo a DOCS_SERVICE_URL con x-service-token de infraction-service.
files_client = FilesClient.from_env("infraction-service")


def _error(e: Exception) -> Dict[str, Any]:
    if isinstance(e, ServiceClientError) and e.status_code is not None:
        return {"ok": False, "message": f"Error from app-docs: {e.status_code}"}
    return {"ok": False, "message": str(e)}


async def increment_file_usage(file_ids: List[int]) -> Dict[str, Any]:
    """Incrementa numero_usos al asociar archivos a un recurso."""
    if not file_ids:
        return {"ok": False, "message": "No file_ids provided"}
    try:
        return (await files_client.increment_usage(file_ids)).model_dump(exclude_none=True)
    except Exception as e:
        logger.error(f"Error incrementing file usage for files {file_ids}: {e}")
        return _error(e)


async def decrement_file_usage(file_ids: List[int]) -> Dict[str, Any]:
    """Decrementa numero_usos al desvincular archivos de un recurso."""
    if not file_ids:
        return {"ok": False, "message": "No file_ids provided"}
    try:
        return (await files_client.decrement_usage(file_ids)).model_dump(exclude_none=True)
    except Exception as e:
        logger.error(f"Error decrementing file usage for files {file_ids}: {e}")
        return _error(e)


async def get_file_info(file_id: int) -> Dict[str, Any]:
    """Información de un archivo: {'ok': True, 'data': {...}} o {'ok': False, ...}."""
    try:
        info = await files_client.get(file_id)
        return {"ok": True, "data": info.model_dump()}
    except NotFoundError:
        return {"ok": False, "message": "File not found"}
    except Exception as e:
        logger.error(f"Error getting file info for file {file_id}: {e}")
        return _error(e)


async def get_files_batch(file_ids: List[int]) -> Dict[str, Any]:
    """Información de múltiples archivos: {'ok': True, 'data': [...]}."""
    if not file_ids:
        return {"ok": True, "data": []}
    try:
        files = await files_client.batch(file_ids)
        return {"ok": True, "data": [f.model_dump() for f in files]}
    except Exception as e:
        logger.error(f"Error getting files batch for files {file_ids}: {e}")
        return _error(e)


async def download_unified_pdf(file_ids: List[int], cookies: Dict[str, str]) -> Dict[str, Any]:
    """
    Combina varios archivos en un único PDF vía app-docs (orden = file_ids).
    Devuelve {'ok': True, 'content': bytes, 'message'} o {'ok': False, 'message'}.
    """
    if not file_ids:
        return {"ok": False, "message": "No file_ids provided"}
    try:
        content = await files_client.download_unified(file_ids, cookies=cookies)
    except Exception as e:
        logger.error(f"Error downloading unified PDF for {len(file_ids)} files: {e}")
        return _error(e)
    logger.info(f"PDF unificado descargado exitosamente ({len(file_ids)} archivos)")
    return {"ok": True, "content": content, "message": "PDF unificado generado exitosamente"}

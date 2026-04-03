import httpx
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

async def increment_file_usage(gateway_url: str, file_ids: List[int]) -> Dict[str, Any]:
    """
    Incrementa el contador de uso de uno o varios archivos en app-docs.
    Se utiliza cuando un archivo se asocia a un recurso.

    Args:
        gateway_url: URL del API Gateway
        file_ids: Lista de IDs de archivos

    Returns:
        dict con el resultado de la operación
    """
    if not file_ids:
        return {"ok": False, "message": "No file_ids provided"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{gateway_url}/docs/increment-usage",
                json={"file_ids": file_ids},
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error incrementing file usage: {response.status_code} - {response.text}")
                return {
                    "ok": False,
                    "message": f"Error from app-docs: {response.status_code}"
                }
    except Exception as e:
        logger.error(f"Exception incrementing file usage for files {file_ids}: {e}")
        return {"ok": False, "message": str(e)}


async def decrement_file_usage(gateway_url: str, file_ids: List[int]) -> Dict[str, Any]:
    """
    Decrementa el contador de uso de uno o varios archivos en app-docs.
    Se utiliza cuando un archivo se desvincula de un recurso.

    Args:
        gateway_url: URL del API Gateway
        file_ids: Lista de IDs de archivos

    Returns:
        dict con el resultado de la operación
    """
    if not file_ids:
        return {"ok": False, "message": "No file_ids provided"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{gateway_url}/docs/decrement-usage",
                json={"file_ids": file_ids},
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error decrementing file usage: {response.status_code} - {response.text}")
                return {
                    "ok": False,
                    "message": f"Error from app-docs: {response.status_code}"
                }
    except Exception as e:
        logger.error(f"Exception decrementing file usage for files {file_ids}: {e}")
        return {"ok": False, "message": str(e)}


async def get_file_info(gateway_url: str, file_id: int) -> Dict[str, Any]:
    """
    Obtiene información de un archivo desde app-docs.

    Args:
        gateway_url: URL del API Gateway
        file_id: ID del archivo

    Returns:
        dict con la información del archivo
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{gateway_url}/docs/{file_id}",
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"ok": False, "message": "File not found"}
            else:
                logger.error(f"Error getting file info: {response.status_code} - {response.text}")
                return {
                    "ok": False,
                    "message": f"Error from app-docs: {response.status_code}"
                }
    except Exception as e:
        logger.error(f"Exception getting file info for file {file_id}: {e}")
        return {"ok": False, "message": str(e)}


async def get_files_batch(gateway_url: str, file_ids: List[int]) -> Dict[str, Any]:
    """
    Obtiene información de múltiples archivos desde app-docs.

    Args:
        gateway_url: URL del API Gateway
        file_ids: Lista de IDs de archivos

    Returns:
        dict con la lista de archivos
    """
    if not file_ids:
        return {"ok": True, "data": []}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/docs/batch",
                json={"file_ids": file_ids},
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting files batch: {response.status_code} - {response.text}")
                return {
                    "ok": False,
                    "message": f"Error from app-docs: {response.status_code}"
                }
    except Exception as e:
        logger.error(f"Exception getting files batch for files {file_ids}: {e}")
        return {"ok": False, "message": str(e)}


async def download_unified_pdf(gateway_url: str, file_ids: List[int], cookies: Dict[str, str]) -> Dict[str, Any]:
    """
    Descarga múltiples archivos y los combina en un único PDF desde app-docs.

    Args:
        gateway_url: URL del API Gateway
        file_ids: Lista de IDs de archivos a combinar (en orden)
        cookies: Diccionario de cookies del request (para autenticación)

    Returns:
        dict con 'ok' (bool) y 'content' (bytes del PDF) o 'message' (error)
    """
    if not file_ids:
        return {"ok": False, "message": "No file_ids provided"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/docs/download-unified",
                json={"file_ids": file_ids},
                cookies=cookies,
                timeout=120.0  # Timeout más largo para PDFs grandes
            )

            if response.status_code == 200:
                logger.info(f"PDF unificado descargado exitosamente ({len(file_ids)} archivos)")
                return {
                    "ok": True,
                    "content": response.content,
                    "message": "PDF unificado generado exitosamente"
                }
            else:
                logger.error(f"Error downloading unified PDF: {response.status_code} - {response.text}")
                return {
                    "ok": False,
                    "message": f"Error from app-docs: {response.status_code}"
                }
    except Exception as e:
        logger.error(f"Exception downloading unified PDF for {len(file_ids)} files: {e}")
        return {"ok": False, "message": str(e)}

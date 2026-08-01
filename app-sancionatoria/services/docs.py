from dotenv import load_dotenv
from typing import List, Dict, Any
import httpx
import logging
import os

from utils.generate_service_jwt import generate_service_jwt

load_dotenv()
DOCS_SERVICE_URL = os.getenv("DOCS_SERVICE_URL", "http://app-docs:8003")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")
logger = logging.getLogger(__name__)

def _service_headers() -> Dict[str, str]:
    if not SERVICE_SECRET_KEY:
        raise RuntimeError("SERVICE_SECRET_KEY no configurado, no se puede autenticar contra app-docs")
    token = generate_service_jwt("sanctioning-service", SERVICE_SECRET_KEY)
    return {"x-service-token": token}

async def increment_file_usage( file_ids: List[int]) -> Dict[str, Any]:
    """
    Incrementa el contador de uso de archivos en app-docs al asociarlos a un
    recurso. El contador es lo que evita que el cleanup borre el archivo de
    MinIO mientras siga referenciado.
    """
    if not file_ids:
        return {"ok": False, "message": "No file_ids provided"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{DOCS_SERVICE_URL}/files/increment-usage",
                json={"file_ids": file_ids},
                headers=_service_headers(),
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

async def decrement_file_usage( file_ids: List[int]) -> Dict[str, Any]:
    """
    Decrementa el contador de uso al desvincular archivos de un recurso.
    Al llegar a cero quedan elegibles para el cleanup de app-docs.
    """
    if not file_ids:
        return {"ok": False, "message": "No file_ids provided"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{DOCS_SERVICE_URL}/files/decrement-usage",
                json={"file_ids": file_ids},
                headers=_service_headers(),
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

async def download_unified_pdf(file_ids: List[int], cookies: Dict[str, str]) -> Dict[str, Any]:
    """
    Combina varios archivos en un único PDF vía app-docs. El orden de
    `file_ids` es el orden de las páginas resultantes.

    Devuelve {'ok': True, 'content': bytes} o {'ok': False, 'message': str}.
    """
    if not file_ids:
        return {"ok": False, "message": "No file_ids provided"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{DOCS_SERVICE_URL}/files/download-unified",
                json={"file_ids": file_ids},
                headers=_service_headers(),
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

"""
Servicio de comunicación east-west con app-docs.
Usado por app-infraction para crear/consultar procesos de documentos.
"""
import os
import httpx
import logging
from dotenv import load_dotenv
from utils.generate_service_jwt import generate_service_jwt

load_dotenv()

DOCS_SERVICE_URL = os.getenv("DOCS_SERVICE_URL", "http://app-docs:8003")
SERVICE_SECRET_KEY = os.getenv("SERVICE_SECRET_KEY")

logger = logging.getLogger(__name__)


def _service_headers() -> dict:
    if not SERVICE_SECRET_KEY:
        raise RuntimeError("SERVICE_SECRET_KEY no configurado, no se puede autenticar contra app-docs")
    token = generate_service_jwt("infraction-service", SERVICE_SECRET_KEY)
    return {"x-service-token": token}


async def create_doc_for_professional(
    nombre: str,
    descripcion: str,
    creador_id: int,
    revisor_id: int,
) -> dict:
    """
    Crea un documento en app-docs con el profesional como creador
    y la ingeniera líder como revisora.
    Llama al endpoint de servicio (no requiere token de usuario).

    Returns:
        {"ok": True, "documento_id": int} | {"ok": False, "message": str}
    """
    try:
        payload = {
            "nombre": nombre,
            "descripcion": descripcion,
            "tipo_archivo": "pdf",
            "creador_id": creador_id,
            "revisores_ids": [revisor_id],
            "origen": "informe_tecnico",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{DOCS_SERVICE_URL}/docs/create-service",
                json=payload,
                headers=_service_headers(),
            )
        if response.status_code == 200:
            data = response.json()
            return {"ok": True, "documento_id": data.get("documento_id")}
        else:
            logger.error(f"create_doc_for_professional error {response.status_code}: {response.text}")
            return {"ok": False, "message": f"app-docs error {response.status_code}"}
    except Exception as e:
        logger.error(f"create_doc_for_professional exception: {e}")
        return {"ok": False, "message": str(e)}


async def finalize_doc_as_rejected(documento_id: int) -> dict:
    """
    Finaliza un proceso de documento como rechazado (fuerza estado='finalizado').
    Llama al endpoint de servicio.

    Returns:
        {"ok": True} | {"ok": False, "message": str}
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                f"{DOCS_SERVICE_URL}/docs/finalize-service/{documento_id}",
                headers=_service_headers(),
            )
        if response.status_code == 200:
            return {"ok": True}
        else:
            logger.error(f"finalize_doc_as_rejected error {response.status_code}: {response.text}")
            return {"ok": False, "message": f"app-docs error {response.status_code}"}
    except Exception as e:
        logger.error(f"finalize_doc_as_rejected exception: {e}")
        return {"ok": False, "message": str(e)}


async def get_doc_detail(documento_id: int) -> dict:
    """
    Obtiene el detalle de un documento desde app-docs (service-to-service).

    Returns:
        dict con datos del documento | {"ok": False, "message": str}
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{DOCS_SERVICE_URL}/docs/detail-service/{documento_id}",
                headers=_service_headers(),
            )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {"ok": False, "message": "Documento no encontrado"}
        else:
            logger.error(f"get_doc_detail error {response.status_code}: {response.text}")
            return {"ok": False, "message": f"app-docs error {response.status_code}"}
    except Exception as e:
        logger.error(f"get_doc_detail exception: {e}")
        return {"ok": False, "message": str(e)}

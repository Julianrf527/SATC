"""Gestión de archivos en app-docs (/files) vía satc_shared.clients.FilesClient.

Las funciones conservan sus firmas y el formato de respuesta dict
({'ok': bool, ...}) que esperan las rutas: nunca lanzan.
"""
from dotenv import load_dotenv
from typing import Any, Dict, Iterable, List, Optional
import logging

from satc_shared.clients import FilesClient, NotFoundError, ServiceClientError

load_dotenv()
logger = logging.getLogger(__name__)

# Directo a DOCS_SERVICE_URL con x-service-token de recurso-service.
files_client = FilesClient.from_env("recurso-service")


def _error(e: Exception) -> Dict[str, Any]:
    """Mensaje para el usuario sin detalles internos (el detalle va al log)."""
    if isinstance(e, ServiceClientError) and e.status_code is not None:
        return {"ok": False, "message": f"El gestor documental respondió {e.status_code}"}
    return {"ok": False, "message": "El gestor documental no está disponible"}


async def increment_file_usage(
    file_ids: Optional[List[int]] = None, *, usos: Optional[Iterable[dict]] = None, usuario_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Asocia archivos en app-docs. ``usos`` (``archivos_entidades.usos``)
    registra el dueño (entidad, fila) y quién lo asocia; ``file_ids`` es el
    formato anterior (solo suma ``numero_usos``). Si funciona, lo anota en el
    registro de la petición (``services.usos_archivos``) para compensarlo si
    la operación termina en error antes del commit."""
    from services.usos_archivos import anotar_suma

    lista = list(usos) if usos is not None else None
    if not (lista or file_ids):
        return {"ok": False, "message": "No file_ids provided"}
    try:
        if lista is not None:
            r = await files_client.increment_usage(usos=lista, usuario_id=usuario_id)
        else:
            r = await files_client.increment_usage(file_ids)
        resultado = r.model_dump(exclude_none=True)
    except Exception as e:
        logger.error(f"Error incrementing file usage for {lista or file_ids}: {e}")
        return _error(e)
    if resultado.get("rechazados"):  # validación de app-docs en modo log: solo se informa
        logger.warning(f"app-docs marcó como ajenos {resultado['rechazados']} (usuario {usuario_id})")
    if resultado.get("ok"):
        if lista is None:
            anotar_suma(file_ids)
        elif resultado.get("registrados", 0) == len(lista):
            # Solo si todas eran nuevas: compensar una que ya existía la
            # borraría y el archivo podría quedar sin uso estando en uso.
            anotar_suma(lista)
    return resultado


async def decrement_file_usage(
    file_ids: Optional[List[int]] = None, *, usos: Optional[Iterable[dict]] = None,
) -> Dict[str, Any]:
    """Suelta archivos en app-docs: con ``usos`` borra esas asociaciones; con
    ``file_ids`` (formato anterior) resta 1 a cada uno."""
    lista = list(usos) if usos is not None else None
    if not (lista or file_ids):
        return {"ok": False, "message": "No file_ids provided"}
    try:
        if lista is not None:
            return (await files_client.decrement_usage(usos=lista)).model_dump(exclude_none=True)
        return (await files_client.decrement_usage(file_ids)).model_dump(exclude_none=True)
    except Exception as e:
        logger.error(f"Error decrementing file usage for {lista or file_ids}: {e}")
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

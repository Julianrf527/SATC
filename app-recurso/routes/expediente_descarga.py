"""Descarga del expediente completo en un único PDF (pestaña Consulta) y de
cada uno de sus documentos.

Prefijo en main.py: ``/expedientes``. Lectura (``requiere_lectura``).
El orden de los documentos está en ``services/expediente_documentos.py``.
"""
import logging
import re
from contextlib import AsyncExitStack

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_lectura
from db.deps import get_db_managed
from db.models import Expediente
from satc_shared.archivos import respuesta_archivo
from satc_shared.clients import NotFoundError, ServiceClientError
import services.docs as docs_svc
from services.expediente_documentos import documentos_del_expediente
from services.expediente_involucrados import datos_cliente
from utils.log import insert_log

router = APIRouter()
logger = logging.getLogger(__name__)


async def _expediente(db: AsyncSession, expediente_id: int) -> Expediente:
    expediente = await db.get(Expediente, expediente_id)
    if expediente is None:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    return expediente


@router.get("/{expediente_id}/documentos")
async def listar_documentos_expediente(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """Documentos que entran en la descarga, en el mismo orden (índice para el front)."""
    await requiere_lectura(request)
    expediente = await _expediente(db, expediente_id)
    return {"ok": True, "data": await documentos_del_expediente(db, expediente)}


@router.get("/{expediente_id}/archivos/{file_id}")
async def ver_archivo_expediente(
    request: Request,
    expediente_id: int,
    file_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """Un documento del expediente (botones "Ver documento"). Solo sirve los
    archivos que pertenecen al expediente (los mismos de la descarga
    completa); app-docs ya no se consulta directo desde el navegador. Reenvía
    ``Range`` (visor de PDF) y deja en la auditoría la primera petición."""
    usuario = await requiere_lectura(request)
    expediente = await _expediente(db, expediente_id)
    documento = next((d for d in await documentos_del_expediente(db, expediente) if d["file_id"] == file_id), None)
    if documento is None:
        raise HTTPException(status_code=404, detail="El documento no pertenece a este expediente")

    try:
        respuesta = await respuesta_archivo(docs_svc.files_client, file_id, request.headers,
                                            nombre=f"{documento['descripcion']}.pdf")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el gestor documental")
    except ServiceClientError as e:
        logger.error("Documento %s del expediente %s: %s", file_id, expediente_id, e)
        raise HTTPException(status_code=502, detail="No se pudo obtener el documento")

    if "range" not in request.headers:  # el visor pide luego por rangos: se audita una vez
        try:
            await insert_log(
                db=db, tipo_evento="VER_DOCUMENTO", resultado="EXITOSO", usuario_id=usuario.user_id,
                expediente_id=expediente.id, expediente_radicado=expediente.radicado,
                detalle=f"{documento['descripcion']} (archivo {file_id})", **datos_cliente(request),
            )
            await db.commit()
        except BaseException:
            await respuesta.background()  # cierra la conexión con app-docs
            raise
    return respuesta


@router.get("/{expediente_id}/descargar")
async def descargar_expediente_completo(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """PDF único del expediente. app-docs lo arma y aquí se reenvía por bloques,
    sin cargarlo en memoria. Queda registro en la auditoría."""
    usuario = await requiere_lectura(request)
    expediente = await _expediente(db, expediente_id)

    documentos = await documentos_del_expediente(db, expediente)
    if not documentos:
        raise HTTPException(status_code=404, detail="No se encontraron documentos para este expediente")
    file_ids = [d["file_id"] for d in documentos]

    pila = AsyncExitStack()
    try:
        respuesta = await pila.enter_async_context(docs_svc.files_client.download_unified_stream(file_ids))
    except ServiceClientError as e:
        await pila.aclose()
        logger.error(f"Error generando el PDF del expediente {expediente.id}: {e}")
        raise HTTPException(status_code=502, detail="No se pudo generar el PDF del expediente")

    try:
        await insert_log(
            db=db, tipo_evento="DESCARGAR_EXPEDIENTE", resultado="EXITOSO", usuario_id=usuario.user_id,
            expediente_id=expediente.id, expediente_radicado=expediente.radicado,
            detalle=f"Descarga del expediente completo {expediente.expediente} ({len(file_ids)} documentos)",
            **datos_cliente(request),
        )
        await db.commit()
    except BaseException:
        await pila.aclose()
        raise

    async def _contenido():
        try:
            async for bloque in respuesta.aiter_bytes():
                yield bloque
        finally:
            await pila.aclose()

    nombre = re.sub(r"[^A-Za-z0-9_-]+", "_", expediente.expediente).strip("_")
    return StreamingResponse(
        _contenido(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="concesion_{nombre}_completo.pdf"'},
    )

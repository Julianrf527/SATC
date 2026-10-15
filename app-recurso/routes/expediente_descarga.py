"""Descarga del expediente completo en un único PDF (plan fase 11, pestaña Consulta).

Prefijo en main.py: ``/expedientes``. Lectura (``requiere_lectura``).
El orden de los documentos está en ``services/expediente_documentos.py``.
"""
import logging
import re
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_lectura
from db.deps import get_db_managed
from db.models import Expediente
from services.docs import download_unified_pdf
from services.expediente_documentos import documentos_del_expediente

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


@router.get("/{expediente_id}/descargar")
async def descargar_expediente_completo(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    await requiere_lectura(request)
    expediente = await _expediente(db, expediente_id)

    documentos = await documentos_del_expediente(db, expediente)
    if not documentos:
        raise HTTPException(status_code=404, detail="No se encontraron documentos para este expediente")
    file_ids = [d["file_id"] for d in documentos]
    logger.info(f"[DOWNLOAD] Expediente {expediente.expediente}: {len(file_ids)} documentos a combinar")

    resultado = await download_unified_pdf(file_ids=file_ids, cookies=dict(request.cookies))
    if not resultado.get("ok"):
        raise HTTPException(
            status_code=502,
            detail=f"Error generando PDF: {resultado.get('message', 'Error desconocido')}",
        )

    nombre = re.sub(r"[^A-Za-z0-9_-]+", "_", expediente.expediente).strip("_")
    return StreamingResponse(
        BytesIO(resultado["content"]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="concesion_{nombre}_completo.pdf"'},
    )

"""Compensación del uso de archivos (``numero_usos`` de app-docs) por petición.

El uso de un archivo se SUMA en app-docs ANTES del commit (si no se pudiera
registrar, no se guarda nada: un archivo referenciado con ``numero_usos = 0``
lo borraría el cleanup) y el de los reemplazados se RESTA después. Si la
operación falla después de sumar (excepción, ``HTTPException`` o commit
fallido) el contador quedaría inflado y el archivo huérfano nunca se borraría.

Punto común: ``db.deps.get_db_managed`` (lo usan todas las rutas de
escritura) abre un registro por petición con ``registro_peticion``:

- Cada suma exitosa se anota en el registro de la petición en curso
  (``anotar_suma``): ``services.docs.increment_file_usage`` (lo usan
  ``_incrementar``, ``registrar_archivos``, ``crear_acto``,
  ``cargar_concepto_final``, comprobante de pago, anexos...) y el servicio de
  revisión compartido (versiones y adjuntos) vía ``FilesConRegistro``.
- Al hacer ``commit`` la sesión vacía el registro: lo sumado ya quedó
  respaldado por la BD.
- Si la petición termina en error, ``compensar`` resta exactamente lo sumado
  y no confirmado (best-effort, con log). Nunca oculta el error original.

Fuera de una petición (scheduler, scripts) no hay registro y nada se anota.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, AsyncIterator, Iterable, Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Lotes de file_ids sumados en la petición en curso y aún no confirmados.
_sumados: ContextVar[Optional[list[list[int]]]] = ContextVar("recurso_usos_sumados", default=None)


def anotar_suma(file_ids: Iterable[Optional[int]]) -> None:
    """Anota un lote sumado con éxito en app-docs (no-op fuera de una petición)."""
    lotes = _sumados.get()
    ids = [int(f) for f in file_ids if f]
    if lotes is not None and ids:
        lotes.append(ids)


def pendientes() -> list[list[int]]:
    """Lotes sumados y aún no confirmados de la petición en curso (copia)."""
    return [list(l) for l in (_sumados.get() or [])]


async def compensar(lotes: list[list[int]], contexto: str = "") -> None:
    """Resta los usos de ``lotes`` (uno por lote, igual que se sumaron).
    Best-effort: registra en log y NUNCA lanza (no debe ocultar el error original)."""
    import services.docs as docs_svc

    for ids in lotes:
        try:
            resultado = await docs_svc.decrement_file_usage(ids)
            if resultado.get("ok"):
                logger.warning(f"Uso de archivos compensado {ids} por operación fallida {contexto}".rstrip())
            else:
                logger.error(f"No se pudo compensar el uso de {ids} {contexto}: {resultado}".rstrip())
        except Exception as e:  # pragma: no cover - decrement_file_usage ya no lanza
            logger.error(f"No se pudo compensar el uso de {ids} {contexto}: {e}".rstrip())


@asynccontextmanager
async def registro_peticion(db: AsyncSession, contexto: str = "") -> AsyncIterator[list[list[int]]]:
    """Registro de usos sumados de una petición ligado a su sesión ``db``.

    El ``commit`` de la sesión lo vacía; si el bloque termina con una
    excepción (``Exception``) se compensa lo pendiente y se relanza."""
    lotes: list[list[int]] = []
    token = _sumados.set(lotes)

    def _confirmado(_session: Any) -> None:
        lotes.clear()

    sync_session = db.sync_session
    event.listen(sync_session, "after_commit", _confirmado)
    try:
        yield lotes
    except Exception:
        if lotes:
            await compensar(list(lotes), contexto)
            lotes.clear()
        raise
    finally:
        event.remove(sync_session, "after_commit", _confirmado)
        try:
            _sumados.reset(token)
        except ValueError:  # otro contexto (no debería pasar): basta con soltar la lista
            _sumados.set(None)


class FilesConRegistro:
    """Envuelve el cliente de app-docs que usa el servicio de revisión
    compartido (``satc_shared.review_process``) para anotar sus sumas."""

    def __init__(self, files: Any):
        self._files = files

    async def increment_usage(self, file_ids: list[int]) -> Any:
        resultado = await self._files.increment_usage(file_ids)
        ok = getattr(resultado, "ok", None)
        if ok is None and isinstance(resultado, dict):
            ok = resultado.get("ok")
        if ok is not False:
            anotar_suma(file_ids)
        return resultado

    def __getattr__(self, nombre: str) -> Any:
        return getattr(self._files, nombre)

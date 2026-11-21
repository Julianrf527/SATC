"""Respuesta de descarga para los endpoints ``GET /<modulo>/archivos/{file_id}``.

El módulo valida con sus tablas que el usuario puede ver la entidad dueña del
archivo y luego responde con ``respuesta_archivo``, que transmite los bytes de
app-docs sin cargarlos en memoria::

    from satc_shared.archivos import respuesta_archivo

    @router.get("/archivos/{file_id}")
    async def descargar(file_id: int, request: Request, ...):
        acto = ...  # dueño del archivo según las tablas del módulo + permiso del usuario
        try:
            return await respuesta_archivo(files_client, file_id, request.headers, nombre=acto.nombre_archivo)
        except NotFoundError:
            raise HTTPException(404, "Archivo no encontrado")
        except ServiceClientError:
            raise HTTPException(502, "No se pudo obtener el archivo")

Reenvía ``Range``/``If-Range`` (pdf.js pide los PDF por rangos) y devuelve el
mismo status de app-docs (200, 206 o 416) con ``Content-Length``,
``Content-Range``, ``Accept-Ranges`` y ``ETag``. ``Content-Disposition`` lleva
el nombre original (app-docs solo conoce el nombre por hash) y se conserva la
decisión inline/adjunto de app-docs (inline solo PDF e imágenes).

Requiere starlette (todos los servicios son FastAPI); se importa al usarse para
no volverlo dependencia del paquete.
"""
from __future__ import annotations

import re
import unicodedata
from contextlib import AsyncExitStack
from typing import Mapping
from urllib.parse import quote

from .clients.files import FilesClient

# Cabeceras de app-docs que se pasan tal cual al navegador.
_REENVIADAS = ("content-type", "content-length", "content-range", "accept-ranges", "etag")

CABECERAS_SEGURIDAD = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "private, no-cache",
}


def content_disposition(nombre: str | None, disposicion: str = "attachment") -> str:
    """``filename`` ASCII de respaldo + ``filename*`` UTF-8 (RFC 6266/5987)
    para nombres con tildes. Sin ruta ni comillas ni caracteres de control."""
    nombre = (nombre or "").replace("\\", "/").rsplit("/", 1)[-1]
    nombre = re.sub(r'[\x00-\x1f\x7f"]', "", nombre).strip() or "archivo"
    ascii_ = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("ascii")
    ascii_ = re.sub(r"[^A-Za-z0-9._ ()-]", "_", ascii_).strip() or "archivo"
    if ascii_ == nombre:
        return f'{disposicion}; filename="{nombre}"'
    return f"{disposicion}; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nombre, safe='')}"


def _disposicion_de(cabecera: str | None) -> str:
    return "inline" if (cabecera or "").strip().lower().startswith("inline") else "attachment"


async def respuesta_archivo(
    files: FilesClient,
    file_id: int,
    request_headers: Mapping[str, str],
    *,
    nombre: str | None = None,
    timeout: float = 300.0,
):
    """StreamingResponse con el archivo ``file_id`` de app-docs.

    ``request_headers``: cabeceras de la petición del navegador (se toman
    ``range`` e ``if-range``). Lanza los errores de ``FilesClient``
    (``NotFoundError`` si no existe, ``ServiceClientError`` si app-docs falla)
    antes de empezar a responder, para que el módulo elija el status."""
    from starlette.background import BackgroundTask
    from starlette.responses import StreamingResponse

    pila = AsyncExitStack()
    resp = await pila.enter_async_context(files.download_stream(
        file_id,
        range=request_headers.get("range"),
        if_range=request_headers.get("if-range"),
        timeout=timeout,
    ))

    cerrado = False

    async def cerrar() -> None:
        nonlocal cerrado
        if not cerrado:
            cerrado = True
            await pila.aclose()

    async def cuerpo():
        try:
            async for bloque in resp.aiter_bytes():  # app-docs no comprime: bytes == cuerpo
                yield bloque
        finally:
            await cerrar()

    headers = {k: resp.headers[k] for k in _REENVIADAS if k in resp.headers}
    media_type = headers.pop("content-type", "application/octet-stream")
    headers.update(CABECERAS_SEGURIDAD)
    headers["Content-Disposition"] = content_disposition(
        nombre, _disposicion_de(resp.headers.get("content-disposition"))
    )
    return StreamingResponse(
        cuerpo(),
        status_code=resp.status_code,
        media_type=media_type,
        headers=headers,
        background=BackgroundTask(cerrar),  # por si el cliente corta antes de leer el cuerpo
    )

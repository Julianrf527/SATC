from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Iterable, Mapping

import httpx

from .base import ServiceClient
from .models import FileIdsRequest, FileInfo, UploadResult, UsageResult, UsoArchivo, UsosRequest


class FilesClient(ServiceClient):
    """Cliente de la gestión de archivos de app-docs (``/files``), directo a
    ``DOCS_SERVICE_URL``.

    Implementa el protocolo ``FileUsageTracker`` (``increment_usage`` /
    ``decrement_usage``) que usa ``satc_shared.review_process``.

    Dueños de los archivos: al asociar un archivo a una entidad, mandar
    ``usos`` (file_id, entidad, entidad_id) y el ``usuario_id`` que asocia en
    ``increment_usage``; al desvincular, los mismos ``usos`` en
    ``decrement_usage``. app-docs pone el servicio a partir del token.

    Nota de permisos en app-docs: ``/files/batch``, ``increment-usage``,
    ``decrement-usage``, ``registrar-usos`` y ``download-unified`` aceptan SOLO los callers de su
    ``EXPECTED_CALLERS`` (hoy sanctioning-service, infraction-service y
    recurso-service).
    """

    target = "app-docs"

    @classmethod
    def from_env(
        cls,
        service_name: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
    ) -> "FilesClient":
        return cls(
            cls._env("DOCS_SERVICE_URL", default="http://app-docs:8003"),
            service_name=service_name,
            secret_key=cls._env("SERVICE_SECRET_KEY"),
            timeout=timeout,
            transport=transport,
        )

    async def upload(
        self,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        *,
        usuario_id: int | None = None,
        timeout: float = 60.0,
    ) -> UploadResult:
        """POST /files/upload (multipart ``archivo``). No incrementa numero_usos:
        quien asocie el archivo a un recurso debe llamar a ``increment_usage``.

        ``usuario_id``: usuario a cuyo nombre se sube. app-docs lo registra y
        luego solo deja asociar a ese usuario los archivos que subió."""
        resp = await self.request(
            "POST", "/files/upload",
            files={"archivo": (filename, content, content_type)},
            data={"usuario_id": str(usuario_id)} if usuario_id is not None else None,
            timeout=timeout,
        )
        return UploadResult.model_validate(self.json_body(resp, self.target))

    async def get(self, file_id: int) -> FileInfo:
        """GET /files/{id}. Lanza NotFoundError si no existe."""
        resp = await self.request("GET", f"/files/{file_id}")
        return FileInfo.model_validate(self.json_body(resp, self.target).get("data") or {})

    async def batch(self, file_ids: list[int]) -> list[FileInfo]:
        """POST /files/batch."""
        if not file_ids:
            return []
        resp = await self.request("POST", "/files/batch", json=FileIdsRequest(file_ids=file_ids).model_dump())
        data = self.json_body(resp, self.target).get("data", []) or []
        return [FileInfo.model_validate(f) for f in data]

    @asynccontextmanager
    async def download(self, file_id: int, *, timeout: float = 120.0) -> AsyncIterator[httpx.Response]:
        """GET /files/download/{id} en streaming::

            async with files.download(7) as resp:
                async for chunk in resp.aiter_bytes():
                    ...
        """
        async with self.stream("GET", f"/files/download/{file_id}", timeout=timeout) as resp:
            yield resp

    @asynccontextmanager
    async def download_stream(
        self,
        file_id: int,
        *,
        range: str | None = None,
        if_range: str | None = None,
        timeout: float = 300.0,
    ) -> AsyncIterator[httpx.Response]:
        """GET /files/download/{id} en streaming reenviando ``Range``/``If-Range``.
        La respuesta puede ser 200, 206 (parcial) o 416 (rango fuera del
        archivo); otro status lanza (404 -> NotFoundError). Para responderle al
        navegador usar ``satc_shared.archivos.respuesta_archivo``."""
        headers = {}
        if range:
            headers["Range"] = range
        if if_range:
            headers["If-Range"] = if_range
        async with self.stream(
            "GET", f"/files/download/{file_id}", timeout=timeout, headers=headers, ok=(200, 206, 416),
        ) as resp:
            yield resp

    async def download_bytes(self, file_id: int, *, timeout: float = 120.0) -> bytes:
        resp = await self.request("GET", f"/files/download/{file_id}", timeout=timeout)
        return resp.content

    @staticmethod
    def _cuerpo_usos(
        file_ids: list[int] | None, usos: Iterable[UsoArchivo | Mapping] | None, usuario_id: int | None,
    ) -> dict:
        if usos is not None:
            lista = [u if isinstance(u, UsoArchivo) else UsoArchivo.model_validate(u) for u in usos]
            return UsosRequest(usos=lista, usuario_id=usuario_id).model_dump(exclude_none=True)
        return FileIdsRequest(file_ids=list(file_ids or [])).model_dump()

    async def _usos(self, ruta: str, cuerpo: dict) -> UsageResult:
        resp = await self.request("PUT", ruta, json=cuerpo, ok=(200, 403))
        body = self.json_body(resp, self.target)
        if resp.status_code == 403 and not (isinstance(body, dict) and "rechazados" in body):
            self._raise_for_status(resp)  # 403 de autenticación: lanza
        return UsageResult.model_validate(body)

    async def increment_usage(
        self,
        file_ids: list[int] | None = None,
        *,
        usos: Iterable[UsoArchivo | Mapping] | None = None,
        usuario_id: int | None = None,
    ) -> UsageResult:
        """PUT /files/increment-usage.

        - ``increment_usage([3, 9])``: formato anterior, suma 1 a numero_usos.
        - ``increment_usage(usos=[{"file_id": 3, "entidad": "acto", "entidad_id": 55}], usuario_id=7)``:
          registra el dueño (idempotente). Si app-docs rechaza archivos ajenos
          devuelve ``ok=False`` con ``rechazados`` (no lanza)."""
        return await self._usos("/files/increment-usage", self._cuerpo_usos(file_ids, usos, usuario_id))

    async def decrement_usage(
        self,
        file_ids: list[int] | None = None,
        *,
        usos: Iterable[UsoArchivo | Mapping] | None = None,
    ) -> UsageResult:
        """PUT /files/decrement-usage (nunca baja de 0). Con ``usos`` borra esas
        asociaciones del servicio."""
        return await self._usos("/files/decrement-usage", self._cuerpo_usos(file_ids, usos, None))

    async def registrar_usos(self, usos: Iterable[UsoArchivo | Mapping]) -> UsageResult:
        """POST /files/registrar-usos: carga inicial de dueños de asociaciones
        que ya existían (no toca numero_usos). Máx. 1000 por llamada."""
        cuerpo = self._cuerpo_usos(None, usos, None)
        resp = await self.request("POST", "/files/registrar-usos", json={"usos": cuerpo["usos"]})
        return UsageResult.model_validate(self.json_body(resp, self.target))

    @asynccontextmanager
    async def download_unified_stream(
        self, file_ids: list[int], *, timeout: float = 300.0,
    ) -> AsyncIterator[httpx.Response]:
        """POST /files/download-unified en streaming (sin cargar el PDF en memoria)::

            async with files.download_unified_stream([3, 9]) as resp:
                async for chunk in resp.aiter_bytes():
                    ...
        """
        async with self.stream(
            "POST", "/files/download-unified",
            json=FileIdsRequest(file_ids=file_ids).model_dump(), timeout=timeout,
        ) as resp:
            yield resp

    async def download_unified(
        self,
        file_ids: list[int],
        *,
        cookies: Mapping[str, str] | None = None,
        timeout: float = 120.0,
    ) -> bytes:
        """POST /files/download-unified: PDF combinado en el orden de ``file_ids``."""
        resp = await self.request(
            "POST", "/files/download-unified",
            json=FileIdsRequest(file_ids=file_ids).model_dump(),
            cookies=cookies, timeout=timeout,
        )
        return resp.content

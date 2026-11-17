from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Mapping

import httpx

from .base import ServiceClient
from .models import FileIdsRequest, FileInfo, UploadResult, UsageResult


class FilesClient(ServiceClient):
    """Cliente de la gestión de archivos de app-docs (``/files``), directo a
    ``DOCS_SERVICE_URL``.

    Implementa el protocolo ``FileUsageTracker`` (``increment_usage`` /
    ``decrement_usage``) que usa ``satc_shared.review_process``.

    Nota de permisos en app-docs: ``/files/batch``, ``increment-usage``,
    ``decrement-usage`` y ``download-unified`` aceptan SOLO los callers de su
    ``EXPECTED_CALLERS`` (hoy sanctioning-service e infraction-service).
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
        timeout: float = 60.0,
    ) -> UploadResult:
        """POST /files/upload (multipart ``archivo``). No incrementa numero_usos:
        quien asocie el archivo a un recurso debe llamar a ``increment_usage``."""
        resp = await self.request(
            "POST", "/files/upload",
            files={"archivo": (filename, content, content_type)},
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

    async def download_bytes(self, file_id: int, *, timeout: float = 120.0) -> bytes:
        resp = await self.request("GET", f"/files/download/{file_id}", timeout=timeout)
        return resp.content

    async def increment_usage(self, file_ids: list[int]) -> UsageResult:
        """PUT /files/increment-usage."""
        resp = await self.request(
            "PUT", "/files/increment-usage", json=FileIdsRequest(file_ids=file_ids).model_dump()
        )
        return UsageResult.model_validate(self.json_body(resp, self.target))

    async def decrement_usage(self, file_ids: list[int]) -> UsageResult:
        """PUT /files/decrement-usage (nunca baja de 0)."""
        resp = await self.request(
            "PUT", "/files/decrement-usage", json=FileIdsRequest(file_ids=file_ids).model_dump()
        )
        return UsageResult.model_validate(self.json_body(resp, self.target))

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

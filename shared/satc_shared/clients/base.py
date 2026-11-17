from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Mapping

import httpx

from ..auth import ServiceTokenConfigError, service_headers
from .errors import (
    NotFoundError,
    ServiceAuthError,
    ServiceConfigError,
    ServiceResponseError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)

DEFAULT_TIMEOUT = 10.0


class ServiceClient:
    """Cliente HTTP base east-west: firma cada petición con el service JWT del
    servicio llamante y traduce fallos a errores tipados.

    Abre un ``httpx.AsyncClient`` por llamada (igual que el código que
    reemplaza); ``transport`` permite inyectar un ``httpx.MockTransport`` en tests.
    """

    target: str = "service"

    def __init__(
        self,
        base_url: str,
        *,
        service_name: str,
        secret_key: str | None,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not base_url:
            raise ServiceConfigError(f"URL de {self.target} no configurada", service=self.target)
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name
        self._secret_key = secret_key
        self.timeout = timeout
        self._transport = transport

    # ------------------------------------------------------------------ util
    @staticmethod
    def _env(*names: str, default: str | None = None) -> str | None:
        for name in names:
            value = os.getenv(name)
            if value:
                return value
        return default

    def headers(self) -> dict[str, str]:
        try:
            return service_headers(self.service_name, self._secret_key)
        except ServiceTokenConfigError as e:
            raise ServiceConfigError(
                f"SERVICE_SECRET_KEY no configurado, no se puede autenticar contra {self.target}",
                service=self.target,
            ) from e

    def _client(self, timeout: float | None, cookies: Mapping[str, str] | None = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.timeout if timeout is None else timeout,
            transport=self._transport,
            cookies=dict(cookies) if cookies else None,
        )

    def _raise_for_status(self, response: httpx.Response, ok: tuple[int, ...] = (200,)) -> None:
        if response.status_code in ok:
            return
        try:
            body = response.text
        except httpx.ResponseNotRead:
            body = ""
        kwargs = dict(service=self.target, status_code=response.status_code, body=body)
        msg = f"Error from {self.target}: {response.status_code}"
        if response.status_code in (401, 403):
            raise ServiceAuthError(msg, **kwargs)
        if response.status_code == 404:
            raise NotFoundError(msg, **kwargs)
        raise ServiceResponseError(msg, **kwargs)

    # --------------------------------------------------------------- request
    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Mapping[str, Any] | None = None,
        files: Any = None,
        cookies: Mapping[str, str] | None = None,
        timeout: float | None = None,
        ok: tuple[int, ...] = (200,),
    ) -> httpx.Response:
        headers = self.headers()
        url = f"{self.base_url}{path}"
        try:
            async with self._client(timeout, cookies) as client:
                response = await client.request(
                    method, url, json=json, params=params, files=files, headers=headers,
                )
        except httpx.TimeoutException as e:
            raise ServiceTimeoutError(f"Timeout llamando a {self.target}: {e}", service=self.target) from e
        except httpx.HTTPError as e:
            raise ServiceUnavailableError(f"Error de red llamando a {self.target}: {e}", service=self.target) from e
        self._raise_for_status(response, ok)
        return response

    @asynccontextmanager
    async def stream(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        timeout: float | None = None,
    ) -> AsyncIterator[httpx.Response]:
        headers = self.headers()
        url = f"{self.base_url}{path}"
        try:
            async with self._client(timeout) as client:
                async with client.stream(method, url, json=json, headers=headers) as response:
                    if response.status_code != 200:
                        await response.aread()
                    self._raise_for_status(response)
                    yield response
        except httpx.TimeoutException as e:
            raise ServiceTimeoutError(f"Timeout llamando a {self.target}: {e}", service=self.target) from e
        except httpx.HTTPError as e:
            raise ServiceUnavailableError(f"Error de red llamando a {self.target}: {e}", service=self.target) from e

    @staticmethod
    def json_body(response: httpx.Response, service: str) -> Any:
        try:
            return response.json()
        except ValueError as e:
            raise ServiceResponseError(
                f"Respuesta no JSON de {service}", service=service,
                status_code=response.status_code, body=response.text,
            ) from e

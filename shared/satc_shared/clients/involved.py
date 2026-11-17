from __future__ import annotations

import httpx

from .base import ServiceClient
from .errors import ServiceResponseError


def normalize_involved_url(raw: str) -> str:
    """Base del API de involucrados: siempre termina en ``/involved`` (las
    variables de entorno históricas a veces lo incluyen y a veces no)."""
    raw = raw.rstrip("/")
    return raw if raw.endswith("/involved") else f"{raw}/involved"


class InvolvedClient(ServiceClient):
    """Cliente de app-involved, directo a ``INVOLVED_SERVICE_URL`` (o el legado
    ``INVOLVED_ROUTE``), con el sufijo ``/involved`` normalizado."""

    target = "app-involved"

    def __init__(self, base_url: str, **kwargs):
        super().__init__(normalize_involved_url(base_url), **kwargs)

    @classmethod
    def from_env(
        cls,
        service_name: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
    ) -> "InvolvedClient":
        return cls(
            cls._env("INVOLVED_SERVICE_URL", "INVOLVED_ROUTE", default="http://app-involved:8004"),
            service_name=service_name,
            secret_key=cls._env("SERVICE_SECRET_KEY"),
            timeout=timeout,
            transport=transport,
        )

    async def bulk(self, ids: list[int]) -> list[dict]:
        """POST /involved/bulk -> lista de involucrados (dicts tal cual los
        devuelve app-involved). Lanza ServiceResponseError si ``ok`` es falso."""
        if not ids:
            return []
        resp = await self.request("POST", "/bulk", json={"ids": list(ids)})
        body = self.json_body(resp, self.target)
        if not body.get("ok"):
            raise ServiceResponseError(
                "app-involved respondió ok=false", service=self.target,
                status_code=resp.status_code, body=resp.text,
            )
        return list(body.get("data") or [])

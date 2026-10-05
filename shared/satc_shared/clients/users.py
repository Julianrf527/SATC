from __future__ import annotations

import httpx

from .base import ServiceClient
from .models import (
    AlertReportRequest,
    NotificationCreate,
    UserInfo,
    VerifyPermissionRequest,
)


class UsersClient(ServiceClient):
    """Cliente de app-users. Todas las llamadas van DIRECTO al servicio
    (``USER_SERVICE_URL``), no vía gateway, autenticadas con x-service-token."""

    target = "app-users"

    @classmethod
    def from_env(
        cls,
        service_name: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
    ) -> "UsersClient":
        return cls(
            cls._env("USER_SERVICE_URL", "USERS_SERVICE_URL", default="http://app-users:8001"),
            service_name=service_name,
            secret_key=cls._env("SERVICE_SECRET_KEY"),
            timeout=timeout,
            transport=transport,
        )

    async def verify_permission(self, user_id: int, permission: str) -> bool:
        """POST /role/verify -> ``tiene_permiso``."""
        body = VerifyPermissionRequest(user_id=user_id, permission_name=permission)
        resp = await self.request("POST", "/role/verify", json=body.model_dump())
        return bool(self.json_body(resp, self.target).get("tiene_permiso", False))

    async def users_by_permission(self, permission: str) -> list[UserInfo]:
        """GET /user/permission/{permission}."""
        resp = await self.request("GET", f"/user/permission/{permission}")
        data = self.json_body(resp, self.target).get("data", []) or []
        return [UserInfo.model_validate(u) for u in data]

    async def users_batch(self, user_ids: list[int]) -> list[UserInfo]:
        """POST /user/batch."""
        if not user_ids:
            return []
        resp = await self.request("POST", "/user/batch", json={"user_ids": list(user_ids)})
        data = self.json_body(resp, self.target).get("data", []) or []
        return [UserInfo.model_validate(u) for u in data]

    async def create_notification(
        self,
        notification: NotificationCreate | None = None,
        *,
        timeout: float = 5.0,
        **fields,
    ) -> None:
        """POST /notification/add (acepta 200 y 201)."""
        payload = notification or NotificationCreate(**fields)
        await self.request(
            "POST", "/notification/add", json=payload.model_dump(),
            timeout=timeout, ok=(200, 201),
        )

    async def send_alert_report(
        self,
        emails: list[str],
        alertas_data: dict,
        *,
        title: str,
        timeout: float = 30.0,
    ) -> None:
        """POST /email/send-alert-report?title=..."""
        body = AlertReportRequest(emails=emails, alertas_data=alertas_data)
        await self.request(
            "POST", "/email/send-alert-report", params={"title": title},
            json=body.model_dump(), timeout=timeout,
        )

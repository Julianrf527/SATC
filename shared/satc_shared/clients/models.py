"""Modelos Pydantic de request/response de las APIs internas (east-west)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class _Abierto(BaseModel):
    # Las APIs devuelven más campos de los que se tipan aquí: se conservan.
    model_config = ConfigDict(extra="allow")


# ------------------------------------------------------------------ app-users
class UserInfo(_Abierto):
    id: int
    nombre: str | None = None
    correo: str | None = None
    numero_documento: str | int | None = None


class VerifyPermissionRequest(BaseModel):
    user_id: int
    permission_name: str


class NotificationCreate(BaseModel):
    mensaje: str
    id_vinculada: str
    tipo: str
    usuario_id: int


class AlertReportRequest(BaseModel):
    emails: list[str]
    alertas_data: dict[str, Any]


# ------------------------------------------------------------------- app-docs
class FileIdsRequest(BaseModel):
    file_ids: list[int]


class FileInfo(_Abierto):
    id: int
    file_url: str
    content_type: str | None = None
    file_size: int | None = None
    numero_usos: int = 0


class UploadResult(_Abierto):
    ok: bool = True
    file_id: int
    file_url: str
    file_hash: str
    message: str | None = None
    deduplicated: bool = False
    numero_usos: int = 0


class UsageResult(_Abierto):
    ok: bool
    message: str | None = None


# --------------------------------------------------------------- app-involved
class InvolucradoInfo(_Abierto):
    id: int

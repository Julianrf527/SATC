"""Modelos Pydantic de request/response de las APIs internas (east-west)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


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
    # Formato nuevo (usos): asociaciones creadas/borradas, ids inexistentes y,
    # con la validación activa, los archivos ajenos que hicieron rechazar el lote.
    registrados: int = 0
    quitados: int = 0
    no_encontrados: list[int] = []
    rechazados: list[int] = []


class UsoArchivo(BaseModel):
    """Entidad de un módulo que usa un archivo. ``servicio`` no va: app-docs lo
    toma del service-token."""

    file_id: int
    entidad: str
    entidad_id: str

    @field_validator("entidad_id", mode="before")
    @classmethod
    def _a_texto(cls, v: Any) -> Any:
        return str(v) if isinstance(v, int) else v


class UsosRequest(BaseModel):
    file_ids: list[int] | None = None
    usos: list[UsoArchivo] | None = None
    usuario_id: int | None = None


# --------------------------------------------------------------- app-involved
class InvolucradoInfo(_Abierto):
    id: int

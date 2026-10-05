"""Clientes HTTP async tipados para la comunicación east-west entre servicios.

Todos firman con el service JWT del servicio llamante (``service_name`` +
``SERVICE_SECRET_KEY``) y lanzan errores tipados (``ServiceClientError`` y
subclases). Los wrappers de cada servicio deciden la política ante fallo
(fail-closed en permisos, ``{}``/``[]`` en enriquecimiento, etc.).
"""
from .base import ServiceClient
from .errors import (
    NotFoundError,
    ServiceAuthError,
    ServiceClientError,
    ServiceConfigError,
    ServiceResponseError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)
from .files import FilesClient
from .involved import InvolvedClient, normalize_involved_url
from .models import (
    FileInfo,
    InvolucradoInfo,
    NotificationCreate,
    UploadResult,
    UsageResult,
    UserInfo,
)
from .users import UsersClient

__all__ = [
    "FileInfo",
    "FilesClient",
    "InvolucradoInfo",
    "InvolvedClient",
    "NotFoundError",
    "NotificationCreate",
    "ServiceAuthError",
    "ServiceClient",
    "ServiceClientError",
    "ServiceConfigError",
    "ServiceResponseError",
    "ServiceTimeoutError",
    "ServiceUnavailableError",
    "UploadResult",
    "UsageResult",
    "UserInfo",
    "UsersClient",
    "normalize_involved_url",
]

from __future__ import annotations


class ServiceClientError(Exception):
    """Base de errores de los clientes inter-servicio."""

    def __init__(self, message: str, *, service: str = "", status_code: int | None = None, body: str = ""):
        super().__init__(message)
        self.service = service
        self.status_code = status_code
        self.body = body


class ServiceConfigError(ServiceClientError):
    """Falta configuración (URL o SERVICE_SECRET_KEY)."""


class ServiceUnavailableError(ServiceClientError):
    """Timeout o error de red hablando con el servicio."""


class ServiceTimeoutError(ServiceUnavailableError):
    """Timeout específico (subclase de ServiceUnavailableError)."""


class ServiceAuthError(ServiceClientError):
    """El servicio rechazó la autenticación (401/403)."""


class NotFoundError(ServiceClientError):
    """404 del servicio."""


class ServiceResponseError(ServiceClientError):
    """Respuesta no-2xx no clasificada, o cuerpo inesperado."""

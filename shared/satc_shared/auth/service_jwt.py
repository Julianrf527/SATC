from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Iterable, Mapping

from jose import jwt

SERVICE_TOKEN_HEADER = "x-service-token"
DEFAULT_ALGORITHM = "HS256"
DEFAULT_TTL = timedelta(minutes=5)

# Identidad de servicio -> variable de entorno con su secreto, tal como la
# reciben los servicios receptores en docker-compose (peer secrets).
SERVICE_SECRET_ENV: dict[str, str] = {
    "sanctioning-service": "SANCTIONING_SERVICE_SECRET",
    "infraction-service": "INFRACTION_SERVICE_SECRET",
    "docs-service": "DOCS_SERVICE_SECRET",
    "involved-service": "INVOLVED_SERVICE_SECRET",
}


class ServiceTokenError(Exception):
    """Base de errores de verificación del service JWT."""


class ServiceTokenConfigError(ServiceTokenError):
    """El receptor no tiene ningún secreto de caller configurado (hoy: HTTP 500)."""


class ServiceTokenMissing(ServiceTokenError):
    """No llegó la cabecera x-service-token (hoy: HTTP 403 'Service token requerido')."""


class ServiceTokenInvalid(ServiceTokenError):
    """Firma inválida/expirada o identidad falseada (hoy: HTTP 403 'Service token inválido')."""


def generate_service_jwt(
    service_name: str,
    secret_key: str,
    *,
    ttl: timedelta = DEFAULT_TTL,
    algorithm: str = DEFAULT_ALGORITHM,
) -> str:
    """Firma el token de servicio con los mismos claims de siempre."""
    now = datetime.now(timezone.utc)
    payload = {
        "service": service_name,
        "exp": now + ttl,
        "iat": now,
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def service_headers(service_name: str, secret_key: str | None) -> dict[str, str]:
    """Cabeceras de autenticación east-west. Lanza si falta el secreto propio."""
    if not secret_key:
        raise ServiceTokenConfigError(
            f"SERVICE_SECRET_KEY no configurado: {service_name} no puede autenticarse"
        )
    return {SERVICE_TOKEN_HEADER: generate_service_jwt(service_name, secret_key)}


def expected_callers_from_env(
    callers: Iterable[str],
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Construye ``{caller: secreto}`` para los callers permitidos, omitiendo
    los que no tengan secreto configurado (mismo comportamiento que los
    ``EXPECTED_CALLERS`` que tenía cada servicio)."""
    env = os.environ if environ is None else environ
    result: dict[str, str] = {}
    for caller in callers:
        var = SERVICE_SECRET_ENV.get(caller)
        if var is None:
            raise KeyError(f"Servicio desconocido: {caller}")
        secret = env.get(var)
        if secret:
            result[caller] = secret
    return result


def identify_caller(
    token: str | None,
    expected_callers: Mapping[str, str],
    *,
    algorithm: str = DEFAULT_ALGORITHM,
) -> str:
    """Devuelve la identidad verificada del caller.

    Prueba la firma contra el secreto de cada caller esperado; el que valida
    determina la identidad, y el claim ``service`` debe coincidir con ella (una
    firma válida con identidad falseada se rechaza).
    """
    if not expected_callers:
        raise ServiceTokenConfigError("No hay secretos de servicio configurados")
    if not token:
        raise ServiceTokenMissing("Service token requerido")

    for caller_name, secret in expected_callers.items():
        try:
            payload = jwt.decode(token, secret, algorithms=[algorithm])
        except Exception:
            continue
        if payload.get("service") != caller_name:
            raise ServiceTokenInvalid("Service token inválido")
        return caller_name

    raise ServiceTokenInvalid("Service token inválido")

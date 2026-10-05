"""Service JWT (cabecera ``x-service-token``) compartido por todos los servicios.

Esquema (idéntico al que cada servicio tenía copiado en
``utils/generate_service_jwt.py`` / ``utils/verify_token.py``):

- Claims: ``{"service": <nombre>, "iat": now, "exp": now + 5 min}``.
- Algoritmo HS256 (``JWT_ALGORITHM`` en el receptor, default HS256).
- Cada servicio firma con SU secreto (``SERVICE_SECRET_KEY`` en su contenedor,
  que en docker-compose es ``<X>_SERVICE_SECRET``).
- El receptor conoce los secretos de sus callers permitidos
  (``SANCTIONING_SERVICE_SECRET``, ``INFRACTION_SERVICE_SECRET``, ...): la
  identidad la determina qué secreto valida la firma, y además el claim
  ``service`` debe coincidir con ese caller.
"""
from .service_jwt import (
    DEFAULT_ALGORITHM,
    DEFAULT_TTL,
    SERVICE_SECRET_ENV,
    SERVICE_TOKEN_HEADER,
    ServiceTokenConfigError,
    ServiceTokenError,
    ServiceTokenInvalid,
    ServiceTokenMissing,
    expected_callers_from_env,
    generate_service_jwt,
    identify_caller,
    service_headers,
)

__all__ = [
    "DEFAULT_ALGORITHM",
    "DEFAULT_TTL",
    "SERVICE_SECRET_ENV",
    "SERVICE_TOKEN_HEADER",
    "ServiceTokenConfigError",
    "ServiceTokenError",
    "ServiceTokenInvalid",
    "ServiceTokenMissing",
    "expected_callers_from_env",
    "generate_service_jwt",
    "identify_caller",
    "service_headers",
]

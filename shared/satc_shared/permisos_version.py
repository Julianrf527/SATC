"""Versión global de permisos en Redis, para invalidar al instante las cachés de
permisos de todos los servicios y workers.

- app-users llama ``incrementar_version_permisos()`` después de cambiar un rol,
  un permiso o el rol/estado de un usuario.
- Cada servicio, antes de leer su caché de permisos, llama
  ``version_permisos()``; si cambió respecto a la última vista, vacía su caché.

Configuración por entorno: ``REDIS_HOST``, ``REDIS_PORT`` (6379),
``REDIS_PASSWORD`` y ``REDIS_DB_PERMISOS`` (2). Sin ``REDIS_HOST``, sin el
paquete ``redis`` o con Redis caído, todo es no-op y cada servicio queda con el
TTL de su caché como red de seguridad.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

CLAVE = "satc:permisos:version"
# Como mucho una lectura a Redis por segundo y por worker.
INTERVALO_LECTURA = 1.0
# Tras un fallo de conexión, no reintentar durante este tiempo.
PAUSA_TRAS_FALLO = 30.0

_cliente: Any = None
_ultima_version: Optional[str] = None
_leida_en = 0.0
_fallo_en = 0.0


def _obtener_cliente() -> Any:
    global _cliente
    if _cliente is not None:
        return _cliente
    host = os.getenv("REDIS_HOST")
    if not host:
        return None
    try:
        import redis.asyncio as redis
    except ImportError:
        return None
    _cliente = redis.Redis(
        host=host,
        port=int(os.getenv("REDIS_PORT") or 6379),
        password=os.getenv("REDIS_PASSWORD") or None,
        db=int(os.getenv("REDIS_DB_PERMISOS") or 2),
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
    )
    return _cliente


def _en_pausa() -> bool:
    return time.monotonic() - _fallo_en < PAUSA_TRAS_FALLO


def _registrar_fallo(accion: str, e: Exception) -> None:
    global _fallo_en
    _fallo_en = time.monotonic()
    logger.warning(f"Versión de permisos: no se pudo {accion} en Redis ({e}); se usa solo el TTL de la caché")


async def version_permisos() -> Optional[str]:
    """Versión actual (``None`` si Redis no está disponible o aún no hubo
    cambios). Consulta Redis como mucho una vez por ``INTERVALO_LECTURA``."""
    global _ultima_version, _leida_en
    ahora = time.monotonic()
    if ahora - _leida_en < INTERVALO_LECTURA:
        return _ultima_version
    cliente = _obtener_cliente()
    if cliente is None or _en_pausa():
        return _ultima_version
    _leida_en = ahora
    try:
        _ultima_version = await cliente.get(CLAVE)
    except Exception as e:
        _registrar_fallo("leer", e)
    return _ultima_version


async def incrementar_version_permisos() -> None:
    """Marca que los permisos cambiaron (best-effort: nunca lanza)."""
    cliente = _obtener_cliente()
    if cliente is None:
        return
    try:
        await cliente.incr(CLAVE)
    except Exception as e:
        _registrar_fallo("incrementar", e)


class SincronizadorPermisos:
    """Recuerda la última versión vista y avisa si cambió.

    Uso::

        sincronizador = SincronizadorPermisos()
        if await sincronizador.cambio():
            await mi_cache.clear()
    """

    def __init__(self) -> None:
        self._vista: Optional[str] = None

    async def cambio(self) -> bool:
        actual = await version_permisos()
        if actual is None or actual == self._vista:
            return False
        # También en la primera lectura: la caché pudo llenarse antes de conocer
        # la versión, así que vaciarla es lo seguro.
        self._vista = actual
        return True

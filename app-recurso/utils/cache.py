"""Caché en memoria con TTL y tope de entradas (por worker) para las consultas
a app-users."""
import asyncio
import time
from collections import OrderedDict
from typing import Any, Optional


class SimpleCache:
    """TTL por entrada y como máximo ``max_entradas``: al llenarse se purgan las
    vencidas y, si no alcanza, las más antiguas (LRU)."""

    def __init__(self, ttl_seconds: int = 300, max_entradas: int = 2000):
        self.ttl_seconds = ttl_seconds
        self.max_entradas = max_entradas
        self._datos: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entrada = self._datos.get(key)
            if entrada is None:
                return None
            valor, vence = entrada
            if time.monotonic() >= vence:
                del self._datos[key]
                return None
            self._datos.move_to_end(key)
            return valor

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._datos[key] = (value, time.monotonic() + self.ttl_seconds)
            self._datos.move_to_end(key)
            if len(self._datos) > self.max_entradas:
                ahora = time.monotonic()
                for k in [k for k, (_, vence) in self._datos.items() if vence <= ahora]:
                    del self._datos[k]
                while len(self._datos) > self.max_entradas:
                    self._datos.popitem(last=False)

    async def clear(self) -> None:
        async with self._lock:
            self._datos.clear()


permission_cache = SimpleCache(ttl_seconds=300)
users_cache = SimpleCache(ttl_seconds=600)

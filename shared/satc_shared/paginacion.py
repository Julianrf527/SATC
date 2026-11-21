"""Respuesta paginada estándar y búsqueda parcial segura para los listados.

Forma de toda respuesta paginada::

    {"ok": true, "data": [...], "total": N, "page": P, "limit": L, "total_pages": T, ...extras}

``total`` cuenta los ítems tras los filtros; ``total_pages`` es al menos 1.
"""
from __future__ import annotations

from math import ceil
from typing import Any, Sequence

ESCAPE = "\\"


def total_paginas(total: int, limit: int) -> int:
    return max(1, ceil(total / max(1, limit)))


def respuesta_paginada(data: Sequence[Any], *, total: int, page: int, limit: int, **extras: Any) -> dict:
    return {
        "ok": True,
        "data": list(data),
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_paginas(total, limit),
        **extras,
    }


def patron_contiene(texto: str) -> str:
    """Patrón ``ILIKE`` "contiene" con ``%``, ``_`` y ``\\`` escapados, para usar
    con ``columna.ilike(patron_contiene(t), escape=ESCAPE)``: así un ``_`` o un
    ``%`` escrito por el usuario se busca literal y no como comodín."""
    limpio = texto.strip().replace(ESCAPE, ESCAPE * 2).replace("%", ESCAPE + "%").replace("_", ESCAPE + "_")
    return f"%{limpio}%"

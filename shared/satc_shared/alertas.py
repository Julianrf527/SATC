"""Paginación y filtros en servidor de la pestaña Alertas.

Genérico: no conoce reglas de plazos ni tipos de alerta de ningún servicio.
Recibe las alertas ya calculadas en el formato de siempre
(``{radicado: {clave: alerta}}``, cada alerta con ``tipo`` y ``semaforo``) y
devuelve una página de la lista plana, ordenada como lo hacía el frontend:
por urgencia (crítico → baja) y luego por % de avance descendente; los
empates conservan el orden de entrada (orden estable).
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Optional

ESTADOS_SEMAFORO = ("verde", "amarillo", "rojo", "vencido")
URGENCIA_ORDEN = {"critico": 0, "alta": 1, "media": 2, "baja": 3}
LIMITE_MAXIMO = 100


def paginar_alertas(
    alertas_por_radicado: Mapping[Any, Mapping[str, dict]],
    *,
    page: int,
    limit: int = 10,
    radicado: Optional[str] = None,
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
) -> dict:
    """Página ``page`` (desde 1) de las alertas tras los filtros.

    - ``radicado``: coincidencia parcial sin distinguir mayúsculas (vacío = sin filtro).
    - ``estado``: estado del semáforo exacto.
    - ``tipo``: tipo de alerta exacto.

    Devuelve ``alertas`` (lista de la página; cada ítem con sus campos +
    ``radicado`` y ``clave``), ``total`` (alertas tras filtros), ``page``,
    ``limit``, ``total_pages`` y ``tipos_disponibles`` (tipos de TODAS las
    alertas recibidas, sin filtros, ordenados).
    """
    if page < 1:
        raise ValueError("page debe ser >= 1")
    if not 1 <= limit <= LIMITE_MAXIMO:
        raise ValueError(f"limit debe estar entre 1 y {LIMITE_MAXIMO}")

    planas = [
        {**alerta, "radicado": rad, "clave": clave}
        for rad, alertas in alertas_por_radicado.items()
        for clave, alerta in alertas.items()
    ]
    tipos_disponibles = sorted({a["tipo"] for a in planas})

    rad = (radicado or "").strip().lower()
    filtradas = [
        a for a in planas
        if (not rad or rad in str(a["radicado"] or "").lower())
        and (not estado or a["semaforo"]["estado"] == estado)
        and (not tipo or a["tipo"] == tipo)
    ]
    filtradas.sort(key=lambda a: (
        URGENCIA_ORDEN.get(a["semaforo"]["urgencia"], len(URGENCIA_ORDEN)),
        -a["semaforo"]["porcentaje_avance"],
    ))

    total = len(filtradas)
    inicio = (page - 1) * limit
    return {
        "alertas": filtradas[inicio:inicio + limit],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit),
        "tipos_disponibles": tipos_disponibles,
    }

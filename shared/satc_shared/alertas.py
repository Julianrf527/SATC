"""Paginación y filtros en servidor de la pestaña Alertas.

Genérico: no conoce reglas de plazos ni tipos de alerta de ningún servicio.
Recibe las alertas ya calculadas en el formato de siempre
(``{radicado: {clave: alerta}}``, cada alerta con ``tipo`` y ``semaforo``) y
devuelve una página de la lista plana, ordenada como lo hacía el frontend:
por urgencia (crítico → baja) y luego por % de avance descendente; los
empates conservan el orden de entrada (orden estable).

Responsable de una alerta (``marcar_responsable``): cada alerta tiene un
``encargado_id`` (persona) y, opcionalmente, ``roles_responsables`` (lista de
``{"permiso", "etiqueta"}``). Si trae roles, la alerta es de todo usuario con
alguno de esos permisos (p. ej. quienes deben revisar el documento o quienes
pueden asignar una visita); si no, del encargado. ``estado_documento`` es solo
informativo.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Optional

ESTADOS_SEMAFORO = ("verde", "amarillo", "rojo", "vencido")
URGENCIA_ORDEN = {"critico": 0, "alta": 1, "media": 2, "baja": 3}
LIMITE_MAXIMO = 100


def roles_responsables(alerta: Mapping[str, Any]) -> list[dict]:
    """Roles a los que corresponde la alerta (vacío si es del encargado)."""
    return list(alerta.get("roles_responsables") or [])


def es_responsable(alerta: Mapping[str, Any], user_id: Optional[int], permisos_usuario: Iterable[str]) -> bool:
    """Por rol si la alerta trae ``roles_responsables``; si no, por ``encargado_id``."""
    roles = roles_responsables(alerta)
    if roles:
        permisos = set(permisos_usuario)
        return any(r.get("permiso") in permisos for r in roles)
    return user_id is not None and alerta.get("encargado_id") == user_id


def marcar_responsable(alerta: dict, user_id: Optional[int], permisos_usuario: Iterable[str]) -> dict:
    """Agrega ``es_responsable`` a la alerta (la modifica y la devuelve)."""
    alerta["es_responsable"] = es_responsable(alerta, user_id, permisos_usuario)
    return alerta


def permisos_de_roles(alertas: Iterable[Mapping[str, Any]]) -> set[str]:
    """Permisos que aparecen en ``roles_responsables`` (para consultar al
    usuario solo esos)."""
    return {r["permiso"] for a in alertas for r in roles_responsables(a) if r.get("permiso")}


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

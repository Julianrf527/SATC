"""GET /expedientes/alertas/todas con ``page``: paginación y filtros en servidor.

Contrato: con ``page`` la respuesta es una página de la lista plana, ordenada
como la ordenaba el frontend (urgencia y luego % de avance desc), con
``total``/``total_pages``/``tipos_disponibles`` y ``estadisticas_semaforo``
del alcance completo. Sin ``page``, la respuesta de siempre (ver
test_alertas_caracterizacion.py). Se verifica contra la respuesta clásica
aplicando, en el test, la misma lógica que tenía el frontend.
"""
import math

import pytest

from tests.conftest import gateway_headers
from tests.test_alertas_caracterizacion import _escenarios, fecha_fija, todos_los_permisos  # noqa: F401

URL = "/expedientes/alertas/todas"
URGENCIA = {"critico": 0, "alta": 1, "media": 2, "baja": 3}


def _esperado(clasica: dict, radicado="", estado=None, tipo=None) -> list:
    """Lo que hacía el frontend: aplanar, filtrar y ordenar (sort estable)."""
    planas = [{**a, "radicado": rad, "clave": k} for rad, als in clasica["alertas"].items() for k, a in als.items()]
    rad = radicado.strip().lower()
    filtradas = [a for a in planas
                 if (not rad or rad in a["radicado"].lower())
                 and (not estado or a["semaforo"]["estado"] == estado)
                 and (not tipo or a["tipo"] == tipo)]
    return sorted(filtradas, key=lambda a: (URGENCIA[a["semaforo"]["urgencia"]], -a["semaforo"]["porcentaje_avance"]))


async def _todas_las_paginas(client, query: str, limit: int) -> tuple[list, dict]:
    primera = (await client.get(f"{URL}?{query}&page=1&limit={limit}", headers=gateway_headers(7))).json()
    items = list(primera["alertas"])
    for p in range(2, primera["total_pages"] + 1):
        items += (await client.get(f"{URL}?{query}&page={p}&limit={limit}", headers=gateway_headers(7))).json()["alertas"]
    return items, primera


@pytest.mark.parametrize("filtros", [
    {},
    {"estado": "vencido"},
    {"estado": "verde"},
    {"tipo": "respuesta_plazo"},
    {"tipo": "concepto_constancia", "estado": "rojo"},
    {"radicado": " car-001"},
    {"radicado": "0004", "tipo": "respuesta_plazo"},
    {"radicado": "no-existe"},
])
async def test_paginas_equivalen_a_la_respuesta_clasica(client, db_session, make_expediente, fecha_fija,
                                                        todos_los_permisos, filtros):
    await _escenarios(db_session, make_expediente)
    clasica = (await client.get(f"{URL}?alcance=todos", headers=gateway_headers(7))).json()
    query = "&".join(["alcance=todos"] + [f"{k}={v}" for k, v in filtros.items()])

    items, primera = await _todas_las_paginas(client, query, limit=3)

    esperado = _esperado(clasica, **filtros)
    assert items == esperado
    assert primera["total"] == len(esperado)
    assert primera["total_pages"] == math.ceil(len(esperado) / 3)
    assert primera["page"] == 1 and primera["limit"] == 3
    # Contadores y tipos: del alcance completo, sin filtros.
    assert primera["estadisticas_semaforo"] == clasica["estadisticas_semaforo"]
    assert primera["tipos_disponibles"] == sorted({a["tipo"] for a in _esperado(clasica)})
    assert primera["total_expedientes"] == clasica["total_expedientes"]
    assert primera["alcance"] == "todos"
    for a in items:
        assert {"radicado", "clave", "es_responsable", "semaforo", "tipo"} <= a.keys()


async def test_es_responsable_y_alcance_mios(client, db_session, make_expediente, fecha_fija, todos_los_permisos):
    await _escenarios(db_session, make_expediente)
    todos = (await client.get(f"{URL}?alcance=todos&page=1&limit=100", headers=gateway_headers(8))).json()
    assert {a["es_responsable"] for a in todos["alertas"]} == {True, False}
    mios = (await client.get(f"{URL}?page=1&limit=100", headers=gateway_headers(8))).json()
    assert mios["alcance"] == "mios" and mios["total"] > 0
    assert all(a["es_responsable"] for a in mios["alertas"])


async def test_limit_por_defecto_10_y_pagina_fuera_de_rango(client, db_session, make_expediente, fecha_fija,
                                                            todos_los_permisos):
    await _escenarios(db_session, make_expediente)
    data = (await client.get(f"{URL}?alcance=todos&page=1", headers=gateway_headers(7))).json()
    assert data["limit"] == 10 and len(data["alertas"]) == 10
    fuera = (await client.get(f"{URL}?alcance=todos&page=99", headers=gateway_headers(7))).json()
    assert fuera["alertas"] == [] and fuera["total"] == data["total"]


async def test_sin_page_ignora_filtros_respuesta_clasica(client, db_session, make_expediente, fecha_fija,
                                                         todos_los_permisos):
    await _escenarios(db_session, make_expediente)
    clasica = (await client.get(f"{URL}?alcance=todos", headers=gateway_headers(7))).json()
    con_filtros = (await client.get(f"{URL}?alcance=todos&estado=verde&tipo=x&limit=5", headers=gateway_headers(7))).json()
    assert con_filtros == clasica
    assert isinstance(clasica["alertas"], dict)


async def test_sin_expedientes_paginado(client, todos_los_permisos):
    data = (await client.get(f"{URL}?page=1", headers=gateway_headers(50))).json()
    assert data["alertas"] == [] and data["total"] == 0 and data["total_pages"] == 0
    assert data["estadisticas_semaforo"] == {"verde": 0, "amarillo": 0, "rojo": 0, "vencido": 0}
    assert data["tipos_disponibles"] == []


@pytest.mark.parametrize("query", ["page=0", "page=1&limit=101", "page=1&limit=0", "page=1&estado=gris"])
async def test_parametros_invalidos_422(client, todos_los_permisos, query):
    resp = await client.get(f"{URL}?{query}", headers=gateway_headers(7))
    assert resp.status_code == 422

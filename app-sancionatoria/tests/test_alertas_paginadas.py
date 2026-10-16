"""GET /expediente/alerts/all con ``page``: paginación y filtros en servidor.

Contrato: con ``page`` la respuesta es una página de la lista plana, ordenada
como la ordenaba el frontend (urgencia y luego % de avance desc), con
``total``/``total_pages``/``tipos_disponibles`` y ``estadisticas_semaforo``
del alcance completo. Sin ``page``, la respuesta de siempre (ver
test_alertas_caracterizacion.py). Se verifica contra la respuesta clásica
aplicando, en el test, la misma lógica que tenía el frontend.
"""
import math

import pytest

from conftest import gateway_headers
from test_alertas_caracterizacion import _escenarios, fecha_fija, involved  # noqa: F401

URL = "/expediente/alerts/all"
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


@pytest.fixture
async def escenarios(db_session, make_expediente, make_acto_administrativo, make_notificacion, fecha_fija, involved):
    return await _escenarios(db_session, make_expediente, make_acto_administrativo, make_notificacion)


@pytest.mark.parametrize("filtros", [
    {},
    {"estado": "vencido"},
    {"estado": "amarillo"},
    {"tipo": "constancia_citacion_pendiente"},
    {"tipo": "decision_fondo", "estado": "rojo"},
    {"radicado": "CAR-000"},
    {"radicado": "zzz"},
])
async def test_paginas_equivalen_a_la_respuesta_clasica(api, escenarios, filtros):
    clasica = (await api.get(f"{URL}?alcance=todos", headers=gateway_headers(5))).json()
    query = "&".join(["alcance=todos"] + [f"{k}={v}" for k, v in filtros.items()])

    primera = (await api.get(f"{URL}?{query}&page=1&limit=4", headers=gateway_headers(5))).json()
    items = list(primera["alertas"])
    for p in range(2, primera["total_pages"] + 1):
        items += (await api.get(f"{URL}?{query}&page={p}&limit=4", headers=gateway_headers(5))).json()["alertas"]

    esperado = _esperado(clasica, **filtros)
    assert items == esperado
    assert primera["total"] == len(esperado)
    assert primera["total_pages"] == math.ceil(len(esperado) / 4)
    assert primera["estadisticas_semaforo"] == clasica["estadisticas_semaforo"]
    assert primera["tipos_disponibles"] == sorted({a["tipo"] for a in _esperado(clasica)})
    assert primera["total_expedientes"] == clasica["total_expedientes"]
    for a in items:
        assert {"radicado", "clave", "es_responsable", "semaforo", "tipo"} <= a.keys()


async def test_es_responsable_por_alcance(api, escenarios):
    todos = (await api.get(f"{URL}?alcance=todos&page=1&limit=100", headers=gateway_headers(9))).json()
    assert {a["es_responsable"] for a in todos["alertas"]} == {True, False}
    mios = (await api.get(f"{URL}?page=1&limit=100", headers=gateway_headers(9))).json()
    assert mios["total"] > 0 and all(a["es_responsable"] for a in mios["alertas"])


async def test_sin_page_ignora_filtros(api, escenarios):
    clasica = (await api.get(f"{URL}?alcance=todos", headers=gateway_headers(5))).json()
    con_filtros = (await api.get(f"{URL}?alcance=todos&estado=rojo&radicado=x", headers=gateway_headers(5))).json()
    assert con_filtros == clasica


async def test_sin_expedientes_paginado(api):
    data = (await api.get(f"{URL}?page=1", headers=gateway_headers(77))).json()
    assert data["alertas"] == [] and data["total"] == 0 and data["total_pages"] == 0
    assert data["estadisticas_semaforo"] == {"verde": 0, "amarillo": 0, "rojo": 0, "vencido": 0}
    # Sin page, la respuesta vacía de siempre (sin estadisticas_semaforo).
    assert (await api.get(URL, headers=gateway_headers(77))).json() == {
        "ok": True, "alcance": "mios", "alertas": {}, "total_expedientes": 0, "expedientes_con_alertas": 0,
    }


@pytest.mark.parametrize("query", ["page=0", "page=1&limit=101", "page=1&estado=gris"])
async def test_parametros_invalidos_422(api, query):
    assert (await api.get(f"{URL}?{query}", headers=gateway_headers(5))).status_code == 422

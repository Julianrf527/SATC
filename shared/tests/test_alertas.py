"""satc_shared.alertas.paginar_alertas: orden, filtros y paginación."""
import pytest

from satc_shared.alertas import paginar_alertas


def _a(tipo, estado, urgencia, pct):
    return {"tipo": tipo, "semaforo": {"estado": estado, "urgencia": urgencia, "porcentaje_avance": pct},
            "es_responsable": True}


ALERTAS = {
    "2024-ABC-1": {"x1": _a("t1", "verde", "baja", 10), "x2": _a("t2", "rojo", "alta", 70)},
    "2024-abd-2": {"y1": _a("t1", "vencido", "critico", 100), "y2": _a("t3", "rojo", "alta", 90)},
    "2025-XYZ-3": {"z1": _a("t2", "amarillo", "media", 40), "z2": _a("t1", "rojo", "alta", 70)},
}


def _claves(r):
    return [a["clave"] for a in r["alertas"]]


def test_orden_por_urgencia_y_avance_estable():
    r = paginar_alertas(ALERTAS, page=1, limit=100)
    # x2 y z2 empatan (alta, 70): conservan el orden de entrada.
    assert _claves(r) == ["y1", "y2", "x2", "z2", "z1", "x1"]
    assert r["total"] == 6 and r["total_pages"] == 1
    assert r["alertas"][0]["radicado"] == "2024-abd-2"
    assert r["alertas"][0]["es_responsable"] is True


def test_paginacion():
    r = paginar_alertas(ALERTAS, page=2, limit=4)
    assert _claves(r) == ["z1", "x1"]
    assert (r["total"], r["total_pages"], r["page"], r["limit"]) == (6, 2, 2, 4)
    assert paginar_alertas(ALERTAS, page=3, limit=4)["alertas"] == []


def test_filtros_y_tipos_disponibles_sin_filtrar():
    r = paginar_alertas(ALERTAS, page=1, radicado="  AB ", estado="rojo")
    assert _claves(r) == ["y2", "x2"]
    r = paginar_alertas(ALERTAS, page=1, tipo="t1")
    assert _claves(r) == ["y1", "z2", "x1"]
    assert r["tipos_disponibles"] == ["t1", "t2", "t3"]


def test_vacio():
    r = paginar_alertas({}, page=1)
    assert r == {"alertas": [], "total": 0, "page": 1, "limit": 10, "total_pages": 0, "tipos_disponibles": []}


@pytest.mark.parametrize("page,limit", [(0, 10), (1, 0), (1, 101)])
def test_parametros_invalidos(page, limit):
    with pytest.raises(ValueError):
        paginar_alertas(ALERTAS, page=page, limit=limit)

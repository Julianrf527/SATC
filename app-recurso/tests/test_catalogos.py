"""Catálogos (routes/catalogos.py): lectura con recurso_consultar/gestionar/super."""
import pytest

from core.permission import Permission
from db.models import UsoAgua


async def test_todos_los_catalogos(client, h_consultor):
    r = await client.get("/catalogos", headers=h_consultor)
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data["municipios"]) == 25
    assert all("veredas" in m for m in data["municipios"])
    assert sum(len(m["veredas"]) for m in data["municipios"]) > 25
    nombres_tipo = {t["nombre"] for t in data["tipos_fuente"]}
    assert {"SUPERFICIAL", "LÓTICO", "LÉNTICO", "SUBTERRÁNEO"} <= nombres_tipo
    assert {"QUEBRADA", "RÍO", "NACIMIENTO"} <= {f["nombre"] for f in data["fuentes"]}
    assert data["usos"] == [u.value for u in UsoAgua]
    assert {t["nombre"] for t in data["tipos_notificacion"]} == {"PERSONAL", "ELECTRÓNICA", "AVISO"}


@pytest.mark.parametrize(
    "ruta", ["/catalogos/municipios", "/catalogos/tipos-fuente", "/catalogos/fuentes",
             "/catalogos/usos", "/catalogos/tipos-notificacion"],
)
async def test_catalogo_individual(client, como, ruta):
    r = await client.get(ruta, headers=como(10, Permission.MANAGE))
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert len(r.json()["data"]) > 0


async def test_veredas_ordenadas_y_agrupadas(client, h_super):
    r = await client.get("/catalogos/municipios", headers=h_super)
    municipios = r.json()["data"]
    assert [m["nombre"] for m in municipios] == sorted(m["nombre"] for m in municipios)
    for m in municipios:
        assert [v["nombre"] for v in m["veredas"]] == sorted(v["nombre"] for v in m["veredas"])


async def test_sin_permiso_403(client, h_sin_permisos):
    r = await client.get("/catalogos", headers=h_sin_permisos)
    assert r.status_code == 403


async def test_sin_gateway_403(client):
    r = await client.get("/catalogos")
    assert r.status_code == 403

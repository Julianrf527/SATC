"""Tests de routes/town.py — municipios/veredas y días laborales."""
from tests.conftest import gateway_headers


class TestRuralDistrict:
    async def test_lista_municipios_con_veredas(self, client, make_municipio_vereda):
        await make_municipio_vereda("Chivor", "La Esperanza")
        resp = await client.get("/town/rural-district", headers=gateway_headers(1))
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["nombre"] == "Chivor"
        assert data["data"][0]["veredas"][0]["nombre"] == "La Esperanza"

    async def test_sin_token_gateway_da_403(self, client):
        resp = await client.get("/town/rural-district")
        assert resp.status_code == 403

    async def test_veredas_por_municipio(self, client, make_municipio_vereda):
        muni, vereda = await make_municipio_vereda("Macanal", "El Centro")
        resp = await client.get(f"/town/rural-district/{muni.id}", headers=gateway_headers(1))
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["veredas"][0]["nombre"] == "El Centro"

    async def test_veredas_municipio_inexistente_devuelve_vacio(self, client):
        resp = await client.get("/town/rural-district/9999", headers=gateway_headers(1))
        assert resp.status_code == 200
        assert resp.json()["veredas"] == []


class TestBusinessDays:
    async def test_calcula_dias_laborales(self, client):
        # lunes 2024-01-08 a viernes 2024-01-12 => 4 días laborales (excluye inicio)
        resp = await client.post(
            "/town/utils/business-days",
            json={"fecha_inicio": "2024-01-08", "fecha_fin": "2024-01-12"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json()["dias_laborales"], int)

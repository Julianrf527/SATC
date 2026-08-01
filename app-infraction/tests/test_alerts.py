"""Tests de routes/file.py — endpoints de alertas de infracción."""
from tests.conftest import gateway_headers


class TestAlertsAll:
    async def test_usuario_sin_expedientes(self, client):
        resp = await client.get("/file/alerts/all", headers=gateway_headers(50))
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["total_expedientes"] == 0

    async def test_sin_token_403(self, client):
        resp = await client.get("/file/alerts/all")
        assert resp.status_code == 403


class TestAlertsExpediente:
    async def test_expediente_inexistente_404(self, client):
        resp = await client.get("/file/alerts/9999", headers=gateway_headers(1))
        assert resp.status_code == 404

    async def test_expediente_ajeno_403(self, client, make_expediente):
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.get(f"/file/alerts/{exp.id}", headers=gateway_headers(99))
        assert resp.status_code == 403

    async def test_expediente_propio_sin_etapas(self, client, make_expediente):
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.get(f"/file/alerts/{exp.id}", headers=gateway_headers(7))
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "alertas" in data

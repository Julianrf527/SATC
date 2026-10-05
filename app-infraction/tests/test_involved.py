"""Tests de routes/involved.py — vínculos involucrado<->expediente."""
import pytest
import routes.involved as involved_module
from tests.conftest import gateway_headers


@pytest.fixture
def consulta_involucrados(monkeypatch):
    async def _verify(user_id, permission):
        return permission == "infraccion_consultar"

    monkeypatch.setattr(involved_module, "verify_permission", _verify)


@pytest.mark.usefixtures("consulta_involucrados")
class TestFileList:
    """/involucrados/{involved_id}/expedientes: expedientes donde participa un involucrado.

    Regresión: antes usaba select(varias columnas).scalar_one_or_none(), que
    devolvía solo el id (int) y luego fallaba al acceder .radicado. Ahora usa
    .first() y devuelve la Row completa.
    """

    async def test_lista_expedientes_del_involucrado(
        self, client, make_expediente, link_involucrado
    ):
        exp = await make_expediente(abogado_responsable_id=3, radicado="RAD-INV-1")
        await link_involucrado(exp.id, involucrado_id=42)
        resp = await client.get("/involucrados/42/expedientes", headers=gateway_headers(3))
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["data"]["total"] == 1
        assert data["data"]["expedientes"][0]["radicado"] == "RAD-INV-1"

    async def test_sin_expedientes_404(self, client):
        resp = await client.get("/involucrados/999/expedientes", headers=gateway_headers(3))
        assert resp.status_code == 404


@pytest.mark.usefixtures("permiso_consulta")
class TestInvolvedList:
    """/involucrados/expediente/{expediente_id}: consulta al microservicio involved."""

    async def test_lista_involucrados(self, client, make_expediente, link_involucrado, monkeypatch):
        exp = await make_expediente(abogado_responsable_id=3)
        await link_involucrado(exp.id, involucrado_id=11)

        async def fake_get(db, ids):
            return [{"id": 11, "nombre": "Juan Perez"}]

        monkeypatch.setattr(involved_module, "get_involucrados_by_ids", fake_get)
        resp = await client.get(f"/involucrados/expediente/{exp.id}", headers=gateway_headers(3))
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["involucrados"][0]["nombre"] == "Juan Perez"

    async def test_expediente_sin_involucrados_devuelve_lista_vacia(self, client, make_expediente):
        exp = await make_expediente(abogado_responsable_id=3)
        resp = await client.get(f"/involucrados/expediente/{exp.id}", headers=gateway_headers(3))
        assert resp.status_code == 200
        assert resp.json()["data"]["involucrados"] == []

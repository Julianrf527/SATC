"""Tests de flujos de stage: medida, concepto, cierre.

Los casos de 'expediente inexistente' sobre endpoints con verificación de
propiedad asumen el comportamiento unificado (403, nunca 404, para no revelar
existencia) — ver services/etapas.get_expediente_con_permiso.
"""
import routes.stage_concepto as concepto_mod
from tests.conftest import gateway_headers


async def _noop(*a, **k):
    return {"ok": True}


class TestMedida:
    async def test_crea_medida_ok(self, client, make_expediente, make_etapa_respuesta, tipo_medida):
        exp = await make_expediente(abogado_responsable_id=7)
        etapa = await make_etapa_respuesta(exp.id, requiere_medida_preventiva=True)
        body = {"tipo_medida_id": tipo_medida.id, "cantidad": "3", "especie": "Madera", "estado_medida": True}
        resp = await client.post(f"/stage/medida/{etapa.id}", json=body, headers=gateway_headers(7))
        assert resp.status_code == 201
        assert resp.json()["ok"] is True

    async def test_medida_usuario_ajeno_403(self, client, make_expediente, make_etapa_respuesta, tipo_medida):
        exp = await make_expediente(abogado_responsable_id=7)
        etapa = await make_etapa_respuesta(exp.id, requiere_medida_preventiva=True)
        body = {"tipo_medida_id": tipo_medida.id, "cantidad": "3", "especie": "Madera"}
        resp = await client.post(f"/stage/medida/{etapa.id}", json=body, headers=gateway_headers(99))
        assert resp.status_code == 403

    async def test_medida_etapa_inexistente_404(self, client):
        # La etapa (no el expediente) es el recurso: 404 legítimo si no existe.
        resp = await client.post(
            "/stage/medida/9999",
            json={"tipo_medida_id": 1, "cantidad": "1", "especie": "x"},
            headers=gateway_headers(7),
        )
        assert resp.status_code == 404


class TestConcepto:
    async def test_crea_y_obtiene_concepto(self, client, make_expediente, make_informe_visita_aceptado, monkeypatch):
        monkeypatch.setattr(concepto_mod, "increment_file_usage", _noop, raising=False)
        monkeypatch.setattr(concepto_mod, "decrement_file_usage", _noop, raising=False)
        exp = await make_expediente(abogado_responsable_id=7)
        await make_informe_visita_aceptado(exp.id)
        resp = await client.post(
            f"/stage/concepto/{exp.id}",
            json={"tipo_acogida_concepto": "AUTO_REQUERIMIENTO"},
            headers=gateway_headers(7),
        )
        assert resp.status_code == 201
        get = await client.get(f"/stage/concepto/{exp.id}", headers=gateway_headers(7))
        assert get.status_code == 200
        assert get.json()["data"]["tipo_acogida_concepto"] == "AUTO_REQUERIMIENTO"

    async def test_concepto_expediente_ajeno_403(self, client, make_expediente):
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.post(
            f"/stage/concepto/{exp.id}",
            json={"tipo_acogida_concepto": "OFICIO"},
            headers=gateway_headers(99),
        )
        assert resp.status_code == 403

    async def test_concepto_expediente_inexistente_403(self, client):
        resp = await client.post(
            "/stage/concepto/9999",
            json={"tipo_acogida_concepto": "OFICIO"},
            headers=gateway_headers(7),
        )
        assert resp.status_code == 403


class TestCierre:
    async def test_cierre_get_sin_datos_404(self, client, make_expediente):
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.get(f"/stage/cierre/{exp.id}", headers=gateway_headers(7))
        assert resp.status_code == 404

    async def test_cierre_post_usuario_ajeno_403(self, client, make_expediente):
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.post(f"/stage/cierre/{exp.id}", json={}, headers=gateway_headers(99))
        assert resp.status_code == 403

    async def test_cierre_post_expediente_inexistente_403(self, client):
        resp = await client.post("/stage/cierre/9999", json={}, headers=gateway_headers(7))
        assert resp.status_code == 403

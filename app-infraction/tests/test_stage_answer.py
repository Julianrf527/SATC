"""Tests de routes/stage_respuesta.py — etapa respuesta y tipos de medida."""
from tests.conftest import gateway_headers

RESPUESTA_BODY = {
    "radicado": "2024EE0001",
    "fecha_radicado": "2024-01-10",
    "documento_radicado_id": 5,
    "requiere_medida_preventiva": False,
}


class TestCrearRespuesta:
    async def test_crea_respuesta_ok(self, client, make_expediente):
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.post(
            f"/stage/answer/{exp.id}", json=RESPUESTA_BODY, headers=gateway_headers(7)
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ok"] is True
        assert data["respuesta_data"]["radicado"] == "2024EE0001"

    async def test_expediente_inexistente_403(self, client):
        # No se distingue "no existe" de "no es tuyo": evita fuga de existencia.
        resp = await client.post(
            "/stage/answer/9999", json=RESPUESTA_BODY, headers=gateway_headers(7)
        )
        assert resp.status_code == 403

    async def test_usuario_sin_permiso_403(self, client, make_expediente):
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.post(
            f"/stage/answer/{exp.id}", json=RESPUESTA_BODY, headers=gateway_headers(99)
        )
        assert resp.status_code == 403

    async def test_respuesta_duplicada_409(self, client, make_expediente):
        exp = await make_expediente(abogado_responsable_id=7)
        h = gateway_headers(7)
        r1 = await client.post(f"/stage/answer/{exp.id}", json=RESPUESTA_BODY, headers=h)
        assert r1.status_code == 201
        r2 = await client.post(
            f"/stage/answer/{exp.id}",
            json={**RESPUESTA_BODY, "radicado": "2024EE0002"},
            headers=h,
        )
        assert r2.status_code == 409

    async def test_body_invalido_422(self, client, make_expediente):
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.post(
            f"/stage/answer/{exp.id}", json={"radicado": "x"}, headers=gateway_headers(7)
        )
        assert resp.status_code == 422


class TestObtenerRespuesta:
    async def test_obtiene_respuesta(self, client, make_expediente, make_etapa_respuesta):
        exp = await make_expediente(abogado_responsable_id=7)
        await make_etapa_respuesta(exp.id, radicado="2024EE0500")
        resp = await client.get(f"/stage/answer/{exp.id}", headers=gateway_headers(7))
        assert resp.status_code == 200
        assert resp.json()["respuesta_data"]["radicado"] == "2024EE0500"

    async def test_sin_respuesta_404(self, client, make_expediente):
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.get(f"/stage/answer/{exp.id}", headers=gateway_headers(7))
        assert resp.status_code == 404


class TestTiposMedida:
    async def test_lista_tipos_medida(self, client, tipo_medida):
        resp = await client.get("/stage/tipo-medida", headers=gateway_headers(1))
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert any(t["nombre"] == "Decomiso" for t in data["data"])

    async def test_sin_token_403(self, client):
        resp = await client.get("/stage/tipo-medida")
        assert resp.status_code == 403

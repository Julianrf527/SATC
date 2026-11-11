"""
Alta de expediente con el PDF "Radicado inicial": el expediente nace con su
documento. Se valida que sea PDF y se registra el uso del archivo dentro de la
misma transacción (si algo falla, no se crea el expediente).
"""
import pytest
from sqlalchemy import select

import routes.file_mutations as mutations_mod
from db.models.expediente import Expediente
from tests.conftest import gateway_headers


@pytest.fixture
def docs(monkeypatch):
    """Simula app-docs: tipo de contenido por file_id y registro de usos."""
    estado = {"tipos": {}, "usos": [], "incremento_ok": True}

    async def _verify(user_id, permission):
        return permission == "infraccion_gestionar"

    async def _noop(*a, **k):
        return {"ok": True}

    async def _user_info(ids):
        return {i: {"nombre": f"Usuario {i}"} for i in ids}

    async def _file_info(file_id):
        tipo = estado["tipos"].get(file_id)
        if tipo is None:
            return {"ok": False, "message": "no existe"}
        return {"ok": True, "data": {"content_type": tipo}}

    async def _incrementar(ids):
        if not estado["incremento_ok"]:
            return {"ok": False, "message": "app-docs caído"}
        estado["usos"].extend(ids)
        return {"ok": True}

    monkeypatch.setattr(mutations_mod, "verify_permission", _verify)
    monkeypatch.setattr(mutations_mod, "create_notification", _noop)
    monkeypatch.setattr(mutations_mod, "get_user_info", _user_info)
    monkeypatch.setattr(mutations_mod, "get_file_info", _file_info)
    monkeypatch.setattr(mutations_mod, "increment_file_usage", _incrementar)
    return estado


def _payload(radicado: str, vereda_id: int, **extra) -> dict:
    return {
        "radicado": radicado,
        "fecha_radicado": "2026-01-10",
        "vereda_id": vereda_id,
        "abogado_responsable_id": 2,
        "direccion": "Calle 1",
        "descripcion": "Prueba",
        "tipos_afectacion_ids": [],
        "quejosos_ids": [],
        "recursos_ids": [],
        "radicados_asociados": [],
        **extra,
    }


async def _buscar(db_session, radicado: str):
    return await db_session.scalar(select(Expediente).where(Expediente.radicado == radicado))


class TestCrearConRadicadoInicial:
    async def test_crea_con_pdf_y_registra_uso(self, client, db_session, docs, make_municipio_vereda):
        _, vereda = await make_municipio_vereda()
        docs["tipos"][501] = "application/pdf"

        resp = await client.post(
            "/expedientes",
            json=_payload("2026ER7001", vereda.id, radicado_inicial_file_id=501),
            headers=gateway_headers(2),
        )

        assert resp.status_code == 200
        exp = await _buscar(db_session, "2026ER7001")
        assert exp is not None and exp.radicado_inicial_file_id == 501
        assert docs["usos"] == [501]

    async def test_sin_radicado_inicial_sigue_funcionando(self, client, db_session, docs, make_municipio_vereda):
        _, vereda = await make_municipio_vereda()

        resp = await client.post(
            "/expedientes", json=_payload("2026ER7002", vereda.id), headers=gateway_headers(2)
        )

        assert resp.status_code == 200
        exp = await _buscar(db_session, "2026ER7002")
        assert exp is not None and exp.radicado_inicial_file_id is None
        assert docs["usos"] == []

    async def test_archivo_no_pdf_da_400_y_no_crea(self, client, db_session, docs, make_municipio_vereda):
        _, vereda = await make_municipio_vereda()
        docs["tipos"][502] = "image/png"

        resp = await client.post(
            "/expedientes",
            json=_payload("2026ER7003", vereda.id, radicado_inicial_file_id=502),
            headers=gateway_headers(2),
        )

        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]
        assert await _buscar(db_session, "2026ER7003") is None

    async def test_archivo_inexistente_da_400(self, client, db_session, docs, make_municipio_vereda):
        _, vereda = await make_municipio_vereda()

        resp = await client.post(
            "/expedientes",
            json=_payload("2026ER7004", vereda.id, radicado_inicial_file_id=999),
            headers=gateway_headers(2),
        )

        assert resp.status_code == 400
        assert await _buscar(db_session, "2026ER7004") is None

    async def test_si_no_registra_uso_no_crea(self, client, db_session, docs, make_municipio_vereda):
        _, vereda = await make_municipio_vereda()
        docs["tipos"][503] = "application/pdf"
        docs["incremento_ok"] = False

        resp = await client.post(
            "/expedientes",
            json=_payload("2026ER7005", vereda.id, radicado_inicial_file_id=503),
            headers=gateway_headers(2),
        )

        assert resp.status_code == 502
        assert await _buscar(db_session, "2026ER7005") is None

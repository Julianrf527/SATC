"""
Documento "Radicado inicial" de los datos del expediente.

PUT /expedientes/{id}/radicado-inicial fija o reemplaza el PDF (file_id ya
subido a app-docs), con los permisos de editar datos básicos
(infraccion_gestionar + encargado). GET /completo/{id} lo devuelve y la
descarga del expediente completo lo pone primero.
"""
import pytest
from sqlalchemy import select

import routes.file_mutations as mutations_mod
import routes.file_query as query_mod
import services.etapas as etapas_mod
from db.models.auditoria import Auditoria
from db.models.expediente import Expediente
from tests.conftest import gateway_headers


def _permisos(permitidos: set[str]):
    async def _verify(user_id, permission):
        return permission in permitidos

    return _verify


@pytest.fixture
def gestionar(monkeypatch):
    for mod in (mutations_mod, query_mod, etapas_mod):
        monkeypatch.setattr(mod, "verify_permission", _permisos({"infraccion_gestionar"}))


async def _fijar(client, expediente_id: int, file_id: int, user_id: int = 5):
    return await client.put(
        f"/expedientes/{expediente_id}/radicado-inicial",
        json={"file_id": file_id},
        headers=gateway_headers(user_id),
    )


async def _file_id_guardado(db_session, expediente_id: int):
    db_session.expire_all()
    return await db_session.scalar(
        select(Expediente.radicado_inicial_file_id).where(Expediente.id == expediente_id)
    )


class TestFijarRadicadoInicial:
    async def test_fijar(self, client, gestionar, stubs_clientes, db_session, make_expediente):
        exp_id = (await make_expediente(abogado_responsable_id=5)).id
        fid = stubs_clientes.files.registrar()

        resp = await _fijar(client, exp_id, fid)

        assert resp.status_code == 200, resp.text
        assert await _file_id_guardado(db_session, exp_id) == fid
        assert stubs_clientes.files.incrementados == [fid]
        assert stubs_clientes.files.decrementados == []
        audit = (await db_session.execute(
            select(Auditoria).where(Auditoria.tipo_evento == "UPDATE_RADICADO_INICIAL")
        )).scalars().all()
        assert len(audit) == 1 and audit[0].expediente_id == exp_id

    async def test_reemplazar_mueve_usos(self, client, gestionar, stubs_clientes, db_session, make_expediente):
        exp = await make_expediente(abogado_responsable_id=5)
        viejo = stubs_clientes.files.registrar()
        nuevo = stubs_clientes.files.registrar()
        assert (await _fijar(client, exp.id, viejo)).status_code == 200

        resp = await _fijar(client, exp.id, nuevo)

        assert resp.status_code == 200, resp.text
        assert await _file_id_guardado(db_session, exp.id) == nuevo
        assert stubs_clientes.files.incrementados == [viejo, nuevo]
        assert stubs_clientes.files.decrementados == [viejo]

    async def test_mismo_archivo_no_toca_usos(self, client, gestionar, stubs_clientes, make_expediente):
        exp = await make_expediente(abogado_responsable_id=5)
        fid = stubs_clientes.files.registrar()
        await _fijar(client, exp.id, fid)

        resp = await _fijar(client, exp.id, fid)

        assert resp.status_code == 200
        assert stubs_clientes.files.incrementados == [fid]
        assert stubs_clientes.files.decrementados == []

    async def test_no_pdf_400(self, client, gestionar, stubs_clientes, db_session, make_expediente):
        exp = await make_expediente(abogado_responsable_id=5)
        fid = stubs_clientes.files.registrar(b"hola", "text/plain")

        resp = await _fijar(client, exp.id, fid)

        assert resp.status_code == 400
        assert await _file_id_guardado(db_session, exp.id) is None
        assert stubs_clientes.files.incrementados == []

    async def test_archivo_inexistente_400(self, client, gestionar, stubs_clientes, make_expediente):
        exp = await make_expediente(abogado_responsable_id=5)
        assert (await _fijar(client, exp.id, 9999)).status_code == 400

    async def test_no_encargado_403(self, client, gestionar, stubs_clientes, db_session, make_expediente):
        exp = await make_expediente(abogado_responsable_id=7)
        fid = stubs_clientes.files.registrar()

        resp = await _fijar(client, exp.id, fid, user_id=5)

        assert resp.status_code == 403
        assert await _file_id_guardado(db_session, exp.id) is None
        assert stubs_clientes.files.incrementados == []

    async def test_encargado_sin_gestionar_403(self, client, monkeypatch, stubs_clientes, make_expediente):
        monkeypatch.setattr(mutations_mod, "verify_permission", _permisos(set()))
        exp = await make_expediente(abogado_responsable_id=5)
        fid = stubs_clientes.files.registrar()

        assert (await _fijar(client, exp.id, fid)).status_code == 403

    async def test_expediente_inexistente_403(self, client, gestionar, stubs_clientes):
        fid = stubs_clientes.files.registrar()
        assert (await _fijar(client, 4242, fid)).status_code == 403


class TestRadicadoInicialEnCompletoYDescarga:
    async def test_aparece_en_completo(self, client, gestionar, stubs_clientes, make_expediente):
        exp = await make_expediente(abogado_responsable_id=5)
        url = f"/expedientes/completo/{exp.id}"

        sin = (await client.get(url, headers=gateway_headers(5))).json()["data"]
        assert sin["radicado_inicial"] is None

        fid = stubs_clientes.files.registrar()
        await _fijar(client, exp.id, fid)
        con = (await client.get(url, headers=gateway_headers(5))).json()["data"]
        assert con["radicado_inicial"] == {"file_id": fid, "nombre": "Radicado inicial"}

    async def test_primero_en_descarga_unificada(
        self, client, gestionar, stubs_clientes, make_expediente, make_etapa_respuesta
    ):
        exp = await make_expediente(abogado_responsable_id=5)
        await make_etapa_respuesta(exp.id, documento_radicado_id=55)
        fid = stubs_clientes.files.registrar()
        await _fijar(client, exp.id, fid)

        resp = await client.get(f"/expedientes/descargar/{exp.id}", headers=gateway_headers(5))

        assert resp.status_code == 200, resp.text
        assert stubs_clientes.files.unificados == [[fid, 55]]

    async def test_solo_radicado_inicial_basta_para_descargar(
        self, client, gestionar, stubs_clientes, make_expediente
    ):
        exp = await make_expediente(abogado_responsable_id=5)
        fid = stubs_clientes.files.registrar()
        await _fijar(client, exp.id, fid)

        resp = await client.get(f"/expedientes/descargar/{exp.id}", headers=gateway_headers(5))

        assert resp.status_code == 200
        assert stubs_clientes.files.unificados == [[fid]]

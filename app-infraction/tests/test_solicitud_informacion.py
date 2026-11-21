"""
Solicitud de información de la etapa de concepto con la respuesta del usuario
(radicado ER, fecha y PDF): opcional, pero si llega uno de los tres datos van
los tres. Se comprueban los usos de archivo en app-docs (stub).
"""
import pytest
from sqlalchemy import select

from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.solicitud_informacion import SolicitudInformacion
from tests.conftest import gateway_headers

ENCARGADO = 7
DOC_SOLICITUD, DOC_RESPUESTA, DOC_RESPUESTA_2 = 900, 901, 902

BASE = {"radicado": "2024EE0001", "fecha_radicado": "2024-01-05", "archivo_solicitud_id": DOC_SOLICITUD}
RESPUESTA = {"radicado_respuesta": "2024ER0002", "fecha_radicado_respuesta": "2024-01-10", "archivo_respuesta_id": DOC_RESPUESTA}


@pytest.fixture
def concepto(db_session, make_expediente):
    async def _make() -> EtapaAcogerConcepto:
        exp = await make_expediente(abogado_responsable_id=ENCARGADO)
        etapa = EtapaAcogerConcepto(expediente_id=exp.id, tipo_acogida_concepto="OFICIO")
        db_session.add(etapa)
        await db_session.flush()
        return etapa

    return _make


async def _crear(client, etapa_id, body):
    return await client.post(f"/etapas/solicitud-informacion/{etapa_id}", json=body, headers=gateway_headers(ENCARGADO))


async def _actualizar(client, solicitud_id, body):
    return await client.put(f"/etapas/solicitud-informacion/{solicitud_id}", json=body, headers=gateway_headers(ENCARGADO))


async def _fila(db_session, solicitud_id) -> SolicitudInformacion:
    return await db_session.scalar(
        select(SolicitudInformacion).where(SolicitudInformacion.id == solicitud_id).execution_options(populate_existing=True)
    )


class TestRespuestaSolicitud:
    async def test_crear_sin_respuesta(self, client, concepto, stubs_clientes):
        etapa = await concepto()
        resp = await _crear(client, etapa.id, BASE)
        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["radicado_respuesta"] is None and data["archivo_respuesta_id"] is None
        assert stubs_clientes.files.incrementados == [DOC_SOLICITUD]

    async def test_crear_con_respuesta_completa(self, client, concepto, stubs_clientes, db_session):
        etapa = await concepto()
        resp = await _crear(client, etapa.id, {**BASE, **RESPUESTA, "radicado_respuesta": "2024er0002"})
        assert resp.status_code == 201, resp.text
        fila = await _fila(db_session, resp.json()["data"]["id"])
        assert fila.radicado_respuesta == "2024ER0002"  # se normaliza a mayúsculas
        assert fila.fecha_radicado_respuesta == "2024-01-10" and fila.archivo_respuesta_id == DOC_RESPUESTA
        assert sorted(stubs_clientes.files.incrementados) == [DOC_SOLICITUD, DOC_RESPUESTA]

    @pytest.mark.parametrize("parcial", [
        {"radicado_respuesta": "2024ER0002"},
        {"fecha_radicado_respuesta": "2024-01-10"},
        {"archivo_respuesta_id": DOC_RESPUESTA},
        {"radicado_respuesta": "2024ER0002", "fecha_radicado_respuesta": "2024-01-10"},
    ])
    async def test_respuesta_incompleta_400(self, client, concepto, parcial):
        etapa = await concepto()
        resp = await _crear(client, etapa.id, {**BASE, **parcial})
        assert resp.status_code == 400
        assert "respuesta" in resp.json()["detail"]

    async def test_formato_y_fecha_de_la_respuesta(self, client, concepto):
        etapa = await concepto()
        resp = await _crear(client, etapa.id, {**BASE, **RESPUESTA, "radicado_respuesta": "2024EE0002"})
        assert resp.status_code == 400 and "ER" in resp.json()["detail"]
        resp = await _crear(client, etapa.id, {**BASE, **RESPUESTA, "fecha_radicado_respuesta": "2999-01-01"})
        assert resp.status_code == 400

    async def test_agregar_reemplazar_y_quitar_respuesta(self, client, concepto, stubs_clientes, db_session):
        etapa = await concepto()
        sid = (await _crear(client, etapa.id, BASE)).json()["data"]["id"]

        # Agregar la respuesta al editar.
        assert (await _actualizar(client, sid, {**BASE, **RESPUESTA})).status_code == 200
        assert stubs_clientes.files.incrementados[-1] == DOC_RESPUESTA

        # Reemplazar el PDF de la respuesta: resta el viejo, suma el nuevo.
        resp = await _actualizar(client, sid, {**BASE, **RESPUESTA, "archivo_respuesta_id": DOC_RESPUESTA_2})
        assert resp.status_code == 200
        assert stubs_clientes.files.decrementados[-1] == DOC_RESPUESTA
        assert stubs_clientes.files.incrementados[-1] == DOC_RESPUESTA_2

        # Quitarla (los tres vacíos): resta su uso y deja las columnas en NULL.
        vacia = {"radicado_respuesta": "", "fecha_radicado_respuesta": "", "archivo_respuesta_id": None}
        assert (await _actualizar(client, sid, {**BASE, **vacia})).status_code == 200
        assert stubs_clientes.files.decrementados[-1] == DOC_RESPUESTA_2
        fila = await _fila(db_session, sid)
        assert fila.radicado_respuesta is None and fila.archivo_respuesta_id is None

    async def test_eliminar_resta_ambos_archivos(self, client, concepto, stubs_clientes):
        etapa = await concepto()
        sid = (await _crear(client, etapa.id, {**BASE, **RESPUESTA})).json()["data"]["id"]
        resp = await client.delete(f"/etapas/solicitud-informacion/{sid}", headers=gateway_headers(ENCARGADO))
        assert resp.status_code == 200
        assert sorted(stubs_clientes.files.decrementados) == [DOC_SOLICITUD, DOC_RESPUESTA]

    async def test_lectura_de_la_etapa_trae_la_respuesta(self, client, concepto, stubs_clientes, monkeypatch):
        import services.etapas as etapas_svc

        async def _permitido(user_id, permiso):
            return True

        monkeypatch.setattr(etapas_svc, "verify_permission", _permitido)
        etapa = await concepto()
        await _crear(client, etapa.id, {**BASE, **RESPUESTA})
        resp = await client.get(f"/etapas/concepto/{etapa.expediente_id}", headers=gateway_headers(ENCARGADO))
        assert resp.status_code == 200, resp.text
        sol = resp.json()["data"]["solicitud_informacion"]
        assert sol["radicado_respuesta"] == "2024ER0002" and sol["archivo_respuesta_id"] == DOC_RESPUESTA

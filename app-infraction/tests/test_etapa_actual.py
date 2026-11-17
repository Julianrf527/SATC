"""
Etapa actual ("Última etapa") de un expediente: services.etapa_actual.

Una sola definición para GET /todos, GET /encargado/{id}, POST /filtrar y
GET /completo/{id}: la etapa más avanzada que existe según el orden del
proceso (respuesta < visita < concepto < seguimiento < cierre), con códigos
estables. Antes había tres cálculos por fecha más reciente que ignoraban la
Respuesta y dejaban "ganar" a un informe sin fechas (NULL va primero en DESC).
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

import routes.file_query as query_mod
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.informe_tecnico import InformeTecnico
from tests.conftest import gateway_headers


@pytest.fixture
def con_consultar(monkeypatch):
    async def _verify(user_id, permission):
        return permission in {"infraccion_consultar", "infraccion_gestionar"}

    monkeypatch.setattr(query_mod, "verify_permission", _verify)


async def _etapas_por_endpoint(client, expediente_id: int, user_id: int = 5) -> set:
    """etapa_actual del expediente según los cuatro endpoints."""
    h = gateway_headers(user_id)
    completo = (await client.get(f"/expedientes/completo/{expediente_id}", headers=h)).json()["data"]
    todos = (await client.get("/expedientes/todos", headers=h)).json()["data"]
    encargado = (await client.get(f"/expedientes/encargado/{user_id}", headers=h)).json()["data"]
    filtrado = (await client.post("/expedientes/filtrar", json={}, headers=h)).json()["data"]
    assert completo["ultima_etapa"] == completo["etapa_actual"]
    return {
        completo["etapa_actual"],
        *(i["etapa_actual"] for i in todos if i["id"] == expediente_id),
        *(i["etapa_actual"] for i in encargado if i["id"] == expediente_id),
        *(i["etapa_actual"] for i in filtrado if i["id"] == expediente_id),
    }


class TestEtapaActual:
    async def test_sin_etapas_es_null(self, client, con_consultar, make_expediente):
        exp = await make_expediente(abogado_responsable_id=5)
        assert await _etapas_por_endpoint(client, exp.id) == {None}

    async def test_incluye_respuesta(self, client, con_consultar, make_expediente, make_etapa_respuesta):
        exp = await make_expediente(abogado_responsable_id=5)
        await make_etapa_respuesta(exp.id)
        assert await _etapas_por_endpoint(client, exp.id) == {"respuesta"}

    async def test_orden_del_proceso_no_fechas(
        self, client, con_consultar, db_session, make_expediente, make_etapa_respuesta
    ):
        """El concepto (creado "antes") gana a la visita aceptada después:
        manda el orden del proceso, no la fecha."""
        exp = await make_expediente(abogado_responsable_id=5)
        await make_etapa_respuesta(exp.id)
        hace_un_anio = datetime.now(ZoneInfo("America/Bogota")) - timedelta(days=365)
        db_session.add(EtapaAcogerConcepto(
            expediente_id=exp.id, tipo_acogida_concepto="OFICIO", fecha_creacion=hace_un_anio,
        ))
        db_session.add(InformeTecnico(
            expediente_id=exp.id, tipo_informe="VISITA",
            fecha_aceptacion_informe=date.today(), fecha_programacion_visita=date.today() + timedelta(days=30),
        ))
        await db_session.flush()

        assert await _etapas_por_endpoint(client, exp.id) == {"concepto"}

    async def test_informe_sin_fechas_no_gana(
        self, client, con_consultar, db_session, make_expediente
    ):
        """Un seguimiento recién creado (sin fechas) no tapa al cierre."""
        exp = await make_expediente(abogado_responsable_id=5)
        db_session.add(EtapaCierre(expediente_id=exp.id))
        db_session.add(InformeTecnico(expediente_id=exp.id, tipo_informe="SEGUIMIENTO"))
        await db_session.flush()

        assert await _etapas_por_endpoint(client, exp.id) == {"cierre"}

    async def test_visita_sin_fechas_supera_respuesta(
        self, client, con_consultar, db_session, make_expediente, make_etapa_respuesta
    ):
        exp = await make_expediente(abogado_responsable_id=5)
        await make_etapa_respuesta(exp.id)
        db_session.add(InformeTecnico(expediente_id=exp.id, tipo_informe="VISITA"))
        await db_session.flush()

        assert await _etapas_por_endpoint(client, exp.id) == {"visita"}

    async def test_cada_expediente_su_etapa(
        self, client, con_consultar, db_session, make_expediente, make_etapa_respuesta
    ):
        a = await make_expediente(abogado_responsable_id=5)
        b = await make_expediente(abogado_responsable_id=5)
        await make_etapa_respuesta(a.id)
        db_session.add(InformeTecnico(expediente_id=b.id, tipo_informe="SEGUIMIENTO"))
        await db_session.flush()

        data = (await client.get("/expedientes/encargado/5", headers=gateway_headers(5))).json()["data"]
        assert {i["id"]: i["etapa_actual"] for i in data} == {a.id: "respuesta", b.id: "seguimiento"}

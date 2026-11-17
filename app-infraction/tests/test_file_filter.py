"""
POST /expedientes/filtrar (búsqueda avanzada de la lista de expedientes).

Cubre: municipio resuelto por la vereda (antes salía el id de la vereda),
filtro por tipo_afectacion_ids, forma de cada item idéntica a la de
GET /todos y GET /encargado/{id}, y alcance según la vista y el permiso
infraccion_consultar.
"""
from datetime import date

import pytest

import routes.file_query as query_mod
import services.involved as involved_svc
from db.models.expediente_recurso import ExpedienteRecurso
from db.models.expediente_tipo_afectacion import ExpedienteTipoAfectacion
from db.models.recurso_afectado import RecursoAfectado
from db.models.tipo_afectacion import TipoAfectacion
from tests.conftest import gateway_headers

CLAVES_ITEM = {
    "id", "radicado", "fecha_radicado", "fecha_creacion", "archivado",
    "municipio", "involucrados", "etapa_actual", "estado",
}


def _permisos(permitidos: set[str]):
    async def _verify(user_id, permission):
        return permission in permitidos

    return _verify


# El usuario de prueba es un abogado de gestión (infraccion_gestionar, que
# exigen los "propios"); los fixtures solo cambian si además puede consultar.
@pytest.fixture
def sin_consultar(monkeypatch):
    monkeypatch.setattr(query_mod, "verify_permission", _permisos({"infraccion_gestionar"}))


@pytest.fixture
def con_consultar(monkeypatch):
    monkeypatch.setattr(
        query_mod, "verify_permission", _permisos({"infraccion_consultar", "infraccion_gestionar"})
    )


@pytest.fixture
def make_tipo_afectacion(db_session):
    async def _make(nombre: str, recurso_nombre: str = "Agua"):
        recurso = RecursoAfectado(nombre=recurso_nombre)
        db_session.add(recurso)
        await db_session.flush()
        tipo = TipoAfectacion(nombre=nombre, recurso_id=recurso.id)
        db_session.add(tipo)
        await db_session.flush()
        return recurso, tipo

    return _make


async def _filtrar(client, user_id: int, **filtros):
    resp = await client.post("/expedientes/filtrar", json=filtros, headers=gateway_headers(user_id))
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


class TestMunicipioYForma:
    async def test_filtro_municipio_y_municipio_en_respuesta(
        self, client, sin_consultar, make_expediente, make_municipio_vereda
    ):
        muni, vereda = await make_municipio_vereda("Chivor", "Centro")
        _, otra_vereda = await make_municipio_vereda("Guateque", "Sur")
        await make_expediente(abogado_responsable_id=5, vereda_id=vereda.id)
        await make_expediente(abogado_responsable_id=5, vereda_id=otra_vereda.id)

        data = await _filtrar(client, 5, municipio_id=muni.id)

        assert len(data) == 1
        assert data[0]["municipio"] == {"id": muni.id, "nombre": "Chivor"}

    async def test_municipio_correcto_con_ids_desalineados(
        self, client, sin_consultar, db_session, make_expediente, make_municipio_vereda
    ):
        from db.models.vereda import Vereda

        muni, vereda = await make_municipio_vereda("Chivor", "Centro")
        # Segunda vereda del mismo municipio: vereda_id (2) != municipio_id (1).
        # Antes el mapa de municipios se indexaba por vereda_id y salía null.
        vereda_b = Vereda(nombre="Norte", municipio_id=muni.id)
        db_session.add(vereda_b)
        await db_session.flush()
        await make_expediente(abogado_responsable_id=5, vereda_id=vereda_b.id)

        data = await _filtrar(client, 5)

        assert data[0]["municipio"] == {"id": muni.id, "nombre": "Chivor"}

    async def test_forma_identica_a_listado_encargado(
        self, client, sin_consultar, make_expediente, make_municipio_vereda, make_informe_visita_aceptado
    ):
        _, vereda = await make_municipio_vereda()
        exp = await make_expediente(
            abogado_responsable_id=5, vereda_id=vereda.id, fecha_radicado=date(2024, 3, 1)
        )
        await make_informe_visita_aceptado(exp.id)

        filtrado = await _filtrar(client, 5)
        listado = (await client.get("/expedientes/encargado/5", headers=gateway_headers(5))).json()["data"]

        assert set(filtrado[0]) == CLAVES_ITEM
        assert filtrado == listado
        item = filtrado[0]
        assert item["fecha_radicado"] == "2024-03-01"
        assert item["archivado"] is False
        assert item["etapa_actual"] == "visita"
        assert item["estado"] is not None

    async def test_forma_identica_a_listado_todos(
        self, client, con_consultar, make_expediente, make_municipio_vereda
    ):
        _, vereda = await make_municipio_vereda()
        await make_expediente(abogado_responsable_id=5, vereda_id=vereda.id, fecha_radicado=date(2024, 3, 1))
        await make_expediente(abogado_responsable_id=9, archivado=True)

        filtrado = await _filtrar(client, 5, alcance="todos")
        listado = (await client.get("/expedientes/todos", headers=gateway_headers(5))).json()["data"]

        assert all(set(i) == CLAVES_ITEM for i in filtrado)
        key = lambda i: i["id"]  # noqa: E731
        assert sorted(filtrado, key=key) == sorted(listado, key=key)

    async def test_involucrados_por_id_de_expediente(
        self, client, sin_consultar, monkeypatch, make_expediente, link_involucrado
    ):
        exp = await make_expediente(abogado_responsable_id=5)
        await link_involucrado(exp.id, 77)

        class _Stub:
            async def bulk(self, ids):
                return [{"id": i, "nombre": f"Inv {i}"} for i in ids]

        monkeypatch.setattr(involved_svc, "involved_client", _Stub())

        data = await _filtrar(client, 5)

        assert data[0]["involucrados"] == [{"id": 77, "nombre": "Inv 77"}]


class TestFiltros:
    async def test_tipo_afectacion_ids(self, client, sin_consultar, db_session, make_expediente, make_tipo_afectacion):
        _, tala = await make_tipo_afectacion("Tala", "Flora")
        _, vertimiento = await make_tipo_afectacion("Vertimiento", "Agua")
        con_tala = await make_expediente(abogado_responsable_id=5)
        con_vert = await make_expediente(abogado_responsable_id=5)
        await make_expediente(abogado_responsable_id=5)  # sin tipos
        db_session.add_all([
            ExpedienteTipoAfectacion(expediente_id=con_tala.id, tipo_afectacion_id=tala.id),
            ExpedienteTipoAfectacion(expediente_id=con_vert.id, tipo_afectacion_id=vertimiento.id),
        ])
        await db_session.flush()

        solo_tala = await _filtrar(client, 5, tipo_afectacion_ids=[tala.id])
        ambos = await _filtrar(client, 5, tipo_afectacion_ids=[tala.id, vertimiento.id])

        assert [e["id"] for e in solo_tala] == [con_tala.id]
        assert {e["id"] for e in ambos} == {con_tala.id, con_vert.id}

    async def test_tipo_afectacion_y_recurso_se_combinan_con_and(
        self, client, sin_consultar, db_session, make_expediente, make_tipo_afectacion
    ):
        flora, tala = await make_tipo_afectacion("Tala", "Flora")
        agua, _ = await make_tipo_afectacion("Vertimiento", "Agua")
        a = await make_expediente(abogado_responsable_id=5)
        b = await make_expediente(abogado_responsable_id=5)
        db_session.add_all([
            ExpedienteTipoAfectacion(expediente_id=a.id, tipo_afectacion_id=tala.id),
            ExpedienteRecurso(expediente_id=a.id, recurso_id=flora.id),
            ExpedienteTipoAfectacion(expediente_id=b.id, tipo_afectacion_id=tala.id),
            ExpedienteRecurso(expediente_id=b.id, recurso_id=agua.id),
        ])
        await db_session.flush()

        data = await _filtrar(client, 5, tipo_afectacion_ids=[tala.id], recurso_ids=[flora.id])

        assert [e["id"] for e in data] == [a.id]

    async def test_sin_resultados_devuelve_lista_vacia(self, client, sin_consultar, make_expediente):
        await make_expediente(abogado_responsable_id=5, direccion="Calle 1")

        assert await _filtrar(client, 5, direccion="no-existe") == []


class TestAlcance:
    async def test_por_defecto_solo_propios_aunque_tenga_permiso(self, client, con_consultar, make_expediente):
        propio = await make_expediente(abogado_responsable_id=5)
        await make_expediente(abogado_responsable_id=9)

        data = await _filtrar(client, 5)

        assert [e["id"] for e in data] == [propio.id]

    async def test_todos_con_permiso_ve_todos(self, client, con_consultar, make_expediente):
        propio = await make_expediente(abogado_responsable_id=5)
        ajeno = await make_expediente(abogado_responsable_id=9)
        sin_encargado = await make_expediente(abogado_responsable_id=None)

        data = await _filtrar(client, 5, alcance="todos")

        assert {e["id"] for e in data} == {propio.id, ajeno.id, sin_encargado.id}

    async def test_todos_sin_permiso_cae_a_propios(self, client, sin_consultar, make_expediente):
        propio = await make_expediente(abogado_responsable_id=5)
        await make_expediente(abogado_responsable_id=9)

        data = await _filtrar(client, 5, alcance="todos")

        assert [e["id"] for e in data] == [propio.id]

    async def test_alcance_invalido_422(self, client, sin_consultar):
        resp = await client.post(
            "/expedientes/filtrar", json={"alcance": "otro"}, headers=gateway_headers(5)
        )
        assert resp.status_code == 422


class TestErrores:
    async def test_sin_token_gateway_403(self, client):
        resp = await client.post("/expedientes/filtrar", json={})
        assert resp.status_code == 403

    async def test_error_inesperado_es_500(self, client, sin_consultar, monkeypatch, make_expediente):
        await make_expediente(abogado_responsable_id=5)

        async def _boom(*a, **k):
            raise RuntimeError("fallo de BD simulado")

        monkeypatch.setattr(query_mod, "calcular_estados", _boom)

        resp = await client.post("/expedientes/filtrar", json={}, headers=gateway_headers(5))

        assert resp.status_code == 500
        assert resp.json() == {"detail": "Error interno del servidor"}

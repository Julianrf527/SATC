"""Tests de routes/file.py — endpoints de alertas de infracción."""
from datetime import date

import pytest

from tests.conftest import gateway_headers


@pytest.fixture
def permisos_infraccion(monkeypatch):
    """permisos_infraccion({...}) fija los permisos del usuario de la petición."""
    import services.etapas as etapas_mod

    def _fijar(concedidos: set[str]):
        async def _verify(user_id, permission):
            return permission in concedidos

        monkeypatch.setattr(etapas_mod, "verify_permission", _verify)

    return _fijar


class TestAlertsAll:
    async def test_usuario_sin_alertas_propias(self, client, make_expediente, permisos_infraccion):
        # "Mis alertas" vacío no es error: el usuario va a "Todas".
        permisos_infraccion({"infraccion_alertas"})
        await make_expediente(abogado_responsable_id=7)
        resp = await client.get("/expedientes/alertas/todas", headers=gateway_headers(50))
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["total_expedientes"] == 0
        assert data["alertas"] == {}

    async def test_mios_sin_permiso_403(self, client, make_expediente, permisos_infraccion):
        # infraccion_alertas desbloquea la pestaña entera (las dos vistas).
        permisos_infraccion({"infraccion_gestionar"})
        await make_expediente(abogado_responsable_id=7)
        resp = await client.get("/expedientes/alertas/todas", headers=gateway_headers(7))
        assert resp.status_code == 403

    async def test_sin_token_403(self, client):
        resp = await client.get("/expedientes/alertas/todas")
        assert resp.status_code == 403


@pytest.fixture
def permiso_gestion(monkeypatch):
    """El usuario tiene infraccion_gestionar (ve solo los expedientes a su cargo)."""
    import services.etapas as etapas_mod

    async def _verify(user_id, permission):
        return permission == "infraccion_gestionar"

    monkeypatch.setattr(etapas_mod, "verify_permission", _verify)


class TestAlertsExpediente:
    """Misma regla que el resto de lecturas del expediente: consultar ve
    cualquiera; gestionar, solo los suyos. 403 también si no existe."""

    async def test_expediente_inexistente_403(self, client, permiso_gestion):
        resp = await client.get("/expedientes/alertas/9999", headers=gateway_headers(1))
        assert resp.status_code == 403

    async def test_expediente_ajeno_403(self, client, make_expediente, permiso_gestion):
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.get(f"/expedientes/alertas/{exp.id}", headers=gateway_headers(99))
        assert resp.status_code == 403

    async def test_sin_permiso_403(self, client, make_expediente):
        # Ser el abogado responsable no basta sin infraccion_gestionar.
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.get(f"/expedientes/alertas/{exp.id}", headers=gateway_headers(7))
        assert resp.status_code == 403

    async def test_consulta_ve_expediente_ajeno(self, client, make_expediente, permiso_consulta):
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.get(f"/expedientes/alertas/{exp.id}", headers=gateway_headers(99))
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    async def test_expediente_propio_sin_etapas(self, client, make_expediente, permiso_gestion):
        exp = await make_expediente(abogado_responsable_id=7)
        resp = await client.get(f"/expedientes/alertas/{exp.id}", headers=gateway_headers(7))
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "alertas" in data


class TestAlertsAlcance:
    """GET /expedientes/alertas/todas?alcance=mios|todos (filtro de la pestaña
    Alertas). Un expediente sin etapa de respuesta siempre tiene la alerta
    respuesta_plazo, así que cada expediente creado aparece en la respuesta."""

    async def test_mios_por_defecto_solo_los_suyos(self, client, make_expediente, permisos_infraccion):
        permisos_infraccion({"infraccion_alertas"})
        propio = await make_expediente(abogado_responsable_id=7)
        await make_expediente(abogado_responsable_id=8)
        resp = await client.get("/expedientes/alertas/todas", headers=gateway_headers(7))
        assert resp.status_code == 200
        data = resp.json()
        assert data["alcance"] == "mios"
        assert data["total_expedientes"] == 1
        assert list(data["alertas"]) == [propio.radicado]
        for alerta in data["alertas"][propio.radicado].values():
            assert alerta["es_responsable"] is True

    async def test_mios_explicito_igual_que_por_defecto(self, client, make_expediente, permisos_infraccion):
        permisos_infraccion({"infraccion_alertas"})
        await make_expediente(abogado_responsable_id=7)
        await make_expediente(abogado_responsable_id=8)
        por_defecto = (await client.get("/expedientes/alertas/todas", headers=gateway_headers(7))).json()
        explicito = (await client.get("/expedientes/alertas/todas?alcance=mios", headers=gateway_headers(7))).json()
        assert por_defecto == explicito

    async def test_todos_con_permiso_marca_es_responsable(self, client, make_expediente, permisos_infraccion):
        permisos_infraccion({"infraccion_alertas"})
        propio = await make_expediente(abogado_responsable_id=7)
        ajeno = await make_expediente(abogado_responsable_id=8)
        sin_abogado = await make_expediente(abogado_responsable_id=None)
        resp = await client.get("/expedientes/alertas/todas?alcance=todos", headers=gateway_headers(7))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["alcance"] == "todos"
        assert data["total_expedientes"] == 3
        assert set(data["alertas"]) == {propio.radicado, ajeno.radicado, sin_abogado.radicado}
        esperado = {propio.radicado: True, ajeno.radicado: False, sin_abogado.radicado: False}
        for radicado, alertas in data["alertas"].items():
            assert alertas, radicado
            for alerta in alertas.values():
                assert alerta["es_responsable"] is esperado[radicado]
        total = sum(len(a) for a in data["alertas"].values())
        assert sum(data["estadisticas_semaforo"].values()) == total

    async def test_todos_sin_permiso_403(self, client, make_expediente, permisos_infraccion):
        # Ni gestionar ni consultar habilitan 'todos': solo el permiso de la pestaña.
        permisos_infraccion({"infraccion_gestionar", "infraccion_consultar"})
        await make_expediente(abogado_responsable_id=7)
        resp = await client.get("/expedientes/alertas/todas?alcance=todos", headers=gateway_headers(7))
        assert resp.status_code == 403

    async def test_alcance_invalido_422(self, client, permisos_infraccion):
        permisos_infraccion({"infraccion_alertas"})
        resp = await client.get("/expedientes/alertas/todas?alcance=otro", headers=gateway_headers(7))
        assert resp.status_code == 422


class TestAlertsResponsablePorRol:
    """Alertas de un rol (roles_responsables): son de todo usuario con ese
    permiso, en cualquier expediente."""

    async def _expediente_con_informe_sin_asignar(self, db_session, make_expediente):
        from db.models.etapa_respuesta import EtapaRespuesta
        from db.models.informe_tecnico import InformeTecnico

        exp = await make_expediente(abogado_responsable_id=7)
        db_session.add(EtapaRespuesta(expediente_id=exp.id, radicado="R-1", fecha_radicado=date.today(), fecha_creacion=date.today(),
                                      documento_radicado_id=1, requiere_medida_preventiva=False))
        db_session.add(InformeTecnico(expediente_id=exp.id, tipo_informe="VISITA", modo="FLUJO"))
        await db_session.commit()
        return exp

    async def test_asignar_visita_es_de_quien_asigna(self, client, db_session, make_expediente, permisos_infraccion):
        exp = await self._expediente_con_informe_sin_asignar(db_session, make_expediente)
        permisos_infraccion({"infraccion_alertas", "infraccion_asignar_informes"})
        data = (await client.get("/expedientes/alertas/todas", headers=gateway_headers(99))).json()
        alerta = data["alertas"][exp.radicado]["visita_asignar"]
        assert alerta["es_responsable"] is True
        assert alerta["encargado_id"] is None
        assert [r["permiso"] for r in alerta["roles_responsables"]] == ["infraccion_asignar_informes"]

    async def test_asignar_visita_no_es_del_abogado(self, client, db_session, make_expediente, permisos_infraccion):
        exp = await self._expediente_con_informe_sin_asignar(db_session, make_expediente)
        permisos_infraccion({"infraccion_alertas", "infraccion_gestionar"})
        data = (await client.get("/expedientes/alertas/todas", headers=gateway_headers(7))).json()
        assert "visita_asignar" not in data["alertas"].get(exp.radicado, {})
        todas = (await client.get("/expedientes/alertas/todas?alcance=todos", headers=gateway_headers(7))).json()
        assert todas["alertas"][exp.radicado]["visita_asignar"]["es_responsable"] is False

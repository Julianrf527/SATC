"""
Permisos de los endpoints cerrados en la auditoría de permisos (2026-10).

Antes solo validaban el token del gateway: cualquier usuario autenticado podía
crear expedientes, adjuntar/editar/borrar anexos de expedientes ajenos, leer
cualquier expediente o disparar el envío masivo de alertas. Ahora:

  POST   /expediente/add                     -> sancionatorio_gestionar
  GET    /expediente/get                     -> sancionatorio_asignar
  GET    /expediente/get/all                 -> sancionatorio_consultar
  GET    /expediente/full/{id}               -> lectura (*)
  GET    /expediente/download-all/{id}       -> lectura (*)
  GET    /stage/full/{id}                    -> lectura (*)
  GET    /stage/<10 etapas>/{id}             -> lectura (*)
  POST/PUT/DELETE /stage/doc-attached/...    -> gestionar + encargado del expediente de la etapa
  GET    /involved/involved-list/{id}        -> lectura (*)
  GET    /involved/file-list/{involucrado}   -> consultar o involucrado_gestionar
  POST   /alerts/send-weekly-report          -> sancionatorio_asignar

  (*) lectura = sancionatorio_consultar, o sancionatorio_gestionar y ser el
      encargado. Ajeno o inexistente -> 403 (no revela qué ids existen).
"""
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from conftest import gateway_headers
from db.models.documento_anexo import DocumentoAnexo
from db.models.etapa_medida_preventiva import EtapaMedidaPreventiva
from db.models.expediente import Expediente

CONSULTAR = "sancionatorio_consultar"
GESTIONAR = "sancionatorio_gestionar"
ASIGNAR = "sancionatorio_asignar"
ALERTAS = "sancionatorio_alertas"
INVOLUCRADOS = "involucrado_gestionar"

SIN_PERMISOS_EXP = "Sin permisos sobre este expediente"

ETAPAS_GET = [
    "investigation", "measure", "start-process", "cessation", "formulation",
    "opening", "closing", "decision", "resource", "execution",
]


@pytest.fixture
def sin_servicios(monkeypatch):
    """Llamadas HTTP a app-users / app-docs / app-involved que no vienen al caso."""
    import routes.alerts as alerts_mod
    import routes.expediente_crud as crud
    import routes.stage as stage
    import services.involucrado as involucrado_srv

    async def _vacio(*_a, **_k):
        return {}

    monkeypatch.setattr(crud, "get_users_by_permission", _vacio)
    monkeypatch.setattr(crud, "get_user_info", _vacio)
    monkeypatch.setattr(crud, "get_involucrados_by_expedientes_ids", _vacio)
    monkeypatch.setattr(stage, "get_involucrados_by_expedientes_ids", _vacio)
    # /stage/full lo importa dentro de la función.
    monkeypatch.setattr(involucrado_srv, "get_involucrados_by_expedientes_ids", _vacio)
    monkeypatch.setattr(stage, "increment_file_usage", AsyncMock())
    monkeypatch.setattr(stage, "decrement_file_usage", AsyncMock())
    tarea = AsyncMock()
    monkeypatch.setattr(alerts_mod, "tarea_envio_alertas_semanal", tarea)
    return tarea


# ── C2: POST /expediente/add ────────────────────────────────────────────────

class TestAgregarExpediente:
    def _body(self, radicado):
        return {
            "radicado": radicado, "expediente": "EXP-NUEVO", "recurso": [], "motivo": "m",
            "encargado_id": 5, "municipio": 1, "vereda": 1, "direccion": "d",
        }

    async def test_sin_gestionar_403_y_no_crea(self, api, permisos, db_session, sin_servicios):
        permisos({CONSULTAR, ASIGNAR, ALERTAS})
        resp = await api.post("/expediente/add", headers=gateway_headers(5), json=self._body("RAD-NUEVO"))
        assert resp.status_code == 403
        assert await db_session.scalar(select(func.count()).select_from(Expediente)) == 0

    async def test_con_gestionar_pasa_el_permiso(self, api, permisos, make_expediente, sin_servicios):
        # Radicado repetido: llega a la validación de negocio (400), es decir,
        # pasó el control de permiso, sin necesitar veredas ni recursos.
        permisos({GESTIONAR})
        existente = await make_expediente(encargado_id=5)
        resp = await api.post("/expediente/add", headers=gateway_headers(5), json=self._body(existente.radicado))
        assert resp.status_code == 400
        assert resp.json()["detail"] == "El radicado ya existe"


# ── A4 / A1: listados ─────────────────────────────────────────────────────────

class TestListados:
    async def test_get_asignacion_sin_asignar_403(self, api, permisos, sin_servicios):
        permisos({GESTIONAR, CONSULTAR})
        assert (await api.get("/expediente/get", headers=gateway_headers(5))).status_code == 403

    async def test_get_asignacion_con_asignar(self, api, permisos, make_expediente, sin_servicios):
        permisos({ASIGNAR})
        exp = await make_expediente(encargado_id=9)
        resp = await api.get("/expediente/get", headers=gateway_headers(5))
        assert resp.status_code == 200
        assert [e["id"] for e in resp.json()["data"]] == [exp.id]

    async def test_get_all_sin_consultar_403(self, api, permisos, sin_servicios):
        permisos({GESTIONAR, ASIGNAR})
        assert (await api.get("/expediente/get/all", headers=gateway_headers(5))).status_code == 403

    async def test_get_all_con_consultar_ve_todos(self, api, permisos, make_expediente, sin_servicios):
        permisos({CONSULTAR})
        a = await make_expediente(encargado_id=5)
        b = await make_expediente(encargado_id=9)
        resp = await api.get("/expediente/get/all", headers=gateway_headers(5))
        assert resp.status_code == 200
        assert {e["id"] for e in resp.json()["data"]} == {a.id, b.id}

    async def test_sin_token_403(self, api):
        assert (await api.get("/expediente/get/all")).status_code == 403


# ── Lecturas de un expediente (A2, A3, A5–A14, A15, A16) ─────────────────────

LECTURAS = (
    [f"/stage/{e}/{{id}}" for e in ETAPAS_GET]
    + ["/stage/full/{id}", "/expediente/full/{id}", "/involved/involved-list/{id}"]
)


class TestLecturaExpediente:
    @pytest.mark.parametrize("ruta", LECTURAS)
    async def test_consultar_abre_expediente_ajeno(self, api, permisos, make_expediente, sin_servicios, ruta):
        permisos({CONSULTAR})
        exp = await make_expediente(encargado_id=9)
        resp = await api.get(ruta.format(id=exp.id), headers=gateway_headers(5))
        assert resp.status_code == 200

    @pytest.mark.parametrize("ruta", LECTURAS)
    async def test_gestionar_abre_el_suyo(self, api, permisos, make_expediente, sin_servicios, ruta):
        permisos({GESTIONAR})
        exp = await make_expediente(encargado_id=5)
        resp = await api.get(ruta.format(id=exp.id), headers=gateway_headers(5))
        assert resp.status_code == 200

    @pytest.mark.parametrize("ruta", LECTURAS)
    async def test_gestionar_no_abre_ajeno(self, api, permisos, make_expediente, sin_servicios, ruta):
        permisos({GESTIONAR})
        exp = await make_expediente(encargado_id=9)
        resp = await api.get(ruta.format(id=exp.id), headers=gateway_headers(5))
        assert resp.status_code == 403
        assert resp.json()["detail"] == SIN_PERMISOS_EXP

    @pytest.mark.parametrize("ruta", LECTURAS)
    async def test_sin_permiso_de_modulo_403_aunque_sea_el_encargado(self, api, permisos, make_expediente, sin_servicios, ruta):
        permisos({ALERTAS, ASIGNAR, INVOLUCRADOS})
        exp = await make_expediente(encargado_id=5)
        resp = await api.get(ruta.format(id=exp.id), headers=gateway_headers(5))
        assert resp.status_code == 403

    @pytest.mark.parametrize("ruta", LECTURAS)
    async def test_inexistente_403_no_404(self, api, permisos, sin_servicios, ruta):
        permisos({CONSULTAR})
        resp = await api.get(ruta.format(id=999999), headers=gateway_headers(5))
        assert resp.status_code == 403

    async def test_download_all_ajeno_con_gestionar_403(self, api, permisos, make_expediente):
        permisos({GESTIONAR})
        exp = await make_expediente(encargado_id=9)
        resp = await api.get(f"/expediente/download-all/{exp.id}", headers=gateway_headers(5))
        assert resp.status_code == 403

    async def test_download_all_con_consultar_pasa_el_permiso(self, api, permisos, make_expediente):
        # Sin documentos el endpoint responde con su propio error de negocio
        # (no 403): el control de permiso ya pasó.
        permisos({CONSULTAR})
        exp = await make_expediente(encargado_id=9)
        resp = await api.get(f"/expediente/download-all/{exp.id}", headers=gateway_headers(5))
        assert resp.status_code != 403


# ── A17: expedientes de un involucrado ───────────────────────────────────────

class TestExpedientesDeInvolucrado:
    async def test_solo_gestionar_403(self, api, permisos):
        permisos({GESTIONAR})
        assert (await api.get("/involved/file-list/1", headers=gateway_headers(5))).status_code == 403

    @pytest.mark.parametrize("permiso", [CONSULTAR, INVOLUCRADOS])
    async def test_con_consultar_o_involucrados_pasa(self, api, permisos, permiso):
        permisos({permiso})
        # Sin vínculos -> 404 propio del endpoint (ya pasó el permiso).
        assert (await api.get("/involved/file-list/1", headers=gateway_headers(5))).status_code == 404


# ── A18: envío manual de alertas ──────────────────────────────────────────────

class TestEnvioSemanal:
    async def test_sin_asignar_403_y_no_envia(self, api, permisos, sin_servicios):
        permisos({GESTIONAR, CONSULTAR, ALERTAS})
        resp = await api.post("/alerts/send-weekly-report", headers=gateway_headers(5))
        assert resp.status_code == 403
        sin_servicios.assert_not_called()

    async def test_con_asignar_envia(self, api, permisos, sin_servicios):
        permisos({ASIGNAR})
        resp = await api.post("/alerts/send-weekly-report", headers=gateway_headers(5))
        assert resp.status_code == 200
        sin_servicios.assert_called_once()


# ── C3–C5: documentos anexos ──────────────────────────────────────────────────

class TestDocumentosAnexos:
    BODY = {"nombre": "Informe Tecnico", "documento_anexo_id": 7, "etapa_tipo": "etapa_medida_preventiva"}

    async def _medida(self, db_session, make_expediente, encargado_id):
        exp = await make_expediente(encargado_id=encargado_id)
        medida = EtapaMedidaPreventiva(expediente_id=exp.id)
        db_session.add(medida)
        await db_session.flush()
        return exp, medida

    async def _anexo(self, db_session, medida):
        doc = DocumentoAnexo(etapa_tipo="etapa_medida_preventiva", etapa_ref_id=medida.id,
                             nombre="Previo", documento_anexo_id=3)
        db_session.add(doc)
        await db_session.flush()
        return doc

    async def _cuantos(self, db_session):
        return await db_session.scalar(select(func.count()).select_from(DocumentoAnexo))

    # POST
    async def test_post_encargado_con_gestionar_201(self, client, permisos, db_session, make_expediente, sin_servicios):
        permisos({GESTIONAR})
        _, medida = await self._medida(db_session, make_expediente, 5)
        resp = await client.post(f"/doc-attached/{medida.id}", headers=gateway_headers(5), json=self.BODY)
        assert resp.status_code == 201

    async def test_post_expediente_ajeno_403(self, client, permisos, db_session, make_expediente, sin_servicios):
        # Ni con consultar se puede escribir en un expediente ajeno.
        permisos({GESTIONAR, CONSULTAR})
        _, medida = await self._medida(db_session, make_expediente, 9)
        resp = await client.post(f"/doc-attached/{medida.id}", headers=gateway_headers(5), json=self.BODY)
        assert resp.status_code == 403
        assert await self._cuantos(db_session) == 0

    async def test_post_encargado_sin_gestionar_403(self, client, permisos, db_session, make_expediente, sin_servicios):
        permisos({CONSULTAR})
        _, medida = await self._medida(db_session, make_expediente, 5)
        resp = await client.post(f"/doc-attached/{medida.id}", headers=gateway_headers(5), json=self.BODY)
        assert resp.status_code == 403
        assert await self._cuantos(db_session) == 0

    async def test_post_etapa_inexistente_403(self, client, permisos, sin_servicios):
        permisos({GESTIONAR})
        resp = await client.post("/doc-attached/999999", headers=gateway_headers(5), json=self.BODY)
        assert resp.status_code == 403

    # PUT
    async def test_put_encargado_200(self, client, permisos, db_session, make_expediente, sin_servicios):
        permisos({GESTIONAR})
        _, medida = await self._medida(db_session, make_expediente, 5)
        doc = await self._anexo(db_session, medida)
        resp = await client.put(f"/doc-attached/{medida.id}/{doc.id}", headers=gateway_headers(5), json=self.BODY)
        assert resp.status_code == 200

    async def test_put_ajeno_403_y_no_cambia(self, client, permisos, db_session, make_expediente, sin_servicios):
        permisos({GESTIONAR, CONSULTAR})
        _, medida = await self._medida(db_session, make_expediente, 9)
        doc = await self._anexo(db_session, medida)
        resp = await client.put(f"/doc-attached/{medida.id}/{doc.id}", headers=gateway_headers(5), json=self.BODY)
        assert resp.status_code == 403
        await db_session.refresh(doc)
        assert doc.nombre == "Previo"

    # DELETE
    async def test_delete_encargado_200(self, client, permisos, db_session, make_expediente, sin_servicios):
        permisos({GESTIONAR})
        _, medida = await self._medida(db_session, make_expediente, 5)
        doc = await self._anexo(db_session, medida)
        resp = await client.delete(f"/doc-attached/{medida.id}/{doc.id}", headers=gateway_headers(5))
        assert resp.status_code == 200
        assert await self._cuantos(db_session) == 0

    async def test_delete_ajeno_403_y_no_borra(self, client, permisos, db_session, make_expediente, sin_servicios):
        permisos({GESTIONAR, CONSULTAR})
        _, medida = await self._medida(db_session, make_expediente, 9)
        doc = await self._anexo(db_session, medida)
        resp = await client.delete(f"/doc-attached/{medida.id}/{doc.id}", headers=gateway_headers(5))
        assert resp.status_code == 403
        assert await self._cuantos(db_session) == 1

    async def test_delete_inexistente_403(self, client, permisos, sin_servicios):
        permisos({GESTIONAR})
        resp = await client.delete("/doc-attached/999999/999999", headers=gateway_headers(5))
        assert resp.status_code == 403

"""
Tests de informes técnicos: asignación con revisor separado, cambio de modo
FLUJO/MANUAL, cargue manual, y el bug fix de sync (estado 'rechazado', antes
comparado incorrectamente contra 'devuelto' — nunca coincidía).
"""
from datetime import date
from types import SimpleNamespace

import pytest

import routes.reports as reports_mod
from core.permission import Permission
from db.models.informe_tecnico import InformeTecnico
from services.estado_expediente import _evaluar_uno
from tests.conftest import gateway_headers


async def _ok(*a, **k):
    return {"ok": True}


async def _create_doc_ok(*a, **k):
    return {"ok": True, "documento_id": 555}


def _make_verify_permission(allowed: bool = True):
    async def _verify(user_id, permission):
        return allowed

    return _verify


@pytest.fixture(autouse=True)
def _mock_permissions(monkeypatch):
    """Por defecto todos los permisos pasan; los tests que necesiten negar
    uno específico sobreescriben con su propio monkeypatch."""
    monkeypatch.setattr(reports_mod, "verify_permission", _make_verify_permission(True))
    monkeypatch.setattr(reports_mod, "create_doc_for_professional", _create_doc_ok)
    monkeypatch.setattr(reports_mod, "finalize_doc_as_rejected", _ok)
    monkeypatch.setattr(reports_mod, "increment_file_usage", _ok)
    monkeypatch.setattr(reports_mod, "decrement_file_usage", _ok)


@pytest.fixture
def make_informe(db_session):
    async def _make(expediente_id: int, **overrides) -> InformeTecnico:
        defaults = dict(expediente_id=expediente_id, tipo_informe="VISITA")
        defaults.update(overrides)
        informe = InformeTecnico(**defaults)
        db_session.add(informe)
        await db_session.flush()
        return informe

    return _make


class TestAssign:
    async def test_asignar_profesional_y_revisor_distintos_ok(self, client, make_expediente, make_informe):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id)

        resp = await client.post(
            f"/informes/{informe.id}/assign",
            json={"profesional_id": 10, "revisor_id": 20},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True

    async def test_asignar_profesional_igual_revisor_400(self, client, make_expediente, make_informe):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id)

        resp = await client.post(
            f"/informes/{informe.id}/assign",
            json={"profesional_id": 10, "revisor_id": 10},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400

    async def test_asignar_revisor_sin_permiso_400(self, client, make_expediente, make_informe, monkeypatch):
        async def _verify(user_id, permission):
            return permission != Permission.REVIEW_REPORTS

        monkeypatch.setattr(reports_mod, "verify_permission", _verify)

        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id)

        resp = await client.post(
            f"/informes/{informe.id}/assign",
            json={"profesional_id": 10, "revisor_id": 20},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400

    async def test_asignar_bloqueado_en_modo_manual(self, client, make_expediente, make_informe):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, modo="MANUAL")

        resp = await client.post(
            f"/informes/{informe.id}/assign",
            json={"profesional_id": 10, "revisor_id": 20},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400


class TestSwitchMode:
    async def test_flujo_a_manual_limpia_asignacion(self, client, make_expediente, make_informe, db_session):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(
            exp.id,
            profesional_asignado_id=10,
            revisor_asignado_id=20,
            fecha_programacion_visita=date(2024, 1, 1),
        )

        resp = await client.put(
            f"/informes/{informe.id}/switch-mode",
            json={"modo": "MANUAL"},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 200
        assert resp.json()["modo"] == "MANUAL"

        await db_session.refresh(informe)
        assert informe.modo == "MANUAL"
        assert informe.profesional_asignado_id is None
        assert informe.revisor_asignado_id is None
        assert informe.fecha_programacion_visita is None

    async def test_manual_a_flujo_decrementa_y_limpia_documento(self, client, make_expediente, make_informe, db_session, monkeypatch):
        decrementados = []

        async def _decrement(file_ids):
            decrementados.extend(file_ids)
            return {"ok": True}

        monkeypatch.setattr(reports_mod, "decrement_file_usage", _decrement)

        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(
            exp.id,
            modo="MANUAL",
            documento_informe_id=999,
            fecha_recibido_informe=date(2024, 1, 1),
            fecha_aceptacion_informe=date(2024, 1, 2),
        )

        resp = await client.put(
            f"/informes/{informe.id}/switch-mode",
            json={"modo": "FLUJO"},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 200

        await db_session.refresh(informe)
        assert informe.modo == "FLUJO"
        assert informe.documento_informe_id is None
        assert informe.fecha_aceptacion_informe is None
        assert decrementados == [999]

    async def test_mismo_modo_no_hace_nada(self, client, make_expediente, make_informe):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, modo="FLUJO")

        resp = await client.put(
            f"/informes/{informe.id}/switch-mode",
            json={"modo": "FLUJO"},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 200
        assert "Ya estaba" in resp.json()["message"]


class TestManualUpload:
    async def test_cargue_manual_requiere_modo_manual(self, client, make_expediente, make_informe):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, modo="FLUJO")

        resp = await client.post(
            f"/informes/{informe.id}/manual-upload",
            json={
                "file_id": 123,
                "fecha_recibido": "2024-01-01",
                "fecha_aceptacion": "2024-01-02",
            },
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400

    async def test_cargue_manual_ok(self, client, make_expediente, make_informe, db_session):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, modo="MANUAL")

        resp = await client.post(
            f"/informes/{informe.id}/manual-upload",
            json={
                "file_id": 123,
                "fecha_recibido": "2024-01-01",
                "fecha_aceptacion": "2024-01-02",
                "fecha_programacion_visita": "2023-12-20",
            },
            headers=gateway_headers(1),
        )
        assert resp.status_code == 200

        await db_session.refresh(informe)
        assert informe.documento_informe_id == 123
        assert informe.fecha_recibido_informe == date(2024, 1, 1)
        assert informe.fecha_aceptacion_informe == date(2024, 1, 2)
        assert informe.fecha_programacion_visita == date(2023, 12, 20)


class TestSyncEstadoRechazado:
    """Bug fix: el estado real de un documento devuelto en app-docs es
    'rechazado', no 'devuelto' — antes esa rama nunca se ejecutaba."""

    async def test_sync_detecta_rechazado(self, client, make_expediente, make_informe, monkeypatch):
        async def _get_doc_detail(docs_id):
            return {"ok": True, "estado": "rechazado"}

        monkeypatch.setattr(reports_mod, "get_doc_detail", _get_doc_detail)

        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, profesional_asignado_id=10)

        # Necesita un proceso activo para que /sync lo encuentre.
        resp_assign = await client.post(
            f"/informes/{informe.id}/assign",
            json={"profesional_id": 10, "revisor_id": 20},
            headers=gateway_headers(1),
        )
        assert resp_assign.status_code == 200

        resp = await client.put(f"/informes/{informe.id}/sync", headers=gateway_headers(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["estado"] == "rechazado"
        assert "devuelto" in body["message"].lower()

    async def test_sync_aprobado_actualiza_informe(self, client, make_expediente, make_informe, monkeypatch, db_session):
        async def _get_doc_detail(docs_id):
            return {
                "ok": True,
                "estado": "aprobado",
                "fecha_ultima_actualizacion": "2024-02-01T10:00:00",
                "ultima_version": {"fecha_subida": "2024-01-30T10:00:00", "file_hash_id": 777},
            }

        monkeypatch.setattr(reports_mod, "get_doc_detail", _get_doc_detail)

        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, profesional_asignado_id=10)

        resp_assign = await client.post(
            f"/informes/{informe.id}/assign",
            json={"profesional_id": 10, "revisor_id": 20},
            headers=gateway_headers(1),
        )
        assert resp_assign.status_code == 200

        resp = await client.put(f"/informes/{informe.id}/sync", headers=gateway_headers(1))
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        await db_session.refresh(informe)
        assert informe.documento_informe_id == 777
        assert informe.fecha_aceptacion_informe == date(2024, 2, 1)


class TestEstadoExpedienteCascade:
    """Unit tests puros de la pirámide de estados (sin DB)."""

    def _base_kwargs(self, **overrides):
        base = dict(
            archivado=False,
            cierre_acto_id=None,
            concepto=None,
            visita=None,
            seguimiento=None,
            notificados_actos=set(),
            solicitud_concepto_ids=set(),
            tiene_involucrados=False,
        )
        base.update(overrides)
        return base

    def test_archivado_gana_sobre_todo(self):
        kwargs = self._base_kwargs(archivado=True, cierre_acto_id=5, notificados_actos=set())
        assert _evaluar_uno(**kwargs) == "ARCHIVADO"

    def test_cierre_sin_notificar(self):
        kwargs = self._base_kwargs(cierre_acto_id=5, notificados_actos=set())
        assert _evaluar_uno(**kwargs) == "NOTIFICAR Y/O COMUNICAR ACTO ADM DE SEGUIMIENTO"

    def test_seguimiento_sin_fecha_programacion(self):
        seguimiento = SimpleNamespace(fecha_programacion_visita=None, fecha_aceptacion_informe=None)
        kwargs = self._base_kwargs(seguimiento=seguimiento)
        assert _evaluar_uno(**kwargs) == "PARA PROGRAMAR SEGUIMIENTO"

    def test_seguimiento_programado(self):
        seguimiento = SimpleNamespace(fecha_programacion_visita=date(2024, 1, 1), fecha_aceptacion_informe=None)
        kwargs = self._base_kwargs(seguimiento=seguimiento)
        assert _evaluar_uno(**kwargs) == "SEGUIMIENTO PROGRAMADO"

    def test_concepto_auto_requerimiento_notificado(self):
        concepto = SimpleNamespace(id=1, tipo_acogida_concepto="AUTO_REQUERIMIENTO", acto_administrativo_id=9)
        kwargs = self._base_kwargs(concepto=concepto, notificados_actos={9})
        assert _evaluar_uno(**kwargs) == "VISITA DE SGTO A CUMPLIMIENTO"

    def test_concepto_auto_requerimiento_no_notificado(self):
        concepto = SimpleNamespace(id=1, tipo_acogida_concepto="AUTO_REQUERIMIENTO", acto_administrativo_id=9)
        kwargs = self._base_kwargs(concepto=concepto, notificados_actos=set())
        assert _evaluar_uno(**kwargs) == "NOTIFICAR Y/O COMUNICAR ACTO ADM. ARCHIVADO"

    def test_solicitud_informacion_sin_involucrados(self):
        concepto = SimpleNamespace(id=1, tipo_acogida_concepto="OFICIO", acto_administrativo_id=None)
        kwargs = self._base_kwargs(concepto=concepto, solicitud_concepto_ids={1}, tiene_involucrados=False)
        assert _evaluar_uno(**kwargs) == "POR ALLEGAR INFORMACIÓN"

    def test_solicitud_informacion_con_involucrados_no_aplica(self):
        concepto = SimpleNamespace(id=1, tipo_acogida_concepto="OFICIO", acto_administrativo_id=None)
        kwargs = self._base_kwargs(concepto=concepto, solicitud_concepto_ids={1}, tiene_involucrados=True)
        assert _evaluar_uno(**kwargs) is None

    def test_visita_sin_fecha_programacion(self):
        visita = SimpleNamespace(fecha_programacion_visita=None, fecha_aceptacion_informe=None)
        kwargs = self._base_kwargs(visita=visita)
        assert _evaluar_uno(**kwargs) == "PARA PROGRAMAR VISITA"

    def test_visita_aceptada_sin_concepto_pide_acoger(self):
        visita = SimpleNamespace(fecha_programacion_visita=date(2024, 1, 1), fecha_aceptacion_informe=date(2024, 1, 5))
        kwargs = self._base_kwargs(visita=visita, concepto=None)
        assert _evaluar_uno(**kwargs) == "ACOGER CONCEPTO"

    def test_visita_programada_sin_aceptar(self):
        visita = SimpleNamespace(fecha_programacion_visita=date(2024, 1, 1), fecha_aceptacion_informe=None)
        kwargs = self._base_kwargs(visita=visita)
        assert _evaluar_uno(**kwargs) == "VISITA PROGRAMADA"

    def test_nada_aplica_devuelve_none(self):
        assert _evaluar_uno(**self._base_kwargs()) is None

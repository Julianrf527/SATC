"""
Tests de informes técnicos: asignación con revisor separado, cambio de modo
FLUJO/MANUAL, cargue manual (matriz obligatoria en VISITA) y edición de la
matriz de recursos afectados. El ciclo de revisión propio está en
test_revision_informes.py.
"""
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import select

import routes.reports as reports_mod
import services.users as users_svc
from core.permission import Permission
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.informe_recurso_afectado import RECURSOS_MATRIZ, InformeRecursoAfectado
from db.models.informe_tecnico import InformeTecnico
from services.estado_expediente import _evaluar_uno
from tests.conftest import gateway_headers


async def _ok(*a, **k):
    return {"ok": True}


def _file_info(content_type: str):
    async def _get(file_id):
        return {"ok": True, "data": {"id": file_id, "content_type": content_type}}

    return _get


def matriz_completa(**cambios) -> list[dict]:
    """Matriz con todos los recursos: AGUA grave/irreversible, el resto "no existe"."""
    filas = [
        {"recurso": r, "magnitud": "GRAVE", "reversibilidad": "IRREVERSIBLE", "no_existe": False}
        if r == "AGUA" else {"recurso": r, "no_existe": True}
        for r in RECURSOS_MATRIZ
    ]
    for fila in filas:
        fila.update(cambios.get(fila["recurso"], {}))
    return filas


def _make_verify_permission(allowed: bool = True):
    async def _verify(user_id, permission):
        return allowed

    return _verify


@pytest.fixture(autouse=True)
def _mock_permissions(monkeypatch, stubs_clientes):
    """Por defecto todos los permisos pasan; los tests que necesiten negar
    uno específico sobreescriben con su propio monkeypatch."""
    monkeypatch.setattr(reports_mod, "verify_permission", _make_verify_permission(True))
    monkeypatch.setattr(users_svc, "verify_permission", _make_verify_permission(True))
    monkeypatch.setattr(reports_mod, "increment_file_usage", _ok)
    monkeypatch.setattr(reports_mod, "decrement_file_usage", _ok)
    monkeypatch.setattr(reports_mod, "get_file_info", _file_info("application/pdf"))


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
            f"/informes/{informe.id}/asignar",
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
            f"/informes/{informe.id}/asignar",
            json={"profesional_id": 10, "revisor_id": 10},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400

    async def test_asignar_revisor_sin_permiso_400(self, client, make_expediente, make_informe, monkeypatch):
        async def _verify(user_id, permission):
            return permission != Permission.LIDER_TECNICO

        monkeypatch.setattr(reports_mod, "verify_permission", _verify)

        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id)

        resp = await client.post(
            f"/informes/{informe.id}/asignar",
            json={"profesional_id": 10, "revisor_id": 20},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400

    async def test_asignar_bloqueado_en_modo_manual(self, client, make_expediente, make_informe):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, modo="MANUAL")

        resp = await client.post(
            f"/informes/{informe.id}/asignar",
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
            f"/informes/{informe.id}/cambiar-modo",
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
            f"/informes/{informe.id}/cambiar-modo",
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
            f"/informes/{informe.id}/cambiar-modo",
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
            f"/informes/{informe.id}/cargue-manual",
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
            f"/informes/{informe.id}/cargue-manual",
            json={
                "file_id": 123,
                "fecha_recibido": "2024-01-01",
                "fecha_aceptacion": "2024-01-02",
                "fecha_programacion_visita": "2023-12-20",
                "recursos_afectados": matriz_completa(),
            },
            headers=gateway_headers(1),
        )
        assert resp.status_code == 200, resp.text

        await db_session.refresh(informe)
        assert informe.documento_informe_id == 123
        assert informe.fecha_recibido_informe == date(2024, 1, 1)
        assert informe.fecha_aceptacion_informe == date(2024, 1, 2)
        assert informe.fecha_programacion_visita == date(2023, 12, 20)
        filas = (await db_session.execute(
            select(InformeRecursoAfectado).where(InformeRecursoAfectado.informe_id == informe.id)
        )).scalars().all()
        assert len(filas) == len(RECURSOS_MATRIZ)
        agua = next(f for f in filas if f.recurso == "AGUA")
        assert (agua.magnitud, agua.reversibilidad, agua.no_existe) == ("GRAVE", "IRREVERSIBLE", False)

    async def test_cargue_manual_visita_sin_matriz_400(self, client, make_expediente, make_informe, db_session):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, modo="MANUAL")
        resp = await client.post(
            f"/informes/{informe.id}/cargue-manual",
            json={"file_id": 123, "fecha_recibido": "2024-01-01", "fecha_aceptacion": "2024-01-02"},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400
        assert "matriz" in resp.json()["detail"]
        await db_session.refresh(informe)
        assert informe.documento_informe_id is None

    async def test_cargue_manual_matriz_incompleta_400(self, client, make_expediente, make_informe):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, modo="MANUAL")
        resp = await client.post(
            f"/informes/{informe.id}/cargue-manual",
            json={"file_id": 123, "fecha_recibido": "2024-01-01", "fecha_aceptacion": "2024-01-02",
                  "recursos_afectados": matriz_completa()[:-1]},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400
        assert RECURSOS_MATRIZ[-1] in resp.json()["detail"]

    async def test_cargue_manual_fila_sin_magnitud_400(self, client, make_expediente, make_informe):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, modo="MANUAL")
        resp = await client.post(
            f"/informes/{informe.id}/cargue-manual",
            json={"file_id": 123, "fecha_recibido": "2024-01-01", "fecha_aceptacion": "2024-01-02",
                  "recursos_afectados": matriz_completa(AGUA={"magnitud": None})},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400
        assert "AGUA" in resp.json()["detail"]

    async def test_cargue_manual_seguimiento_no_pide_matriz(self, client, make_expediente, make_informe):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, modo="MANUAL", tipo_informe="SEGUIMIENTO")
        resp = await client.post(
            f"/informes/{informe.id}/cargue-manual",
            json={"file_id": 123, "fecha_recibido": "2024-01-01", "fecha_aceptacion": "2024-01-02"},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 200, resp.text

    async def test_cargue_manual_rechaza_word(self, client, make_expediente, make_informe, db_session, monkeypatch):
        monkeypatch.setattr(
            reports_mod,
            "get_file_info",
            _file_info("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        )
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, modo="MANUAL")

        resp = await client.post(
            f"/informes/{informe.id}/cargue-manual",
            json={"file_id": 123, "fecha_recibido": "2024-01-01", "fecha_aceptacion": "2024-01-02",
                  "recursos_afectados": matriz_completa()},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]

        await db_session.refresh(informe)
        assert informe.documento_informe_id is None


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
        assert _evaluar_uno(**kwargs) == "NOTIFICAR ACTO ADM. ARCHIVADO"

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


class TestPersonaElegidaConPermiso:
    """5.2: la persona elegida (profesional / revisor) debe tener el permiso con
    que la pantalla AsignarInformes arma sus listas (GET /informes/usuarios-*)."""

    @staticmethod
    def _solo(monkeypatch, negado: str):
        async def _verify(user_id, permission):
            return permission != negado

        monkeypatch.setattr(reports_mod, "verify_permission", _verify)

    async def test_asignar_profesional_sin_permiso_400(self, client, make_expediente, make_informe, monkeypatch):
        self._solo(monkeypatch, Permission.TECNICO)
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id)
        resp = await client.post(
            f"/informes/{informe.id}/asignar",
            json={"profesional_id": 10, "revisor_id": 20},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400
        assert "infraccion_tecnico" in resp.json()["detail"]

    async def test_cargue_manual_profesional_sin_permiso_400(self, client, make_expediente, make_informe, monkeypatch):
        self._solo(monkeypatch, Permission.TECNICO)
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, modo="MANUAL")
        resp = await client.post(
            f"/informes/{informe.id}/cargue-manual",
            json={"file_id": 123, "fecha_recibido": "2024-01-01", "fecha_aceptacion": "2024-01-02",
                  "profesional_id": 10, "recursos_afectados": matriz_completa()},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400
        assert "infraccion_tecnico" in resp.json()["detail"]

    async def test_cargue_manual_revisor_sin_permiso_400(self, client, make_expediente, make_informe, monkeypatch):
        self._solo(monkeypatch, Permission.LIDER_TECNICO)
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id, modo="MANUAL")
        resp = await client.post(
            f"/informes/{informe.id}/cargue-manual",
            json={"file_id": 123, "fecha_recibido": "2024-01-01", "fecha_aceptacion": "2024-01-02",
                  "revisor_id": 20, "recursos_afectados": matriz_completa()},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 400
        assert "infraccion_lider_tecnico" in resp.json()["detail"]


class TestEdicionMatriz:
    """El técnico edita solo la matriz (no el informe) hasta Acoger concepto;
    super gestión la edita en informes MANUAL."""

    TECNICO, OTRO, SUPER = 10, 30, 40

    @pytest.fixture
    def solo_super_tiene_cargue(self, monkeypatch):
        async def _verify(user_id, permission):
            if permission == Permission.MANUAL_UPLOAD:
                return int(user_id) == self.SUPER
            return True

        monkeypatch.setattr(reports_mod, "verify_permission", _verify)
        monkeypatch.setattr(users_svc, "verify_permission", _verify)

    @pytest.fixture
    def informe_aceptado(self, make_expediente, make_informe):
        async def _make(**overrides):
            exp = await make_expediente(abogado_responsable_id=7)
            datos = dict(profesional_asignado_id=self.TECNICO, fecha_aceptacion_informe=date(2024, 1, 15))
            datos.update(overrides)
            return await make_informe(exp.id, **datos)

        return _make

    @staticmethod
    async def _acoger_concepto(db_session, expediente_id):
        db_session.add(EtapaAcogerConcepto(expediente_id=expediente_id, tipo_acogida_concepto="OFICIO"))
        await db_session.flush()

    async def _put(self, client, informe_id, user, filas=None):
        return await client.put(
            f"/informes/{informe_id}/recursos",
            json={"filas": filas if filas is not None else matriz_completa()},
            headers=gateway_headers(user),
        )

    async def test_tecnico_edita_antes_de_concepto(self, client, informe_aceptado, solo_super_tiene_cargue, db_session):
        informe = await informe_aceptado()
        assert (await self._put(client, informe.id, self.TECNICO)).status_code == 200
        resp = await self._put(client, informe.id, self.TECNICO, matriz_completa(AGUA={"magnitud": "LEVE"}))
        assert resp.status_code == 200, resp.text
        agua = await db_session.scalar(select(InformeRecursoAfectado).where(
            InformeRecursoAfectado.informe_id == informe.id, InformeRecursoAfectado.recurso == "AGUA"))
        await db_session.refresh(agua)
        assert agua.magnitud == "LEVE"

    async def test_tecnico_no_edita_con_concepto(self, client, informe_aceptado, solo_super_tiene_cargue, db_session):
        informe = await informe_aceptado()
        await self._acoger_concepto(db_session, informe.expediente_id)
        resp = await self._put(client, informe.id, self.TECNICO)
        assert resp.status_code == 400
        assert "Acoger concepto" in resp.json()["detail"]

    async def test_otro_usuario_403(self, client, informe_aceptado, solo_super_tiene_cargue):
        informe = await informe_aceptado()
        assert (await self._put(client, informe.id, self.OTRO)).status_code == 403

    async def test_super_gestion_edita_manual_aun_con_concepto(
        self, client, informe_aceptado, solo_super_tiene_cargue, db_session,
    ):
        informe = await informe_aceptado(modo="MANUAL")
        await self._acoger_concepto(db_session, informe.expediente_id)
        assert (await self._put(client, informe.id, self.SUPER)).status_code == 200

    async def test_super_gestion_no_edita_flujo(self, client, informe_aceptado, solo_super_tiene_cargue):
        informe = await informe_aceptado(modo="FLUJO")
        assert (await self._put(client, informe.id, self.SUPER)).status_code == 403

    async def test_edicion_exige_matriz_completa(self, client, informe_aceptado, solo_super_tiene_cargue):
        informe = await informe_aceptado()
        assert (await self._put(client, informe.id, self.TECNICO, matriz_completa()[:3])).status_code == 400

    async def test_seguimiento_no_tiene_matriz(self, client, informe_aceptado, solo_super_tiene_cargue):
        informe = await informe_aceptado(tipo_informe="SEGUIMIENTO")
        assert (await self._put(client, informe.id, self.TECNICO)).status_code == 400

    async def test_mios_puede_editar_matriz(self, client, informe_aceptado, solo_super_tiene_cargue, db_session):
        informe = await informe_aceptado()

        async def _fila():
            resp = await client.get("/informes/mios", headers=gateway_headers(self.TECNICO))
            assert resp.status_code == 200, resp.text
            return next(f for f in resp.json()["data"] if f["id"] == informe.id)

        fila = await _fila()
        assert fila["puede_editar_matriz"] is True
        assert "puede_diligenciar_matriz" not in fila

        await self._acoger_concepto(db_session, informe.expediente_id)
        assert (await _fila())["puede_editar_matriz"] is False


class TestListadoFiltroFechas:
    """GET /informes (Asignar informes): el rango de fechas toma días completos."""

    async def test_fecha_hasta_incluye_todo_el_dia(self, client, make_expediente, make_informe):
        from datetime import datetime

        exp = await make_expediente()
        # Sin zona: Postgres las toma en la zona de la sesión, igual que los límites.
        ultimo_instante = await make_informe(exp.id, fecha_creacion=datetime(2026, 11, 20, 23, 59, 59, 500000))
        dia_siguiente = await make_informe(exp.id, fecha_creacion=datetime(2026, 11, 21, 0, 0, 1))
        dia_anterior = await make_informe(exp.id, fecha_creacion=datetime(2026, 11, 19, 23, 59, 59))

        resp = await client.get(
            "/informes?fecha_desde=2026-11-20&fecha_hasta=2026-11-20", headers=gateway_headers(1)
        )

        assert resp.status_code == 200, resp.text
        ids = {i["id"] for i in resp.json()["data"]}
        assert ultimo_instante.id in ids
        assert dia_siguiente.id not in ids
        assert dia_anterior.id not in ids


class TestFechaAsignacionYAdvertencia:
    """Asignar guarda fecha_asignacion la primera vez (reasignar no la cambia)
    y avisa, sin bloquear, si la visita queda a más de 30 días hábiles."""

    async def test_asignar_guarda_fecha_y_avisa_fuera_de_plazo(
        self, client, make_expediente, make_informe, db_session, monkeypatch
    ):
        from datetime import timedelta

        hoy = date(2026, 6, 10)
        monkeypatch.setattr(reports_mod, "hoy_bogota", lambda: hoy)
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id)

        lejos = date(2026, 9, 30)
        resp = await client.post(
            f"/informes/{informe.id}/asignar",
            json={"profesional_id": 10, "revisor_id": 20, "fecha_programacion_visita": lejos.isoformat()},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["advertencia"].startswith("Fecha fuera del plazo")
        await db_session.refresh(informe)
        assert informe.fecha_asignacion == hoy

        # Reasignar más tarde, con fecha dentro del plazo: no avisa ni mueve la fecha.
        monkeypatch.setattr(reports_mod, "hoy_bogota", lambda: hoy + timedelta(days=7))
        resp = await client.put(
            f"/informes/{informe.id}/asignar",
            json={"profesional_id": 11, "revisor_id": 20, "fecha_programacion_visita": "2026-06-25"},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["advertencia"] is None
        await db_session.refresh(informe)
        assert informe.fecha_asignacion == hoy

    async def test_sin_fecha_de_programacion_no_marca_asignacion(self, client, make_expediente, make_informe, db_session):
        exp = await make_expediente(abogado_responsable_id=7)
        informe = await make_informe(exp.id)
        resp = await client.post(
            f"/informes/{informe.id}/asignar",
            json={"profesional_id": 10, "revisor_id": 20},
            headers=gateway_headers(1),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["advertencia"] is None
        await db_session.refresh(informe)
        assert informe.fecha_asignacion is None

    async def test_listado_trae_el_limite_de_programacion(self, client, monkeypatch):
        from services.alertas import limite_programacion

        hoy = date(2026, 6, 10)
        monkeypatch.setattr(reports_mod, "hoy_bogota", lambda: hoy)
        resp = await client.get("/informes", headers=gateway_headers(1))
        assert resp.status_code == 200, resp.text
        assert resp.json()["fecha_limite_programacion"] == limite_programacion(hoy).isoformat()

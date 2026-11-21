"""
Acoger concepto · seguimiento (etapa 5): copia del acoger concepto de la visita
sobre la misma tabla (``etapa_acoger_concepto.instancia = 'SEGUIMIENTO'``).

- Se habilita con el informe técnico de SEGUIMIENTO aceptado.
- Las dos instancias no se mezclan (GET/POST propios; PUT, oficio y
  solicitud por id de etapa).
- El cierre, con concepto de la visita en AUTO_REQUERIMIENTO, espera a esta
  etapa: si es AUTO_REQUERIMIENTO, su acto con una notificación EXITOSA.
- Cascada: cambiar el modo del seguimiento o el tipo del concepto de la
  visita la borra; etapa actual, estados y alertas la reconocen.
- El acto de acoger concepto (ambas instancias) no admite comunicación.
"""
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import select

import routes.file_query as query_mod
from db.models.acto_administrativo import ActoAdministrativo
from db.models.etapa_acoger_concepto import INSTANCIA_SEGUIMIENTO, INSTANCIA_VISITA, EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.informe_tecnico import InformeTecnico
from db.models.notificacion import Notificacion
from db.models.oficio_remite import OficioRemite
from services.alertas import _Datos, _calcular
from services.cascada_etapas import eliminar_etapas_posteriores
from services.estado_expediente import _evaluar_uno
from tests.conftest import gateway_headers

ENCARGADO = 7


@pytest.fixture
def lectura(monkeypatch):
    import services.etapas as etapas_mod

    async def _verify(user_id, permission):
        return True

    monkeypatch.setattr(etapas_mod, "verify_permission", _verify)


@pytest.fixture
def escenario(db_session, make_expediente):
    """Expediente con visita aceptada, concepto de la visita y (opcional)
    informe de seguimiento aceptado y concepto · seguimiento."""

    async def _make(*, tipo_visita="AUTO_REQUERIMIENTO", seguimiento_aceptado=True, tipo_seguimiento=None):
        exp = await make_expediente(abogado_responsable_id=ENCARGADO)
        db_session.add(InformeTecnico(expediente_id=exp.id, tipo_informe="VISITA",
                                      fecha_aceptacion_informe=date(2024, 1, 15)))
        concepto = EtapaAcogerConcepto(expediente_id=exp.id, tipo_acogida_concepto=tipo_visita)
        db_session.add(concepto)
        db_session.add(InformeTecnico(
            expediente_id=exp.id, tipo_informe="SEGUIMIENTO",
            fecha_aceptacion_informe=date(2024, 3, 1) if seguimiento_aceptado else None,
        ))
        seguimiento = None
        if tipo_seguimiento:
            seguimiento = EtapaAcogerConcepto(expediente_id=exp.id, instancia=INSTANCIA_SEGUIMIENTO,
                                              tipo_acogida_concepto=tipo_seguimiento)
            db_session.add(seguimiento)
        await db_session.flush()
        return exp, concepto, seguimiento

    return _make


async def _acto(db_session, concepto, *, exitosa=None):
    acto = ActoAdministrativo(tipo_acto="AUTO", numerado=12, fecha_numerado=date(2024, 3, 5))
    db_session.add(acto)
    await db_session.flush()
    concepto.acto_administrativo_id = acto.id
    if exitosa is not None:
        db_session.add(Notificacion(acto_administrativo_id=acto.id, involucrado_id=1, notificacion_exitosa=exitosa))
    await db_session.flush()
    return acto


async def _cierre(client, expediente_id):
    return await client.get(f"/etapas/cierre/{expediente_id}", headers=gateway_headers(ENCARGADO))


class TestCrearYLeer:
    async def test_no_creable_sin_informe_de_seguimiento_aceptado(self, client, escenario, lectura):
        exp, _, _ = await escenario(seguimiento_aceptado=False)
        resp = await client.get(f"/etapas/concepto-seguimiento/{exp.id}", headers=gateway_headers(ENCARGADO))
        assert resp.status_code == 404
        assert resp.json()["creable"] is False and "SEGUIMIENTO" in resp.json()["creable_msg"]

        resp = await client.post(f"/etapas/concepto-seguimiento/{exp.id}", json={"tipo_acogida_concepto": "OFICIO"},
                                 headers=gateway_headers(ENCARGADO))
        assert resp.status_code == 400

    async def test_crear_no_toca_el_concepto_de_la_visita(self, client, escenario, lectura, db_session):
        exp, concepto, _ = await escenario()
        h = gateway_headers(ENCARGADO)
        assert (await client.get(f"/etapas/concepto-seguimiento/{exp.id}", headers=h)).json()["creable"] is True

        resp = await client.post(f"/etapas/concepto-seguimiento/{exp.id}",
                                 json={"tipo_acogida_concepto": "RESOLUCION_ARCHIVO"}, headers=h)
        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["instancia"] == INSTANCIA_SEGUIMIENTO and data["id"] != concepto.id

        # Una sola por expediente; el concepto de la visita sigue igual.
        resp = await client.post(f"/etapas/concepto-seguimiento/{exp.id}",
                                 json={"tipo_acogida_concepto": "OFICIO"}, headers=h)
        assert resp.status_code == 409
        visita = (await client.get(f"/etapas/concepto/{exp.id}", headers=h)).json()["data"]
        assert visita["id"] == concepto.id and visita["instancia"] == INSTANCIA_VISITA
        assert visita["tipo_acogida_concepto"] == "AUTO_REQUERIMIENTO"

    async def test_solicitud_de_informacion_por_id_de_etapa(self, client, escenario, stubs_clientes):
        exp, concepto, seguimiento = await escenario(tipo_seguimiento="OFICIO")
        resp = await client.post(
            f"/etapas/solicitud-informacion/{seguimiento.id}",
            json={"radicado": "2024EE0009", "fecha_radicado": "2024-03-02", "archivo_solicitud_id": 990},
            headers=gateway_headers(ENCARGADO),
        )
        assert resp.status_code == 201, resp.text


class TestCierre:
    async def test_espera_el_concepto_seguimiento(self, client, escenario, lectura):
        exp, _, _ = await escenario()
        body = (await _cierre(client, exp.id)).json()
        assert body["creable"] is False and "seguimiento" in body["creable_msg"]

    async def test_auto_requerimiento_exige_notificacion_exitosa(self, client, escenario, lectura, db_session):
        exp, _, seguimiento = await escenario(tipo_seguimiento="AUTO_REQUERIMIENTO")
        assert "acto" in (await _cierre(client, exp.id)).json()["creable_msg"]

        acto = await _acto(db_session, seguimiento, exitosa=False)
        body = (await _cierre(client, exp.id)).json()
        assert body["creable"] is False and "notificación exitosa" in body["creable_msg"]
        resp = await client.post(f"/etapas/cierre/{exp.id}", headers=gateway_headers(ENCARGADO))
        assert resp.status_code == 400

        db_session.add(Notificacion(acto_administrativo_id=acto.id, involucrado_id=2, notificacion_exitosa=True))
        await db_session.flush()
        assert (await _cierre(client, exp.id)).json()["creable"] is True
        resp = await client.post(f"/etapas/cierre/{exp.id}", headers=gateway_headers(ENCARGADO))
        assert resp.status_code == 201, resp.text

    async def test_resolucion_archivo_y_oficio_en_el_seguimiento(self, client, escenario, lectura, db_session):
        exp, _, _ = await escenario(tipo_seguimiento="RESOLUCION_ARCHIVO")
        assert (await _cierre(client, exp.id)).json()["creable"] is True

        exp, _, seguimiento = await escenario(tipo_seguimiento="OFICIO")
        assert "oficio" in (await _cierre(client, exp.id)).json()["creable_msg"]
        db_session.add(OficioRemite(etapa_acoger_concepto_id=seguimiento.id, radicado="2024EE0010",
                                    fecha_remitido="2024-03-03", archivo_remite_id=991))
        await db_session.flush()
        assert (await _cierre(client, exp.id)).json()["creable"] is True

    async def test_concepto_de_la_visita_terminal_no_cambia(self, client, escenario, lectura):
        exp, _, _ = await escenario(tipo_visita="RESOLUCION_ARCHIVO", seguimiento_aceptado=False)
        assert (await _cierre(client, exp.id)).json()["creable"] is True


class TestCascada:
    async def test_cambiar_modo_del_seguimiento_borra_concepto_seguimiento(self, escenario, db_session):
        exp, concepto, seguimiento = await escenario(tipo_seguimiento="AUTO_REQUERIMIENTO")
        await _acto(db_session, seguimiento, exitosa=True)
        db_session.add(EtapaCierre(expediente_id=exp.id))
        await db_session.flush()

        vista = await eliminar_etapas_posteriores(db_session, exp.id, "seguimiento", ejecutar=False)
        assert [e["codigo"] for e in vista.a_dict()["etapas"]] == ["concepto_seguimiento", "cierre"]
        etapa = vista.etapas["concepto_seguimiento"]
        assert etapa.conteos["actos"] == 1 and etapa.conteos["notificaciones"] == 1

        await eliminar_etapas_posteriores(db_session, exp.id, "seguimiento")
        restantes = (await db_session.execute(
            select(EtapaAcogerConcepto.id).where(EtapaAcogerConcepto.expediente_id == exp.id)
        )).scalars().all()
        assert restantes == [concepto.id]

    async def test_cambiar_tipo_del_concepto_de_la_visita_borra_el_seguimiento(
        self, client, escenario, db_session, stubs_clientes
    ):
        exp, concepto, seguimiento = await escenario(tipo_seguimiento="RESOLUCION_ARCHIVO")
        resp = await client.put(f"/etapas/concepto/{concepto.id}", json={"tipo_acogida_concepto": "OFICIO"},
                                headers=gateway_headers(ENCARGADO))
        assert resp.status_code == 200, resp.text
        assert resp.json()["concepto_seguimiento_eliminado"] is True
        assert await db_session.scalar(
            select(EtapaAcogerConcepto.id).where(EtapaAcogerConcepto.id == seguimiento.id)
        ) is None

    async def test_cambiar_tipo_del_seguimiento_no_toca_la_visita(self, client, escenario, db_session, stubs_clientes):
        exp, concepto, seguimiento = await escenario(tipo_seguimiento="RESOLUCION_ARCHIVO")
        resp = await client.put(f"/etapas/concepto/{seguimiento.id}", json={"tipo_acogida_concepto": "OFICIO"},
                                headers=gateway_headers(ENCARGADO))
        assert resp.status_code == 200, resp.text
        assert resp.json()["concepto_seguimiento_eliminado"] is False
        assert resp.json()["data"]["instancia"] == INSTANCIA_SEGUIMIENTO


class TestEtapaActual:
    async def test_concepto_seguimiento_va_entre_seguimiento_y_cierre(
        self, client, escenario, db_session, monkeypatch
    ):
        async def _verify(user_id, permission):
            return True

        monkeypatch.setattr(query_mod, "verify_permission", _verify)
        exp, _, _ = await escenario(tipo_seguimiento="OFICIO")
        body = (await client.get(f"/expedientes/completo/{exp.id}", headers=gateway_headers(ENCARGADO))).json()
        assert body["data"]["etapa_actual"] == "concepto_seguimiento"
        assert body["etapas_existentes"] == [2, 3, 4, 5]

        db_session.add(EtapaCierre(expediente_id=exp.id))
        await db_session.flush()
        body = (await client.get(f"/expedientes/completo/{exp.id}", headers=gateway_headers(ENCARGADO))).json()
        assert body["data"]["etapa_actual"] == "cierre" and body["etapas_existentes"][-1] == 6


class TestComunicacion:
    async def test_acto_de_concepto_no_admite_comunicacion(self, client, escenario, db_session):
        exp, _, seguimiento = await escenario(tipo_seguimiento="AUTO_REQUERIMIENTO")
        acto = await _acto(db_session, seguimiento)
        resp = await client.post(
            "/actos/comunicaciones",
            data={"expediente_id": exp.id, "acto_admin_id": acto.id, "numerado": 1,
                  "fecha_numerado": "2024-03-06", "fecha_envio": "2024-03-06", "documento_comunicacion_id": 992},
            headers=gateway_headers(ENCARGADO),
        )
        assert resp.status_code == 400
        assert "notifica" in resp.json()["detail"]


def _cs(**kw):
    base = dict(id=20, tipo_acogida_concepto="AUTO_REQUERIMIENTO", acto_administrativo_id=None)
    base.update(kw)
    return SimpleNamespace(**base)


class TestEstados:
    def _kw(self, **over):
        base = dict(
            archivado=False, cierre_acto_id=None,
            concepto=SimpleNamespace(id=1, tipo_acogida_concepto="AUTO_REQUERIMIENTO", acto_administrativo_id=9),
            visita=None,
            seguimiento=SimpleNamespace(fecha_programacion_visita=date(2024, 2, 1),
                                        fecha_aceptacion_informe=date(2024, 3, 1)),
            notificados_actos={9}, solicitud_concepto_ids=set(), tiene_involucrados=True,
        )
        base.update(over)
        return base

    def test_seguimiento_aceptado_sin_etapa_pide_acoger(self):
        assert _evaluar_uno(**self._kw()) == "ACOGER CONCEPTO SEGUIMIENTO"

    def test_seguimiento_sin_aceptar_sigue_programado(self):
        seg = SimpleNamespace(fecha_programacion_visita=date(2024, 2, 1), fecha_aceptacion_informe=None)
        assert _evaluar_uno(**self._kw(seguimiento=seg)) == "SEGUIMIENTO PROGRAMADO"

    def test_acto_sin_notificar(self):
        kw = self._kw(concepto_seguimiento=_cs(acto_administrativo_id=30))
        assert _evaluar_uno(**kw) == "NOTIFICAR ACTO ADM. CONCEPTO SEGUIMIENTO"

    def test_auto_sin_acto_sigue_en_la_etapa(self):
        assert _evaluar_uno(**self._kw(concepto_seguimiento=_cs())) == "ACOGER CONCEPTO SEGUIMIENTO"

    def test_solicitud_sin_involucrados(self):
        kw = self._kw(concepto_seguimiento=_cs(tipo_acogida_concepto="OFICIO"), solicitud_concepto_ids={20},
                      tiene_involucrados=False)
        assert _evaluar_uno(**kw) == "POR ALLEGAR INFORMACIÓN"

    def test_notificado_queda_para_cierre(self):
        kw = self._kw(concepto_seguimiento=_cs(acto_administrativo_id=30), notificados_actos={9, 30})
        assert _evaluar_uno(**kw) == "PARA CIERRE"

    def test_con_cierre_no_pide_cierre(self):
        kw = self._kw(concepto_seguimiento=_cs(tipo_acogida_concepto="RESOLUCION_ARCHIVO"), tiene_cierre=True)
        assert _evaluar_uno(**kw) == "SEGUIMIENTO PROGRAMADO"


class TestAlertas:
    def test_alertas_con_prefijo_propio(self):
        hoy = date(2026, 3, 10)
        visita = SimpleNamespace(id=1, tipo_acogida_concepto="AUTO_REQUERIMIENTO", acto_administrativo_id=9,
                                 fecha_termino_calculada=date(2026, 2, 1), dias_termino=10)
        seg = SimpleNamespace(id=2, tipo_acogida_concepto="AUTO_REQUERIMIENTO", acto_administrativo_id=30,
                              fecha_termino_calculada=date(2026, 4, 1), dias_termino=15)
        notif = SimpleNamespace(id=5, fecha_constancia_citacion=date(2026, 3, 2))
        datos = _Datos(fecha_creacion=date(2026, 1, 1), tiene_respuesta=True, concepto=visita,
                       concepto_seguimiento=seg, notifs_seguimiento=[notif])
        alertas = _calcular(datos, hoy)
        # Término de la visita vencido sin informe de seguimiento: toca asignarlo.
        assert set(alertas) == {"concepto_termino", "seguimiento_asignar", "concepto_seguimiento_termino",
                                "concepto_seguimiento_constancia_5"}
        assert alertas["concepto_seguimiento_termino"]["etapa"] == "Concepto seguimiento"
        assert "comunicación" not in alertas["concepto_seguimiento_constancia_5"]["accion_requerida"]

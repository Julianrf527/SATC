"""Cambio de modo de un informe técnico con borrado en cascada de las etapas
posteriores (services/cascada_etapas.py), su vista previa
(GET /informes/{id}/cambiar-modo/impacto) y el cambio de tipo de concepto
(routes/stage_concepto.py), que reutiliza las mismas funciones."""
from datetime import date

import pytest
from sqlalchemy import func, select

import routes.reports as reports_mod
import routes.stage_concepto as concepto_mod
import services.cascada_etapas as cascada_mod
from db.models.acto_administrativo import ActoAdministrativo
from db.models.auditoria import Auditoria
from db.models.comunicacion import Comunicacion
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.informe_proceso import (
    InformeProceso,
    InformeProcesoAuditoria,
    InformeProcesoRevision,
    InformeProcesoRevisor,
    InformeProcesoVersion,
)
from db.models.informe_recurso_afectado import InformeRecursoAfectado
from db.models.informe_tecnico import InformeTecnico
from db.models.notificacion import Notificacion
from db.models.oficio_remite import OficioRemite
from db.models.solicitud_informacion import SolicitudInformacion
from tests.conftest import gateway_headers

ABOGADO = 7

# Archivos (ids ficticios de app-docs)
DOC_VISITA = 501
DOC_ACTO_CONCEPTO, DOC_CITACION, DOC_NOTIFICACION, DOC_COMUNICACION = 601, 602, 603, 604
DOC_OFICIO, DOC_SOLICITUD = 605, 606
DOC_SEGUIMIENTO_V1, DOC_SEGUIMIENTO_V2, DOC_ADJUNTO = 701, 702, 703  # el informe aceptado usa la v1
DOC_ACTO_CIERRE, DOC_CITACION_CIERRE, DOC_COMUNICACION_CIERRE = 801, 802, 803

TODAS = [
    ActoAdministrativo, Notificacion, Comunicacion, EtapaAcogerConcepto, OficioRemite, SolicitudInformacion,
    EtapaCierre, InformeTecnico, InformeProceso, InformeProcesoVersion, InformeProcesoRevision,
    InformeProcesoAuditoria, InformeProcesoRevisor, InformeRecursoAfectado,
]


class Registro:
    """Sustituye decrement/increment_file_usage y guarda cada llamada."""

    def __init__(self, fallar_en: int | None = None):
        self.decrementos: list[list[int]] = []
        self.incrementos: list[list[int]] = []
        self.fallar_en = fallar_en

    async def decrementar(self, ids):
        self.decrementos.append(list(ids))
        if self.fallar_en is not None and len(self.decrementos) == self.fallar_en:
            return {"ok": False, "message": "app-docs caído"}
        return {"ok": True}

    async def incrementar(self, ids):
        self.incrementos.append(list(ids))
        return {"ok": True}


@pytest.fixture
def registro(monkeypatch, stubs_clientes):
    async def _permitido(user_id, permission):
        return True

    reg = Registro()
    monkeypatch.setattr(reports_mod, "verify_permission", _permitido)
    monkeypatch.setattr(reports_mod, "decrement_file_usage", reg.decrementar)
    monkeypatch.setattr(reports_mod, "increment_file_usage", reg.incrementar)
    monkeypatch.setattr(concepto_mod, "decrement_file_usage", reg.decrementar)
    return reg


async def _contar(db, modelo, *condiciones) -> int:
    return await db.scalar(select(func.count()).select_from(modelo).where(*condiciones))


async def _conteos(db) -> dict[str, int]:
    return {m.__tablename__: await _contar(db, m) for m in TODAS}


async def _acto(db, doc, *, citacion=None, notificacion=None, comunicacion=None, involucrado=1) -> ActoAdministrativo:
    acto = ActoAdministrativo(tipo_acto="AUTO", numerado=1, documento_acto_administrativo_id=doc)
    db.add(acto)
    await db.flush()
    if citacion or notificacion:
        db.add(Notificacion(
            acto_administrativo_id=acto.id, involucrado_id=involucrado,
            documento_citacion_id=citacion, documento_notificacion_id=notificacion,
        ))
    if comunicacion:
        db.add(Comunicacion(acto_administrativo_id=acto.id, documento_comunicacion_id=comunicacion))
    await db.flush()
    return acto


async def _escenario(db, make_expediente, *, con_concepto=True, con_seguimiento=True, con_cierre=True):
    """Expediente con visita MANUAL aceptada y, opcionalmente, concepto
    completo, seguimiento por FLUJO aceptado (2 versiones + adjunto) y cierre."""
    exp = await make_expediente(abogado_responsable_id=ABOGADO)
    visita = InformeTecnico(
        expediente_id=exp.id, tipo_informe="VISITA", modo="MANUAL", documento_informe_id=DOC_VISITA,
        fecha_recibido_informe=date(2024, 1, 1), fecha_aceptacion_informe=date(2024, 1, 2),
    )
    db.add(visita)
    await db.flush()
    db.add(InformeRecursoAfectado(informe_id=visita.id, recurso="AGUA", no_existe=True))
    out = {"exp": exp, "visita": visita}

    if con_concepto:
        acto = await _acto(db, DOC_ACTO_CONCEPTO, citacion=DOC_CITACION, notificacion=DOC_NOTIFICACION,
                           comunicacion=DOC_COMUNICACION)
        concepto = EtapaAcogerConcepto(expediente_id=exp.id, tipo_acogida_concepto="OFICIO",
                                       acto_administrativo_id=acto.id)
        db.add(concepto)
        await db.flush()
        db.add(OficioRemite(etapa_acoger_concepto_id=concepto.id, radicado="2024EE0001",
                            fecha_radicado="2024-01-03", fecha_remitido="2024-01-04", archivo_remite_id=DOC_OFICIO))
        db.add(SolicitudInformacion(etapa_acoger_concepto_id=concepto.id, radicado="2024EE0002",
                                    fecha_radicado="2024-01-05", archivo_solicitud_id=DOC_SOLICITUD))
        out["concepto"] = concepto

    if con_seguimiento:
        seg = InformeTecnico(
            expediente_id=exp.id, tipo_informe="SEGUIMIENTO", modo="FLUJO", documento_informe_id=DOC_SEGUIMIENTO_V1,
            profesional_asignado_id=10, revisor_asignado_id=20,
            fecha_recibido_informe=date(2024, 2, 1), fecha_aceptacion_informe=date(2024, 2, 2),
        )
        db.add(seg)
        await db.flush()
        proceso = InformeProceso(informe_id=seg.id, nombre="Seguimiento", estado="aprobado", creador_id=10,
                                 version_actual=2, activo=True, asignador_id=1)
        db.add(proceso)
        await db.flush()
        # v2 (Word) devuelta con adjunto; la v1 (PDF) quedó aprobada: no importa el orden aquí.
        db.add_all([
            InformeProcesoVersion(proceso_id=proceso.id, numero_version=1, file_id=DOC_SEGUIMIENTO_V2,
                                  archivo_url="/f/702", archivo_nombre="borrador.docx", usuario_subida_id=10),
            InformeProcesoVersion(proceso_id=proceso.id, numero_version=2, file_id=DOC_SEGUIMIENTO_V1,
                                  archivo_url="/f/701", archivo_nombre="final.pdf", usuario_subida_id=10),
            InformeProcesoRevision(proceso_id=proceso.id, version_revisada=1, revisor_id=20, accion="rechazado",
                                   adjunto_file_id=DOC_ADJUNTO),
            InformeProcesoRevision(proceso_id=proceso.id, version_revisada=2, revisor_id=20, accion="aprobado"),
            InformeProcesoAuditoria(proceso_id=proceso.id, accion="crear", usuario_id=1),
            InformeProcesoRevisor(proceso_id=proceso.id, revisor_id=20),
        ])
        out["seguimiento"] = seg

    if con_cierre:
        acto_c = await _acto(db, DOC_ACTO_CIERRE, citacion=DOC_CITACION_CIERRE, comunicacion=DOC_COMUNICACION_CIERRE)
        cierre = EtapaCierre(expediente_id=exp.id, acto_administrativo_id=acto_c.id)
        db.add(cierre)
        out["cierre"] = cierre

    await db.flush()
    # Commit real: el rollback del endpoint no debe deshacer el escenario.
    await db.commit()
    return out


async def _cambiar(client, informe_id, modo, user=1):
    return await client.put(f"/informes/{informe_id}/cambiar-modo", json={"modo": modo}, headers=gateway_headers(user))


async def _impacto(client, informe_id, user=1):
    return await client.get(f"/informes/{informe_id}/cambiar-modo/impacto", headers=gateway_headers(user))


class TestCambioEnVisita:
    async def test_borra_concepto_seguimiento_y_cierre_sin_huerfanos(self, client, db_session, make_expediente, registro):
        esc = await _escenario(db_session, make_expediente)
        visita = esc["visita"]

        resp = await _cambiar(client, visita.id, "FLUJO")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert [e["codigo"] for e in body["etapas_eliminadas"]] == ["concepto", "seguimiento", "cierre"]

        # Solo queda el informe de visita (ya en FLUJO y limpio); nada huérfano.
        conteos = await _conteos(db_session)
        assert conteos == {**{m.__tablename__: 0 for m in TODAS}, "informe_tecnico": 1}
        informe = await db_session.get(InformeTecnico, visita.id, populate_existing=True)
        assert informe.modo == "FLUJO"
        assert informe.documento_informe_id is None
        assert informe.fecha_aceptacion_informe is None

        # Un uso por registro: el archivo del seguimiento aceptado resta dos
        # (uso propio del informe + su versión); el resto, uno.
        assert registro.decrementos == [
            sorted([
                DOC_VISITA, DOC_ACTO_CONCEPTO, DOC_CITACION, DOC_NOTIFICACION, DOC_COMUNICACION, DOC_OFICIO,
                DOC_SOLICITUD, DOC_SEGUIMIENTO_V1, DOC_SEGUIMIENTO_V2, DOC_ADJUNTO, DOC_ACTO_CIERRE,
                DOC_CITACION_CIERRE, DOC_COMUNICACION_CIERRE,
            ]),
            [DOC_SEGUIMIENTO_V1],
        ]
        assert registro.incrementos == []

    async def test_registra_auditoria_con_lo_eliminado(self, client, db_session, make_expediente, registro):
        esc = await _escenario(db_session, make_expediente)
        resp = await _cambiar(client, esc["visita"].id, "FLUJO")
        assert resp.status_code == 200

        log = await db_session.scalar(select(Auditoria).where(Auditoria.tipo_evento == "CAMBIAR_MODO_INFORME"))
        assert log is not None
        assert log.expediente_id == esc["exp"].id
        assert "Acoger concepto" in log.detalle and "Cierre" in log.detalle
        etapas = {e["codigo"]: e for e in log.datos_anteriores["etapas_eliminadas"]}
        assert set(etapas) == {"concepto", "seguimiento", "cierre"}
        assert etapas["seguimiento"]["ids"]["informes"] == [esc["seguimiento"].id]
        assert etapas["concepto"]["ids"]["etapa"] == [esc["concepto"].id]
        assert log.datos_anteriores["informe"]["documento_informe_id"] == DOC_VISITA
        assert log.datos_anteriores["usos_restados"][str(DOC_SEGUIMIENTO_V1)] == 2

    async def test_flujo_a_manual_tambien_borra(self, client, db_session, make_expediente, registro):
        esc = await _escenario(db_session, make_expediente, con_seguimiento=False)
        visita = esc["visita"]
        visita.modo = "FLUJO"
        await db_session.commit()

        resp = await _cambiar(client, visita.id, "MANUAL")
        assert resp.status_code == 200
        assert [e["codigo"] for e in resp.json()["etapas_eliminadas"]] == ["concepto", "cierre"]
        assert await _contar(db_session, EtapaAcogerConcepto) == 0
        assert await _contar(db_session, EtapaCierre) == 0
        assert await _contar(db_session, ActoAdministrativo) == 0


class TestCambioEnSeguimiento:
    async def test_solo_borra_cierre(self, client, db_session, make_expediente, registro):
        esc = await _escenario(db_session, make_expediente)
        seg = esc["seguimiento"]

        resp = await _cambiar(client, seg.id, "MANUAL")
        assert resp.status_code == 200, resp.text
        assert [e["codigo"] for e in resp.json()["etapas_eliminadas"]] == ["cierre"]

        assert await _contar(db_session, EtapaCierre) == 0
        # El concepto queda intacto con todo lo suyo.
        assert await _contar(db_session, EtapaAcogerConcepto) == 1
        assert await _contar(db_session, ActoAdministrativo) == 1
        assert await _contar(db_session, Notificacion) == 1
        assert await _contar(db_session, Comunicacion) == 1
        assert await _contar(db_session, OficioRemite) == 1
        assert await _contar(db_session, SolicitudInformacion) == 1
        # El seguimiento sigue existiendo (solo cambió de modo); su proceso queda archivado.
        informe = await db_session.get(InformeTecnico, seg.id, populate_existing=True)
        assert informe.modo == "MANUAL" and informe.documento_informe_id is None
        proceso = await db_session.scalar(select(InformeProceso).where(InformeProceso.informe_id == seg.id))
        assert proceso is not None and proceso.activo is False
        assert await _contar(db_session, InformeProcesoVersion) == 2

        # Cierre (acto, citación, comunicación) + uso propio del informe de seguimiento.
        assert registro.decrementos == [
            sorted([DOC_SEGUIMIENTO_V1, DOC_ACTO_CIERRE, DOC_CITACION_CIERRE, DOC_COMUNICACION_CIERRE])
        ]


class TestSinEtapasPosteriores:
    async def test_igual_que_antes(self, client, db_session, make_expediente, registro):
        esc = await _escenario(db_session, make_expediente, con_concepto=False, con_seguimiento=False, con_cierre=False)
        visita = esc["visita"]

        impacto = await _impacto(client, visita.id)
        assert impacto.status_code == 200
        assert impacto.json()["etapas"] == []

        resp = await _cambiar(client, visita.id, "FLUJO")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Modo actualizado"
        assert resp.json()["etapas_eliminadas"] == []
        assert registro.decrementos == [[DOC_VISITA]]
        assert await _contar(db_session, InformeRecursoAfectado) == 0


class TestVistaPrevia:
    async def test_coincide_con_lo_borrado(self, client, db_session, make_expediente, registro):
        esc = await _escenario(db_session, make_expediente)

        impacto = await _impacto(client, esc["visita"].id)
        assert impacto.status_code == 200
        etapas = impacto.json()["etapas"]
        assert [e["codigo"] for e in etapas] == ["concepto", "seguimiento", "cierre"]
        assert [e["etiqueta"] for e in etapas] == ["Acoger concepto", "Visita de seguimiento", "Cierre"]
        por_codigo = {e["codigo"]: e for e in etapas}
        assert por_codigo["concepto"]["detalle"] == (
            "1 acto administrativo, 1 notificación, 1 comunicación, 1 oficio remite, 1 solicitud de información"
        )
        assert por_codigo["seguimiento"]["detalle"] == (
            "1 informe técnico, 1 proceso de revisión, 2 versiones, 2 revisiones"
        )
        # La vista previa no borra nada ni toca usos.
        assert await _contar(db_session, EtapaAcogerConcepto) == 1
        assert registro.decrementos == []

        resp = await _cambiar(client, esc["visita"].id, "FLUJO")
        assert resp.status_code == 200
        assert resp.json()["etapas_eliminadas"] == etapas

    async def test_desde_seguimiento_solo_cierre(self, client, db_session, make_expediente, registro):
        esc = await _escenario(db_session, make_expediente)
        resp = await _impacto(client, esc["seguimiento"].id)
        assert [e["codigo"] for e in resp.json()["etapas"]] == ["cierre"]
        assert resp.json()["etapas"][0]["detalle"] == "1 acto administrativo, 1 notificación, 1 comunicación"

    async def test_informe_inexistente_404(self, client, registro):
        resp = await _impacto(client, 9999)
        assert resp.status_code == 404


class TestRollback:
    async def test_fallo_a_mitad_de_la_cascada_no_borra_nada(self, client, db_session, make_expediente, registro, monkeypatch):
        esc = await _escenario(db_session, make_expediente)
        antes = await _conteos(db_session)

        # Se borra de atrás hacia adelante: cierre y seguimiento ya se
        # borraron (flush) cuando falla el concepto.
        async def _boom(*a, **k):
            raise RuntimeError("fallo simulado")

        visita_id = esc["visita"].id  # tras el rollback los objetos quedan expirados
        monkeypatch.setitem(cascada_mod._ELIMINADORES, "concepto", _boom)
        resp = await _cambiar(client, visita_id, "FLUJO")
        assert resp.status_code == 500

        assert await _conteos(db_session) == antes
        informe = await db_session.get(InformeTecnico, visita_id, populate_existing=True)
        assert informe.modo == "MANUAL" and informe.documento_informe_id == DOC_VISITA
        assert registro.decrementos == []
        assert await _contar(db_session, Auditoria) == 0

    async def test_fallo_al_restar_usos_revierte_y_devuelve_lo_restado(self, client, db_session, make_expediente, registro):
        esc = await _escenario(db_session, make_expediente)
        antes = await _conteos(db_session)
        registro.fallar_en = 2  # la segunda ronda (DOC_SEGUIMIENTO_V1 por segunda vez)

        resp = await _cambiar(client, esc["visita"].id, "FLUJO")
        assert resp.status_code == 502

        assert await _conteos(db_session) == antes
        assert await _contar(db_session, Auditoria) == 0
        # La primera ronda ya se había restado: se devuelve.
        assert registro.incrementos == [registro.decrementos[0]]


class TestPermisos:
    @pytest.fixture
    def sin_permiso(self, monkeypatch, registro):
        async def _denegado(user_id, permission):
            return False

        monkeypatch.setattr(reports_mod, "verify_permission", _denegado)

    async def test_cambiar_modo_403(self, client, db_session, make_expediente, sin_permiso, registro):
        esc = await _escenario(db_session, make_expediente)
        resp = await _cambiar(client, esc["visita"].id, "FLUJO")
        assert resp.status_code == 403
        assert await _contar(db_session, EtapaAcogerConcepto) == 1
        assert registro.decrementos == []

    async def test_impacto_403(self, client, db_session, make_expediente, sin_permiso):
        esc = await _escenario(db_session, make_expediente)
        resp = await _impacto(client, esc["visita"].id)
        assert resp.status_code == 403


@pytest.mark.usefixtures("permiso_consulta")
class TestCambioTipoConcepto:
    """stage_concepto usa las mismas funciones: borra acto (con notificaciones
    y comunicación), oficio y cierre; conserva la etapa y la solicitud."""

    async def test_cambio_de_tipo_borra_acto_oficio_y_cierre(self, client, db_session, make_expediente, registro):
        esc = await _escenario(db_session, make_expediente, con_seguimiento=False)
        concepto = esc["concepto"]

        resp = await client.put(
            f"/etapas/concepto/{concepto.id}",
            json={"tipo_acogida_concepto": "AUTO_REQUERIMIENTO", "dias_termino": 10},
            headers=gateway_headers(ABOGADO),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["cierre_eliminado"] is True
        assert body["data"]["tipo_acogida_concepto"] == "AUTO_REQUERIMIENTO"
        assert body["data"]["acto_admin"] is None
        assert body["data"]["oficio_remite"] is None
        assert body["data"]["solicitud_informacion"]["archivo_solicitud_id"] == DOC_SOLICITUD

        assert await _contar(db_session, EtapaAcogerConcepto) == 1
        assert await _contar(db_session, SolicitudInformacion) == 1
        assert await _contar(db_session, EtapaCierre) == 0
        assert await _contar(db_session, ActoAdministrativo) == 0
        assert await _contar(db_session, Notificacion) == 0
        assert await _contar(db_session, Comunicacion) == 0
        assert await _contar(db_session, OficioRemite) == 0
        assert registro.decrementos == [sorted([
            DOC_ACTO_CONCEPTO, DOC_CITACION, DOC_NOTIFICACION, DOC_COMUNICACION, DOC_OFICIO,
            DOC_ACTO_CIERRE, DOC_CITACION_CIERRE, DOC_COMUNICACION_CIERRE,
        ])]

    async def test_mismo_tipo_no_borra_nada(self, client, db_session, make_expediente, registro):
        esc = await _escenario(db_session, make_expediente, con_seguimiento=False)
        resp = await client.put(
            f"/etapas/concepto/{esc['concepto'].id}",
            json={"tipo_acogida_concepto": "OFICIO"},
            headers=gateway_headers(ABOGADO),
        )
        assert resp.status_code == 200
        assert resp.json()["cierre_eliminado"] is False
        assert await _contar(db_session, EtapaCierre) == 1
        assert await _contar(db_session, ActoAdministrativo) == 2
        assert registro.decrementos == []

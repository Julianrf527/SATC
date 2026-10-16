"""Tests de caracterización de la pestaña Alertas (sancionatorio).

Fijan la salida EXACTA (valores y orden de claves) de los endpoints de alertas
y del reporte semanal para escenarios que recorren las 7 alertas de
services/alertas.py con distintas fechas y semáforos. El snapshot
(tests/snapshots/alertas_sancionatorio.json) se generó con la implementación
previa a la optimización (>13 consultas por expediente y una llamada a
app-involved por expediente); la versión en bloque debe reproducirlo idéntico.
Regenerar SOLO si cambia una regla de negocio:

    SNAPSHOT_UPDATE=1 python -m pytest tests/test_alertas_caracterizacion.py
"""
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import holidays
import pytest

from conftest import gateway_headers
from db.models.documento_anexo import DocumentoAnexo
from db.models.etapa_apertura_probatoria import EtapaAperturaProbatoria
from db.models.etapa_cesacion import EtapaCesacion
from db.models.etapa_cierre_probatoria import EtapaCierreProbatoria
from db.models.etapa_decision_fondo import EtapaDecisionFondo
from db.models.etapa_formulacion_cargos import EtapaFormulacionCargos
from db.models.etapa_indagacion import EtapaIndagacion
from db.models.etapa_inicio_sancionatorio import EtapaInicioSancionatorio
from db.models.etapa_medida_preventiva import EtapaMedidaPreventiva
from db.models.etapa_probatoria_recurso import EtapaProbatoriaRecurso

SNAPSHOT = Path(__file__).parent / "snapshots" / "alertas_sancionatorio.json"
HOY = date(2026, 3, 16)
BOG = ZoneInfo("America/Bogota")


class _FechaFija(date):
    @classmethod
    def today(cls):
        return HOY


@pytest.fixture
def fecha_fija(monkeypatch):
    import routes.expediente_alertas as rutas
    import services.alertas_scheduler as sched

    monkeypatch.setattr(rutas, "date", _FechaFija)
    monkeypatch.setattr(sched, "date", _FechaFija)


class _InvolvedStub:
    """app-involved en memoria: el 99 no existe; registra cada llamada bulk."""

    def __init__(self):
        self.llamadas: list[list[int]] = []

    async def bulk(self, ids):
        self.llamadas.append(sorted(ids))
        return [{"id": i, "nombre": f"Nombre{i}", "apellido": f"Apellido{i}"} for i in ids if i != 99]


@pytest.fixture
def involved(monkeypatch):
    import services.involucrado as inv_mod

    stub = _InvolvedStub()
    monkeypatch.setattr(inv_mod, "involved_client", stub)
    return stub


def _ts(y, m, d, h=10, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=BOG)


async def _escenarios(db, make_expediente, make_acto_administrativo, make_notificacion):
    ids = []

    async def exp(encargado=5):
        e = await make_expediente(encargado_id=encargado, radicado=f"CAR-{len(ids) + 1:04d}")
        ids.append(e.id)
        return e

    async def acto(*notifs):
        """notifs: (exitosa, fecha_notificacion, fecha_constancia, involucrado_id)."""
        a = await make_acto_administrativo()
        for exitosa, fnot, fconst, inv in notifs:
            await make_notificacion(a.id, notificacion_exitosa=exitosa, fecha_notificacion=fnot,
                                    fecha_constancia_citacion=fconst, involucrado_id=inv)
        return a.id

    def doc(etapa_tipo, ref, nombre):
        db.add(DocumentoAnexo(etapa_tipo=etapa_tipo, etapa_ref_id=ref, nombre=nombre, documento_anexo_id=1))

    async def add(obj):
        db.add(obj)
        await db.flush()
        return obj

    # 1. Indagación sin inicio (amarillo, con hora que cambia de día en UTC), con inicio, vencida.
    e = await exp()
    await add(EtapaIndagacion(expediente_id=e.id, fecha_creacion=_ts(2025, 11, 1, 22)))
    e = await exp()
    await add(EtapaIndagacion(expediente_id=e.id, fecha_creacion=_ts(2025, 11, 1)))
    await add(EtapaInicioSancionatorio(expediente_id=e.id))
    e = await exp()
    await add(EtapaIndagacion(expediente_id=e.id, fecha_creacion=_ts(2025, 8, 1)))
    e = await exp()
    await add(EtapaIndagacion(expediente_id=e.id, fecha_creacion=_ts(2026, 3, 1)))

    # 2/3. Formulación notificada (min de fechas exitosas) con documento, sin decisión.
    e = await exp()
    a = await acto((True, date(2026, 2, 20), None, None), (True, date(2026, 2, 2), None, None),
                   (False, date(2026, 1, 2), None, None))
    await add(EtapaFormulacionCargos(expediente_id=e.id, acto_administrativo_id=a, documento_id=7))
    # Formulación notificada + decisión con acto (sin alerta2) sin documento; decisión sin recurso → alerta6.
    e = await exp()
    a = await acto((True, date(2025, 12, 10), None, None))
    await add(EtapaFormulacionCargos(expediente_id=e.id, acto_administrativo_id=a))
    a = await acto((True, date(2026, 3, 5), None, None), (True, None, None, None))
    await add(EtapaDecisionFondo(expediente_id=e.id, acto_administrativo_id=a))
    # Formulación sin éxito / éxito sin fecha / sin acto.
    e = await exp()
    a = await acto((False, date(2026, 2, 2), None, None), (None, date(2026, 2, 2), None, None))
    await add(EtapaFormulacionCargos(expediente_id=e.id, acto_administrativo_id=a, documento_id=1))
    e = await exp()
    a = await acto((True, None, None, None))
    await add(EtapaFormulacionCargos(expediente_id=e.id, acto_administrativo_id=a, documento_id=1))
    e = await exp()
    await add(EtapaFormulacionCargos(expediente_id=e.id, documento_id=1))
    # Formulación notificada y decisión SIN acto → alerta2 sigue.
    e = await exp(encargado=9)
    a = await acto((True, date(2025, 10, 1), None, None))
    await add(EtapaFormulacionCargos(expediente_id=e.id, acto_administrativo_id=a, documento_id=3))
    await add(EtapaDecisionFondo(expediente_id=e.id))

    # 4. Apertura probatoria: sin informe (con un anexo de otro nombre), con informe.
    e = await exp()
    a = await acto((True, date(2026, 1, 20), None, None))
    ap = await add(EtapaAperturaProbatoria(expediente_id=e.id, acto_administrativo_id=a))
    doc("etapa_apertura_probatoria", ap.id, "Otro anexo")
    doc("etapa_cierre_probatoria", ap.id, "Informe Tecnico")
    e = await exp()
    a = await acto((True, date(2026, 1, 20), None, None))
    ap = await add(EtapaAperturaProbatoria(expediente_id=e.id, acto_administrativo_id=a))
    doc("etapa_apertura_probatoria", ap.id, "Informe Tecnico")

    # 5. Cierre probatoria: sin alegato / con alegato.
    e = await exp()
    a = await acto((True, date(2026, 3, 10), None, None))
    ci = await add(EtapaCierreProbatoria(expediente_id=e.id, acto_administrativo_id=a))
    e = await exp()
    a = await acto((True, date(2026, 3, 10), None, None))
    ci = await add(EtapaCierreProbatoria(expediente_id=e.id, acto_administrativo_id=a))
    doc("etapa_cierre_probatoria", ci.id, "Alegato de conclusion")

    # 6. Decisión con recurso presentado: probatoria con decisión no notificada,
    #    probatoria sin acto de decisión, sin probatoria con acto_recurso
    #    no notificado / notificado / sin acto_recurso.
    async def decision_con_recurso(fecha, acto_recurso=None):
        e = await exp()
        a = await acto((True, fecha, None, None))
        d = await add(EtapaDecisionFondo(expediente_id=e.id, acto_administrativo_id=a, acto_recurso_id=acto_recurso))
        doc("etapa_decision_fondo", d.id, "Recurso")
        return e

    e = await decision_con_recurso(date(2025, 6, 1))
    dec = await acto((False, date(2025, 7, 1), None, None))
    await add(EtapaProbatoriaRecurso(expediente_id=e.id, acto_decision_id=dec))
    e = await decision_con_recurso(date(2024, 12, 1))
    await add(EtapaProbatoriaRecurso(expediente_id=e.id))
    e = await decision_con_recurso(date(2026, 2, 1))
    dec = await acto((True, date(2026, 2, 15), None, None))
    await add(EtapaProbatoriaRecurso(expediente_id=e.id, acto_decision_id=dec))
    await decision_con_recurso(date(2025, 9, 1), acto_recurso=await acto((None, None, None, None)))
    await decision_con_recurso(date(2025, 9, 1), acto_recurso=await acto((True, date(2025, 10, 1), None, None)))
    await decision_con_recurso(date(2025, 9, 1))

    # 7. Constancias de citación pendientes en varias etapas (y una etapa
    #    excluida: cesación). Indagación e inicio comparten acto (gana la última etiqueta).
    e = await exp()
    # La consulta previa no tenía ORDER BY: el número de alerta_constancia_N
    # dependía del plan (orden físico o del índice (acto, exitosa), con False
    # antes que NULL). Aquí el orden por id coincide con ambos planes; la
    # versión en bloque fija el orden por id.
    a = await acto((False, None, date(2026, 3, 10), 10), (True, None, date(2026, 3, 1), 12),
                   (False, None, None, 13), (False, None, date(2026, 2, 1), None),
                   (False, None, date(2026, 2, 20), 99), (None, None, date(2026, 1, 20), 11))
    await add(EtapaMedidaPreventiva(expediente_id=e.id, acto_administrativo_id=a))
    compartido = await acto((False, None, date(2026, 3, 15), 10))
    await add(EtapaIndagacion(expediente_id=e.id, acto_administrativo_id=compartido, fecha_creacion=_ts(2026, 3, 14)))
    await add(EtapaInicioSancionatorio(expediente_id=e.id, acto_administrativo_id=compartido))
    a = await acto((False, None, date(2026, 3, 1), 14))
    await add(EtapaCesacion(expediente_id=e.id, acto_administrativo_id=a))
    e = await exp(encargado=9)
    a = await acto((False, None, date(2025, 12, 1), 15), (True, date(2026, 1, 10), date(2025, 12, 1), 15))
    await add(EtapaCierreProbatoria(expediente_id=e.id, acto_administrativo_id=a))

    # Expediente sin etapas.
    await exp()

    await db.commit()
    db.expunge_all()  # como en producción: sesión sin objetos en memoria
    return ids


async def test_salida_identica_al_snapshot(api, db_session, make_expediente, make_acto_administrativo,
                                           make_notificacion, fecha_fija, involved):
    from services.alertas_scheduler import obtener_alertas_usuario

    ids = await _escenarios(db_session, make_expediente, make_acto_administrativo, make_notificacion)
    salida = {}
    llamadas_por_alcance = []
    for alcance in ("todos", "mios"):
        involved.llamadas.clear()
        resp = await api.get(f"/expediente/alerts/all?alcance={alcance}", headers=gateway_headers(5))
        assert resp.status_code == 200, resp.text
        salida[f"todas_{alcance}"] = resp.json()
        llamadas_por_alcance.append(len(involved.llamadas))
    for user in (9, 50):
        salida[f"todas_mios_{user}"] = (await api.get("/expediente/alerts/all", headers=gateway_headers(user))).json()
    for i in ids:
        resp = await api.get(f"/expediente/alerts/{i}", headers=gateway_headers(5))
        assert resp.status_code == 200, resp.text
        salida[f"expediente_{i}"] = resp.json()
    for user in (5, 9):
        salida[f"reporte_semanal_{user}"] = await obtener_alertas_usuario(user, db_session)

    actual = json.dumps(salida, ensure_ascii=False, indent=1)
    if os.getenv("SNAPSHOT_UPDATE"):
        SNAPSHOT.parent.mkdir(exist_ok=True)
        SNAPSHOT.write_text(actual, encoding="utf-8")
    assert actual == SNAPSHOT.read_text(encoding="utf-8")
    # Nombres de involucrados de todos los expedientes: UNA llamada bulk.
    assert llamadas_por_alcance == [1, 1]


async def test_app_involved_falla_nombres_vacios(api, db_session, make_expediente, make_acto_administrativo,
                                                 make_notificacion, fecha_fija, monkeypatch):
    """Si app-involved falla, las alertas salen igual con involucrado_nombre vacío."""
    import services.involucrado as inv_mod

    class _Caido:
        async def bulk(self, ids):
            raise RuntimeError("caído")

    monkeypatch.setattr(inv_mod, "involved_client", _Caido())
    e = await make_expediente(encargado_id=5)
    a = await make_acto_administrativo()
    await make_notificacion(a.id, notificacion_exitosa=False, fecha_constancia_citacion=date(2026, 3, 1),
                            involucrado_id=10)
    db_session.add(EtapaMedidaPreventiva(expediente_id=e.id, acto_administrativo_id=a.id))
    await db_session.commit()
    data = (await api.get("/expediente/alerts/all", headers=gateway_headers(5))).json()
    alerta = data["alertas"][e.radicado]["alerta_constancia_1"]
    assert alerta["involucrado_nombre"] == ""
    assert alerta["etapa"] == "DETALLE MEDIDA PREVENTIVA"


# ── Días laborales: idéntico a la implementación previa ──────────────────────

def _dias_laborales_previa(fecha_inicio: date, fecha_fin: date) -> int:
    if fecha_inicio >= fecha_fin:
        return 0
    co = holidays.Colombia(years=range(fecha_inicio.year, fecha_fin.year + 1))
    n, f = 0, fecha_inicio + timedelta(days=1)
    while f <= fecha_fin:
        if f.weekday() < 5 and f not in co:
            n += 1
        f += timedelta(days=1)
    return n


def _fecha_despues_previa(fecha_inicio: date, dias: int) -> date:
    co = holidays.Colombia(years=range(fecha_inicio.year, fecha_inicio.year + 1))
    f, n = fecha_inicio, 0
    while n < dias:
        f += timedelta(days=1)
        if f.weekday() < 5 and f not in co:
            n += 1
    return f


def test_dias_laborales_igual_a_la_version_previa():
    from utils.functions import calcular_dias_laborales, obtener_fecha_despues_dias_laborales

    inicio = date(2018, 1, 1)
    for d in range(0, 365 * 12, 5):
        f = inicio + timedelta(days=d)
        for dias in (10, 30, 80):
            assert obtener_fecha_despues_dias_laborales(f, dias) == _fecha_despues_previa(f, dias), (f, dias)
        for delta in (-3, 0, 1, 40, 400):
            fin = f + timedelta(days=delta)
            assert calcular_dias_laborales(f, fin) == _dias_laborales_previa(f, fin), (f, fin)

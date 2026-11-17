"""Tests de caracterización de la pestaña Alertas (infracciones).

Fijan la salida EXACTA (valores y orden de claves) de los endpoints de alertas
y del reporte semanal para un conjunto de escenarios con distintas etapas,
fechas y semáforos. El snapshot (tests/snapshots/alertas_infraccion.json) se
generó con la implementación previa a la optimización (una consulta por
expediente); la versión optimizada (consultas IN en bloque) debe reproducirlo
idéntico. Regenerar SOLO si cambia una regla de negocio:

    SNAPSHOT_UPDATE=1 python -m pytest tests/test_alertas_caracterizacion.py
"""
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import holidays
import pytest

from tests.conftest import gateway_headers
from db.models.acto_administrativo import ActoAdministrativo
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.notificacion import Notificacion

SNAPSHOT = Path(__file__).parent / "snapshots" / "alertas_infraccion.json"
HOY = date(2026, 3, 16)  # lunes; el 23-mar-2026 es festivo (San José)
BOG = ZoneInfo("America/Bogota")


class _FechaFija(date):
    @classmethod
    def today(cls):
        return HOY


@pytest.fixture
def fecha_fija(monkeypatch):
    import routes.file_alerts as rutas
    import services.alertas_scheduler as sched

    monkeypatch.setattr(rutas, "date", _FechaFija)
    monkeypatch.setattr(sched, "date", _FechaFija)


@pytest.fixture
def todos_los_permisos(monkeypatch):
    import services.etapas as etapas_mod

    async def _verify(user_id, permission):
        return True

    monkeypatch.setattr(etapas_mod, "verify_permission", _verify)


def _ts(y, m, d, h=10, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=BOG)


async def _escenarios(db, make_expediente):
    """Expedientes con todas las ramas del cálculo. Devuelve sus ids."""
    ids = []

    async def exp(abogado=7, creado=None, respuesta=False):
        e = await make_expediente(abogado_responsable_id=abogado, fecha_creacion=creado or _ts(2026, 3, 13),
                                  radicado=f"CAR-{len(ids) + 1:04d}")
        if respuesta:
            db.add(EtapaRespuesta(expediente_id=e.id, fecha_radicado=date(2026, 1, 5), fecha_creacion=date(2026, 1, 5)))
        ids.append(e.id)
        return e

    async def concepto(e, tipo, acto=True, dias=None, fecha_termino=None):
        acto_id = None
        if acto:
            a = ActoAdministrativo(tipo_acto="auto")
            db.add(a)
            await db.flush()
            acto_id = a.id
        db.add(EtapaAcogerConcepto(expediente_id=e.id, tipo_acogida_concepto=tipo, acto_administrativo_id=acto_id,
                                   dias_termino=dias, fecha_termino_calculada=fecha_termino))
        await db.flush()
        return acto_id

    def notif(acto_id, constancia, exitosa, inv=1):
        db.add(Notificacion(acto_administrativo_id=acto_id, involucrado_id=inv,
                            fecha_constancia_citacion=constancia, notificacion_exitosa=exitosa))

    # Sin respuesta: verde / amarillo-rojo / vencido / cruce de año con festivos.
    await exp(creado=_ts(2026, 3, 13))
    await exp(creado=_ts(2026, 3, 2, 21, 30))  # 02:30 UTC del día siguiente
    await exp(creado=_ts(2026, 2, 20))
    await exp(creado=_ts(2025, 12, 22))
    await exp(creado=_ts(2026, 3, 4))
    # Concepto AUTO_REQUERIMIENTO con notificaciones de todo tipo + término.
    e = await exp(respuesta=True)
    acto = await concepto(e, "AUTO_REQUERIMIENTO", dias=10, fecha_termino=date(2026, 3, 25))
    notif(acto, date(2026, 3, 5), False)
    notif(acto, date(2026, 2, 10), False, inv=2)
    notif(acto, date(2026, 3, 1), None)
    notif(acto, date(2026, 3, 1), True)
    notif(acto, None, False)
    notif(acto, date(2026, 2, 27), False, inv=3)
    # Otro tipo de acogida: solo el término (rojo).
    e = await exp(respuesta=True)
    acto = await concepto(e, "ACOGER", dias=30, fecha_termino=date(2026, 3, 17))
    notif(acto, date(2026, 3, 5), False)
    # Respuesta sin concepto: sin alertas.
    await exp(respuesta=True)
    # Otro abogado, sin respuesta.
    await exp(abogado=8, creado=_ts(2026, 3, 9))
    # Sin abogado, con respuesta; AUTO_REQUERIMIENTO sin acto, término vencido.
    e = await exp(abogado=None, respuesta=True)
    await concepto(e, "AUTO_REQUERIMIENTO", acto=False, dias=5, fecha_termino=date(2026, 3, 10))
    # AUTO_REQUERIMIENTO con constancia y sin término; dias_termino=0 no alerta.
    e = await exp(abogado=8, respuesta=True)
    acto = await concepto(e, "AUTO_REQUERIMIENTO", dias=0, fecha_termino=date(2026, 3, 30))
    notif(acto, date(2026, 3, 12), False)
    # Sin respuesta + concepto (ambas ramas en un mismo expediente).
    e = await exp(creado=_ts(2026, 2, 27, 23, 59))
    acto = await concepto(e, "AUTO_REQUERIMIENTO", dias=15, fecha_termino=date(2026, 4, 8))
    notif(acto, date(2025, 12, 30), False)

    await db.commit()
    db.expunge_all()  # como en producción: sesión sin objetos en memoria
    return ids


async def _salida_completa(client, db_session, ids):
    from services.alertas_scheduler import obtener_alertas_usuario

    salida = {}
    for alcance in ("todos", "mios"):
        resp = await client.get(f"/expedientes/alertas/todas?alcance={alcance}", headers=gateway_headers(7))
        assert resp.status_code == 200, resp.text
        salida[f"todas_{alcance}"] = resp.json()
    for user in (8, 50):
        resp = await client.get("/expedientes/alertas/todas", headers=gateway_headers(user))
        salida[f"todas_mios_{user}"] = resp.json()
    for i in ids:
        resp = await client.get(f"/expedientes/alertas/{i}", headers=gateway_headers(7))
        assert resp.status_code == 200, resp.text
        salida[f"expediente_{i}"] = resp.json()
    for user in (7, 8):
        salida[f"reporte_semanal_{user}"] = await obtener_alertas_usuario(user, db_session)
    return salida


async def test_salida_identica_al_snapshot(client, db_session, make_expediente, fecha_fija, todos_los_permisos):
    ids = await _escenarios(db_session, make_expediente)
    salida = await _salida_completa(client, db_session, ids)
    # json.dumps sin sort_keys: compara también el orden de las claves.
    actual = json.dumps(salida, ensure_ascii=False, indent=1)
    if os.getenv("SNAPSHOT_UPDATE"):
        SNAPSHOT.parent.mkdir(exist_ok=True)
        SNAPSHOT.write_text(actual, encoding="utf-8")
    assert actual == SNAPSHOT.read_text(encoding="utf-8")


# ── Días hábiles: idéntico a la implementación previa ─────────────────────────

def _fecha_limite_habiles_previa(fecha_inicio: date, dias_habiles: int) -> date:
    """Copia literal de la versión previa (un calendario por llamada)."""
    co_hol = holidays.Colombia(years=range(fecha_inicio.year, fecha_inicio.year + 2))
    count = 0
    current = fecha_inicio
    while count < dias_habiles:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in co_hol:
            count += 1
    return current


def test_dias_habiles_igual_a_la_version_previa():
    from services.alertas import fecha_limite_habiles as _fecha_limite_habiles

    inicio = date(2018, 1, 1)
    for d in range(0, 365 * 12, 3):
        f = inicio + timedelta(days=d)
        for dias in (1, 15, 30):
            assert _fecha_limite_habiles(f, dias) == _fecha_limite_habiles_previa(f, dias), (f, dias)

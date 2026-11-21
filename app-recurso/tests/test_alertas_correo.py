"""Correo semanal de alertas (services/alertas_correo.py)."""
import asyncio
import inspect
from datetime import date, datetime, timedelta

from sqlalchemy import delete

from core.permission import Permission
from db.models import EnvioAlertasSemanal
from services import alertas_correo as correo
from tests.conftest import TestSessionLocal
from tests.fixtures_etapas import *  # noqa: F401,F403

# Semanas lejanas para no chocar con envíos reales ni entre tests (la BD persiste).
LUNES = date(2099, 1, 5)


async def _limpiar(*semanas: date) -> None:
    async with TestSessionLocal() as db:
        await db.execute(delete(EnvioAlertasSemanal).where(EnvioAlertasSemanal.semana.in_(semanas)))
        await db.commit()


def test_job_registrado_es_corrutina():
    """Regresión: con una lambda que devuelve la corrutina, APScheduler nunca la ejecuta."""
    job = correo.crear_scheduler(TestSessionLocal).get_job(correo.JOB_ID)
    assert inspect.iscoroutinefunction(job.func)
    campos = {f.name: str(f) for f in job.trigger.fields}
    assert campos["day_of_week"] == "mon" and campos["hour"] == "8" and campos["minute"] == "0"
    assert str(job.trigger.timezone) == "America/Bogota"
    assert job.misfire_grace_time == 12 * 3600 and job.coalesce is True and job.max_instances == 1


async def test_el_scheduler_real_ejecuta_el_job(monkeypatch):
    llamado = asyncio.Event()

    async def falso(sesion, hoy=None):
        llamado.set()
        return True

    monkeypatch.setattr(correo, "ejecutar_envio_semanal", falso)
    scheduler = correo.crear_scheduler(TestSessionLocal)
    scheduler.start()
    try:
        scheduler.get_job(correo.JOB_ID).modify(next_run_time=datetime.now(scheduler.timezone))
        await asyncio.wait_for(llamado.wait(), timeout=5)
    finally:
        scheduler.shutdown(wait=False)


async def test_reclamo_por_semana():
    siguiente = LUNES + timedelta(days=7)
    await _limpiar(LUNES, siguiente)
    async with TestSessionLocal() as db:
        assert await correo.reclamar_envio(db, LUNES) is True
        assert await correo.reclamar_envio(db, LUNES) is False
        assert await correo.reclamar_envio(db, siguiente) is True
    assert correo.lunes_de(LUNES + timedelta(days=3)) == LUNES and correo.lunes_de(LUNES) == LUNES


async def test_cuatro_workers_envian_una_sola_vez(client, stubs, rv_permisos, expediente):
    semana = LUNES + timedelta(days=14)
    await _limpiar(semana)
    await post(client, f"/etapas/{expediente.id}/admite/asignarme")  # alerta a cargo de ABOGADO

    resultados = await asyncio.gather(*(correo.ejecutar_envio_semanal(TestSessionLocal, semana) for _ in range(4)))
    assert sorted(resultados) == [False, False, False, True]

    al_abogado = [r for r in stubs.users.reportes_alertas if r["emails"] == [f"u{ABOGADO}@test.local"]]
    assert len(al_abogado) == 1
    datos = al_abogado[0]["datos"]
    assert expediente.radicado in datos["alertas"]
    assert set(datos["alertas"][expediente.radicado]) == {"admite_primera_version"}
    assert al_abogado[0]["title"] == correo.TITULO
    # Un reinicio dentro del margen no vuelve a enviar.
    assert await correo.ejecutar_envio_semanal(TestSessionLocal, semana) is False


async def test_en_revision_el_correo_va_al_rol_revisor(client, stubs, rv_permisos, expediente):
    semana = LUNES + timedelta(days=21)
    await _limpiar(semana)
    pid = (await post(client, f"/etapas/{expediente.id}/admite/asignarme")).json()["data"]["proceso_id"]
    await subir(client, pid)  # en revisión: le toca al líder jurídico

    assert await correo.ejecutar_envio_semanal(TestSessionLocal, semana) is True
    por_correo = {r["emails"][0]: r["datos"]["alertas"] for r in stubs.users.reportes_alertas}
    assert "admite_revision" in por_correo[f"u{JURIDICO}@test.local"].get(expediente.radicado, {})
    assert expediente.radicado not in por_correo.get(f"u{ABOGADO}@test.local", {})
    assert expediente.radicado not in por_correo.get(f"u{PROYECTO}@test.local", {})


def test_reporte_de_filtra_por_responsable_y_no_modifica_las_alertas():
    rol = {"permiso": Permission.LIDER_TECNICO, "etiqueta": "Líder técnico"}
    semaforo = {"estado": "rojo"}
    por_radicado = {
        "R1": {"a": {"encargado_id": 7, "roles_responsables": [], "semaforo": semaforo}},
        "R2": {"b": {"encargado_id": 7, "roles_responsables": [rol], "semaforo": semaforo}},
    }
    tecnico = correo.reporte_de(7, {Permission.TECNICO}, por_radicado)
    assert list(tecnico["alertas"]) == ["R1"] and tecnico["estadisticas_semaforo"]["rojo"] == 1
    lider = correo.reporte_de(9, {Permission.LIDER_TECNICO}, por_radicado)
    assert list(lider["alertas"]) == ["R2"] and lider["alertas"]["R2"]["b"]["es_responsable"] is True
    assert correo.reporte_de(9, set(), por_radicado) is None
    assert "es_responsable" not in por_radicado["R2"]["b"]  # se copian antes de marcar

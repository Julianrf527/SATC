"""Envío semanal de alertas: el job se ejecuta de verdad y una sola vez por
semana aunque gunicorn corra varios workers (cada uno con su scheduler)."""
import asyncio
import inspect
from datetime import date

import pytest
from fastapi import FastAPI

import services.alertas_scheduler as sched


def test_lunes_de():
    assert sched.lunes_de(date(2026, 11, 20)) == date(2026, 11, 16)  # viernes
    assert sched.lunes_de(date(2026, 11, 16)) == date(2026, 11, 16)  # lunes


async def test_job_registrado_es_corrutina(monkeypatch):
    monkeypatch.delenv("ALERTAS_CORREO_SEMANAL", raising=False)
    # Regresión: con `lambda: corrutina()` APScheduler creaba la corrutina y
    # nunca la ejecutaba (el correo no salía nunca).
    registrados = {}

    class _Scheduler:
        def add_job(self, func, **kw):
            registrados["func"], registrados["kw"] = func, kw

        def start(self):
            pass

        def shutdown(self):
            pass

    monkeypatch.setattr(sched, "scheduler", _Scheduler())
    app = FastAPI()
    sched.configurar_scheduler_alertas(app, lambda: None)
    for handler in app.router.on_startup:
        await handler()
    assert inspect.iscoroutinefunction(registrados["func"])
    assert registrados["kw"]["coalesce"] is True and registrados["kw"]["max_instances"] == 1


def test_apagado_por_variable(monkeypatch):
    monkeypatch.setenv("ALERTAS_CORREO_SEMANAL", "FALSE")
    app = FastAPI()
    sched.configurar_scheduler_alertas(app, lambda: None)
    assert app.router.on_startup == []


async def test_job_de_apscheduler_se_ejecuta(monkeypatch):
    # Con el scheduler real: el job async corre y llama al envío.
    llamadas = []

    async def _envio(get_db):
        llamadas.append(get_db)
        return True

    monkeypatch.setattr(sched, "ejecutar_envio_semanal", _envio)
    monkeypatch.delenv("ALERTAS_CORREO_SEMANAL", raising=False)
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    real = AsyncIOScheduler()
    monkeypatch.setattr(sched, "scheduler", real)
    app = FastAPI()
    sched.configurar_scheduler_alertas(app, "get_db")
    for handler in app.router.on_startup:
        await handler()
    real.get_job("envio_alertas_semanal_infraccion").modify(next_run_time=None)
    real.add_job(real.get_job("envio_alertas_semanal_infraccion").func)  # ejecutar ya
    await asyncio.sleep(0.3)
    real.shutdown(wait=False)
    assert llamadas == ["get_db"]


@pytest.fixture
def get_db_test(db_session):
    async def _get_db():
        yield db_session
    return _get_db


async def test_varios_workers_envian_una_sola_vez(monkeypatch, get_db_test):
    enviados = []

    async def _tarea(db):
        enviados.append(1)

    monkeypatch.setattr(sched, "tarea_envio_alertas_semanal", _tarea)
    resultados = [await sched.ejecutar_envio_semanal(get_db_test) for _ in range(4)]
    assert resultados == [True, False, False, False]
    assert enviados == [1]


async def test_reclamar_envio_por_semana(db_session):
    assert await sched.reclamar_envio(db_session, date(2026, 11, 16)) is True
    assert await sched.reclamar_envio(db_session, date(2026, 11, 16)) is False
    assert await sched.reclamar_envio(db_session, date(2026, 11, 23)) is True

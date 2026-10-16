"""5.4: el uso de archivos sumado en app-docs ANTES del commit se compensa si la
operación termina en error (services/usos_archivos.py + db.deps.get_db_managed)."""
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import services.docs as docs_svc
from db.models import ActoAdmite, Expediente
from services.usos_archivos import pendientes, registro_peticion
from tests.fixtures_etapas import *  # noqa: F401,F403


def acto(stubs) -> dict:
    return {"clase_acto": "RES", "numerado": numerado(), "fecha_numerado": "2015-03-01",
            "file_id": stubs.files.registrar()}


def _commit_falla(monkeypatch):
    """El siguiente commit de una sesión falla (BD caída, conflicto...)."""
    original = AsyncSession.commit
    estado = {"fallar": True}

    async def _commit(self):
        if estado["fallar"]:
            estado["fallar"] = False
            raise RuntimeError("commit fallido (simulado)")
        return await original(self)

    monkeypatch.setattr(AsyncSession, "commit", _commit)


async def test_crear_expediente_commit_fallido_compensa(client, h_gestor, payload_expediente, stubs,
                                                       db_session, monkeypatch):
    body = payload_expediente()
    _commit_falla(monkeypatch)
    r = await client.post("/expedientes", json=body, headers=h_gestor)
    assert r.status_code == 500, r.text  # el error original no se oculta
    comprobante = body["doc_comprobante_pago_id"]
    assert stubs.files.incrementados == [comprobante]
    assert stubs.files.decrementados == [comprobante]  # compensado
    assert await db_session.scalar(select(func.count(Expediente.id))) == 0


async def test_super_gestion_error_tras_sumar_compensa_todo(client, rv_permisos, expediente, db_session,
                                                           monkeypatch):
    """Acto (crear_acto) + documentos (registrar_archivos): si la auditoría
    falla después de sumar, se restan exactamente esos usos."""
    import routes.super_gestion as sg

    stubs = rv_permisos

    async def _auditar_falla(*a, **k):
        raise HTTPException(status_code=409, detail="conflicto simulado")

    monkeypatch.setattr(sg, "auditar", _auditar_falla)
    body = {"acto": acto(stubs), "doc_oficio_alcaldia_id": stubs.files.registrar()}
    r = await post(client, f"/super-gestion/{expediente.id}/admite", SUPER_G, body, esperado=409)
    assert r.json()["detail"] == "conflicto simulado"
    sumados = sorted(stubs.files.incrementados)
    assert sorted([body["acto"]["file_id"], body["doc_oficio_alcaldia_id"]]) == sumados
    assert sorted(stubs.files.decrementados) == sumados
    assert await db_session.scalar(select(ActoAdmite.id)) is None


async def test_operacion_exitosa_no_compensa(client, rv_permisos, expediente):
    stubs = rv_permisos
    body = {"acto": acto(stubs), "doc_oficio_alcaldia_id": stubs.files.registrar()}
    await post(client, f"/super-gestion/{expediente.id}/admite", SUPER_G, body)
    assert len(stubs.files.incrementados) == 2
    assert stubs.files.decrementados == []


async def test_version_del_servicio_compartido_se_compensa(client, rv_permisos, rv_proceso, monkeypatch):
    """La suma que hace satc_shared.review_process al subir una versión también
    se anota y se compensa si el commit falla."""
    stubs = rv_permisos
    _, _, proceso = await rv_proceso("AUTO_ADMITE")
    _commit_falla(monkeypatch)
    r = await subir(client, proceso.id, user=ABOGADO)
    assert r.status_code == 500, r.text
    assert stubs.files.incrementados, "la versión debió sumar su uso"
    assert sorted(stubs.files.decrementados) == sorted(stubs.files.incrementados)


async def test_registro_commit_confirma_y_error_posterior_no_compensa(db_session, stubs):
    """Lo sumado antes del commit queda confirmado: un error DESPUÉS del commit
    (p. ej. al enviar avisos) no lo resta."""
    with pytest.raises(RuntimeError):
        async with registro_peticion(db_session):
            assert (await docs_svc.increment_file_usage([501]))["ok"]
            assert pendientes() == [[501]]
            await db_session.commit()
            assert pendientes() == []
            raise RuntimeError("falla al avisar")
    assert stubs.files.decrementados == []


async def test_registro_sin_commit_compensa_y_relanza(db_session, stubs):
    with pytest.raises(HTTPException) as exc:
        async with registro_peticion(db_session):
            await docs_svc.increment_file_usage([601, 602])
            await docs_svc.increment_file_usage([603])
            raise HTTPException(status_code=400, detail="original")
    assert exc.value.detail == "original"
    assert sorted(stubs.files.decrementados) == [601, 602, 603]
    # Fuera de una petición no se anota nada.
    await docs_svc.increment_file_usage([700])
    assert pendientes() == []


async def test_compensacion_que_falla_no_oculta_el_error(db_session, stubs, monkeypatch):
    async def _decrement_caido(file_ids):
        raise RuntimeError("app-docs caído")

    monkeypatch.setattr(stubs.files, "decrement_usage", _decrement_caido)
    with pytest.raises(HTTPException) as exc:
        async with registro_peticion(db_session):
            await docs_svc.increment_file_usage([801])
            raise HTTPException(status_code=409, detail="original")
    assert exc.value.detail == "original"

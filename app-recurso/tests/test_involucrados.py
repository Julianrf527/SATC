"""Solicitantes: vincular / desvincular / representante (routes/involucrados.py, V14)."""
import asyncio
from datetime import date

from sqlalchemy import select

from db.models import (
    ActoAdministrativo,
    ActoAdmite,
    Auditoria,
    ExpedienteInvolucrado,
    Notificacion,
    TipoActo,
    TipoVinculo,
)
from tests.conftest import TestSessionLocal


async def _vinculos(expediente_id):
    async with TestSessionLocal() as s:
        return (await s.execute(
            select(ExpedienteInvolucrado).where(ExpedienteInvolucrado.expediente_id == expediente_id)
        )).scalars().all()


async def test_vincular_varios_solicitantes(client, h_gestor, crear_expediente, stubs):
    exp = await crear_expediente()
    stubs.involved.registrar(1, nombre="Juan")
    stubs.involved.registrar(2, nombre="María")
    for inv in (1, 2):
        r = await client.post("/involucrados/vinculos", json={"expediente_id": exp.id, "involucrado_id": inv}, headers=h_gestor)
        assert r.status_code == 201, r.text
        d = r.json()["data"]
        assert d["tipo_vinculo"] == "SOLICITANTE"
        assert d["version"] == 1
        assert d["involucrado"]["id"] == inv
    assert {v.involucrado_id for v in await _vinculos(exp.id)} == {1, 2}

    r = await client.get(f"/involucrados/expediente/{exp.id}", headers=h_gestor)
    assert [v["involucrado"]["nombre"] for v in r.json()["data"]] == ["Juan", "María"]
    async with TestSessionLocal() as s:
        eventos = (await s.execute(select(Auditoria.tipo_evento))).scalars().all()
    assert eventos == ["VINCULAR_INVOLUCRADO", "VINCULAR_INVOLUCRADO"]


async def test_vincular_duplicado_409(client, h_gestor, crear_expediente, vincular):
    exp = await crear_expediente()
    await vincular(exp.id, 5)
    r = await client.post("/involucrados/vinculos", json={"expediente_id": exp.id, "involucrado_id": 5}, headers=h_gestor)
    assert r.status_code == 409


async def test_vincular_concurrente_una_409(client, h_gestor, crear_expediente, stubs):
    exp = await crear_expediente()
    stubs.involved.registrar(6)
    body = {"expediente_id": exp.id, "involucrado_id": 6}
    r1, r2 = await asyncio.gather(
        client.post("/involucrados/vinculos", json=body, headers=h_gestor),
        client.post("/involucrados/vinculos", json=body, headers=h_gestor),
    )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409]
    assert len(await _vinculos(exp.id)) == 1


async def test_vincular_involucrado_inexistente_404(client, h_gestor, crear_expediente):
    exp = await crear_expediente()
    r = await client.post("/involucrados/vinculos", json={"expediente_id": exp.id, "involucrado_id": 777}, headers=h_gestor)
    assert r.status_code == 404


async def test_vincular_expediente_inexistente_404(client, h_gestor, stubs):
    stubs.involved.registrar(1)
    r = await client.post("/involucrados/vinculos", json={"expediente_id": 9999, "involucrado_id": 1}, headers=h_gestor)
    assert r.status_code == 404


async def test_vincular_app_involved_caido_502(client, h_gestor, crear_expediente, stubs):
    exp = await crear_expediente()
    stubs.involved.caido = True
    r = await client.post("/involucrados/vinculos", json={"expediente_id": exp.id, "involucrado_id": 1}, headers=h_gestor)
    assert r.status_code == 502


async def test_v14_nit_sin_representante_400(client, h_gestor, crear_expediente, stubs):
    exp = await crear_expediente()
    stubs.involved.registrar(10, tipo_documento="NIT", digito_verificacion="3")
    r = await client.post("/involucrados/vinculos", json={"expediente_id": exp.id, "involucrado_id": 10}, headers=h_gestor)
    assert r.status_code == 400
    assert "NIT" in r.json()["detail"]
    assert await _vinculos(exp.id) == []


async def test_v14_nit_con_representante(client, h_gestor, crear_expediente, stubs):
    exp = await crear_expediente()
    stubs.involved.registrar(10, tipo_documento="NIT")
    stubs.involved.registrar(11, nombre="Rep Legal")
    r = await client.post(
        "/involucrados/vinculos",
        json={"expediente_id": exp.id, "involucrado_id": 10, "representante_id": 11},
        headers=h_gestor,
    )
    assert r.status_code == 201
    d = r.json()["data"]
    assert d["representante"]["nombre"] == "Rep Legal"
    assert d["requiere_representante"] is True


async def test_v14_representante_inexistente_404(client, h_gestor, crear_expediente, stubs):
    exp = await crear_expediente()
    stubs.involved.registrar(10, tipo_documento="NIT")
    r = await client.post(
        "/involucrados/vinculos",
        json={"expediente_id": exp.id, "involucrado_id": 10, "representante_id": 404},
        headers=h_gestor,
    )
    assert r.status_code == 404


async def test_v14_super_gestion_omite_validacion(client, h_super, crear_expediente, stubs):
    exp = await crear_expediente()
    stubs.involved.registrar(10, tipo_documento="NIT")
    r = await client.post("/involucrados/vinculos", json={"expediente_id": exp.id, "involucrado_id": 10}, headers=h_super)
    assert r.status_code == 201


async def test_vincular_solo_consulta_403(client, h_consultor, crear_expediente, stubs):
    exp = await crear_expediente()
    stubs.involved.registrar(1)
    r = await client.post("/involucrados/vinculos", json={"expediente_id": exp.id, "involucrado_id": 1}, headers=h_consultor)
    assert r.status_code == 403


# ─── Representante ───────────────────────────────────────────────────────────

async def test_editar_representante_con_version(client, h_gestor, crear_expediente, vincular, stubs):
    exp = await crear_expediente()
    stubs.involved.registrar(10, tipo_documento="NIT")
    stubs.involved.registrar(12)
    v = await vincular(exp.id, 10, representante_id=11)

    r = await client.patch(f"/involucrados/vinculos/{v.id}/representante",
                           json={"representante_id": 12, "version": 1}, headers=h_gestor)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["version"] == 2
    assert (await _vinculos(exp.id))[0].representante_id == 12

    # Version vieja → 409
    r = await client.patch(f"/involucrados/vinculos/{v.id}/representante",
                           json={"representante_id": 11, "version": 1}, headers=h_gestor)
    assert r.status_code == 409
    # Quitar el representante de un NIT → 400 (V14)
    r = await client.patch(f"/involucrados/vinculos/{v.id}/representante",
                           json={"representante_id": None, "version": 2}, headers=h_gestor)
    assert r.status_code == 400


async def test_editar_representante_concurrente_una_409(client, h_gestor, crear_expediente, vincular, stubs):
    exp = await crear_expediente()
    for i in (31, 32):
        stubs.involved.registrar(i)
    v = await vincular(exp.id, 30)
    r1, r2 = await asyncio.gather(
        client.patch(f"/involucrados/vinculos/{v.id}/representante", json={"representante_id": 31, "version": 1}, headers=h_gestor),
        client.patch(f"/involucrados/vinculos/{v.id}/representante", json={"representante_id": 32, "version": 1}, headers=h_gestor),
    )
    assert sorted([r1.status_code, r2.status_code]) == [200, 409]


async def test_quitar_representante_persona_natural(client, h_gestor, crear_expediente, vincular):
    exp = await crear_expediente()
    v = await vincular(exp.id, 30, representante_id=31)
    r = await client.patch(f"/involucrados/vinculos/{v.id}/representante",
                           json={"representante_id": None, "version": 1}, headers=h_gestor)
    assert r.status_code == 200
    assert (await _vinculos(exp.id))[0].representante_id is None


# ─── Desvincular ─────────────────────────────────────────────────────────────

async def test_desvincular(client, h_gestor, crear_expediente, vincular):
    exp = await crear_expediente()
    v = await vincular(exp.id, 40)
    r = await client.delete(f"/involucrados/vinculos/{v.id}?version=1", headers=h_gestor)
    assert r.status_code == 200
    assert await _vinculos(exp.id) == []
    async with TestSessionLocal() as s:
        log = (await s.execute(select(Auditoria))).scalar_one()
    assert log.tipo_evento == "DESVINCULAR_INVOLUCRADO"
    assert log.datos_anteriores["involucrado"]["id"] == 40


async def test_desvincular_version_vieja_409(client, h_gestor, crear_expediente, vincular):
    exp = await crear_expediente()
    v = await vincular(exp.id, 40, version=2)
    r = await client.delete(f"/involucrados/vinculos/{v.id}?version=1", headers=h_gestor)
    assert r.status_code == 409
    assert len(await _vinculos(exp.id)) == 1


async def test_desvincular_inexistente_404(client, h_gestor):
    r = await client.delete("/involucrados/vinculos/9999?version=1", headers=h_gestor)
    assert r.status_code == 404


async def test_no_se_gestiona_tercero_por_esta_ruta(client, h_gestor, crear_expediente, vincular):
    exp = await crear_expediente()
    v = await vincular(exp.id, 50, tipo_vinculo=TipoVinculo.TERCERO_INTERVINIENTE)
    r = await client.delete(f"/involucrados/vinculos/{v.id}?version=1", headers=h_gestor)
    assert r.status_code == 400
    r = await client.patch(f"/involucrados/vinculos/{v.id}/representante",
                           json={"representante_id": None, "version": 1}, headers=h_gestor)
    assert r.status_code == 400


async def test_desvincular_con_notificaciones_409(client, h_gestor, crear_expediente, vincular, db_session, stubs):
    exp = await crear_expediente()
    v = await vincular(exp.id, 60)
    acto = ActoAdministrativo(tipo_acto=TipoActo.AUTO_ADMITE, numerado=1, fecha_numerado=date(2026, 4, 1),
                              documento_acto_administrativo_id=stubs.files.registrar())
    db_session.add(acto)
    await db_session.flush()
    db_session.add(ActoAdmite(expediente_id=exp.id, encargado_acto_id=10, acto_admin_id=acto.id))
    db_session.add(Notificacion(acto_admin_id=acto.id, numerado=5, involucrado_id=60,
                                fecha_numerado=date(2026, 4, 2), fecha_envio_citacion=date(2026, 4, 2),
                                fecha_constancia_citacion=date(2026, 4, 3)))
    await db_session.commit()

    r = await client.delete(f"/involucrados/vinculos/{v.id}?version=1", headers=h_gestor)
    assert r.status_code == 409
    assert "notificaciones" in r.json()["detail"]


async def test_listar_filtrando_tipo(client, h_consultor, crear_expediente, vincular):
    exp = await crear_expediente()
    await vincular(exp.id, 70)
    await vincular(exp.id, 71, tipo_vinculo=TipoVinculo.TERCERO_INTERVINIENTE)
    r = await client.get(f"/involucrados/expediente/{exp.id}?tipo_vinculo=TERCERO_INTERVINIENTE", headers=h_consultor)
    assert [v["involucrado_id"] for v in r.json()["data"]] == [71]

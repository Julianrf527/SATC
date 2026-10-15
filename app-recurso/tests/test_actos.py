"""Actos administrativos, comunicación y notificación (/actos + services/actos)."""
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from db.models import (
    ActoAdmite,
    ActoAdministrativo,
    Decision,
    ExpedienteInvolucrado,
    RecursoReposicion,
    TipoActo,
    TipoVinculo,
)
from tests.fixtures_revision import *  # noqa: F401,F403

SOLICITANTE, TERCERO, AJENO = 501, 502, 503


@pytest.fixture
def acto_admite(db_session, crear_expediente, vincular, rv_permisos):
    """Expediente con solicitante + tercero y auto admite (encargado ABOGADO) con acto."""
    from services.actos import crear_acto

    async def _make(numerado=12):
        exp = await crear_expediente()
        await vincular(exp.id, SOLICITANTE)
        await vincular(exp.id, TERCERO, tipo_vinculo=TipoVinculo.TERCERO_INTERVINIENTE)
        doc = rv_permisos.files.registrar()
        acto = await crear_acto(db_session, clase_acto="AUTO", tipo_acto="AUTO_ADMITE", numerado=numerado,
                                fecha_numerado="2026-04-01", documento_id=doc, user_id=ABOGADO)
        etapa = ActoAdmite(expediente_id=exp.id, encargado_acto_id=ABOGADO, acto_admin_id=acto.id)
        db_session.add(etapa)
        await db_session.commit()
        return exp.id, acto.id, doc

    return _make


@pytest.fixture
def acto_decision(db_session, crear_expediente, vincular, rv_permisos):
    """Expediente con solicitante + tercero y decisión (encargado ABOGADO) con acto:
    un acto que sí se notifica."""
    from services.actos import crear_acto

    async def _make(numerado=12):
        exp = await crear_expediente()
        await vincular(exp.id, SOLICITANTE)
        await vincular(exp.id, TERCERO, tipo_vinculo=TipoVinculo.TERCERO_INTERVINIENTE)
        doc = rv_permisos.files.registrar()
        acto = await crear_acto(db_session, clase_acto="AUTO", tipo_acto="DECISION", numerado=numerado,
                                fecha_numerado="2026-04-01", documento_id=doc, user_id=ABOGADO)
        db_session.add(Decision(expediente_id=exp.id, encargado_acto_id=ABOGADO, acto_admin_id=acto.id))
        await db_session.commit()
        return exp.id, acto.id, doc

    return _make


def _form_notif(exp_id, acto_id, involucrado_id, stubs, **extra):
    datos = {
        "expediente_id": exp_id, "acto_admin_id": acto_id, "involucrado_id": involucrado_id,
        "numerado": "0045", "fecha_numerado": "2026-04-02", "fecha_envio_citacion": "2026-04-03",
        "fecha_constancia_citacion": "2026-04-04", "documento_citacion_id": stubs.files.registrar(),
        "notificacion_exitosa": "false",
    }
    datos.update(extra)
    return {k: str(v) for k, v in datos.items()}


async def test_crear_acto_validaciones(db_session, rv_permisos, acto_admite):
    from services.actos import crear_acto

    exp_id, acto_id, doc = await acto_admite()
    assert doc in rv_permisos.files.incrementados
    acto = await db_session.scalar(select(ActoAdministrativo).where(ActoAdministrativo.id == acto_id))
    assert acto.tipo_acto == TipoActo.AUTO_ADMITE and acto.numerado == 12
    for numerado in ("12345", "0", "-3", "abc"):
        with pytest.raises(HTTPException) as e:
            await crear_acto(db_session, clase_acto="AUTO", tipo_acto="AUTO_ADMITE", numerado=numerado,
                             fecha_numerado="2026-04-01", documento_id=1, user_id=ABOGADO)
        assert e.value.status_code == 400
    with pytest.raises(HTTPException) as e:  # mismo numerado y fecha del mismo tipo
        await crear_acto(db_session, clase_acto="AUTO", tipo_acto="AUTO_ADMITE", numerado="0012",
                         fecha_numerado="2026-04-01", documento_id=1, user_id=ABOGADO)
    assert e.value.status_code == 409
    with pytest.raises(HTTPException) as e:  # Auto/Resolución obligatorio y válido
        await crear_acto(db_session, clase_acto="", tipo_acto="AUTO_ADMITE", numerado=5,
                         fecha_numerado="2026-04-01", documento_id=1, user_id=ABOGADO)
    assert e.value.status_code == 400
    with pytest.raises(HTTPException) as e:
        await crear_acto(db_session, clase_acto="AUTO", tipo_acto="AUTO", numerado=1, fecha_numerado="2026-04-01",
                         documento_id=1, user_id=ABOGADO)
    assert e.value.status_code == 400


async def test_etapa_de_acto_y_recurso(db_session, crear_expediente, rv_permisos, acto_admite):
    from services.actos import crear_acto, etapa_de_acto

    exp_id, acto_id, _ = await acto_admite()
    etapa = await etapa_de_acto(db_session, acto_id)
    assert etapa.etapa_tipo == "acto_admite" and etapa.expediente_id == exp_id and etapa.encargado_id == ABOGADO

    exp = await crear_expediente()
    decision = Decision(expediente_id=exp.id, encargado_acto_id=ABOGADO)
    db_session.add(decision)
    await db_session.flush()
    acto_rec = await crear_acto(db_session, clase_acto="AUTO", tipo_acto=TipoActo.RECURSO, numerado=7,
                                fecha_numerado=date(2026, 5, 1), documento_id=9, user_id=ABOGADO2)
    db_session.add(RecursoReposicion(decision_id=decision.id, encargado_acto_id=ABOGADO2, acto_admin_id=acto_rec.id,
                                     radicado="R1", fecha_radicado=date(2026, 4, 20), doc_recurso_id=3))
    await db_session.commit()
    etapa = await etapa_de_acto(db_session, acto_rec.id)
    assert etapa.etapa_tipo == "recurso_reposicion" and etapa.expediente_id == exp.id
    assert etapa.encargado_id == ABOGADO2
    assert await etapa_de_acto(db_session, 999999) is None


async def test_get_acto_y_tipos(client, rv_permisos, acto_admite):
    exp_id, acto_id, _ = await acto_admite()
    r = await client.get(f"/actos/administrativos/{acto_id}", headers=headers(ABOGADO))
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["tipo_acto"] == "AUTO_ADMITE" and d["etapa_tipo"] == "acto_admite"
    assert d["comunicacion"] is None and d["notificacion"]["involucrados"] == []
    assert {i["involucrado_id"] for i in d["involucrados_notificables"]} == {SOLICITANTE, TERCERO}
    # El auto que admite solo se comunica: nunca ofrece notificar.
    assert "crear_comunicacion" in d["acciones_disponibles"] and "crear_notificacion" not in d["acciones_disponibles"]
    assert "eliminar_acto" not in d["acciones_disponibles"]
    r = await client.get(f"/actos/administrativos/{acto_id}", headers=headers(LECTOR))
    assert r.status_code == 200 and r.json()["data"]["acciones_disponibles"] == []
    assert (await client.get(f"/actos/administrativos/{acto_id}", headers=headers(EXTRANO))).status_code == 403
    tipos = (await client.get("/actos/tipos-notificacion", headers=headers(LECTOR))).json()["data"]
    assert {t["nombre"] for t in tipos} >= {"PERSONAL", "AVISO"}


async def test_comunicacion_crud(client, rv_permisos, acto_admite):
    stubs = rv_permisos
    exp_id, acto_id, _ = await acto_admite()
    doc = stubs.files.registrar()
    form = {"expediente_id": exp_id, "acto_admin_id": acto_id, "numerado": "0003",
            "fecha_numerado": "2026-04-02", "fecha_envio": "2026-04-03", "documento_comunicacion_id": doc}
    form = {k: str(v) for k, v in form.items()}

    # Otro abogado (gestionar, no encargado) → 403; consulta → 403.
    assert (await client.post("/actos/comunicaciones", data=form, headers=headers(ABOGADO2))).status_code == 403
    assert (await client.post("/actos/comunicaciones", data=form, headers=headers(LECTOR))).status_code == 403
    bad = dict(form, expediente_id="999999")
    assert (await client.post("/actos/comunicaciones", data=bad, headers=headers(ABOGADO))).status_code == 400

    r = await client.post("/actos/comunicaciones", data=form, headers=headers(ABOGADO))
    assert r.status_code == 201, r.text
    com = r.json()["data"]
    assert com["numerado"] == 3 and com["documento_comunicacion_id"] == doc
    assert com["fecha_creacion"]  # fecha de registro (antes siempre null)
    d = (await client.get(f"/actos/administrativos/{acto_id}", headers=headers(ABOGADO))).json()["data"]
    from datetime import datetime as _dt
    assert _dt.fromisoformat(d["comunicacion"]["fecha_creacion"]) == _dt.fromisoformat(com["fecha_creacion"])
    assert doc in stubs.files.incrementados
    # Una por acto.
    assert (await client.post("/actos/comunicaciones", data=form, headers=headers(ABOGADO))).status_code == 409

    doc2 = stubs.files.registrar()
    upd = dict(form, numerado="0004", documento_comunicacion_id=str(doc2))
    r = await client.put(f"/actos/comunicaciones/{com['id']}", data=upd, headers=headers(SUPER_G))
    assert r.status_code == 200 and r.json()["data"]["numerado"] == 4
    assert doc in stubs.files.decrementados and doc2 in stubs.files.incrementados

    r = await client.request("DELETE", f"/actos/comunicaciones/{com['id']}", json={"expediente_id": exp_id},
                             headers=headers(ABOGADO))
    assert r.status_code == 200 and doc2 in stubs.files.decrementados


@pytest.fixture
def acto_tercero(db_session, crear_expediente, vincular, rv_permisos):
    """Expediente con solicitante y un tercero reconocido por acto (RECONOCE_TERCERO)."""
    from services.actos import crear_acto

    async def _make():
        exp = await crear_expediente()
        await vincular(exp.id, SOLICITANTE)
        v = await vincular(exp.id, TERCERO, tipo_vinculo=TipoVinculo.TERCERO_INTERVINIENTE)
        acto = await crear_acto(db_session, clase_acto="AUTO", tipo_acto="RECONOCE_TERCERO", numerado=21,
                                fecha_numerado="2026-04-01", documento_id=rv_permisos.files.registrar(),
                                user_id=SUPER_G)
        v = await db_session.get(ExpedienteInvolucrado, v.id)
        v.acto_admin_id = acto.id
        await db_session.commit()
        return exp.id, acto.id

    return _make


def _form_com(exp_id, acto_id, stubs):
    return {k: str(v) for k, v in {
        "expediente_id": exp_id, "acto_admin_id": acto_id, "numerado": "0003", "fecha_numerado": "2026-04-02",
        "fecha_envio": "2026-04-03", "documento_comunicacion_id": stubs.files.registrar()}.items()}


def test_regla_comunicar_notificar():
    from services.actos import ACTOS_SOLO_COMUNICACION, se_comunica, se_notifica

    assert ACTOS_SOLO_COMUNICACION == {TipoActo.AUTO_ADMITE, TipoActo.RECONOCE_TERCERO}
    for tipo in TipoActo:
        assert se_comunica(tipo) != se_notifica(tipo)
        assert se_comunica(tipo.value) == se_comunica(tipo)
    assert se_comunica("RECONOCE_TERCERO") and not se_notifica("RECONOCE_TERCERO")
    assert se_notifica("DECISION") and not se_comunica("DECISION")


async def test_acto_tercero_solo_se_comunica(client, rv_permisos, acto_tercero):
    exp_id, acto_id = await acto_tercero()
    d = (await client.get(f"/actos/administrativos/{acto_id}", headers=headers(SUPER_G))).json()["data"]
    assert "crear_comunicacion" in d["acciones_disponibles"]
    assert "crear_notificacion" not in d["acciones_disponibles"]
    r = await client.post("/actos/notificaciones", data=_form_notif(exp_id, acto_id, TERCERO, rv_permisos),
                          headers=headers(SUPER_G))
    assert r.status_code == 400 and "solo se comunica" in r.json()["detail"]
    r = await client.post("/actos/comunicaciones", data=_form_com(exp_id, acto_id, rv_permisos),
                          headers=headers(SUPER_G))
    assert r.status_code == 201, r.text


async def test_decision_no_se_comunica(client, db_session, rv_permisos, acto_decision):
    from db.models import Comunicacion

    exp_id, acto_id, _ = await acto_decision()
    d = (await client.get(f"/actos/administrativos/{acto_id}", headers=headers(ABOGADO))).json()["data"]
    assert "crear_notificacion" in d["acciones_disponibles"]
    assert not {"crear_comunicacion", "editar_comunicacion"} & set(d["acciones_disponibles"])
    r = await client.post("/actos/comunicaciones", data=_form_com(exp_id, acto_id, rv_permisos),
                          headers=headers(ABOGADO))
    assert r.status_code == 400 and "solo se notifica" in r.json()["detail"]
    # Dato heredado (comunicación en un acto que ya no se comunica): se puede
    # corregir o eliminar, pero no crear otra.
    db_session.add(Comunicacion(acto_administrativo_id=acto_id, numerado=1, fecha_numerado=date(2026, 4, 2),
                                fecha_envio=date(2026, 4, 3), documento_comunicacion_id=77))
    await db_session.commit()
    d = (await client.get(f"/actos/administrativos/{acto_id}", headers=headers(ABOGADO))).json()["data"]
    assert {"editar_comunicacion", "eliminar_comunicacion"} <= set(d["acciones_disponibles"])
    assert "crear_comunicacion" not in d["acciones_disponibles"]


async def test_auto_admite_no_se_notifica(client, rv_permisos, acto_admite):
    """Regla del área: el auto que admite solo se comunica (a todos, sin distinguir)."""
    exp_id, acto_id, _ = await acto_admite()
    r = await client.post("/actos/notificaciones", data=_form_notif(exp_id, acto_id, SOLICITANTE, rv_permisos),
                          headers=headers(ABOGADO))
    assert r.status_code == 400 and "solo se comunica" in r.json()["detail"]
    r = await client.post("/actos/notificaciones", data=_form_notif(exp_id, acto_id, TERCERO, rv_permisos),
                          headers=headers(SUPER_G))
    assert r.status_code == 400


async def test_notificaciones_y_acto_notificado(client, db_session, rv_permisos, acto_decision):
    from services.actos import acto_notificado, notificaciones_completas

    stubs = rv_permisos
    exp_id, acto_id, _ = await acto_decision()
    assert await acto_notificado(db_session, acto_id) is False

    # Involucrado ajeno al expediente → 400. Sin constancia de citación → 400.
    r = await client.post("/actos/notificaciones", data=_form_notif(exp_id, acto_id, AJENO, stubs), headers=headers(ABOGADO))
    assert r.status_code == 400
    r = await client.post("/actos/notificaciones", data=_form_notif(exp_id, acto_id, SOLICITANTE, stubs,
                          fecha_constancia_citacion=""), headers=headers(ABOGADO))
    assert r.status_code == 400
    # Exitosa sin tipo → 400.
    r = await client.post("/actos/notificaciones", data=_form_notif(exp_id, acto_id, SOLICITANTE, stubs,
                          notificacion_exitosa="true"), headers=headers(ABOGADO))
    assert r.status_code == 400

    r = await client.post("/actos/notificaciones", data=_form_notif(exp_id, acto_id, SOLICITANTE, stubs),
                          headers=headers(ABOGADO))
    assert r.status_code == 201, r.text
    n1 = r.json()["data"]
    assert n1["involucrado_id"] == SOLICITANTE and n1["notificacion_exitosa"] is False and n1["version"] == 1
    # Duplicada por persona → 409.
    r = await client.post("/actos/notificaciones", data=_form_notif(exp_id, acto_id, SOLICITANTE, stubs,
                          numerado="0046"), headers=headers(ABOGADO))
    assert r.status_code == 409
    # Mismo numerado + fecha en otra notificación → 409.
    r = await client.post("/actos/notificaciones", data=_form_notif(exp_id, acto_id, TERCERO, stubs),
                          headers=headers(ABOGADO))
    assert r.status_code == 409
    r = await client.post("/actos/notificaciones", data=_form_notif(exp_id, acto_id, TERCERO, stubs, numerado="0047"),
                          headers=headers(ABOGADO))
    assert r.status_code == 201
    n2 = r.json()["data"]

    estado = await notificaciones_completas(db_session, acto_id)
    assert estado == {"total": 2, "exitosas": 0, "notificado": False}

    # Registrar entrega exitosa de ambos.
    personal = await _tipo(client, "PERSONAL")
    for n in (n1, n2):
        form = _form_notif(exp_id, acto_id, n["involucrado_id"], stubs, numerado=str(n["numerado"]),
                           documento_citacion_id=n["documento_citacion_id"], notificacion_exitosa="true",
                           tipo_notificacion_id=personal, documento_notificacion_id=stubs.files.registrar(),
                           fecha_notificacion="2026-04-10", version=n["version"])
        form.pop("acto_admin_id"), form.pop("involucrado_id")
        r = await client.put(f"/actos/notificaciones/{n['id']}", data=form, headers=headers(ABOGADO))
        assert r.status_code == 200, r.text
        assert r.json()["data"]["fecha_notificacion"] == "2026-04-10" and r.json()["data"]["version"] == 2
    # Versión vieja → 409.
    r = await client.put(f"/actos/notificaciones/{n1['id']}", data={**form, "version": "1"}, headers=headers(ABOGADO))
    assert r.status_code == 409

    db_session.expire_all()
    assert await acto_notificado(db_session, acto_id) is True

    r = await client.request("DELETE", f"/actos/notificaciones/{n2['id']}", json={"expediente_id": exp_id},
                             headers=headers(ABOGADO2))
    assert r.status_code == 403
    r = await client.request("DELETE", f"/actos/notificaciones/{n2['id']}", json={"expediente_id": exp_id},
                             headers=headers(ABOGADO))
    assert r.status_code == 200
    r = await client.get(f"/actos/administrativos/{acto_id}", headers=headers(ABOGADO))
    d = r.json()["data"]
    assert len(d["notificacion"]["involucrados"]) == 1 and d["notificado"] is True
    assert "crear_notificacion" in d["acciones_disponibles"]


async def _tipo(client, nombre):
    tipos = (await client.get("/actos/tipos-notificacion", headers=headers(ABOGADO))).json()["data"]
    return next(t["id"] for t in tipos if t["nombre"] == nombre)


async def test_corregir_y_eliminar_acto(client, db_session, rv_permisos, acto_admite):
    stubs = rv_permisos
    exp_id, acto_id, doc = await acto_admite()
    await acto_admite(numerado=13)  # otro acto con 13 en la misma fecha
    doc2 = stubs.files.registrar()
    form = {"expediente_id": str(exp_id), "tipo_acto": "AUTO", "numerado": "0013",
            "fecha_numerado": "2026-04-01", "documento_acto_administrativo_id": str(doc2)}
    r = await client.put(f"/actos/administrativos/{acto_id}", data=form, headers=headers(ABOGADO))
    assert r.status_code == 409  # numerado 13 + fecha ya usado
    form["numerado"] = "0014"
    assert (await client.put(f"/actos/administrativos/{acto_id}", data=form, headers=headers(ABOGADO2))).status_code == 403
    r = await client.put(f"/actos/administrativos/{acto_id}", data=form, headers=headers(ABOGADO))
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    # El formulario manda Auto/Resolución en `tipo_acto`; la clase interna no cambia.
    assert d["numerado"] == 14 and d["tipo_acto"] == "AUTO_ADMITE" and d["clase_acto"] == "AUTO"
    r = await client.put(f"/actos/administrativos/{acto_id}", data={**form, "tipo_acto": "RES"}, headers=headers(ABOGADO))
    assert r.status_code == 200 and r.json()["data"]["clase_acto"] == "RES"
    r = await client.put(f"/actos/administrativos/{acto_id}", data={**form, "tipo_acto": "OTRO"}, headers=headers(ABOGADO))
    assert r.status_code == 400
    assert d["documento_acto_administrativo_id"] == doc2 and doc in stubs.files.decrementados

    # Eliminar: el encargado no, super gestión sí (desenlaza la etapa).
    r = await client.delete(f"/actos/administrativos/{acto_id}", headers=headers(ABOGADO))
    assert r.status_code == 403
    r = await client.delete(f"/actos/administrativos/{acto_id}?expediente_id={exp_id}", headers=headers(SUPER_G))
    assert r.status_code == 200, r.text
    db_session.expire_all()
    etapa = await db_session.scalar(select(ActoAdmite).where(ActoAdmite.expediente_id == exp_id))
    assert etapa.acto_admin_id is None
    assert await db_session.scalar(select(ActoAdministrativo).where(ActoAdministrativo.id == acto_id)) is None

"""Etapa 4 · Decisión, ejecutoria y recurso de reposición (V7, V8, V13)."""
from sqlalchemy import select

from db.models import Decision, RecursoReposicion
from tests.fixtures_etapas import *  # noqa: F401,F403


async def test_decision_requiere_constancia_v7(client, rv_permisos, expediente):
    stubs = rv_permisos
    exp_id = expediente.id
    await post(client, f"/etapas/{exp_id}/decision/asignarme", esperado=400)  # V4
    await admite_firmado(client, stubs, exp_id)
    r = await post(client, f"/etapas/{exp_id}/decision/asignarme", esperado=400)
    assert "V7" in r.json()["detail"]
    # No requiere concepto técnico: con la constancia basta
    await con_constancia(client, stubs, exp_id)
    arbol = await etapas(client, exp_id)
    assert "asignarme" in arbol["decision"]["acciones_disponibles"]
    await post(client, f"/etapas/{exp_id}/decision/asignarme")


async def test_decision_v8_y_una_sola_vez(client, rv_permisos, expediente, db_session):
    stubs = rv_permisos
    exp_id = expediente.id
    await admite_firmado(client, stubs, exp_id)
    await con_constancia(client, stubs, exp_id)
    r = await post(client, f"/etapas/{exp_id}/decision/asignarme")
    await aprobar_para_firma(client, r.json()["data"]["proceso_id"], ABOGADO)
    url = f"/etapas/{exp_id}/decision/version-final"
    # V8: requiere_memorias solo si OTORGADA
    r = await post(client, url, json=acto_body(stubs, decision="NEGADA", requiere_memorias=True), esperado=400)
    assert "V8" in r.json()["detail"]
    # OTORGADA exige indicar requiere_memorias
    await post(client, url, json=acto_body(stubs, decision="OTORGADA"), esperado=400)
    # Auto o Resolución lo elige quien carga: obligatorio y solo AUTO/RES.
    sin_clase = acto_body(stubs, decision="DESISTIDA")
    sin_clase.pop("clase_acto")
    await post(client, url, json=sin_clase, esperado=422)
    await post(client, url, json=acto_body(stubs, decision="DESISTIDA", clase_acto="AUTO_ADMITE"), esperado=422)
    data = (await post(client, url, json=acto_body(stubs, decision="DESISTIDA", clase_acto="RES"))).json()["data"]
    assert data["decision"] == "DESISTIDA" and data["requiere_memorias"] is False
    await post(client, url, json=acto_body(stubs, decision="OTORGADA", requiere_memorias=False), esperado=409)
    arbol = await etapas(client, exp_id)
    assert arbol["etapa_actual"] == "decision"
    assert arbol["decision"]["acto"]["clase_acto"] == "RES" and arbol["decision"]["acto"]["tipo_acto"] == "DECISION"
    assert any("V9" in m for m in arbol["memorias"]["motivos_bloqueo"])
    assert any("V10" in m for m in arbol["obras"]["motivos_bloqueo"])


async def test_ejecutoria(client, rv_permisos, con_decision, db_session):
    exp_id, _ = await con_decision("NEGADA", None)
    arbol = await etapas(client, exp_id)
    assert "registrar_ejecutoria" in arbol["decision"]["acciones_disponibles"]
    v = arbol["decision"]["version"]
    await put(client, f"/etapas/{exp_id}/decision/ejecutoria", ABOGADO2,
              {"version": v, "fecha_ejecutoria": "2026-07-01"}, esperado=403)
    r = await put(client, f"/etapas/{exp_id}/decision/ejecutoria", json={"version": v, "fecha_ejecutoria": "2026-07-01"})
    assert r.json()["data"]["version"] == v + 1
    await put(client, f"/etapas/{exp_id}/decision/ejecutoria", json={"version": v, "fecha_ejecutoria": "2026-07-02"},
              esperado=409)
    d = await db_session.scalar(select(Decision).where(Decision.expediente_id == exp_id))
    assert str(d.fecha_ejecutoria) == "2026-07-01"


async def test_recurso_v13_y_acto(client, rv_permisos, con_decision, catalogo, db_session):
    stubs = rv_permisos
    exp_id, data = await con_decision("NEGADA", None)
    radicado = {"radicado": "2026ER5555", "fecha_radicado": "2026-06-10", "file_id": stubs.files.registrar()}
    # V13: decisión no notificada
    r = await post(client, f"/etapas/{exp_id}/recurso", json=radicado, esperado=400)
    assert "V13" in r.json()["detail"]
    arbol = await etapas(client, exp_id)
    assert arbol["decision"]["recurso"]["habilitada"] is False
    await notificar(client, stubs, catalogo, exp_id, data["acto_id"])
    arbol = await etapas(client, exp_id)
    assert arbol["decision"]["acto"]["notificado"] is True
    assert "crear_recurso" in arbol["decision"]["recurso"]["acciones_disponibles"]
    r = await post(client, f"/etapas/{exp_id}/recurso", json=radicado, esperado=201)
    await post(client, f"/etapas/{exp_id}/recurso", json=radicado, esperado=409)
    # Asignación atómica + acto que lo resuelve
    datos = await acto_completo(client, stubs, f"/etapas/{exp_id}/recurso", ABOGADO2, resultado="CONFIRMA")
    assert datos["resultado"] == "CONFIRMA"
    await post(client, f"/etapas/{exp_id}/recurso/asignarme", esperado=409)
    rec = await db_session.scalar(select(RecursoReposicion))
    assert rec.encargado_acto_id == ABOGADO2 and rec.acto_admin_id == datos["acto_id"]
    arbol = await etapas(client, exp_id, ABOGADO2)
    assert arbol["decision"]["recurso"]["acto"]["tipo_acto"] == "RECURSO"
    assert arbol["decision"]["recurso"]["datos"]["resultado"] == "CONFIRMA"

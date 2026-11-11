"""Acción del concepto de la etapa 2 (Decide / Requiere), edición del concepto
cargado y eliminación del requerimiento desde super gestión."""
from sqlalchemy import select, text

from core.permission import Permission

from db.models import ActoAdministrativo, ConceptoTecnico, Decision, Requerimiento
from db.models.documento_proceso import DocumentoProceso
from services.validaciones import MSG_CONCEPTO_DECIDE
from tests.fixtures_etapas import *  # noqa: F401,F403
from tests.fixtures_etapas import CAUDALES


async def _concepto_cargado(client, stubs, exp_id: int, accion: str) -> dict:
    await admite_firmado(client, stubs, exp_id)
    await concepto_firmado(client, stubs, exp_id, "etapa2", **CAUDALES, accion=accion)
    return buscar_concepto(await etapas(client, exp_id), "etapa2")


async def _con_requerimiento(client, stubs, exp_id: int) -> None:
    """Requerimiento firmado + respuesta del usuario + concepto adicional cargado."""
    await acto_completo(client, stubs, f"/etapas/{exp_id}/requerimientos/etapa3")
    req = (await etapas(client, exp_id))["requerimiento"]
    await put(client, f"/etapas/{exp_id}/requerimientos/etapa3/respuesta", json={
        "version": req["version"], "radicado_oficio_entrada": "2026ER1", "fecha_oficio_entrada": "2026-06-01",
        "doc_oficio_entrada_id": stubs.files.registrar()})
    await post(client, f"/etapas/{exp_id}/conceptos/adicional/tecnico", json={"tecnico_id": TECNICO})
    await concepto_firmado(client, stubs, exp_id, "adicional")


async def _editar(client, concepto_id: int, user: int = TECNICO, esperado: int = 200, **body):
    r = await client.put(f"/etapas/conceptos/{concepto_id}", json=body, headers=headers(user))
    assert r.status_code == esperado, r.text
    return r.json()


# ─────────────────────────────────────────────────────────── V6 y acción

async def test_accion_obligatoria_al_cargar(client, rv_permisos, expediente):
    stubs = rv_permisos
    await admite_firmado(client, stubs, expediente.id)
    nodo = buscar_concepto(await etapas(client, expediente.id), "etapa2")
    await aprobar_para_firma(client, nodo["proceso"]["proceso_id"], TECNICO)
    url = f"/etapas/{expediente.id}/conceptos/etapa2/version-final"
    body = {"file_id": stubs.files.registrar(), "fecha_aceptacion": "2026-05-20", **CAUDALES}
    r = await post(client, url, TECNICO, body, esperado=400)
    assert "acción" in r.json()["detail"]
    await post(client, url, TECNICO, {**body, "accion": "OTRA"}, esperado=422)
    await post(client, url, TECNICO, {**body, "accion": "DECIDE"})


async def test_decide_bloquea_requerimiento_y_requiere_lo_habilita(client, rv_permisos, expediente):
    stubs = rv_permisos
    exp_id = expediente.id
    nodo = await _concepto_cargado(client, stubs, exp_id, "DECIDE")
    assert nodo["datos"]["accion"] == "DECIDE"
    arbol = await etapas(client, exp_id)
    assert MSG_CONCEPTO_DECIDE in arbol["requerimiento"]["motivos_bloqueo"]
    assert "asignarme" not in arbol["requerimiento"]["acciones_disponibles"]
    r = await post(client, f"/etapas/{exp_id}/requerimientos/etapa3/asignarme", esperado=400)
    assert r.json()["detail"] == MSG_CONCEPTO_DECIDE

    # El técnico lo corrige a «Requiere» → el requerimiento se habilita.
    await _editar(client, nodo["id"], version=nodo["version"], accion="REQUIERE")
    arbol = await etapas(client, exp_id)
    assert arbol["requerimiento"]["motivos_bloqueo"] == []
    await post(client, f"/etapas/{exp_id}/requerimientos/etapa3/asignarme")


# ─────────────────────────────────────────────────────── edición (técnico)

async def test_tecnico_edita_concepto_cargado(client, rv_permisos, expediente, db_session):
    stubs = rv_permisos
    exp_id = expediente.id
    nodo = await _concepto_cargado(client, stubs, exp_id, "REQUIERE")
    cid, version, pdf_anterior = nodo["id"], nodo["version"], nodo["datos"]["doc_concepto_tecnico_id"]

    d = (await client.get(f"/etapas/conceptos/{cid}", headers=headers(TECNICO))).json()["data"]
    assert "editar_concepto" in d["acciones_disponibles"] and d["datos"]["accion"] == "REQUIERE"

    # Solo el técnico encargado; con versión vigente; algo que cambiar.
    rv_permisos.permisos.dar(77, Permission.TECNICO)
    await _editar(client, cid, user=77, esperado=403, version=version, caudal_otorgado=2)
    await _editar(client, cid, user=ABOGADO, esperado=403, version=version, caudal_otorgado=2)
    await _editar(client, cid, esperado=409, version=version + 5, caudal_otorgado=2)
    await _editar(client, cid, esperado=400, version=version, caudal_otorgado=CAUDALES["caudal_otorgado"])

    nuevo_pdf = stubs.files.registrar()
    r = await _editar(client, cid, version=version, caudal_otorgado=2.5, num_usuarios=9,
                      fecha_aceptacion="2026-05-25", file_id=nuevo_pdf, accion="DECIDE")
    assert r["data"]["accion"] == "DECIDE" and r["data"]["doc_concepto_tecnico_id"] == nuevo_pdf
    c = await db_session.get(ConceptoTecnico, cid)
    await db_session.refresh(c)
    assert c.caudal_otorgado == 2.5 and c.num_usuarios == 9 and str(c.fecha_aceptacion) == "2026-05-25"
    assert nuevo_pdf in stubs.files.incrementados and pdf_anterior in stubs.files.decrementados
    # El técnico y la fecha de visita no se editan por aquí (se ignoran: no son del cuerpo).
    r = await client.put(f"/etapas/conceptos/{cid}", headers=headers(TECNICO), json={
        "version": c.version, "fecha_visita_tecnica": "2030-01-01", "tecnico_encargado_id": 77})
    assert r.status_code == 400  # nada editable en el cuerpo → "No hay cambios"


async def test_tecnico_no_edita_tras_la_decision(client, rv_permisos, con_decision):
    exp_id, _ = await con_decision()
    nodo = buscar_concepto(await etapas(client, exp_id), "etapa2")
    d = (await client.get(f"/etapas/conceptos/{nodo['id']}", headers=headers(TECNICO))).json()["data"]
    assert "editar_concepto" not in d["acciones_disponibles"]
    r = await _editar(client, nodo["id"], esperado=400, version=nodo["version"], caudal_otorgado=3)
    assert "decisión" in r["detail"]


async def test_tecnico_no_pasa_a_decide_con_requerimiento(client, rv_permisos, expediente):
    stubs = rv_permisos
    exp_id = expediente.id
    nodo = await _concepto_cargado(client, stubs, exp_id, "REQUIERE")
    await post(client, f"/etapas/{exp_id}/requerimientos/etapa3/asignarme")
    r = await _editar(client, nodo["id"], esperado=400, version=nodo["version"], accion="DECIDE")
    assert "super gestión" in r["detail"]
    # Otros datos sí.
    await _editar(client, nodo["id"], version=nodo["version"], num_usuarios=12)


# ─────────────────────────────────── super gestión: Decide elimina el requerimiento

async def test_super_pasa_a_decide_y_elimina_requerimiento(client, rv_permisos, expediente, db_session):
    stubs = rv_permisos
    exp_id = expediente.id
    nodo = await _concepto_cargado(client, stubs, exp_id, "REQUIERE")
    await _con_requerimiento(client, stubs, exp_id)
    req = await db_session.scalar(select(Requerimiento).where(Requerimiento.expediente_id == exp_id))
    req_id, acto_id, adicional_id = req.id, req.acto_admin_id, req.concepto_tecnico_id
    acto = await db_session.get(ActoAdministrativo, acto_id)
    adicional = await db_session.get(ConceptoTecnico, adicional_id)
    archivos = {acto.documento_acto_administrativo_id, req.doc_oficio_entrada_id, adicional.doc_concepto_tecnico_id}

    # Super ve la advertencia en el árbol; el abogado no.
    arbol = (await client.get(f"/etapas/{exp_id}", headers=headers(SUPER_G))).json()["data"]
    aviso = arbol["concepto"]["aviso_cambio_decide"]
    assert "ELIMINARÁ" in aviso and "concepto técnico adicional" in aviso and "respuesta del usuario" in aviso
    assert "aviso_cambio_decide" not in (await etapas(client, exp_id))["concepto"]

    url = f"/super-gestion/{exp_id}/conceptos/etapa2"
    version = arbol["concepto"]["version"]
    r = await post(client, url, SUPER_G, {"version": version, "accion": "DECIDE"}, esperado=409)
    assert r.json()["detail"] == aviso
    assert await db_session.scalar(select(Requerimiento.id).where(Requerimiento.expediente_id == exp_id))

    r = await post(client, url, SUPER_G, {"version": version, "accion": "DECIDE",
                                          "confirmar_eliminar_requerimiento": True})
    assert r.json()["data"]["requerimiento_eliminado"] is True
    db_session.expire_all()
    assert await db_session.scalar(select(Requerimiento).where(Requerimiento.expediente_id == exp_id)) is None
    assert await db_session.get(ActoAdministrativo, acto_id) is None
    assert await db_session.get(ConceptoTecnico, adicional_id) is None
    restantes = (await db_session.execute(select(DocumentoProceso.etapa_tipo, DocumentoProceso.etapa_ref_id).where(
        DocumentoProceso.expediente_id == exp_id))).all()
    assert ("requerimiento", req_id) not in restantes and ("concepto_tecnico", adicional_id) not in restantes
    assert archivos <= set(stubs.files.decrementados)
    arbol = await etapas(client, exp_id)
    assert arbol["concepto"]["datos"]["accion"] == "DECIDE" and arbol["requerimiento"]["existe"] is False
    assert MSG_CONCEPTO_DECIDE in arbol["requerimiento"]["motivos_bloqueo"]
    assert nodo["id"] == arbol["concepto"]["id"]


async def test_super_accion_solo_etapa2_y_obligatoria(client, rv_permisos, expediente):
    stubs = rv_permisos
    exp_id = expediente.id
    S = SUPER_G
    await post(client, f"/super-gestion/{exp_id}/admite", S, {
        "acto": {"clase_acto": "AUTO", "numerado": numerado(), "fecha_numerado": "2015-03-01",
                 "file_id": stubs.files.registrar()}, "tecnico_id": TECNICO, "fecha_visita_tecnica": "2015-03-05"})
    url = f"/super-gestion/{exp_id}/conceptos/etapa2"
    r = await post(client, url, S, {"fecha_aceptacion": "2015-03-10", **CAUDALES, "file_id": stubs.files.registrar()},
                   esperado=400)
    assert "acción" in r.json()["detail"]
    await post(client, url, S, {"fecha_aceptacion": "2015-03-10", **CAUDALES, "accion": "REQUIERE",
                                "file_id": stubs.files.registrar()})
    r = await post(client, f"/super-gestion/{exp_id}/conceptos/adicional", S, {"accion": "DECIDE"}, esperado=400)
    assert "etapa 2" in r.json()["detail"]


# ───────────────────────────────────────────────── migración de los existentes

async def test_migracion_completa_accion_de_conceptos_cargados(crear_expediente, db_session):
    from db.migrations import aplicar_migraciones
    from tests.conftest import engine

    async def concepto(exp_id, cargado=True):
        c = ConceptoTecnico(expediente_id=exp_id, tecnico_encargado_id=TECNICO,
                            doc_concepto_tecnico_id=1 if cargado else None)
        db_session.add(c)
        await db_session.flush()
        return c.id

    con_req, con_dec, sin_nada, sin_cargar = [await crear_expediente() for _ in range(4)]
    ids = {
        "req": await concepto(con_req.id), "dec": await concepto(con_dec.id),
        "nada": await concepto(sin_nada.id), "sin_cargar": await concepto(sin_cargar.id, cargado=False),
    }
    db_session.add(Requerimiento(expediente_id=con_req.id))
    db_session.add(Decision(expediente_id=con_dec.id))
    await db_session.commit()

    async with engine.begin() as conn:
        await aplicar_migraciones(conn)
    filas = dict((await db_session.execute(text(
        "SELECT id, accion FROM concepto_tecnico WHERE id = ANY(:ids)"), {"ids": list(ids.values())})).all())
    assert filas[ids["req"]] == "REQUIERE"
    assert filas[ids["dec"]] == "DECIDE"
    assert filas[ids["nada"]] == "REQUIERE"
    assert filas[ids["sin_cargar"]] is None

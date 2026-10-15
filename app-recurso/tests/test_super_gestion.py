"""Super gestión: cargue directo sin revisión, asignación ni validaciones §6."""
from sqlalchemy import select

from db.models import ActoAdmite, ConceptoTecnico, Decision, MemoriasCalculo, ReciboSatisfaccionObras
from db.models.documento_proceso import DocumentoProceso
from tests.fixtures_etapas import *  # noqa: F401,F403


def acto(stubs) -> dict:
    return {"clase_acto": "RES", "numerado": numerado(), "fecha_numerado": "2015-03-01", "file_id": stubs.files.registrar()}


async def test_solo_super(client, rv_permisos, expediente):
    await post(client, f"/super-gestion/{expediente.id}/admite", ABOGADO, {}, esperado=403)


async def test_cargue_historico_completo_salta_validaciones(client, rv_permisos, expediente, db_session):
    stubs = rv_permisos
    exp_id = expediente.id
    S = SUPER_G
    # Decisión y memorias SIN auto admite, sin constancia y sin requiere_memorias (V4, V7, V9 omitidas)
    r = await post(client, f"/super-gestion/{exp_id}/decision", S,
                   {"decision": "OTORGADA", "requiere_memorias": False, "acto": acto(stubs),
                    "fecha_ejecutoria": "2015-05-01"})
    assert r.json()["data"]["acto_id"]
    await post(client, f"/super-gestion/{exp_id}/memorias", S,
               {"radicado": "1995ER1", "fecha_radicado": "2015-06-01", "file_id": stubs.files.registrar()})
    # Constraints de BD sí: crear memorias otra vez es actualizar; crear recurso sin radicado → 400
    await post(client, f"/super-gestion/{exp_id}/recurso", S, {"resultado": "CONFIRMA"}, esperado=400)
    # Auto admite con técnico: nace el concepto con su proceso
    r = await post(client, f"/super-gestion/{exp_id}/admite", S, {
        "encargado_acto_id": ABOGADO, "acto": acto(stubs), "tecnico_id": TECNICO,
        "fecha_visita_tecnica": "2015-02-01", "doc_constancia_fijacion_aviso_id": stubs.files.registrar()})
    admite = await db_session.scalar(select(ActoAdmite).where(ActoAdmite.expediente_id == exp_id))
    assert admite.encargado_acto_id == ABOGADO and admite.acto_admin_id and admite.doc_constancia_fijacion_aviso_id
    concepto = await db_session.scalar(select(ConceptoTecnico).where(ConceptoTecnico.expediente_id == exp_id))
    proc = await db_session.scalar(select(DocumentoProceso).where(
        DocumentoProceso.etapa_tipo == "concepto_tecnico", DocumentoProceso.etapa_ref_id == concepto.id))
    assert proc.activo
    # Concepto cargado directo: cierra el proceso abierto
    await post(client, f"/super-gestion/{exp_id}/conceptos/etapa2", S,
               {"fecha_aceptacion": "2015-03-10", **CAUDALES, "file_id": stubs.files.registrar()})
    await db_session.refresh(proc)
    assert proc.activo is False
    # Acto otra vez → 409 (se corrige por /actos)
    await post(client, f"/super-gestion/{exp_id}/admite", S, {"acto": acto(stubs)}, esperado=409)
    # Concepto de memorias (técnico sin permiso de técnico: se omite V3) + requerimiento hijo + acto
    await post(client, f"/super-gestion/{exp_id}/conceptos/memorias", S,
               {"tecnico_encargado_id": 88, "fecha_aceptacion": "2015-07-01", "cumple": True,
                "file_id": stubs.files.registrar()})
    await post(client, f"/super-gestion/{exp_id}/requerimientos/memorias", S, {"acto": acto(stubs)})
    await post(client, f"/super-gestion/{exp_id}/memorias/subsanacion", S,
               {"radicado": "1995ER2", "fecha_radicado": "2015-08-01", "file_id": stubs.files.registrar()})
    await post(client, f"/super-gestion/{exp_id}/memorias", S, {"acto": acto(stubs), "encargado_acto_id": ABOGADO2})
    await post(client, f"/super-gestion/{exp_id}/obras", S, {"radicado": "1995ER3", "fecha_radicado": "2016-01-01",
                                                             "file_id": stubs.files.registrar(), "acto": acto(stubs)})
    await post(client, f"/super-gestion/{exp_id}/obras/nuevo-informe", S,
               {"radicado": "1995ER4", "fecha_radicado": "2016-02-01", "file_id": stubs.files.registrar()})
    # Concepto de obras sin padre → 400 (estructura); con padre ok
    await post(client, f"/super-gestion/{exp_id}/conceptos/adicional", S,
               {"tecnico_encargado_id": TECNICO}, esperado=400)
    m = await db_session.scalar(select(MemoriasCalculo).where(MemoriasCalculo.expediente_id == exp_id))
    o = await db_session.scalar(select(ReciboSatisfaccionObras).where(ReciboSatisfaccionObras.expediente_id == exp_id))
    assert m.acto_admin_id and m.requerimiento_id and m.subsanacion_id and m.encargado_acto_id == ABOGADO2
    assert o.acto_admin_id and o.nuevo_informe_usuario_id
    d = await db_session.scalar(select(Decision).where(Decision.expediente_id == exp_id))
    assert str(d.fecha_ejecutoria) == "2015-05-01"

    arbol = await etapas(client, exp_id, S)
    assert arbol["etapa_actual"] == "obras"
    assert "super_cargar" in arbol["admite"]["acciones_disponibles"]
    assert arbol["memorias"]["aprobacion"]["acto"]["tipo_acto"] == "APRUEBA_MEMORIAS"
    # La descarga (A) ve todos los documentos cargados
    docs = (await client.get(f"/expedientes/{exp_id}/documentos", headers=headers(S))).json()["data"]
    assert len(docs) >= 10


async def test_super_cierra_proceso_en_revision(client, rv_permisos, expediente, db_session):
    stubs = rv_permisos
    exp_id = expediente.id
    r = await post(client, f"/etapas/{exp_id}/admite/asignarme")
    pid = r.json()["data"]["proceso_id"]
    await post(client, f"/super-gestion/{exp_id}/admite", SUPER_G, {"acto": acto(stubs), "version": 99}, esperado=409)
    await post(client, f"/super-gestion/{exp_id}/admite", SUPER_G, {"acto": acto(stubs)})
    proc = await db_session.get(DocumentoProceso, pid)
    assert proc.activo is False and proc.estado == "finalizado"


async def test_super_tercero(client, rv_permisos, expediente, vincular, db_session):
    stubs = rv_permisos
    v = await vincular(expediente.id, TERCERO_P, tipo_vinculo=TipoVinculo.TERCERO_INTERVINIENTE)
    r = await post(client, f"/super-gestion/terceros/{v.id}/acto", SUPER_G, {"acto": acto(stubs)})
    await db_session.refresh(v)
    assert v.acto_admin_id == r.json()["data"]["acto_id"]


async def test_leer_etapas_sin_n_mas_1(client, rv_permisos, expediente, vincular):
    """El número de consultas no crece con la cantidad de actos/terceros."""
    from sqlalchemy import event

    from tests.conftest import engine

    stubs = rv_permisos
    exp_id = expediente.id

    async def contar() -> int:
        n = {"q": 0}

        def _cuenta(*_a, **_k):
            n["q"] += 1

        event.listen(engine.sync_engine, "before_cursor_execute", _cuenta)
        try:
            await etapas(client, exp_id, SUPER_G)
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", _cuenta)
        return n["q"]

    await post(client, f"/super-gestion/{exp_id}/admite", SUPER_G, {"acto": acto(stubs)})
    await post(client, f"/super-gestion/{exp_id}/decision", SUPER_G, {"decision": "NEGADA", "acto": acto(stubs)})

    async def tercero(pid):
        v = await vincular(exp_id, pid, tipo_vinculo=TipoVinculo.TERCERO_INTERVINIENTE)
        await post(client, f"/super-gestion/terceros/{v.id}/acto", SUPER_G, {"acto": acto(stubs)})

    await tercero(600)
    pocos = await contar()
    for pid in (601, 602, 603, 604):
        await tercero(pid)
    muchos = await contar()
    assert muchos == pocos, (pocos, muchos)


async def test_super_sin_encargado(client, rv_permisos, expediente, db_session):
    """Cargue histórico sin abogado: la etapa queda con encargado NULL, sin proceso
    de revisión, nadie puede "Asignarme" y solo super gestión gestiona el acto."""
    from db.models import Requerimiento

    stubs = rv_permisos
    exp_id = expediente.id
    S = SUPER_G
    await post(client, f"/super-gestion/{exp_id}/admite", S, {"acto": acto(stubs)})
    await post(client, f"/super-gestion/{exp_id}/requerimientos/etapa3", S, {})
    await post(client, f"/super-gestion/{exp_id}/decision", S, {"decision": "OTORGADA", "acto": acto(stubs)})
    await post(client, f"/super-gestion/{exp_id}/memorias", S,
               {"radicado": "1995ER1", "fecha_radicado": "2015-06-01", "file_id": stubs.files.registrar()})
    await post(client, f"/super-gestion/{exp_id}/requerimientos/memorias", S, {"acto": acto(stubs)})

    admite = await db_session.scalar(select(ActoAdmite).where(ActoAdmite.expediente_id == exp_id))
    decision = await db_session.scalar(select(Decision).where(Decision.expediente_id == exp_id))
    reqs = (await db_session.execute(select(Requerimiento))).scalars().all()
    assert admite.encargado_acto_id is None and decision.encargado_acto_id is None
    assert len(reqs) == 2 and all(r.encargado_acto_id is None for r in reqs)
    assert await db_session.scalar(select(DocumentoProceso.id)) is None  # sin encargado no hay proceso

    arbol = await etapas(client, exp_id, ABOGADO)
    for nodo in (arbol["admite"], arbol["requerimiento"], arbol["decision"], arbol["memorias"]["requerimiento"]):
        assert nodo["existe"] and nodo["encargado"] is None
        assert "asignarme" not in nodo["acciones_disponibles"], nodo["codigo"]
    assert arbol["admite"]["acto"]["acciones_disponibles"] == []
    # La API de asignación no crea una segunda fila.
    await post(client, f"/etapas/{exp_id}/admite/asignarme", ABOGADO, esperado=409)
    # El acto lo gestiona solo super gestión.
    acto_id = admite.acto_admin_id
    form = {"expediente_id": str(exp_id), "tipo_acto": "RES", "numerado": "0777", "fecha_numerado": "2015-03-02"}
    r = await client.put(f"/actos/administrativos/{acto_id}", data=form, headers=headers(ABOGADO))
    assert r.status_code == 403
    r = await client.put(f"/actos/administrativos/{acto_id}", data=form, headers=headers(S))
    assert r.status_code == 200, r.text
    assert "editar_acto" in (await etapas(client, exp_id, S))["admite"]["acto"]["acciones_disponibles"]
    # Mis documentos no se rompe con etapas sin encargado.
    r = await client.get("/mis-documentos", headers=headers(S))
    assert r.status_code == 200, r.text


async def test_super_con_encargado_elegido(client, rv_permisos, expediente, db_session):
    """Si se elige abogado y la etapa queda sin acto, nace su proceso a nombre del
    abogado; si luego se elige otro, el proceso se reasigna. Sin enviar el campo
    al actualizar, se conserva el encargado."""
    exp_id = expediente.id
    await post(client, f"/super-gestion/{exp_id}/decision", SUPER_G, {"encargado_acto_id": ABOGADO})
    d = await db_session.scalar(select(Decision).where(Decision.expediente_id == exp_id))
    assert d.encargado_acto_id == ABOGADO
    proc = await db_session.scalar(select(DocumentoProceso).where(
        DocumentoProceso.etapa_tipo == "decision", DocumentoProceso.etapa_ref_id == d.id))
    assert proc.activo and proc.creador_id == ABOGADO
    await post(client, f"/super-gestion/{exp_id}/decision", SUPER_G, {"encargado_acto_id": ABOGADO2})
    await db_session.refresh(proc)
    assert proc.creador_id == ABOGADO2
    await post(client, f"/super-gestion/{exp_id}/decision", SUPER_G, {"decision": "NEGADA"})
    await db_session.refresh(d)
    assert d.encargado_acto_id == ABOGADO2
    assert (await etapas(client, exp_id))["decision"]["encargado"]["id"] == ABOGADO2


async def test_listar_abogados(client, rv_permisos):
    r = await client.get("/etapas/abogados", headers=headers(SUPER_G))
    assert r.status_code == 200, r.text
    ids = {u["id"] for u in r.json()["data"]}
    assert {ABOGADO, ABOGADO2} <= ids and TECNICO not in ids
    assert (await client.get("/etapas/abogados", headers=headers(LECTOR))).status_code == 403

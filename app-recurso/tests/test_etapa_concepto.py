"""Etapa 2 · Concepto técnico y Etapa 3 · Requerimiento (+ concepto adicional)."""
from datetime import date

from sqlalchemy import select

from core.permission import Permission
from db.models import ConceptoTecnico, Requerimiento
from tests.fixtures_etapas import *  # noqa: F401,F403


async def test_concepto_etapa2(client, rv_permisos, expediente, db_session):
    stubs = rv_permisos
    exp_id = expediente.id
    # Sin auto admite no hay concepto (V5) ni selección manual
    await post(client, f"/etapas/{exp_id}/conceptos/etapa2/tecnico", json={"tecnico_id": TECNICO}, esperado=400)
    await admite_firmado(client, stubs, exp_id)
    rv_permisos.permisos.dar(TECNICO, Permission.CONSULT)  # para ver el árbol con sus acciones
    arbol = await etapas(client, exp_id, TECNICO)
    nodo = arbol["concepto"]
    assert nodo["existe"] and "subir_version" in nodo["acciones_disponibles"]
    await aprobar_para_firma(client, nodo["proceso"]["proceso_id"], TECNICO)
    url = f"/etapas/{exp_id}/conceptos/etapa2/version-final"
    body = {"file_id": stubs.files.registrar(), "fecha_aceptacion": "2026-05-20", **CAUDALES}
    # Solo el técnico seleccionado (V3): un abogado sin recurso_tecnico → 403; otro técnico → 403
    await post(client, url, ABOGADO, body, esperado=403)
    rv_permisos.permisos.dar(77, Permission.TECNICO)
    await post(client, url, 77, body, esperado=403)
    # Faltan caudales → 400
    await post(client, url, TECNICO, {"file_id": body["file_id"], "fecha_aceptacion": "2026-05-20"}, esperado=400)
    data = (await post(client, url, TECNICO, body)).json()["data"]
    assert data["fecha_aceptacion"] == "2026-05-20"
    c = await db_session.scalar(select(ConceptoTecnico).where(ConceptoTecnico.expediente_id == exp_id))
    assert c.caudal_otorgado == 1.2 and c.num_usuarios == 3 and c.doc_concepto_tecnico_id == body["file_id"]
    await post(client, url, TECNICO, body, esperado=409)
    arbol = await etapas(client, exp_id)
    assert arbol["concepto"]["proceso"]["estado_proceso"]["codigo"] == "aprobado"
    # V6 ya se cumple: el requerimiento queda habilitado
    assert arbol["requerimiento"]["habilitada"] and "asignarme" in arbol["requerimiento"]["acciones_disponibles"]


async def test_requerimiento_etapa3_completo(client, rv_permisos, expediente, db_session):
    stubs = rv_permisos
    exp_id = expediente.id
    await admite_firmado(client, stubs, exp_id)
    # V6: sin concepto cargado → 400
    await post(client, f"/etapas/{exp_id}/requerimientos/etapa3/asignarme", esperado=400)
    arbol = await etapas(client, exp_id)
    assert any("V6" in m for m in arbol["requerimiento"]["motivos_bloqueo"])
    await concepto_firmado(client, stubs, exp_id, "etapa2", **CAUDALES)
    data = await acto_completo(client, stubs, f"/etapas/{exp_id}/requerimientos/etapa3")
    assert data["acto_id"]
    # Concepto adicional antes de la respuesta → 400
    await post(client, f"/etapas/{exp_id}/conceptos/adicional/tecnico", json={"tecnico_id": TECNICO}, esperado=400)
    # Respuesta del usuario (solo el encargado, V2)
    arbol = await etapas(client, exp_id)
    req = arbol["requerimiento"]
    assert "registrar_respuesta" in req["acciones_disponibles"]
    respuesta = {"version": req["version"], "radicado_oficio_entrada": "2026ER777",
                 "fecha_oficio_entrada": "2026-06-01", "doc_oficio_entrada_id": stubs.files.registrar()}
    await put(client, f"/etapas/{exp_id}/requerimientos/etapa3/respuesta", ABOGADO2, respuesta, esperado=403)
    r = await put(client, f"/etapas/{exp_id}/requerimientos/etapa3/respuesta", json=respuesta)
    assert r.json()["data"]["version"] == req["version"] + 1
    await put(client, f"/etapas/{exp_id}/requerimientos/etapa3/respuesta", json=respuesta, esperado=409)
    # Concepto adicional: solo el encargado del requerimiento selecciona; técnico con permiso
    await post(client, f"/etapas/{exp_id}/conceptos/adicional/tecnico", ABOGADO2, {"tecnico_id": TECNICO}, esperado=403)
    await post(client, f"/etapas/{exp_id}/conceptos/adicional/tecnico", json={"tecnico_id": ABOGADO2}, esperado=400)
    await post(client, f"/etapas/{exp_id}/conceptos/adicional/tecnico", json={"tecnico_id": TECNICO})
    await post(client, f"/etapas/{exp_id}/conceptos/adicional/tecnico", json={"tecnico_id": TECNICO}, esperado=409)
    await concepto_firmado(client, stubs, exp_id, "adicional")
    req_db = await db_session.scalar(select(Requerimiento).where(Requerimiento.expediente_id == exp_id))
    adicional = await db_session.get(ConceptoTecnico, req_db.concepto_tecnico_id)
    assert adicional.expediente_id is None and adicional.doc_concepto_tecnico_id
    arbol = await etapas(client, exp_id)
    assert arbol["etapa_actual"] == "requerimiento"
    assert arbol["requerimiento"]["datos"]["radicado_oficio_entrada"] == "2026ER777"
    assert arbol["requerimiento"]["concepto_adicional"]["datos"]["fecha_aceptacion"] == "2026-05-20"
    assert arbol["requerimiento"]["acto"]["tipo_acto"] == "REQUERIMIENTO"


async def test_tipo_concepto_desconocido(client, rv_permisos, expediente):
    await post(client, f"/etapas/{expediente.id}/conceptos/otro/tecnico", json={"tecnico_id": TECNICO}, esperado=404)
    await post(client, f"/etapas/{expediente.id}/requerimientos/otro/asignarme", esperado=404)


async def test_tecnico_sin_gestionar_desde_mis_informes(client, rv_permisos, expediente, db_session):
    """El técnico (solo recurso_tecnico) ve y carga SU concepto por id (V3 manda sobre V1)."""
    stubs = rv_permisos
    exp_id = expediente.id
    await admite_firmado(client, stubs, exp_id)
    r = await client.get("/mis-documentos", headers=headers(TECNICO))
    fila = r.json()["data"]["documentos"][0]
    assert fila["etapa_padre"] == "concepto_tecnico" and fila["sub_proceso"] == "concepto_etapa2"
    concepto_id = fila["etapa_ref_id"]
    # Sin lectura de expedientes, pero sí su concepto
    assert (await client.get(f"/etapas/{exp_id}", headers=headers(TECNICO))).status_code == 403
    r = await client.get(f"/etapas/conceptos/{concepto_id}", headers=headers(TECNICO))
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["tipo"] == "etapa2" and d["expediente"]["id"] == exp_id
    assert d["acciones_disponibles"] == ["subir_version"]
    assert "caudal_fuente" in d["campos"]["obligatorios"]
    # Otro técnico no lo ve
    rv_permisos.permisos.dar(77, Permission.TECNICO)
    assert (await client.get(f"/etapas/conceptos/{concepto_id}", headers=headers(77))).status_code == 403
    await aprobar_para_firma(client, fila["proceso_id"], TECNICO)
    d = (await client.get(f"/etapas/conceptos/{concepto_id}", headers=headers(TECNICO))).json()["data"]
    assert d["acciones_disponibles"] == ["cargar_version_final"]
    body = {"file_id": stubs.files.registrar(), "fecha_aceptacion": "2026-05-20", **CAUDALES}
    await post(client, f"/etapas/conceptos/{concepto_id}/version-final", 77, body, esperado=403)
    data = (await post(client, f"/etapas/conceptos/{concepto_id}/version-final", TECNICO, body)).json()["data"]
    assert data["tipo"] == "etapa2" and data["doc_concepto_tecnico_id"] == body["file_id"]
    # El detalle del proceso también trae el contexto de etapa
    det = (await client.get(f"/revision-documentos/{fila['proceso_id']}", headers=headers(TECNICO))).json()
    assert det["etapa_padre"] == "concepto_tecnico"


async def test_etapa_padre_de_requerimientos(db_session, crear_expediente):
    from db.models import MemoriasCalculo
    from db.models.documento_proceso import DocumentoProceso
    from services.etapas import etapas_padre

    exp = await crear_expediente()
    r3 = Requerimiento(expediente_id=exp.id, encargado_acto_id=ABOGADO)
    rm = Requerimiento(expediente_id=None, encargado_acto_id=ABOGADO)
    db_session.add_all([r3, rm])
    await db_session.flush()
    db_session.add(MemoriasCalculo(expediente_id=exp.id, radicado="R1", fecha_radicado=date(2026, 1, 1),
                                   doc_planos_id=1, requerimiento_id=rm.id))
    await db_session.flush()
    procesos = [
        DocumentoProceso(id=1, tipo_documento="REQUERIMIENTO", etapa_tipo="requerimiento", etapa_ref_id=r3.id),
        DocumentoProceso(id=2, tipo_documento="REQUERIMIENTO", etapa_tipo="requerimiento", etapa_ref_id=rm.id),
        DocumentoProceso(id=3, tipo_documento="RECURSO", etapa_tipo="recurso_reposicion", etapa_ref_id=1),
        DocumentoProceso(id=4, tipo_documento="CONCEPTO_ADICIONAL", etapa_tipo="concepto_tecnico", etapa_ref_id=1),
    ]
    ctx = await etapas_padre(db_session, procesos)
    assert ctx[1]["etapa_padre"] == "requerimiento" and ctx[1]["sub_proceso"] == "requerimiento_etapa3"
    assert ctx[2]["etapa_padre"] == "memorias_calculo" and ctx[2]["sub_proceso"] == "requerimiento_memorias"
    assert ctx[3]["etapa_padre"] == "decision" and ctx[3]["sub_proceso"] == "recurso"
    assert ctx[4]["etapa_padre"] == "requerimiento"
    await db_session.rollback()


# ─── 5.3: una sola definición de los campos de cada concepto ────────────────

def test_definicion_campos_concepto_forma():
    from services.etapas import CAMPOS_CONCEPTO, TIPOS_CONCEPTO, definicion_campos_concepto

    assert set(CAMPOS_CONCEPTO) == set(TIPOS_CONCEPTO)
    d = definicion_campos_concepto("etapa2")
    assert d["obligatorios"] == ["file_id", "fecha_aceptacion", "caudal_fuente", "caudal_disponible",
                                 "caudal_otorgado", "num_usuarios"]
    assert d["opcionales"] == []
    assert [c["campo"] for c in d["campos"]] == ["fecha_aceptacion", "caudal_fuente", "caudal_disponible",
                                                 "caudal_otorgado", "num_usuarios"]
    assert d["campos"][0] == {"campo": "fecha_aceptacion", "tipo": "fecha",
                              "etiqueta": "Fecha del concepto (firma)", "obligatorio": True}
    assert {c["campo"]: c["tipo"] for c in d["campos"]}["num_usuarios"] == "entero"
    adicional = definicion_campos_concepto("adicional")
    assert adicional["obligatorios"] == ["file_id", "fecha_aceptacion"]
    assert all(not c["obligatorio"] for c in adicional["campos"] if c["campo"] != "fecha_aceptacion")
    obras = definicion_campos_concepto("obras_segundo")
    assert {c["campo"]: (c["tipo"], c["obligatorio"]) for c in obras["campos"]} == {
        "fecha_aceptacion": ("fecha", True), "cumple": ("si_no", True), "fecha_visita_tecnica": ("fecha", True)}
    for tipo in TIPOS_CONCEPTO:
        for c in definicion_campos_concepto(tipo)["campos"]:
            assert set(c) == {"campo", "tipo", "etiqueta", "obligatorio"}
            assert c["tipo"] in ("fecha", "decimal", "entero", "si_no") and c["etiqueta"]


async def test_arbol_y_concepto_por_id_traen_la_misma_definicion(client, rv_permisos, expediente):
    from services.etapas import definicion_campos_concepto

    stubs = rv_permisos
    exp_id = expediente.id
    arbol = await etapas(client, exp_id)
    # Aunque el concepto no exista (cargue directo), el nodo trae su definición.
    assert arbol["concepto"]["existe"] is False
    assert arbol["concepto"]["campos"] == definicion_campos_concepto("etapa2")
    assert arbol["memorias"]["concepto"]["campos"] == definicion_campos_concepto("memorias")
    await admite_firmado(client, stubs, exp_id)
    arbol = await etapas(client, exp_id)
    cid = arbol["concepto"]["id"]
    r = await client.get(f"/etapas/conceptos/{cid}", headers=headers(TECNICO))
    assert r.status_code == 200, r.text
    assert r.json()["data"]["campos"] == arbol["concepto"]["campos"]

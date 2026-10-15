"""Tercero interviniente (transversal) y documentos anexos."""
from sqlalchemy import select

from db.models import DocumentoAnexo, ExpedienteInvolucrado
from tests.fixtures_etapas import *  # noqa: F401,F403


async def test_tercero_vincular_reconocer(client, rv_permisos, expediente, db_session):
    stubs = rv_permisos
    exp_id = expediente.id
    stubs.involved.registrar(TERCERO_P, nombre="Opositor")
    stubs.involved.registrar(600, tipo_documento="NIT")
    # V14 también para terceros
    await post(client, "/terceros", json={"expediente_id": exp_id, "involucrado_id": 600}, esperado=400)
    await post(client, "/terceros", LECTOR, {"expediente_id": exp_id, "involucrado_id": TERCERO_P}, esperado=403)
    r = await post(client, "/terceros", json={"expediente_id": exp_id, "involucrado_id": TERCERO_P}, esperado=201)
    vid = r.json()["data"]["id"]
    assert r.json()["data"]["tipo_vinculo"] == "TERCERO_INTERVINIENTE"
    await post(client, "/terceros", json={"expediente_id": exp_id, "involucrado_id": TERCERO_P}, esperado=409)
    # El solicitante no se gestiona por /terceros
    sol = await db_session.scalar(select(ExpedienteInvolucrado.id).where(
        ExpedienteInvolucrado.involucrado_id == SOLICITANTE))
    await post(client, f"/terceros/{sol}/asignarme", esperado=400)

    arbol = await etapas(client, exp_id)
    t = arbol["terceros"][0]
    assert t["involucrado"]["nombre"] == "Opositor"
    assert {"asignarme", "desvincular", "editar_representante"} <= set(t["acciones_disponibles"])
    # Asignación (encargado = creador del proceso) + 409 al segundo
    r = await post(client, f"/terceros/{vid}/asignarme")
    await post(client, f"/terceros/{vid}/asignarme", ABOGADO2, esperado=409)
    # Con proceso en proyección no se desvincula
    r2 = await client.delete(f"/terceros/{vid}?version=1", headers=headers(ABOGADO))
    assert r2.status_code == 409
    await aprobar_para_firma(client, r.json()["data"]["proceso_id"], ABOGADO)
    await post(client, f"/terceros/{vid}/version-final", ABOGADO2, acto_body(stubs), esperado=403)
    data = (await post(client, f"/terceros/{vid}/version-final", json=acto_body(stubs))).json()["data"]
    vinculo = await db_session.get(ExpedienteInvolucrado, vid)
    assert vinculo.acto_admin_id == data["acto_id"]
    lista = (await client.get(f"/terceros/expediente/{exp_id}", headers=headers(LECTOR))).json()["data"]
    assert lista[0]["acto"]["tipo_acto"] == "RECONOCE_TERCERO" and lista[0]["acciones_disponibles"] == []
    arbol = await etapas(client, exp_id)
    # Regla del área (14/10/2026): el acto que reconoce al tercero solo se comunica.
    acciones_acto = arbol["terceros"][0]["acto"]["acciones_disponibles"]
    assert "crear_comunicacion" in acciones_acto and "crear_notificacion" not in acciones_acto
    assert arbol["terceros"][0]["encargado"]["id"] == ABOGADO
    # Sin documentos anexos para el tercero.
    assert "gestionar_anexos" not in arbol["terceros"][0]["acciones_disponibles"]
    assert arbol["terceros"][0]["anexos"] == []


async def test_tercero_desvincular(client, rv_permisos, expediente):
    exp_id = expediente.id
    rv_permisos.involved.registrar(TERCERO_P)
    r = await post(client, "/terceros", json={"expediente_id": exp_id, "involucrado_id": TERCERO_P}, esperado=201)
    vid = r.json()["data"]["id"]
    r = await client.delete(f"/terceros/{vid}?version=1", headers=headers(ABOGADO))
    assert r.status_code == 200, r.text
    assert (await etapas(client, exp_id))["terceros"] == []


async def test_documentos_anexos(client, rv_permisos, expediente, db_session):
    stubs = rv_permisos
    exp_id = expediente.id
    await admite_firmado(client, stubs, exp_id)
    arbol = await etapas(client, exp_id)
    cid = arbol["concepto"]["id"]
    assert "gestionar_anexos" in arbol["concepto"]["acciones_disponibles"]
    base = {"expediente_id": exp_id, "etapa_tipo": "concepto_tecnico", "etapa_ref_id": cid, "nombre": "Fotos visita"}
    await post(client, "/documentos-anexos", LECTOR, {**base, "documento_anexo_id": stubs.files.registrar()},
               esperado=403)
    await post(client, "/documentos-anexos", json={**base, "etapa_tipo": "otra", "documento_anexo_id": 1}, esperado=400)
    # El tercero interviniente no lleva anexos.
    await post(client, "/documentos-anexos",
               json={**base, "etapa_tipo": "expediente_involucrado", "documento_anexo_id": 1}, esperado=400)
    await post(client, "/documentos-anexos", json={**base, "etapa_ref_id": 9999,
                                                   "documento_anexo_id": stubs.files.registrar()}, esperado=404)
    otro = await crear_expediente_vacio(client, db_session)
    await post(client, "/documentos-anexos", json={**base, "expediente_id": otro,
                                                   "documento_anexo_id": stubs.files.registrar()}, esperado=404)
    fid = stubs.files.registrar()
    r = await post(client, "/documentos-anexos", json={**base, "documento_anexo_id": fid}, esperado=201)
    aid = r.json()["data"]["id"]
    assert fid in stubs.files.incrementados
    r = await client.get(f"/documentos-anexos?expediente_id={exp_id}&etapa_tipo=concepto_tecnico&etapa_ref_id={cid}",
                         headers=headers(LECTOR))
    assert [a["nombre"] for a in r.json()["data"]] == ["Fotos visita"]
    assert (await etapas(client, exp_id))["concepto"]["anexos"][0]["documento_anexo_id"] == fid
    await put(client, f"/documentos-anexos/{aid}", json={"expediente_id": exp_id, "nombre": "Fotos"})
    # La descarga del expediente (A) lo incluye
    docs = (await client.get(f"/expedientes/{exp_id}/documentos", headers=headers(LECTOR))).json()["data"]
    assert fid in [d["file_id"] for d in docs]
    r = await client.delete(f"/documentos-anexos/{aid}?expediente_id={exp_id}", headers=headers(ABOGADO))
    assert r.status_code == 200 and fid in stubs.files.decrementados
    assert await db_session.scalar(select(DocumentoAnexo.id)) is None


async def test_editar_anexo_reemplaza_pdf(client, rv_permisos, expediente, db_session):
    """PUT /documentos-anexos/{id}: nombre y, opcional, otro PDF (+1 nuevo, −1 anterior tras el commit)."""
    stubs = rv_permisos
    exp_id = expediente.id
    await admite_firmado(client, stubs, exp_id)
    cid = (await etapas(client, exp_id))["concepto"]["id"]
    fid = stubs.files.registrar()
    r = await post(client, "/documentos-anexos", json={"expediente_id": exp_id, "etapa_tipo": "concepto_tecnico",
                                                       "etapa_ref_id": cid, "nombre": "Fotos",
                                                       "documento_anexo_id": fid}, esperado=201)
    aid = r.json()["data"]["id"]
    # Solo nombre: no toca usos.
    stubs.files.incrementados.clear()
    await put(client, f"/documentos-anexos/{aid}", json={"expediente_id": exp_id, "nombre": "Fotos 2"})
    assert stubs.files.incrementados == [] and fid not in stubs.files.decrementados
    # El mismo PDF: tampoco.
    await put(client, f"/documentos-anexos/{aid}", json={"expediente_id": exp_id, "nombre": "Fotos 2",
                                                         "documento_anexo_id": fid})
    assert stubs.files.incrementados == [] and fid not in stubs.files.decrementados
    # Otro archivo que no es PDF → 400, sin cambios.
    docx = stubs.files.registrar(content=b"PK..", content_type="application/msword")
    await put(client, f"/documentos-anexos/{aid}", json={"expediente_id": exp_id, "nombre": "X",
                                                         "documento_anexo_id": docx}, esperado=400)
    # Reemplazo válido.
    nuevo = stubs.files.registrar()
    r = await put(client, f"/documentos-anexos/{aid}", json={"expediente_id": exp_id, "nombre": "Fotos visita",
                                                             "documento_anexo_id": nuevo})
    data = r.json()["data"]
    assert data["documento_anexo_id"] == nuevo and data["nombre"] == "Fotos visita"
    assert nuevo in stubs.files.incrementados and fid in stubs.files.decrementados
    anexo = await db_session.get(DocumentoAnexo, aid)
    await db_session.refresh(anexo)
    assert anexo.documento_anexo_id == nuevo
    # Lector no edita.
    await put(client, f"/documentos-anexos/{aid}", LECTOR, json={"expediente_id": exp_id, "nombre": "Y"},
              esperado=403)


async def test_anexos_propios_de_informes_y_subsanacion(client, rv_permisos, expediente):
    """Los nodos informe / nuevo informe (obras) y subsanación (memorias) tienen sus
    propios anexos y ofrecen gestionarlos."""
    stubs = rv_permisos
    exp_id = expediente.id
    radicado = lambda r: {"radicado": r, "fecha_radicado": "2016-01-01", "file_id": stubs.files.registrar()}  # noqa: E731
    await post(client, f"/super-gestion/{exp_id}/memorias", SUPER_G, radicado("1995ER1"))
    await post(client, f"/super-gestion/{exp_id}/memorias/subsanacion", SUPER_G, radicado("1995ER2"))
    await post(client, f"/super-gestion/{exp_id}/obras", SUPER_G, radicado("1995ER3"))
    await post(client, f"/super-gestion/{exp_id}/obras/nuevo-informe", SUPER_G, radicado("1995ER4"))
    arbol = await etapas(client, exp_id)
    nodos = {
        "informe_usuario": arbol["obras"]["informe"],
        "nuevo_informe": arbol["obras"]["nuevo_informe"],
        "subsanacion": arbol["memorias"]["subsanacion"],
    }
    for nombre, nodo in nodos.items():
        assert "gestionar_anexos" in nodo["acciones_disponibles"], nombre
        await post(client, "/documentos-anexos", json={
            "expediente_id": exp_id, "etapa_tipo": nodo["etapa_tipo"], "etapa_ref_id": nodo["id"],
            "nombre": f"Anexo {nombre}", "documento_anexo_id": stubs.files.registrar()}, esperado=201)
    arbol = await etapas(client, exp_id)
    assert [a["nombre"] for a in arbol["obras"]["informe"]["anexos"]] == ["Anexo informe_usuario"]
    assert [a["nombre"] for a in arbol["obras"]["nuevo_informe"]["anexos"]] == ["Anexo nuevo_informe"]
    assert [a["nombre"] for a in arbol["memorias"]["subsanacion"]["anexos"]] == ["Anexo subsanacion"]
    # La fila de obras no mezcla los anexos de su informe.
    assert arbol["obras"]["anexos"] == []
    assert "gestionar_anexos" not in (await etapas(client, exp_id, LECTOR))["obras"]["informe"]["acciones_disponibles"]


async def crear_expediente_vacio(client, db_session) -> int:
    from db.models import Expediente

    exp = await db_session.scalar(select(Expediente))
    return exp.id + 1000  # expediente inexistente → 404

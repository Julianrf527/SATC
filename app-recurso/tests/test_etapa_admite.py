"""Etapa 1 · Auto que admite + árbol de etapas (leer_etapas)."""
from sqlalchemy import select

from db.models import ActoAdmite, ConceptoTecnico
from db.models.documento_proceso import DocumentoProceso
from tests.fixtures_etapas import *  # noqa: F401,F403


async def test_arbol_inicial(client, expediente):
    arbol = await etapas(client, expediente.id)
    assert arbol["etapa_actual"] is None
    assert arbol["acciones_disponibles"] == ["vincular_tercero"]
    assert arbol["admite"]["existe"] is False and arbol["admite"]["habilitada"] is True
    assert arbol["admite"]["acciones_disponibles"] == ["asignarme"]
    # V4 bloquea todo lo demás
    assert arbol["requerimiento"]["habilitada"] is False
    assert any("V4" in m for m in arbol["requerimiento"]["motivos_bloqueo"])
    assert any("V4" in m for m in arbol["decision"]["motivos_bloqueo"])
    assert arbol["concepto"]["acciones_disponibles"] == []
    # El consultor ve el árbol sin acciones
    r = await client.get(f"/expedientes/{expediente.id}", headers=headers(LECTOR))
    etapas_exp = r.json()["data"]["etapas"]
    assert etapas_exp["admite"]["acciones_disponibles"] == [] and etapas_exp["acciones_disponibles"] == []


async def test_asignarme_permisos_y_unicidad(client, expediente):
    r = await client.post(f"/etapas/{expediente.id}/admite/asignarme", headers=headers(LECTOR))
    assert r.status_code == 403
    r = await post(client, f"/etapas/{expediente.id}/admite/asignarme")
    assert r.json()["data"]["encargado_acto_id"] == ABOGADO and r.json()["data"]["proceso_id"]
    await post(client, f"/etapas/{expediente.id}/admite/asignarme", ABOGADO2, esperado=409)
    arbol = await etapas(client, expediente.id, ABOGADO)
    assert arbol["etapa_actual"] == "admite"
    assert arbol["admite"]["encargado"] == {"id": ABOGADO, "nombre": f"Usuario {ABOGADO}"}
    assert "subir_version" in arbol["admite"]["acciones_disponibles"]
    assert arbol["admite"]["proceso"]["estado_proceso"]["codigo"] == "pendiente_carga"
    otro = await etapas(client, expediente.id, ABOGADO2)
    assert "subir_version" not in otro["admite"]["acciones_disponibles"]


async def test_version_final_admite_nace_concepto(client, rv_permisos, expediente, db_session):
    stubs = rv_permisos
    r = await post(client, f"/etapas/{expediente.id}/admite/asignarme")
    pid = r.json()["data"]["proceso_id"]
    # Antes de aprobado para firma → 409 (B)
    await post(client, f"/etapas/{expediente.id}/admite/version-final", json=acto_body(
        stubs, tecnico_id=TECNICO, fecha_visita_tecnica="2026-05-02"), esperado=409)
    await aprobar_para_firma(client, pid, ABOGADO)
    arbol = await etapas(client, expediente.id)
    assert "cargar_version_final" in arbol["admite"]["acciones_disponibles"]
    # V2: otro abogado no puede cargar
    await post(client, f"/etapas/{expediente.id}/admite/version-final", ABOGADO2, acto_body(
        stubs, tecnico_id=TECNICO, fecha_visita_tecnica="2026-05-02"), esperado=403)
    # V3: el técnico debe tener recurso_tecnico
    await post(client, f"/etapas/{expediente.id}/admite/version-final", json=acto_body(
        stubs, tecnico_id=ABOGADO2, fecha_visita_tecnica="2026-05-02"), esperado=400)
    # V5: técnico y fecha de visita obligatorios
    await post(client, f"/etapas/{expediente.id}/admite/version-final", json=acto_body(stubs), esperado=422)
    data = (await post(client, f"/etapas/{expediente.id}/admite/version-final", json=acto_body(
        stubs, tecnico_id=TECNICO, fecha_visita_tecnica="2026-05-02"))).json()["data"]
    assert data["acto_id"] and data["concepto_tecnico_id"]

    concepto = await db_session.scalar(select(ConceptoTecnico).where(ConceptoTecnico.expediente_id == expediente.id))
    assert concepto.tecnico_encargado_id == TECNICO and str(concepto.fecha_visita_tecnica) == "2026-05-02"
    proc = await db_session.scalar(select(DocumentoProceso).where(
        DocumentoProceso.etapa_tipo == "concepto_tecnico", DocumentoProceso.etapa_ref_id == concepto.id))
    assert proc.creador_id == TECNICO and proc.tipo_documento == "CONCEPTO_ETAPA2"

    arbol = await etapas(client, expediente.id)
    assert arbol["etapa_actual"] == "concepto"
    assert arbol["admite"]["acto"]["tipo_acto"] == "AUTO_ADMITE"
    assert "crear_comunicacion" in arbol["admite"]["acto"]["acciones_disponibles"]
    assert "cargar_constancia_fijacion" in arbol["admite"]["acciones_disponibles"]
    assert arbol["concepto"]["tecnico"]["id"] == TECNICO
    # Segunda carga → 409
    await post(client, f"/etapas/{expediente.id}/admite/version-final", json=acto_body(
        stubs, tecnico_id=TECNICO, fecha_visita_tecnica="2026-05-02"), esperado=409)
    # Aviso al técnico
    assert any("Concepto técnico" in m for m in stubs.users.para(TECNICO))


async def test_documentos_admite(client, rv_permisos, expediente, db_session):
    stubs = rv_permisos
    await post(client, f"/etapas/{expediente.id}/admite/asignarme")
    arbol = await etapas(client, expediente.id)
    # Antes del acto: no se pueden cargar
    await put(client, f"/etapas/{expediente.id}/admite/documentos", json={
        "version": arbol["admite"]["version"], "doc_oficio_alcaldia_id": stubs.files.registrar()}, esperado=400)
    await post(client, f"/etapas/{expediente.id}/admite/version-final", esperado=None)  # sin body → 422
    proceso = arbol["admite"]["proceso"]["proceso_id"]
    await aprobar_para_firma(client, proceso, ABOGADO)
    await post(client, f"/etapas/{expediente.id}/admite/version-final", json=acto_body(
        stubs, tecnico_id=TECNICO, fecha_visita_tecnica="2026-05-02"))
    version = (await etapas(client, expediente.id))["admite"]["version"]
    oficio = stubs.files.registrar()
    # No PDF → 400
    docx = stubs.files.registrar(content=b"PK", content_type="application/msword")
    await put(client, f"/etapas/{expediente.id}/admite/documentos", json={
        "version": version, "doc_oficio_alcaldia_id": docx}, esperado=400)
    # Otro abogado → 403 (V2)
    await put(client, f"/etapas/{expediente.id}/admite/documentos", ABOGADO2, json={
        "version": version, "doc_oficio_alcaldia_id": oficio}, esperado=403)
    r = await put(client, f"/etapas/{expediente.id}/admite/documentos", json={
        "version": version, "doc_oficio_alcaldia_id": oficio})
    nueva = r.json()["data"]["version"]
    assert nueva == version + 1 and oficio in stubs.files.incrementados
    # versión vieja → 409
    await put(client, f"/etapas/{expediente.id}/admite/documentos", json={
        "version": version, "doc_fijacion_aviso_id": stubs.files.registrar()}, esperado=409)
    # Reemplazo: decrementa el anterior
    otro = stubs.files.registrar()
    await put(client, f"/etapas/{expediente.id}/admite/documentos", json={
        "version": nueva, "doc_oficio_alcaldia_id": otro})
    assert oficio in stubs.files.decrementados
    fila = await db_session.scalar(select(ActoAdmite).where(ActoAdmite.expediente_id == expediente.id))
    assert fila.doc_oficio_alcaldia_id == otro


async def test_lista_tecnicos(client, rv_permisos):
    r = await client.get("/etapas/tecnicos", headers=headers(ABOGADO))
    assert r.status_code == 200
    assert [t["id"] for t in r.json()["data"]] == [TECNICO]
    r = await client.get("/etapas/tecnicos", headers=headers(TECNICO))
    assert r.status_code == 403

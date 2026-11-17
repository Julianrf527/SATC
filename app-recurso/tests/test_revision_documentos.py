"""Motor de revisión por pasos/permisos (/revision-documentos, DISENO §4)."""
import asyncio

import pytest
from sqlalchemy import select

from db.models.documento_proceso import DocumentoProceso, DocumentoProcesoRevision
from satc_shared.review_process import ArchivoRef
from tests.fixtures_revision import *  # noqa: F401,F403


async def _proceso(db_session, pid) -> DocumentoProceso:
    db_session.expire_all()
    return await db_session.scalar(select(DocumentoProceso).where(DocumentoProceso.id == pid))


async def test_crear_proceso_queda_pendiente_carga(client, rv_proceso, stubs):
    _, _, p = await rv_proceso("AUTO_ADMITE")
    d = await detalle(client, p.id, ABOGADO)
    assert d["estado"]["codigo"] == "pendiente_carga"
    assert d["tipo_documento"] == "AUTO_ADMITE" and d["etapa_tipo"] == "acto_admite"
    assert d["paso_actual"] == 1 and d["total_pasos"] == 2
    assert d["subida_version"]["permitida"] is True
    assert d["acciones_disponibles"] == []
    # El revisor ve el documento pero aún no puede actuar.
    assert codigos(await detalle(client, p.id, JURIDICO)) == []


async def test_cadena_decision_dos_pasos_con_paso_paralelo(client, rv_proceso, db_session, stubs):
    _, _, p = await rv_proceso("DECISION")
    assert (await subir(client, p.id)).status_code == 200
    # Notifica a los del paso 1.
    assert any("pendiente de tu revisión" in m for m in stubs.users.para(JURIDICO))

    # Paso 2 aún no: el líder del proyecto ve acciones bloqueadas.
    d = await detalle(client, p.id, PROYECTO)
    assert codigos(d) == ["aprobado", "devuelto"]
    assert all(a["bloqueada"] and "no es tu turno" in a["bloqueada"] for a in d["acciones_disponibles"])
    r = await revisar(client, p.id, "aprobado", PROYECTO)
    assert r.status_code == 409

    d = await detalle(client, p.id, JURIDICO)
    assert codigos(d) == ["aprobado", "devuelto"] and not d["acciones_disponibles"][0]["bloqueada"]
    r = await revisar(client, p.id, "aprobado", JURIDICO)
    assert r.status_code == 200, r.text
    assert r.json()["avanzo_paso"] is True and r.json()["paso_actual"] == 2

    # Paso 2 paralelo: el primero aprueba (Aprobar), el último ve "Aprobar para firma".
    assert codigos(await detalle(client, p.id, ASESORA)) == ["aprobado", "devuelto"]
    r = await revisar(client, p.id, "aprobado", ASESORA)
    assert r.status_code == 200 and r.json()["estado"]["codigo"] == "en_revision"
    assert codigos(await detalle(client, p.id, PROYECTO)) == ["aprobado_firma", "devuelto"]
    # La asesora ya revisó: bloqueada con motivo y no puede repetir.
    d = await detalle(client, p.id, ASESORA)
    assert all("Ya revisaste" in a["bloqueada"] for a in d["acciones_disponibles"])
    assert (await revisar(client, p.id, "aprobado", ASESORA)).status_code == 409

    r = await revisar(client, p.id, "aprobado_firma", PROYECTO)
    assert r.status_code == 200, r.text
    assert r.json()["estado"]["codigo"] == "aprobado_firma"
    assert any("aprobado para firma" in m for m in stubs.users.para(ABOGADO))

    d = await detalle(client, p.id, ABOGADO)
    assert d["subida_version"]["permitida"] is False and "Cargar versión final" in d["subida_version"]["motivo"]
    assert [x["estado"] for x in d["pasos"]] == ["completado", "completado"]
    revs = (await db_session.execute(select(DocumentoProcesoRevision).order_by(DocumentoProcesoRevision.id))).scalars().all()
    assert [(r.paso, r.permiso, r.accion) for r in revs] == [
        (0, "recurso_lider_juridico", "aprobado"),
        (1, "recurso_asesora_subdireccion", "aprobado"),
        (1, "recurso_lider_proyecto", "aprobado_firma"),
    ]


async def test_aprobado_en_ultimo_lugar_tambien_lleva_a_firma(client, rv_proceso):
    """Si el último pendiente pulsa 'aprobado' (detalle viejo) el resultado es el mismo."""
    _, _, p = await rv_proceso("AUTO_ADMITE")
    await subir(client, p.id)
    await revisar(client, p.id, "aprobado", JURIDICO)
    r = await revisar(client, p.id, "aprobado", PROYECTO)
    assert r.status_code == 200 and r.json()["estado"]["codigo"] == "aprobado_firma"
    assert r.json()["accion"] == "aprobado_firma"


async def test_aprobar_para_firma_antes_de_tiempo_400(client, rv_proceso):
    _, _, p = await rv_proceso("AUTO_ADMITE")
    await subir(client, p.id)
    r = await revisar(client, p.id, "aprobado_firma", JURIDICO)
    assert r.status_code == 400 and "último paso" in r.json()["detail"]


async def test_concepto_etapa2_paralelo_devolucion_y_nueva_version_avanza(client, rv_proceso, db_session, stubs):
    _, _, p = await rv_proceso("CONCEPTO_ETAPA2", encargado=TECNICO)
    assert (await subir(client, p.id, user=TECNICO)).status_code == 200
    # Líder técnico aprueba, SIG devuelve con adjunto.
    assert (await revisar(client, p.id, "aprobado", LIDER_TECNICO)).status_code == 200
    r = await revisar(client, p.id, "devuelto", SIG, comentario="corregir coordenadas", adjunto=DOCX)
    assert r.status_code == 200, r.text
    assert r.json()["estado"]["codigo"] == "rechazado"
    assert any("devuelto por SIG" in m for m in stubs.users.para(TECNICO))
    d = await detalle(client, p.id, TECNICO)
    assert d["revisiones"][0]["adjunto"]["nombre"] == "documento.docx"
    assert d["revisiones"][0]["permiso"] == "recurso_sig" and d["revisiones"][0]["paso"] == 1

    # Nueva versión: nadie del paso 1 queda pendiente → pasa directo al paso 2.
    r = await subir(client, p.id, user=TECNICO)
    assert r.status_code == 200, r.text
    assert r.json()["estado"]["codigo"] == "en_revision" and r.json()["paso_actual"] == 2
    assert (await revisar(client, p.id, "aprobado", SIG)).status_code == 409
    assert any("pendiente de tu revisión" in m for m in stubs.users.para(PROYECTO))
    r = await revisar(client, p.id, "aprobado_firma", PROYECTO)
    assert r.status_code == 200 and r.json()["estado"]["codigo"] == "aprobado_firma"


async def test_devolucion_parcial_vuelve_al_mismo_paso(client, rv_proceso):
    """Si en el paso paralelo uno devuelve antes de que el otro revise, la nueva
    versión vuelve al mismo paso y solo espera al que falta."""
    _, _, p = await rv_proceso("CONCEPTO_ETAPA2", encargado=TECNICO)
    await subir(client, p.id, user=TECNICO)
    await revisar(client, p.id, "devuelto", SIG, comentario="ajustar")
    r = await subir(client, p.id, user=TECNICO)
    assert r.json()["paso_actual"] == 1
    d = await detalle(client, p.id, LIDER_TECNICO)
    assert codigos(d) == ["aprobado", "devuelto"]
    pendientes = [x["permiso"] for x in d["pasos"][0]["permisos"] if not x["revisado"]]
    assert pendientes == ["recurso_lider_tecnico"]
    r = await revisar(client, p.id, "aprobado", LIDER_TECNICO)
    assert r.json()["paso_actual"] == 2


async def test_devolucion_en_ultimo_paso_y_correccion_queda_aprobado_firma(client, rv_proceso):
    """Regla §5.2: quien devolvió no revisa otra vez; si era el último pendiente
    de la cadena la corrección queda aprobada para firma."""
    _, _, p = await rv_proceso("CONCEPTO_MEMORIAS", encargado=TECNICO)
    await subir(client, p.id, user=TECNICO)
    await revisar(client, p.id, "devuelto", LIDER_TECNICO, comentario="falta firma")
    r = await subir(client, p.id, user=TECNICO)
    assert r.json()["estado"]["codigo"] == "aprobado_firma"


async def test_version_final_pdf_auto_aprueba(client, rv_proceso, db_session, stubs):
    from services.revision_documentos import Avisos, Conflicto, cargar_version_final, servicio
    from satc_shared.review_process import PermisoDenegado, ValidacionError

    _, _, p = await rv_proceso("CONCEPTO_ADICIONAL", encargado=TECNICO)
    pid = p.id
    await subir(client, pid, user=TECNICO)

    proceso = await _proceso(db_session, pid)
    pdf = ArchivoRef(file_id=stubs.files.registrar(), url="/files/x", nombre="final.pdf")
    with pytest.raises(Conflicto):  # aún en revisión
        await cargar_version_final(db_session, proceso, pdf, TECNICO, Avisos())
    await db_session.rollback()

    assert (await revisar(client, pid, "aprobado_firma", LIDER_TECNICO)).status_code == 200
    # Subir por /revision-documentos en aprobado_firma no se permite.
    r = await subir(client, pid, archivo=PDF, user=TECNICO)
    assert r.status_code == 409 and "Cargar versión final" in r.json()["detail"]

    proceso = await _proceso(db_session, pid)
    docx = ArchivoRef(file_id=stubs.files.registrar(), url="/files/y", nombre="final.docx")
    with pytest.raises(ValidacionError):
        await cargar_version_final(db_session, proceso, docx, TECNICO, Avisos())
    await db_session.rollback()
    proceso = await _proceso(db_session, pid)
    with pytest.raises(PermisoDenegado):
        await cargar_version_final(db_session, proceso, pdf, ABOGADO, Avisos())
    await db_session.rollback()

    proceso = await _proceso(db_session, pid)
    avisos = Avisos()
    res = await cargar_version_final(db_session, proceso, pdf, TECNICO, avisos)
    await db_session.commit()
    assert res.estado_nuevo == "aprobado"
    assert pdf.file_id in stubs.files.incrementados
    await avisos.enviar()
    assert any("versión firmada cargada" in m for m in stubs.users.para(LIDER_TECNICO))
    d = await detalle(client, pid, TECNICO)
    assert d["estado"]["codigo"] == "aprobado" and d["revisiones"][0]["revisor_id"] == LIDER_TECNICO
    assert d["subida_version"]["permitida"] is False


async def test_permisos_403(client, rv_proceso):
    _, _, p = await rv_proceso("AUTO_ADMITE")
    await subir(client, p.id)
    # Sin permiso de revisor de la cadena → 403 al revisar.
    assert (await revisar(client, p.id, "aprobado", LIDER_TECNICO)).status_code == 403
    assert (await revisar(client, p.id, "aprobado", EXTRANO)).status_code == 403
    # Solo el encargado sube.
    assert (await subir(client, p.id, user=ABOGADO2)).status_code == 403
    # Ver: extraño no; consulta sí (sin acciones ni subida).
    r = await client.get(f"/revision-documentos/{p.id}", headers=headers(EXTRANO))
    assert r.status_code == 403
    d = await detalle(client, p.id, LECTOR)
    assert d["acciones_disponibles"] == [] and d["subida_version"] is None
    assert (await client.get("/revision-documentos/999999", headers=headers(LECTOR))).status_code == 403


async def test_devolver_exige_comentario(client, rv_proceso):
    _, _, p = await rv_proceso("AUTO_ADMITE")
    await subir(client, p.id)
    r = await revisar(client, p.id, "devuelto", JURIDICO, comentario="")
    assert r.status_code == 400


async def test_revisores_concurrentes_mismo_permiso(client, rv_proceso):
    _, _, p = await rv_proceso("AUTO_ADMITE")
    await subir(client, p.id)
    r1, r2 = await asyncio.gather(
        revisar(client, p.id, "aprobado", JURIDICO),
        revisar(client, p.id, "aprobado", JURIDICO2),
    )
    assert sorted([r1.status_code, r2.status_code]) == [200, 409], (r1.text, r2.text)
    d = await detalle(client, p.id, ABOGADO)
    assert d["paso_actual"] == 2
    assert len([r for r in d["revisiones"] if r["permiso"] == "recurso_lider_juridico"]) == 1


async def test_por_etapa_historial_auditoria_y_descarga(client, rv_proceso):
    _, etapa, p = await rv_proceso("AUTO_ADMITE")
    await subir(client, p.id)
    r = await client.get(f"/revision-documentos/por-etapa/acto_admite/{etapa.id}", headers=headers(JURIDICO))
    assert r.status_code == 200 and r.json()["id"] == p.id
    r = await client.get("/revision-documentos/por-etapa/acto_admite/9999", headers=headers(JURIDICO))
    assert r.status_code == 404
    r = await client.get("/revision-documentos/por-etapa/acto_admite/9999", headers=headers(EXTRANO))
    assert r.status_code == 403

    h = (await client.get(f"/revision-documentos/{p.id}/historial", headers=headers(ABOGADO))).json()["data"]
    assert len(h["versiones"]) == 1
    a = (await client.get(f"/revision-documentos/{p.id}/auditoria", headers=headers(ABOGADO))).json()["data"]
    assert [x["accion"] for x in a] == ["crear", "subir_version_inicial"]

    vid = h["versiones"][0]["version_id"]
    r = await client.get(f"/revision-documentos/{p.id}/versiones/{vid}/descarga", headers=headers(JURIDICO))
    assert r.status_code == 200 and r.content == DOCX[1]
    r = await client.get(f"/revision-documentos/{p.id}/versiones/{vid}/descarga", headers=headers(EXTRANO))
    assert r.status_code == 403


async def test_crear_proceso_duplicado_y_cerrar(rv_proceso, db_session):
    from services.revision_documentos import (
        Avisos, ProcesoYaExiste, cerrar_proceso_vigente, crear_proceso, proceso_vigente,
    )
    from satc_shared.review_process import ValidacionError

    exp, etapa, p = await rv_proceso("AUTO_ADMITE")
    exp_id, etapa_id = exp.id, etapa.id
    with pytest.raises(ProcesoYaExiste):
        await crear_proceso(db_session, expediente_id=exp_id, tipo_documento="AUTO_ADMITE",
                            etapa_tipo="acto_admite", etapa_ref_id=etapa_id, encargado_id=ABOGADO,
                            usuario_id=ABOGADO, avisos=Avisos())
    with pytest.raises(ValidacionError):
        await crear_proceso(db_session, expediente_id=exp_id, tipo_documento="DECISION",
                            etapa_tipo="acto_admite", etapa_ref_id=etapa_id, encargado_id=ABOGADO,
                            usuario_id=ABOGADO, avisos=Avisos())
    await db_session.rollback()
    cerrado = await cerrar_proceso_vigente(db_session, "acto_admite", etapa_id, usuario_id=SUPER_G,
                                           descripcion="Cargue directo")
    await db_session.commit()
    assert cerrado.estado == "finalizado" and cerrado.activo is False
    assert await proceso_vigente(db_session, "acto_admite", etapa_id) is None

"""Descarga del expediente completo (routes/expediente_descarga.py)."""
from datetime import date

from db.models import (
    ActoAdministrativo,
    ActoAdmite,
    Comunicacion,
    ConceptoTecnico,
    Decision,
    DocumentoAnexo,
    Notificacion,
    RecursoReposicion,
    Requerimiento,
    TipoActo,
    TipoDecision,
    TipoVinculo,
)


async def _acto(db, files, tipo, numero):
    acto = ActoAdministrativo(tipo_acto=tipo, numerado=numero, fecha_numerado=date(2026, 4, 1),
                              documento_acto_administrativo_id=files.registrar())
    db.add(acto)
    await db.flush()
    return acto


async def test_descarga_en_orden_del_proceso(client, h_consultor, crear_expediente, vincular, db_session, stubs):
    f = stubs.files
    exp = await crear_expediente()

    admite_acto = await _acto(db_session, f, TipoActo.AUTO_ADMITE, 1)
    com = Comunicacion(numerado=1, fecha_numerado=date(2026, 4, 1), fecha_envio=date(2026, 4, 2),
                       documento_comunicacion_id=f.registrar(), acto_administrativo_id=admite_acto.id)
    notif = Notificacion(acto_admin_id=admite_acto.id, numerado=2, involucrado_id=1,
                         fecha_numerado=date(2026, 4, 1), fecha_envio_citacion=date(2026, 4, 1),
                         fecha_constancia_citacion=date(2026, 4, 2),
                         documento_citacion_id=f.registrar(), documento_notificacion_id=f.registrar())
    admite = ActoAdmite(expediente_id=exp.id, encargado_acto_id=10, acto_admin_id=admite_acto.id,
                        doc_oficio_alcaldia_id=f.registrar(), doc_fijacion_aviso_id=f.registrar(),
                        doc_constancia_fijacion_aviso_id=f.registrar())
    db_session.add_all([com, notif, admite])
    await db_session.flush()
    anexo_admite = DocumentoAnexo(etapa_tipo="acto_admite", etapa_ref_id=admite.id, nombre="Foto",
                                  documento_anexo_id=f.registrar())

    tercero_acto = await _acto(db_session, f, TipoActo.RECONOCE_TERCERO, 2)
    concepto = ConceptoTecnico(expediente_id=exp.id, tecnico_encargado_id=20, doc_concepto_tecnico_id=f.registrar())
    adicional = ConceptoTecnico(tecnico_encargado_id=20, doc_concepto_tecnico_id=f.registrar())
    db_session.add_all([anexo_admite, concepto, adicional])
    await db_session.flush()
    anexo_concepto = DocumentoAnexo(etapa_tipo="concepto_tecnico", etapa_ref_id=concepto.id, nombre="Aforo",
                                    documento_anexo_id=f.registrar())
    req_acto = await _acto(db_session, f, TipoActo.REQUERIMIENTO, 3)
    req = Requerimiento(expediente_id=exp.id, encargado_acto_id=10, acto_admin_id=req_acto.id,
                        doc_oficio_entrada_id=f.registrar(), concepto_tecnico_id=adicional.id)
    dec_acto = await _acto(db_session, f, TipoActo.DECISION, 4)
    decision = Decision(expediente_id=exp.id, encargado_acto_id=10, acto_admin_id=dec_acto.id,
                        decision=TipoDecision.OTORGADA)
    db_session.add_all([anexo_concepto, req, decision])
    await db_session.flush()
    recurso_acto = await _acto(db_session, f, TipoActo.RECURSO, 5)
    recurso = RecursoReposicion(decision_id=decision.id, radicado="2026ER55555", fecha_radicado=date(2026, 5, 1),
                                doc_recurso_id=f.registrar(), acto_admin_id=recurso_acto.id)
    db_session.add(recurso)
    await db_session.commit()
    await vincular(exp.id, 99, tipo_vinculo=TipoVinculo.TERCERO_INTERVINIENTE, acto_admin_id=tercero_acto.id)

    esperado = [
        exp.doc_comprobante_pago_id,
        admite_acto.documento_acto_administrativo_id, com.documento_comunicacion_id,
        notif.documento_citacion_id, notif.documento_notificacion_id,
        admite.doc_oficio_alcaldia_id, admite.doc_fijacion_aviso_id, admite.doc_constancia_fijacion_aviso_id,
        anexo_admite.documento_anexo_id,
        tercero_acto.documento_acto_administrativo_id,
        concepto.doc_concepto_tecnico_id, anexo_concepto.documento_anexo_id,
        req_acto.documento_acto_administrativo_id, req.doc_oficio_entrada_id, adicional.doc_concepto_tecnico_id,
        dec_acto.documento_acto_administrativo_id,
        recurso.doc_recurso_id, recurso_acto.documento_acto_administrativo_id,
    ]

    r = await client.get(f"/expedientes/{exp.id}/documentos", headers=h_consultor)
    assert r.status_code == 200
    assert [d["file_id"] for d in r.json()["data"]] == esperado

    r = await client.get(f"/expedientes/{exp.id}/descargar", headers=h_consultor)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert 'filename="concesion_CA_' in r.headers["content-disposition"]
    assert r.content == b"%PDF-unificado"
    assert f.unificados == [esperado]


async def test_descarga_solo_informacion_base(client, h_consultor, crear_expediente, stubs):
    exp = await crear_expediente()
    r = await client.get(f"/expedientes/{exp.id}/descargar", headers=h_consultor)
    assert r.status_code == 200
    assert stubs.files.unificados == [[exp.doc_comprobante_pago_id]]


async def test_descarga_inexistente_404(client, h_consultor):
    r = await client.get("/expedientes/9999/descargar", headers=h_consultor)
    assert r.status_code == 404


async def test_descarga_sin_permiso_403(client, h_sin_permisos, crear_expediente):
    exp = await crear_expediente()
    r = await client.get(f"/expedientes/{exp.id}/descargar", headers=h_sin_permisos)
    assert r.status_code == 403

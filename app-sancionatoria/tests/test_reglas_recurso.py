"""
Reglas de negocio con recurso (probatoria de recurso y su acto de decisión,
`etapa_probatoria_recurso.acto_decision_id`):

1. Ejecución de la sanción (GET `creable` y POST usan la misma regla):
   - Sin recurso: basta la decisión de fondo con su acto notificado.
   - Con recurso: el acto que DECIDE el recurso (acto_decision_id) debe estar
     notificado con éxito; la notificación del acto principal de la probatoria
     o de la decisión de fondo no basta.
2. Alerta "Notificar decisión del recurso" (services/alertas.py, alerta6):
   mira acto_decision_id, no el acto principal de la probatoria.
"""
from datetime import date, timedelta

from conftest import gateway_headers
from db.models.documento_anexo import DocumentoAnexo
from db.models.etapa_decision_fondo import EtapaDecisionFondo
from db.models.etapa_probatoria_recurso import EtapaProbatoriaRecurso
from services.alertas import calcular_alertas_expediente

HOY = date.today()


async def _acto(make_acto_administrativo, make_notificacion, notificado: bool | None):
    """Acto administrativo; notificado=None -> sin notificaciones."""
    acto = await make_acto_administrativo()
    if notificado is not None:
        await make_notificacion(acto.id, notificacion_exitosa=notificado,
                                fecha_notificacion=HOY - timedelta(days=30))
    return acto


async def _decision_notificada(db_session, exp, make_acto_administrativo, make_notificacion):
    acto = await _acto(make_acto_administrativo, make_notificacion, True)
    recurso_acto = await make_acto_administrativo()
    decision = EtapaDecisionFondo(expediente_id=exp.id, acto_administrativo_id=acto.id,
                                  acto_recurso_id=recurso_acto.id)
    db_session.add(decision)
    await db_session.flush()
    return decision


async def _recurso(db_session, exp, acto_principal=None, acto_decision=None):
    recurso = EtapaProbatoriaRecurso(
        expediente_id=exp.id,
        acto_administrativo_id=acto_principal.id if acto_principal else None,
        acto_decision_id=acto_decision.id if acto_decision else None,
    )
    db_session.add(recurso)
    await db_session.flush()
    return recurso


async def _creable_y_post(client, exp):
    creable = (await client.get(f"/execution/{exp.id}", headers=gateway_headers(1))).json()["creable"]
    post = await client.post(f"/execution/{exp.id}", headers=gateway_headers(1))
    return creable, post


# ── 1. Ejecución ──────────────────────────────────────────────────────────────

async def test_ejecucion_sin_recurso_basta_decision_notificada(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    await _decision_notificada(db_session, exp, make_acto_administrativo, make_notificacion)
    creable, post = await _creable_y_post(client, exp)
    assert creable == {"status": True}
    assert post.status_code == 201


async def test_ejecucion_sin_recurso_y_decision_sin_notificar_no_creable(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    acto = await _acto(make_acto_administrativo, make_notificacion, False)
    db_session.add(EtapaDecisionFondo(expediente_id=exp.id, acto_administrativo_id=acto.id))
    await db_session.flush()
    creable, post = await _creable_y_post(client, exp)
    assert creable["status"] is False
    assert post.status_code == 400


async def test_ejecucion_con_recurso_sin_acto_de_decision_no_creable(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    """La decisión de fondo notificada ya no basta si hay recurso."""
    exp = await make_expediente(encargado_id=1)
    await _decision_notificada(db_session, exp, make_acto_administrativo, make_notificacion)
    await _recurso(db_session, exp)
    creable, post = await _creable_y_post(client, exp)
    assert creable["status"] is False
    assert "recurso" in creable["msg"]
    assert post.status_code == 400
    assert post.json()["detail"] == creable["msg"]


async def test_ejecucion_con_recurso_mira_el_acto_de_decision_no_el_principal(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    await _decision_notificada(db_session, exp, make_acto_administrativo, make_notificacion)
    principal = await _acto(make_acto_administrativo, make_notificacion, True)
    decision_rec = await _acto(make_acto_administrativo, make_notificacion, False)
    await _recurso(db_session, exp, acto_principal=principal, acto_decision=decision_rec)
    creable, post = await _creable_y_post(client, exp)
    assert creable["status"] is False
    assert post.status_code == 400


async def test_ejecucion_con_recurso_decidido_y_notificado_es_creable(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    await _decision_notificada(db_session, exp, make_acto_administrativo, make_notificacion)
    principal = await _acto(make_acto_administrativo, make_notificacion, None)
    decision_rec = await _acto(make_acto_administrativo, make_notificacion, True)
    await _recurso(db_session, exp, acto_principal=principal, acto_decision=decision_rec)
    creable, post = await _creable_y_post(client, exp)
    assert creable == {"status": True}
    assert post.status_code == 201


# ── 2. Alerta "Notificar decisión del recurso" ───────────────────────────────

async def _escenario_alerta(db_session, make_expediente, make_acto_administrativo, make_notificacion,
                            principal_notificado, decision_notificada):
    exp = await make_expediente(encargado_id=1)
    decision = await _decision_notificada(db_session, exp, make_acto_administrativo, make_notificacion)
    db_session.add(DocumentoAnexo(etapa_tipo="etapa_decision_fondo", etapa_ref_id=decision.id,
                                  nombre="Recurso", documento_anexo_id=1))
    principal = await _acto(make_acto_administrativo, make_notificacion, principal_notificado)
    decision_rec = (await _acto(make_acto_administrativo, make_notificacion, decision_notificada)
                    if decision_notificada is not None else None)
    await _recurso(db_session, exp, acto_principal=principal, acto_decision=decision_rec)
    await db_session.commit()
    return await calcular_alertas_expediente(exp.radicado, db_session, HOY)


async def test_alerta_decision_recurso_si_el_acto_de_decision_no_esta_notificado(db_session, make_expediente, make_acto_administrativo, make_notificacion):
    # Antes: el acto principal notificado apagaba la alerta aunque la decisión
    # del recurso no se hubiera notificado.
    alertas = await _escenario_alerta(db_session, make_expediente, make_acto_administrativo, make_notificacion,
                                      principal_notificado=True, decision_notificada=False)
    assert alertas["alerta6"]["tipo"] == "resolucion_recurso"
    assert alertas["alerta6"]["accion_requerida"] == "Notificar decisión del recurso"


async def test_alerta_decision_recurso_si_aun_no_hay_acto_de_decision(db_session, make_expediente, make_acto_administrativo, make_notificacion):
    alertas = await _escenario_alerta(db_session, make_expediente, make_acto_administrativo, make_notificacion,
                                      principal_notificado=True, decision_notificada=None)
    assert alertas["alerta6"]["tipo"] == "resolucion_recurso"


async def test_sin_alerta_cuando_la_decision_del_recurso_esta_notificada(db_session, make_expediente, make_acto_administrativo, make_notificacion):
    # El acto principal sin notificar no importa: la alerta mira acto_decision_id.
    alertas = await _escenario_alerta(db_session, make_expediente, make_acto_administrativo, make_notificacion,
                                      principal_notificado=None, decision_notificada=True)
    assert "alerta6" not in alertas

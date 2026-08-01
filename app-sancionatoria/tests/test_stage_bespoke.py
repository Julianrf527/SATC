"""
Las 3 etapas que quedaron fuera del motor genérico: formulación (Form() en
vez de JSON), recurso (creable con lógica ramificada) y ejecución (múltiples
documentos independientes).
"""
from conftest import gateway_headers
from db.models.etapa_inicio_sancionatorio import EtapaInicioSancionatorio
from db.models.etapa_decision_fondo import EtapaDecisionFondo


# ── FORMULACIÓN (Form(), no JSON) ───────────────────────────────────────────

async def test_formulacion_rechaza_sin_inicio_proceso_notificado(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    resp = await client.post(f"/formulation/{exp.id}", headers=gateway_headers(1), data={"descargos": "true"})
    assert resp.status_code == 400


async def test_formulacion_crear_y_actualizar(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    acto = await make_acto_administrativo()
    await make_notificacion(acto.id, notificacion_exitosa=True)
    db_session.add(EtapaInicioSancionatorio(expediente_id=exp.id, acto_administrativo_id=acto.id))
    await db_session.flush()

    creado = await client.post(f"/formulation/{exp.id}", headers=gateway_headers(1), data={"descargos": "true"})
    assert creado.status_code == 201

    obtenido = (await client.get(f"/formulation/{exp.id}", headers=gateway_headers(1))).json()
    assert obtenido["formulacion_cargos"]["descargos"] is True

    actualizado = await client.put(f"/formulation/{exp.id}", headers=gateway_headers(1), data={"descargos": "false"})
    assert actualizado.status_code == 200

    releido = (await client.get(f"/formulation/{exp.id}", headers=gateway_headers(1))).json()
    assert releido["formulacion_cargos"]["descargos"] is False


# ── RECURSO (creable ramificado — no encaja en el motor genérico) ──────────

async def test_recurso_no_creable_sin_decision(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    resp = await client.get(f"/resource/{exp.id}", headers=gateway_headers(1))
    assert resp.status_code == 200
    assert resp.json()["recurso"]["creable"]["status"] is False


async def test_recurso_post_rechaza_si_decision_no_tiene_acto_recurso(client, db_session, make_expediente, make_acto_administrativo):
    """El POST de recurso exige dec.acto_recurso_id puntual — no alcanza con
    que la decisión de fondo simplemente exista o tenga su acto principal."""
    exp = await make_expediente(encargado_id=1)
    acto = await make_acto_administrativo()
    db_session.add(EtapaDecisionFondo(expediente_id=exp.id, acto_administrativo_id=acto.id))
    await db_session.flush()

    resp = await client.post(f"/resource/{exp.id}", headers=gateway_headers(1))
    assert resp.status_code == 400


async def test_recurso_post_ok_con_acto_recurso_en_decision(client, db_session, make_expediente, make_acto_administrativo):
    exp = await make_expediente(encargado_id=1)
    acto = await make_acto_administrativo()
    acto_recurso = await make_acto_administrativo()
    db_session.add(EtapaDecisionFondo(expediente_id=exp.id, acto_administrativo_id=acto.id, acto_recurso_id=acto_recurso.id))
    await db_session.flush()

    resp = await client.post(f"/resource/{exp.id}", headers=gateway_headers(1))
    assert resp.status_code == 201


# ── EJECUCIÓN (varios documentos independientes) ────────────────────────────

async def test_ejecucion_rechaza_sin_decision_notificada(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    body = {"tipo_acto": "auto", "fecha_auto": "2026-01-01"}
    resp = await client.post(f"/execution/{exp.id}", headers=gateway_headers(1), json=body)
    assert resp.status_code == 400


async def test_ejecucion_crear_y_actualizar(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    acto = await make_acto_administrativo()
    await make_notificacion(acto.id, notificacion_exitosa=True)
    db_session.add(EtapaDecisionFondo(expediente_id=exp.id, acto_administrativo_id=acto.id))
    await db_session.flush()

    body = {"tipo_acto": "auto", "fecha_auto": "2026-01-01", "cobro_coactivo": True}
    creado = await client.post(f"/execution/{exp.id}", headers=gateway_headers(1), json=body)
    assert creado.status_code == 201

    obtenido = (await client.get(f"/execution/{exp.id}", headers=gateway_headers(1))).json()
    assert obtenido["ejecucion_sancion"]["cobro_coactivo"] is True

    nuevo_body = {"tipo_acto": "auto", "fecha_auto": "2026-01-02", "cobro_coactivo": False}
    actualizado = await client.put(f"/execution/{exp.id}", headers=gateway_headers(1), json=nuevo_body)
    assert actualizado.status_code == 200

    releido = (await client.get(f"/execution/{exp.id}", headers=gateway_headers(1))).json()
    assert releido["ejecucion_sancion"]["cobro_coactivo"] is False


async def test_ejecucion_rechaza_fecha_futura(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    acto = await make_acto_administrativo()
    await make_notificacion(acto.id, notificacion_exitosa=True)
    db_session.add(EtapaDecisionFondo(expediente_id=exp.id, acto_administrativo_id=acto.id))
    await db_session.flush()

    body = {"tipo_acto": "auto", "fecha_auto": "2099-01-01"}
    resp = await client.post(f"/execution/{exp.id}", headers=gateway_headers(1), json=body)
    assert resp.status_code == 422

"""
Las 2 etapas que quedaron fuera del motor genérico: formulación (documento de
descargos con contador de usos) y ejecución (4 documentos independientes).
Ambas usan body JSON, igual que el resto de etapas.
"""
from conftest import gateway_headers
from db.models.etapa_inicio_sancionatorio import EtapaInicioSancionatorio
from db.models.etapa_decision_fondo import EtapaDecisionFondo


async def _inicio_notificado(db_session, exp, make_acto_administrativo, make_notificacion):
    acto = await make_acto_administrativo()
    await make_notificacion(acto.id, notificacion_exitosa=True)
    db_session.add(EtapaInicioSancionatorio(expediente_id=exp.id, acto_administrativo_id=acto.id))
    await db_session.flush()


async def _decision_notificada(db_session, exp, make_acto_administrativo, make_notificacion):
    acto = await make_acto_administrativo()
    await make_notificacion(acto.id, notificacion_exitosa=True)
    db_session.add(EtapaDecisionFondo(expediente_id=exp.id, acto_administrativo_id=acto.id))
    await db_session.flush()


# ── FORMULACIÓN (JSON {descargos, documento_id}) ─────────────────────────────

async def test_formulacion_rechaza_sin_inicio_proceso_notificado(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    resp = await client.post(f"/formulation/{exp.id}", headers=gateway_headers(1), json={"descargos": True})
    assert resp.status_code == 400

    get = (await client.get(f"/formulation/{exp.id}", headers=gateway_headers(1))).json()
    assert get["formulacion_cargos"] is None
    assert get["creable"]["status"] is False


async def test_formulacion_crear_y_actualizar(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    await _inicio_notificado(db_session, exp, make_acto_administrativo, make_notificacion)

    creado = await client.post(f"/formulation/{exp.id}", headers=gateway_headers(1), json={"descargos": True})
    assert creado.status_code == 201
    etapa_id = creado.json()["etapa_id"]

    obtenido = (await client.get(f"/formulation/{exp.id}", headers=gateway_headers(1))).json()
    formulacion = obtenido["formulacion_cargos"]
    assert formulacion["etapa_id"] == etapa_id
    assert formulacion["descargos"] is True
    assert formulacion["documento_id"] is None
    assert obtenido["creable"]["status"] is True

    actualizado = await client.put(f"/formulation/{exp.id}", headers=gateway_headers(1), json={"descargos": False, "documento_id": None})
    assert actualizado.status_code == 200
    assert actualizado.json()["etapa_id"] == etapa_id

    releido = (await client.get(f"/formulation/{exp.id}", headers=gateway_headers(1))).json()
    assert releido["formulacion_cargos"]["descargos"] is False


async def test_formulacion_crear_vacia_y_luego_completar(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    """Flujo del frontend: "Crear Etapa" hace POST sin body y la información se guarda con PUT."""
    exp = await make_expediente(encargado_id=1)
    await _inicio_notificado(db_session, exp, make_acto_administrativo, make_notificacion)

    assert (await client.post(f"/formulation/{exp.id}", headers=gateway_headers(1))).status_code == 201
    obtenido = (await client.get(f"/formulation/{exp.id}", headers=gateway_headers(1))).json()["formulacion_cargos"]
    assert obtenido["etapa_id"] and obtenido["descargos"] is None

    resp = await client.put(f"/formulation/{exp.id}", headers=gateway_headers(1), json={"descargos": None})
    assert resp.status_code == 200


async def test_formulacion_forma_vieja_form_data_da_422(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    await _inicio_notificado(db_session, exp, make_acto_administrativo, make_notificacion)

    resp = await client.post(f"/formulation/{exp.id}", headers=gateway_headers(1), data={"descargos": "true"})
    assert resp.status_code == 422
    assert (await client.post(f"/formulation/{exp.id}", headers=gateway_headers(1))).status_code == 201
    resp = await client.put(f"/formulation/{exp.id}", headers=gateway_headers(1), data={"descargos": "false"})
    assert resp.status_code == 422
    resp = await client.put(f"/formulation/{exp.id}", headers=gateway_headers(1), json={"descargos": False, "etapa_id": 1})
    assert resp.status_code == 422


# ── EJECUCIÓN (tipo_acto "AUTO0123", documento_acto_administrativo_id, documento_cobro_id) ──

BODY_EJECUCION = {
    "tipo_acto": "AUTO0123",
    "fecha_auto": "2026-01-01",
    "documento_acto_administrativo_id": None,
    "cobro_coactivo": True,
    "documento_cobro_id": None,
    "disposicion": False,
    "ruia": False,
    "documento_ruia_id": None,
    "memorando": False,
    "documento_memorando_id": None,
}


async def test_ejecucion_rechaza_sin_decision_notificada(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    resp = await client.post(f"/execution/{exp.id}", headers=gateway_headers(1), json=BODY_EJECUCION)
    assert resp.status_code == 400

    get = (await client.get(f"/execution/{exp.id}", headers=gateway_headers(1))).json()
    assert get["ejecucion_sancion"] is None
    assert get["creable"]["status"] is False


async def test_ejecucion_crear_y_actualizar(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    await _decision_notificada(db_session, exp, make_acto_administrativo, make_notificacion)

    creado = await client.post(f"/execution/{exp.id}", headers=gateway_headers(1), json=BODY_EJECUCION)
    assert creado.status_code == 201
    etapa_id = creado.json()["etapa_id"]

    obtenido = (await client.get(f"/execution/{exp.id}", headers=gateway_headers(1))).json()
    ejecucion = obtenido["ejecucion_sancion"]
    assert ejecucion["etapa_id"] == etapa_id
    assert ejecucion["tipo_acto"] == "AUTO0123"
    assert ejecucion["fecha_auto"] == "2026-01-01"
    assert ejecucion["cobro_coactivo"] is True
    assert "documento_cobro_id" in ejecucion and "documento_acto_administrativo_id" in ejecucion
    assert obtenido["creable"]["status"] is True

    nuevo_body = {**BODY_EJECUCION, "tipo_acto": "RES0456", "fecha_auto": "2026-01-02", "cobro_coactivo": False}
    actualizado = await client.put(f"/execution/{exp.id}", headers=gateway_headers(1), json=nuevo_body)
    assert actualizado.status_code == 200

    releido = (await client.get(f"/execution/{exp.id}", headers=gateway_headers(1))).json()["ejecucion_sancion"]
    assert releido["cobro_coactivo"] is False
    assert releido["tipo_acto"] == "RES0456"


async def test_ejecucion_crear_vacia_y_luego_completar(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    await _decision_notificada(db_session, exp, make_acto_administrativo, make_notificacion)

    assert (await client.post(f"/execution/{exp.id}", headers=gateway_headers(1))).status_code == 201
    vacia = (await client.get(f"/execution/{exp.id}", headers=gateway_headers(1))).json()["ejecucion_sancion"]
    assert vacia["etapa_id"] and vacia["tipo_acto"] is None

    assert (await client.put(f"/execution/{exp.id}", headers=gateway_headers(1), json=BODY_EJECUCION)).status_code == 200


async def test_ejecucion_rechaza_fecha_futura(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    await _decision_notificada(db_session, exp, make_acto_administrativo, make_notificacion)

    resp = await client.post(f"/execution/{exp.id}", headers=gateway_headers(1), json={**BODY_EJECUCION, "fecha_auto": "2099-01-01"})
    assert resp.status_code == 422


async def test_ejecucion_forma_vieja_da_422(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    """La forma que enviaba el frontend antes: auto_admin, documento_auto_id,
    documento_cobro_coactivo_id, etapa_id y booleanos como string."""
    exp = await make_expediente(encargado_id=1)
    await _decision_notificada(db_session, exp, make_acto_administrativo, make_notificacion)
    assert (await client.post(f"/execution/{exp.id}", headers=gateway_headers(1))).status_code == 201

    vieja = {
        "etapa_id": "1", "cobro_coactivo": "true", "disposicion": "false", "ruia": "false",
        "memorando": "false", "auto_admin": "AUTO0123", "fecha_auto": "2026-01-01",
        "documento_auto_id": "10", "documento_cobro_coactivo_id": "11",
    }
    assert (await client.put(f"/execution/{exp.id}", headers=gateway_headers(1), json=vieja)).status_code == 422
    # tipo_acto con formato inválido
    mal = {**BODY_EJECUCION, "tipo_acto": "auto"}
    assert (await client.put(f"/execution/{exp.id}", headers=gateway_headers(1), json=mal)).status_code == 422

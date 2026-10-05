"""
Resto de las etapas genéricas: apertura probatoria, cierre probatoria y
decisión de fondo. Los precondicionantes de "creable" (acto administrativo +
notificación exitosa en la etapa anterior) se arman directo por ORM en vez de
pasar por acto.py — eso es responsabilidad de otro router, fuera del alcance
del motor genérico que se está probando acá.
"""
from conftest import gateway_headers
from db.models.etapa_formulacion_cargos import EtapaFormulacionCargos
from db.models.etapa_apertura_probatoria import EtapaAperturaProbatoria
from db.models.etapa_cierre_probatoria import EtapaCierreProbatoria


# ── APERTURA (creable = notif exitosa en formulación de cargos) ────────────

async def test_apertura_no_creable_sin_formulacion(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    resp = await client.get(f"/opening/{exp.id}", headers=gateway_headers(1))
    assert resp.status_code == 200
    assert resp.json()["creable"]["status"] is False


async def test_apertura_post_ok_con_formulacion_notificada(client, db_session, make_expediente, make_acto_administrativo, make_notificacion):
    exp = await make_expediente(encargado_id=1)
    acto = await make_acto_administrativo()
    await make_notificacion(acto.id, notificacion_exitosa=True)
    db_session.add(EtapaFormulacionCargos(expediente_id=exp.id, acto_administrativo_id=acto.id))
    await db_session.flush()

    creable = (await client.get(f"/opening/{exp.id}", headers=gateway_headers(1))).json()["creable"]
    assert creable["status"] is True

    resp = await client.post(f"/opening/{exp.id}", headers=gateway_headers(1))
    assert resp.status_code == 201


# ── CIERRE (creable = apertura con acto administrativo, sin exigir notif) ──

async def test_cierre_no_creable_sin_apertura(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    resp = await client.get(f"/closing/{exp.id}", headers=gateway_headers(1))
    assert resp.json()["creable"]["status"] is False


async def test_cierre_post_ok_con_apertura_y_acto_sin_notificar(client, db_session, make_expediente, make_acto_administrativo):
    """A diferencia de las demás, cierre solo exige que la apertura tenga acto
    administrativo — no requiere notificación exitosa (requiere_acto=True,
    no requiere_notif)."""
    exp = await make_expediente(encargado_id=1)
    acto = await make_acto_administrativo()
    db_session.add(EtapaAperturaProbatoria(expediente_id=exp.id, acto_administrativo_id=acto.id))
    await db_session.flush()

    creable = (await client.get(f"/closing/{exp.id}", headers=gateway_headers(1))).json()["creable"]
    assert creable["status"] is True

    resp = await client.post(f"/closing/{exp.id}", headers=gateway_headers(1))
    assert resp.status_code == 201


# ── DECISIÓN DE FONDO (creable = notif en cierre) ──

async def test_decision_sin_etapa_devuelve_none(client, make_expediente):
    """Como todas las etapas: null cuando no existe y `creable` en la raíz."""
    exp = await make_expediente(encargado_id=1)
    resp = await client.get(f"/decision/{exp.id}", headers=gateway_headers(1))
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision_fondo"] is None
    assert body["creable"]["status"] is False


async def test_decision_crear_y_actualizar(client, db_session, make_expediente, make_acto_administrativo, make_notificacion, tipo_sancion):
    exp = await make_expediente(encargado_id=1)
    acto = await make_acto_administrativo()
    await make_notificacion(acto.id, notificacion_exitosa=True)
    db_session.add(EtapaCierreProbatoria(expediente_id=exp.id, acto_administrativo_id=acto.id))
    await db_session.flush()

    body = {"tipo_sancion_id": tipo_sancion.id, "detalle": "Sanción por decomiso"}
    creado = await client.post(f"/decision/{exp.id}", headers=gateway_headers(1), json=body)
    assert creado.status_code == 201

    obtenido = (await client.get(f"/decision/{exp.id}", headers=gateway_headers(1))).json()
    decision = obtenido["decision_fondo"]
    assert decision["etapa_id"] == creado.json()["etapa_id"]
    assert decision["tipo_sancion_id"] == tipo_sancion.id
    assert decision["detalle"] == "Sanción por decomiso"
    assert "informacion" not in decision
    assert decision["acto_recurso"] is None
    assert decision["creable_acto_recurso"]["status"] is False

    nuevo_body = {"tipo_sancion_id": tipo_sancion.id, "detalle": "Sanción actualizada"}
    actualizado = await client.put(f"/decision/{exp.id}", headers=gateway_headers(1), json=nuevo_body)
    assert actualizado.status_code == 200

    releido = (await client.get(f"/decision/{exp.id}", headers=gateway_headers(1))).json()
    assert releido["decision_fondo"]["detalle"] == "Sanción actualizada"

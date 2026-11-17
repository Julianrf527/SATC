"""
Contrato único de las etapas (ver el bloque "CONTRATO DE LAS ETAPAS" en
routes/stage.py): GET → {"<clave>": Etapa | null, "creable"?} con `etapa_id` y
campos propios planos; bodies JSON estrictos (forma vieja → 422).
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from conftest import gateway_headers
from db.models.documento_anexo import DocumentoAnexo
from db.models.etapa_cierre_probatoria import EtapaCierreProbatoria
from db.models.etapa_decision_fondo import EtapaDecisionFondo
from db.models.etapa_indagacion import EtapaIndagacion
from db.models.etapa_medida_preventiva import EtapaMedidaPreventiva
from db.models.etapa_probatoria_recurso import EtapaProbatoriaRecurso

GENERICAS_SIN_BODY = [
    ("investigation", "indagacion"),
    ("start-process", "inicio_proceso"),
]


@pytest.fixture
def sin_app_docs(monkeypatch):
    """Los contadores de uso de archivos llaman a app-docs por HTTP."""
    import routes.acto_admin as acto_admin
    import routes.stage as stage
    for modulo in (acto_admin, stage):
        monkeypatch.setattr(modulo, "increment_file_usage", AsyncMock())
        monkeypatch.setattr(modulo, "decrement_file_usage", AsyncMock())


# ── Forma común ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ruta,clave", GENERICAS_SIN_BODY)
async def test_get_devuelve_etapa_id_tras_crear(client, make_expediente, ruta, clave):
    exp = await make_expediente(encargado_id=1)
    assert (await client.get(f"/{ruta}/{exp.id}", headers=gateway_headers(1))).json()[clave] is None

    creado = (await client.post(f"/{ruta}/{exp.id}", headers=gateway_headers(1))).json()
    etapa = (await client.get(f"/{ruta}/{exp.id}", headers=gateway_headers(1))).json()[clave]
    assert etapa["etapa_id"] == creado["etapa_id"] == etapa["id"]
    assert etapa["acto_admin"] is None
    assert etapa["documentos_anexos"] == []


async def test_creable_va_en_la_raiz_no_en_la_etapa(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    await client.post(f"/start-process/{exp.id}", headers=gateway_headers(1))
    assert (await client.post(f"/cessation/{exp.id}", headers=gateway_headers(1))).status_code == 201

    body = (await client.get(f"/cessation/{exp.id}", headers=gateway_headers(1))).json()
    assert body["creable"] == {"status": True}
    assert "creable" not in body["cesacion"]


# ── Medida preventiva ───────────────────────────────────────────────────────

async def test_medida_vacia_y_luego_put(client, make_expediente, tipo_medida):
    exp = await make_expediente(encargado_id=1)
    assert (await client.post(f"/measure/{exp.id}", headers=gateway_headers(1))).status_code == 201
    vacia = (await client.get(f"/measure/{exp.id}", headers=gateway_headers(1))).json()["medida"]
    assert vacia["etapa_id"] and vacia["tipo_medida_id"] is None

    body = {"tipo_medida_id": tipo_medida.id, "cantidad": "5 m³", "especie": "Roble", "estado_medida": None}
    assert (await client.put(f"/measure/{exp.id}", headers=gateway_headers(1), json=body)).status_code == 200
    medida = (await client.get(f"/measure/{exp.id}", headers=gateway_headers(1))).json()["medida"]
    assert (medida["tipo_medida_id"], medida["cantidad"], medida["estado_medida"]) == (tipo_medida.id, "5 m³", None)


async def test_medida_forma_vieja_da_422(client, make_expediente, tipo_medida):
    exp = await make_expediente(encargado_id=1)
    await client.post(f"/measure/{exp.id}", headers=gateway_headers(1))
    vieja = {"tipo_medida_id": tipo_medida.id, "cantidad": "5 m³", "especie": "Roble", "estado_medida": True, "etapa_id": 1}
    assert (await client.put(f"/measure/{exp.id}", headers=gateway_headers(1), json=vieja)).status_code == 422


# ── Cesación ────────────────────────────────────────────────────────────────

async def test_cesacion_crear_obtener_actualizar(client, make_expediente, tipo_cesacion):
    exp = await make_expediente(encargado_id=1)
    await client.post(f"/start-process/{exp.id}", headers=gateway_headers(1))
    creado = await client.post(f"/cessation/{exp.id}", headers=gateway_headers(1))
    assert creado.status_code == 201

    assert (await client.put(f"/cessation/{exp.id}", headers=gateway_headers(1), json={"tipo_cesacion_id": tipo_cesacion.id})).status_code == 200
    cesacion = (await client.get(f"/cessation/{exp.id}", headers=gateway_headers(1))).json()["cesacion"]
    assert cesacion["etapa_id"] == creado.json()["etapa_id"]
    assert cesacion["tipo_cesacion_id"] == tipo_cesacion.id
    assert cesacion["tipo_cesacion_nombre"] == tipo_cesacion.nombre


async def test_cesacion_forma_vieja_da_422(client, make_expediente, tipo_cesacion):
    exp = await make_expediente(encargado_id=1)
    await client.post(f"/start-process/{exp.id}", headers=gateway_headers(1))
    await client.post(f"/cessation/{exp.id}", headers=gateway_headers(1))
    vieja = {"tipo_cesacion_id": tipo_cesacion.id, "etapa_id": 1}
    assert (await client.put(f"/cessation/{exp.id}", headers=gateway_headers(1), json=vieja)).status_code == 422


# ── Decisión de fondo ───────────────────────────────────────────────────────

async def _cierre_notificado(db_session, exp, make_acto_administrativo, make_notificacion):
    acto = await make_acto_administrativo()
    await make_notificacion(acto.id, notificacion_exitosa=True)
    db_session.add(EtapaCierreProbatoria(expediente_id=exp.id, acto_administrativo_id=acto.id))
    await db_session.flush()


async def test_catalogo_tipos_sancion(client, tipo_sancion):
    resp = await client.get("/sanction-type", headers=gateway_headers(1))
    assert resp.status_code == 200
    assert {"id": tipo_sancion.id, "nombre": tipo_sancion.nombre} in resp.json()["data"]


async def test_decision_vacia_luego_put_y_forma_vieja_422(client, db_session, make_expediente, make_acto_administrativo, make_notificacion, tipo_sancion):
    exp = await make_expediente(encargado_id=1)
    await _cierre_notificado(db_session, exp, make_acto_administrativo, make_notificacion)
    assert (await client.post(f"/decision/{exp.id}", headers=gateway_headers(1))).status_code == 201

    body = {"tipo_sancion_id": tipo_sancion.id, "detalle": "Multa"}
    assert (await client.put(f"/decision/{exp.id}", headers=gateway_headers(1), json=body)).status_code == 200
    decision = (await client.get(f"/decision/{exp.id}", headers=gateway_headers(1))).json()["decision_fondo"]
    assert (decision["tipo_sancion_id"], decision["detalle"]) == (tipo_sancion.id, "Multa")

    vieja = {**body, "etapa_id": decision["etapa_id"]}
    assert (await client.put(f"/decision/{exp.id}", headers=gateway_headers(1), json=vieja)).status_code == 422


async def test_decision_creable_acto_recurso(client, db_session, make_expediente, make_acto_administrativo):
    exp = await make_expediente(encargado_id=1)
    acto = await make_acto_administrativo()
    decision = EtapaDecisionFondo(expediente_id=exp.id, acto_administrativo_id=acto.id)
    db_session.add(decision)
    await db_session.flush()

    def creable():
        return client.get(f"/decision/{exp.id}", headers=gateway_headers(1))

    sin_doc = (await creable()).json()["decision_fondo"]["creable_acto_recurso"]
    assert sin_doc["status"] is False and "Recurso" in sin_doc["msg"]

    anexo = DocumentoAnexo(etapa_tipo="etapa_decision_fondo", etapa_ref_id=decision.id, nombre="Recurso", documento_anexo_id=1)
    db_session.add(anexo)
    await db_session.flush()
    assert (await creable()).json()["decision_fondo"]["creable_acto_recurso"] == {"status": True}

    # Plazo vencido (más de 15 días hábiles desde la subida)
    anexo.fecha_subida = datetime.now(timezone.utc) - timedelta(days=60)
    await db_session.flush()
    vencido = (await creable()).json()["decision_fondo"]["creable_acto_recurso"]
    assert vencido["status"] is False and "15 días hábiles" in vencido["msg"]

    # Con el acto de recurso ya creado sigue siendo gestionable
    acto_recurso = await make_acto_administrativo()
    decision.acto_recurso_id = acto_recurso.id
    await db_session.flush()
    datos = (await creable()).json()["decision_fondo"]
    assert datos["creable_acto_recurso"] == {"status": True}
    assert datos["acto_recurso"]["id"] == acto_recurso.id
    assert datos["acto_recurso"]["nivel_auxiliar"] is True


# ── Probatoria de recurso ───────────────────────────────────────────────────

async def test_recurso_sin_etapa_devuelve_none_y_creable_en_raiz(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    body = (await client.get(f"/resource/{exp.id}", headers=gateway_headers(1))).json()
    assert body["recurso"] is None
    assert body["creable"]["status"] is False


async def test_recurso_creable_y_get_con_etapa_id(client, db_session, make_expediente, make_acto_administrativo):
    exp = await make_expediente(encargado_id=1)
    acto = await make_acto_administrativo()
    acto_recurso = await make_acto_administrativo()
    db_session.add(EtapaDecisionFondo(expediente_id=exp.id, acto_administrativo_id=acto.id, acto_recurso_id=acto_recurso.id))
    await db_session.flush()

    antes = (await client.get(f"/resource/{exp.id}", headers=gateway_headers(1))).json()
    assert antes["recurso"] is None and antes["creable"] == {"status": True}

    creado = await client.post(f"/resource/{exp.id}", headers=gateway_headers(1))
    assert creado.status_code == 201
    recurso = (await client.get(f"/resource/{exp.id}", headers=gateway_headers(1))).json()["recurso"]
    assert recurso["etapa_id"] == creado.json()["etapa_id"]
    assert recurso["tipo_etapa_id"] == 12
    assert recurso["acto_admin"] is None
    assert recurso["acto_decision"] is None

    # Recargar ya no ofrece crearla de nuevo: el POST repetido da 409.
    assert (await client.post(f"/resource/{exp.id}", headers=gateway_headers(1))).status_code == 409


async def test_recurso_acto_de_decision_auxiliar(client, db_session, make_expediente, make_acto_administrativo, sin_app_docs):
    """El acto auxiliar (nivel_auxiliar=true) de la probatoria de recurso se
    guarda en acto_decision_id y el GET lo devuelve como `acto_decision`."""
    exp = await make_expediente(encargado_id=1)
    acto_principal = await make_acto_administrativo()
    recurso = EtapaProbatoriaRecurso(expediente_id=exp.id, acto_administrativo_id=acto_principal.id)
    db_session.add(recurso)
    await db_session.flush()

    form = {
        "tipo_acto": "RES", "numerado": "77", "fecha_numerado": "2026-01-05",
        "nivel_auxiliar": "true", "documento_acto_administrativo_id": "9",
        "etapa_tipo": "etapa_probatoria_recurso", "etapa_ref_id": str(recurso.id),
    }
    resp = await client.post("http://test/acto/acto-admin", headers=gateway_headers(1), data=form)
    assert resp.status_code == 201, resp.text
    acto_id = resp.json()["data"]["id"]

    etapa = (await client.get(f"/resource/{exp.id}", headers=gateway_headers(1))).json()["recurso"]
    assert etapa["acto_admin"]["id"] == acto_principal.id
    assert etapa["acto_decision"]["id"] == acto_id
    assert etapa["acto_decision"]["nivel_auxiliar"] is True

    # Borrar el acto limpia la columna
    borrado = await client.delete(f"http://test/acto/acto-admin/{acto_id}?expediente_id={exp.id}", headers=gateway_headers(1))
    assert borrado.status_code == 200
    recurso_id = recurso.id
    db_session.expire_all()
    assert await db_session.scalar(select(EtapaProbatoriaRecurso.acto_decision_id).where(EtapaProbatoriaRecurso.id == recurso_id)) is None


async def test_acto_auxiliar_en_etapa_sin_acto_auxiliar_da_400(client, db_session, make_expediente, make_acto_administrativo, sin_app_docs):
    exp = await make_expediente(encargado_id=1)
    acto = await make_acto_administrativo()
    etapa = EtapaIndagacion(expediente_id=exp.id, acto_administrativo_id=acto.id)
    db_session.add(etapa)
    await db_session.flush()
    form = {
        "tipo_acto": "AUTO", "numerado": "78", "fecha_numerado": "2026-01-05",
        "nivel_auxiliar": "true", "documento_acto_administrativo_id": "9",
        "etapa_tipo": "etapa_indagacion", "etapa_ref_id": str(etapa.id),
    }
    resp = await client.post("http://test/acto/acto-admin", headers=gateway_headers(1), data=form)
    assert resp.status_code == 400


# ── Documentos anexos: etapa_tipo obligatorio ───────────────────────────────

async def test_doc_anexo_exige_etapa_tipo_y_lo_respeta(client, db_session, make_expediente, sin_app_docs):
    """Los ids de etapa se repiten entre tablas: sin etapa_tipo el documento
    podía terminar en otra etapa (p. ej. el informe técnico importado)."""
    exp1 = await make_expediente(encargado_id=1)
    exp2 = await make_expediente(encargado_id=1)
    indagacion = EtapaIndagacion(expediente_id=exp1.id)
    medida = EtapaMedidaPreventiva(expediente_id=exp2.id)
    db_session.add_all([indagacion, medida])
    await db_session.flush()
    assert indagacion.id == medida.id  # mismo id en dos tablas distintas

    sin_tipo = {"nombre": "Informe Tecnico", "documento_anexo_id": 5}
    assert (await client.post(f"/doc-attached/{medida.id}", headers=gateway_headers(1), json=sin_tipo)).status_code == 422
    tipo_invalido = {**sin_tipo, "etapa_tipo": "etapa_inexistente"}
    assert (await client.post(f"/doc-attached/{medida.id}", headers=gateway_headers(1), json=tipo_invalido)).status_code == 400

    ok = await client.post(f"/doc-attached/{medida.id}", headers=gateway_headers(1), json={**sin_tipo, "etapa_tipo": "etapa_medida_preventiva"})
    assert ok.status_code == 201
    docs_medida = (await client.get(f"/measure/{exp2.id}", headers=gateway_headers(1))).json()["medida"]["documentos_anexos"]
    docs_indagacion = (await client.get(f"/investigation/{exp1.id}", headers=gateway_headers(1))).json()["indagacion"]["documentos_anexos"]
    assert [d["nombre"] for d in docs_medida] == ["Informe Tecnico"]
    assert docs_indagacion == []

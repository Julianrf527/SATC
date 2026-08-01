"""
Tests del motor genérico de stage.py (services/etapas.py + _get_etapa /
_post_etapa / _put_etapa). Cubre los 3 patrones representativos de las 7
etapas genéricas: sin body (indagación), body + lookup de nombre (medida
preventiva) y body + creable dependiente de otra etapa (cesación).
"""
from conftest import gateway_headers


# ── INDAGACIÓN (sin body, sin creable) ──────────────────────────────────────

async def test_indagacion_get_sin_etapa_devuelve_none(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    resp = await client.get(f"/investigation/{exp.id}", headers=gateway_headers(1))
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"ok": True, "indagacion": None}


async def test_indagacion_crear_y_obtener(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    creado = await client.post(f"/investigation/{exp.id}", headers=gateway_headers(1))
    assert creado.status_code == 201
    data = creado.json()
    assert data["ok"] is True
    assert "id" in data and "etapa_id" in data
    assert data["message"] == "Indagación creada"

    obtenido = await client.get(f"/investigation/{exp.id}", headers=gateway_headers(1))
    assert obtenido.status_code == 200
    indagacion = obtenido.json()["indagacion"]
    assert indagacion["tipo_etapa_id"] == 2
    assert indagacion["expediente_id"] == exp.id
    assert indagacion["acto_admin"] is None
    assert indagacion["documentos_anexos"] == []


async def test_indagacion_crear_duplicada_da_409(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    await client.post(f"/investigation/{exp.id}", headers=gateway_headers(1))
    resp = await client.post(f"/investigation/{exp.id}", headers=gateway_headers(1))
    assert resp.status_code == 409


# ── PERMISOS: no debe distinguir "no existe" de "existe pero no es tuyo" ───

async def test_indagacion_expediente_inexistente_da_403(client):
    resp = await client.get("/investigation/999999", headers=gateway_headers(1))
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Sin permisos sobre este expediente"


async def test_indagacion_expediente_de_otro_usuario_da_403_mismo_mensaje(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    resp = await client.get(f"/investigation/{exp.id}", headers=gateway_headers(2))
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Sin permisos sobre este expediente"


# ── MEDIDA PREVENTIVA (body + lookup de nombre para auditoría) ─────────────

async def test_medida_crear_con_body_y_actualizar(client, make_expediente, tipo_medida):
    exp = await make_expediente(encargado_id=1)
    body = {"tipo_medida_id": tipo_medida.id, "cantidad": "10", "especie": "Roble", "estado_medida": True}
    creado = await client.post(f"/measure/{exp.id}", headers=gateway_headers(1), json=body)
    assert creado.status_code == 201

    obtenido = (await client.get(f"/measure/{exp.id}", headers=gateway_headers(1))).json()
    info = obtenido["medida"]["informacion"]
    assert info["cantidad"] == "10"
    assert info["especie"] == "Roble"
    assert "tipo_medidas" in info

    nuevo_body = {"tipo_medida_id": tipo_medida.id, "cantidad": "20", "especie": "Cedro", "estado_medida": False}
    actualizado = await client.put(f"/measure/{exp.id}", headers=gateway_headers(1), json=nuevo_body)
    assert actualizado.status_code == 200

    releido = (await client.get(f"/measure/{exp.id}", headers=gateway_headers(1))).json()
    info2 = releido["medida"]["informacion"]
    assert info2["cantidad"] == "20"
    assert info2["especie"] == "Cedro"
    assert info2["estado_medida"] is False


# ── CESACIÓN (creable depende de otra etapa) ────────────────────────────────

async def test_cesacion_no_creable_sin_inicio_proceso(client, make_expediente):
    exp = await make_expediente(encargado_id=1)
    resp = await client.get(f"/cessation/{exp.id}", headers=gateway_headers(1))
    assert resp.status_code == 200
    creable = resp.json()["creable"]
    assert creable["status"] is False
    assert "inicio del proceso sancionatorio" in creable["msg"].lower()


async def test_cesacion_post_rechaza_sin_inicio_proceso(client, make_expediente, tipo_cesacion):
    exp = await make_expediente(encargado_id=1)
    resp = await client.post(f"/cessation/{exp.id}", headers=gateway_headers(1), json={"tipo_cesacion_id": tipo_cesacion.id})
    assert resp.status_code == 400


async def test_cesacion_post_ok_despues_de_inicio_proceso(client, make_expediente, tipo_cesacion):
    exp = await make_expediente(encargado_id=1)
    inicio = await client.post(f"/start-process/{exp.id}", headers=gateway_headers(1))
    assert inicio.status_code == 201

    creable = (await client.get(f"/cessation/{exp.id}", headers=gateway_headers(1))).json()["creable"]
    assert creable["status"] is True

    resp = await client.post(f"/cessation/{exp.id}", headers=gateway_headers(1), json={"tipo_cesacion_id": tipo_cesacion.id})
    assert resp.status_code == 201

"""Listado y detalle de expedientes (routes/expediente_query.py)."""
import services.etapas_lectura as etapas_lectura
from db.models import TipoVinculo


async def test_listado_paginado(client, h_consultor, crear_expediente):
    for _ in range(3):
        await crear_expediente()
    r = await client.get("/expedientes?page=1&limit=2", headers=h_consultor)
    assert r.status_code == 200
    body = r.json()
    assert body["totalCount"] == 3
    assert len(body["data"]) == 2
    r2 = await client.get("/expedientes?page=2&limit=2", headers=h_consultor)
    assert len(r2.json()["data"]) == 1
    ids = {e["id"] for e in body["data"]} | {e["id"] for e in r2.json()["data"]}
    assert len(ids) == 3
    item = body["data"][0]
    for clave in ("radicado", "expediente", "numero_vital", "vereda", "municipio", "tipo_fuente",
                  "involucrados", "version", "fecha_radicado"):
        assert clave in item


async def test_filtros(client, h_gestor, crear_expediente, catalogo, vincular):
    a = await crear_expediente(radicado="2026ER11111", expediente="CA 101-26", numero_vital="VIT-AAA")
    b = await crear_expediente(radicado="2026ER22222", expediente="CA 102-26", numero_vital="VIT-BBB",
                               vereda_id=catalogo.otra_vereda_id)
    await vincular(a.id, 501)

    async def ids(qs):
        r = await client.get(f"/expedientes?{qs}", headers=h_gestor)
        assert r.status_code == 200
        return {e["id"] for e in r.json()["data"]}

    assert await ids("radicado=11111") == {a.id}
    assert await ids("expediente=ca 102") == {b.id}
    assert await ids("numero_vital=bbb") == {b.id}
    assert await ids(f"vereda_id={catalogo.vereda_id}") == {a.id}
    assert await ids(f"municipio_id={catalogo.otro_municipio_id}") == {b.id}
    assert await ids("involucrado_id=501") == {a.id}
    assert await ids("involucrado_id=999") == set()
    assert await ids("") == {a.id, b.id}


async def test_listado_resuelve_involucrados(client, h_consultor, crear_expediente, vincular, stubs):
    exp = await crear_expediente()
    stubs.involved.registrar(7, nombre="Ana Pérez")
    await vincular(exp.id, 7)
    data = (await client.get("/expedientes", headers=h_consultor)).json()["data"]
    assert data[0]["involucrados"] == [{
        "involucrado_id": 7, "tipo_vinculo": "SOLICITANTE", "nombre": "Ana Pérez",
        "tipo_documento": "CC", "numero_documento": 1_000_007,
    }]


async def test_listado_sin_permiso_403(client, h_sin_permisos):
    r = await client.get("/expedientes", headers=h_sin_permisos)
    assert r.status_code == 403


async def test_detalle_completo(client, h_gestor, crear_expediente, catalogo, vincular, stubs):
    exp = await crear_expediente(fuente_ids=catalogo.fuente_ids, usos=["RIEGO", "DOMESTICO"])
    stubs.involved.registrar(20, nombre="Acueducto Veredal", tipo_documento="NIT")
    stubs.involved.registrar(21, nombre="Representante")
    await vincular(exp.id, 20, representante_id=21)
    await vincular(exp.id, 22, tipo_vinculo=TipoVinculo.TERCERO_INTERVINIENTE)

    r = await client.get(f"/expedientes/{exp.id}", headers=h_gestor)
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["version"] == 1
    assert d["expediente"] == exp.expediente
    assert d["vereda"]["id"] == catalogo.vereda_id
    assert d["municipio"]["id"] == catalogo.municipio_id
    assert d["tipo_fuente"]["id"] == catalogo.tipo_fuente_id
    assert sorted(f["id"] for f in d["fuentes"]) == sorted(catalogo.fuente_ids)
    assert d["usos"] == ["DOMESTICO", "RIEGO"]
    assert d["comprobante_pago"]["file_id"] == exp.doc_comprobante_pago_id
    # Forma real del árbol: sección C de API.md (agente C).
    assert d["etapas"]["etapa_actual"] is None and "admite" in d["etapas"]
    assert d["acciones_disponibles"] == ["editar_informacion_base", "vincular_solicitante", "descargar_expediente"]

    solicitante, tercero = d["involucrados"]
    assert solicitante["tipo_vinculo"] == "SOLICITANTE"
    assert solicitante["involucrado"]["nombre"] == "Acueducto Veredal"
    assert solicitante["representante"]["nombre"] == "Representante"
    assert solicitante["requiere_representante"] is True
    assert solicitante["version"] == 1
    assert solicitante["acciones_disponibles"] == ["editar_representante", "desvincular"]
    assert tercero["tipo_vinculo"] == "TERCERO_INTERVINIENTE"
    assert tercero["acciones_disponibles"] == []


async def test_detalle_consulta_sin_acciones_de_gestion(client, h_consultor, crear_expediente, vincular):
    exp = await crear_expediente()
    await vincular(exp.id, 30)
    d = (await client.get(f"/expedientes/{exp.id}", headers=h_consultor)).json()["data"]
    assert d["acciones_disponibles"] == ["descargar_expediente"]
    assert d["involucrados"][0]["acciones_disponibles"] == []


async def test_detalle_usa_hook_de_etapas(client, h_consultor, crear_expediente, monkeypatch):
    exp = await crear_expediente()
    llamado = {}

    async def _leer(db, expediente, usuario):
        llamado["args"] = (expediente.id, usuario.user_id)
        return {"acto_admite": None}

    import routes.expediente_query as q
    monkeypatch.setattr(q, "leer_etapas", _leer)
    d = (await client.get(f"/expedientes/{exp.id}", headers=h_consultor)).json()["data"]
    assert d["etapas"] == {"acto_admite": None}
    assert llamado["args"] == (exp.id, 11)
    assert etapas_lectura.leer_etapas is not _leer


async def test_detalle_app_involved_caido_no_rompe(client, h_consultor, crear_expediente, vincular, stubs):
    exp = await crear_expediente()
    await vincular(exp.id, 40)
    stubs.involved.caido = True
    r = await client.get(f"/expedientes/{exp.id}", headers=h_consultor)
    assert r.status_code == 200
    assert r.json()["data"]["involucrados"][0]["involucrado"] == {"id": 40}


async def test_detalle_inexistente_404(client, h_consultor):
    r = await client.get("/expedientes/99999", headers=h_consultor)
    assert r.status_code == 404


async def test_detalle_sin_permiso_403(client, h_sin_permisos, crear_expediente):
    exp = await crear_expediente()
    r = await client.get(f"/expedientes/{exp.id}", headers=h_sin_permisos)
    assert r.status_code == 403

"""Crear y editar la información base (routes/expediente_mutations.py)."""
import asyncio

from sqlalchemy import select

from db.models import Auditoria, Expediente, ExpedienteFuente, ExpedienteUso
from tests.conftest import TestSessionLocal


async def _expediente_bd(expediente_id: int) -> Expediente:
    async with TestSessionLocal() as s:
        return await s.get(Expediente, expediente_id)


# ─── Crear ───────────────────────────────────────────────────────────────────

async def test_crear_expediente(client, h_gestor, payload_expediente, catalogo, stubs):
    body = payload_expediente(fuente_ids=catalogo.fuente_ids, usos=["DOMESTICO", "RIEGO", "RIEGO"])
    r = await client.post("/expedientes", json=body, headers=h_gestor)
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["version"] == 1
    assert data["expediente"] == body["expediente"]

    async with TestSessionLocal() as s:
        exp = await s.get(Expediente, data["id"])
        assert exp.radicado == body["radicado"]
        assert exp.numero_vital == body["numero_vital"]
        fuentes = (await s.execute(select(ExpedienteFuente.fuente_id).where(ExpedienteFuente.expediente_id == exp.id))).scalars().all()
        usos = (await s.execute(select(ExpedienteUso.uso).where(ExpedienteUso.expediente_id == exp.id))).scalars().all()
        assert sorted(fuentes) == sorted(catalogo.fuente_ids)
        assert sorted(u.value for u in usos) == ["DOMESTICO", "RIEGO"]  # sin repetidos
        log = (await s.execute(select(Auditoria))).scalars().all()
        assert [a.tipo_evento for a in log] == ["INSERT_EXPEDIENTE"]
        assert log[0].usuario_id == 10
    assert stubs.files.incrementados == [body["doc_comprobante_pago_id"]]


async def test_crear_con_super_gestion(client, h_super, payload_expediente):
    r = await client.post("/expedientes", json=payload_expediente(), headers=h_super)
    assert r.status_code == 201


async def test_crear_sin_permiso_de_gestion_403(client, h_consultor, payload_expediente, stubs):
    r = await client.post("/expedientes", json=payload_expediente(), headers=h_consultor)
    assert r.status_code == 403
    assert stubs.files.incrementados == []


async def test_campos_obligatorios_422(client, h_gestor, payload_expediente):
    for campo in ("numero_vital", "nombre_predio", "matricula_inmobiliaria", "codigo_catastral",
                  "doc_comprobante_pago_id", "vereda_id", "tipo_fuente_id", "nombre_fuente"):
        body = payload_expediente()
        body.pop(campo)
        r = await client.post("/expedientes", json=body, headers=h_gestor)
        assert r.status_code == 422, campo
    r = await client.post("/expedientes", json=payload_expediente(numero_vital="   "), headers=h_gestor)
    assert r.status_code == 422
    r = await client.post("/expedientes", json=payload_expediente(fuente_ids=[]), headers=h_gestor)
    assert r.status_code == 422
    r = await client.post("/expedientes", json=payload_expediente(usos=["NO_EXISTE"]), headers=h_gestor)
    assert r.status_code == 422
    r = await client.post("/expedientes", json=payload_expediente(expediente="CA 0001-2026"), headers=h_gestor)
    assert r.status_code == 422  # varchar(9)


async def test_radicado_duplicado_409(client, h_gestor, payload_expediente, crear_expediente):
    existente = await crear_expediente()
    r = await client.post("/expedientes", json=payload_expediente(radicado=existente.radicado), headers=h_gestor)
    assert r.status_code == 409
    assert "radicado" in r.json()["detail"]


async def test_numero_expediente_duplicado_409(client, h_gestor, payload_expediente, crear_expediente):
    existente = await crear_expediente(expediente="CA 001-26")
    r = await client.post("/expedientes", json=payload_expediente(expediente="CA 001-26"), headers=h_gestor)
    assert r.status_code == 409
    assert "número de expediente" in r.json()["detail"]


async def test_creacion_concurrente_mismo_radicado_una_409(client, h_gestor, payload_expediente):
    a = payload_expediente(radicado="2026ER77777")
    b = payload_expediente(radicado="2026ER77777")
    r1, r2 = await asyncio.gather(
        client.post("/expedientes", json=a, headers=h_gestor),
        client.post("/expedientes", json=b, headers=h_gestor),
    )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409]
    async with TestSessionLocal() as s:
        assert len((await s.execute(select(Expediente))).scalars().all()) == 1


async def test_catalogos_inexistentes_400(client, h_gestor, payload_expediente):
    r = await client.post("/expedientes", json=payload_expediente(vereda_id=999999), headers=h_gestor)
    assert r.status_code == 400 and "vereda" in r.json()["detail"]
    r = await client.post("/expedientes", json=payload_expediente(tipo_fuente_id=999999), headers=h_gestor)
    assert r.status_code == 400 and "tipo de fuente" in r.json()["detail"]
    r = await client.post("/expedientes", json=payload_expediente(fuente_ids=[999999]), headers=h_gestor)
    assert r.status_code == 400 and "Fuentes" in r.json()["detail"]


async def test_comprobante_inexistente_o_no_pdf_400(client, h_gestor, payload_expediente, stubs):
    r = await client.post("/expedientes", json=payload_expediente(doc_comprobante_pago_id=99999), headers=h_gestor)
    assert r.status_code == 400
    imagen = stubs.files.registrar(b"PNG", "image/png")
    r = await client.post("/expedientes", json=payload_expediente(doc_comprobante_pago_id=imagen), headers=h_gestor)
    assert r.status_code == 400
    assert "PDF" in r.json()["detail"]


async def test_falla_registro_de_uso_502_y_no_crea(client, h_gestor, payload_expediente, stubs):
    stubs.files.fallar_incremento = True
    r = await client.post("/expedientes", json=payload_expediente(), headers=h_gestor)
    assert r.status_code == 502
    async with TestSessionLocal() as s:
        assert (await s.execute(select(Expediente))).scalars().all() == []


# ─── Editar ──────────────────────────────────────────────────────────────────

async def test_editar_expediente_reemplaza_fuentes_y_usos(
    client, h_gestor, payload_expediente, crear_expediente, catalogo, stubs
):
    exp = await crear_expediente(fuente_ids=catalogo.fuente_ids[:1], usos=["DOMESTICO"])
    body = payload_expediente(
        radicado=exp.radicado, expediente=exp.expediente,
        doc_comprobante_pago_id=exp.doc_comprobante_pago_id,
        nombre_predio="El Cedro", vereda_id=catalogo.otra_vereda_id,
        fuente_ids=catalogo.fuente_ids[1:], usos=["PECUARIO", "ABREVADERO"],
        version=1,
    )
    r = await client.put(f"/expedientes/{exp.id}", json=body, headers=h_gestor)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["version"] == 2

    detalle = (await client.get(f"/expedientes/{exp.id}", headers=h_gestor)).json()["data"]
    assert detalle["version"] == 2
    assert detalle["nombre_predio"] == "El Cedro"
    assert detalle["vereda"]["id"] == catalogo.otra_vereda_id
    assert [f["id"] for f in detalle["fuentes"]] == catalogo.fuente_ids[1:]
    assert detalle["usos"] == ["ABREVADERO", "PECUARIO"]
    # El comprobante no cambió: no se toca su contador de usos.
    assert stubs.files.incrementados == [] and stubs.files.decrementados == []

    async with TestSessionLocal() as s:
        log = (await s.execute(select(Auditoria).where(Auditoria.tipo_evento == "UPDATE_EXPEDIENTE_BASICO"))).scalar_one()
        assert log.datos_anteriores["nombre_predio"] == "La Esperanza"
        assert log.datos_nuevos["nombre_predio"] == "El Cedro"
        assert log.datos_nuevos["usos"] == ["ABREVADERO", "PECUARIO"]


async def test_editar_reemplaza_comprobante_y_ajusta_usos_de_archivo(
    client, h_gestor, payload_expediente, crear_expediente, stubs
):
    exp = await crear_expediente()
    nuevo = stubs.files.registrar()
    body = payload_expediente(
        radicado=exp.radicado, expediente=exp.expediente, doc_comprobante_pago_id=nuevo, version=1
    )
    r = await client.put(f"/expedientes/{exp.id}", json=body, headers=h_gestor)
    assert r.status_code == 200
    assert stubs.files.incrementados == [nuevo]
    assert stubs.files.decrementados == [exp.doc_comprobante_pago_id]


async def test_editar_con_version_vieja_409(client, h_gestor, payload_expediente, crear_expediente):
    exp = await crear_expediente()
    base = dict(radicado=exp.radicado, expediente=exp.expediente,
                doc_comprobante_pago_id=exp.doc_comprobante_pago_id)
    r = await client.put(f"/expedientes/{exp.id}", json=payload_expediente(**base, version=1), headers=h_gestor)
    assert r.status_code == 200
    r = await client.put(
        f"/expedientes/{exp.id}", json=payload_expediente(**base, nombre_predio="Otro", version=1), headers=h_gestor
    )
    assert r.status_code == 409
    assert "otra persona" in r.json()["detail"]
    assert (await _expediente_bd(exp.id)).nombre_predio == "La Esperanza"


async def test_edicion_concurrente_misma_version_una_200_una_409(
    client, h_gestor, payload_expediente, crear_expediente, catalogo
):
    """Plan §7: dos ediciones con la misma version → una 200 y una 409, sin pisar datos."""
    exp = await crear_expediente()
    base = dict(radicado=exp.radicado, expediente=exp.expediente,
                doc_comprobante_pago_id=exp.doc_comprobante_pago_id, version=1)
    a = payload_expediente(**base, nombre_predio="Predio A", usos=["RIEGO"])
    b = payload_expediente(**base, nombre_predio="Predio B", usos=["INDUSTRIAL"], fuente_ids=catalogo.fuente_ids)

    r1, r2 = await asyncio.gather(
        client.put(f"/expedientes/{exp.id}", json=a, headers=h_gestor),
        client.put(f"/expedientes/{exp.id}", json=b, headers=h_gestor),
    )
    assert sorted([r1.status_code, r2.status_code]) == [200, 409]
    ganador = a if r1.status_code == 200 else b

    detalle = (await client.get(f"/expedientes/{exp.id}", headers=h_gestor)).json()["data"]
    assert detalle["version"] == 2
    assert detalle["nombre_predio"] == ganador["nombre_predio"]
    # Fuentes y usos quedan coherentes con la edición ganadora (no mezclados).
    assert detalle["usos"] == ganador["usos"]
    assert [f["id"] for f in detalle["fuentes"]] == sorted(ganador["fuente_ids"])


async def test_editar_a_radicado_de_otro_409(client, h_gestor, payload_expediente, crear_expediente):
    otro = await crear_expediente()
    exp = await crear_expediente()
    body = payload_expediente(radicado=otro.radicado, expediente=exp.expediente,
                              doc_comprobante_pago_id=exp.doc_comprobante_pago_id, version=1)
    r = await client.put(f"/expedientes/{exp.id}", json=body, headers=h_gestor)
    assert r.status_code == 409


async def test_editar_inexistente_404(client, h_gestor, payload_expediente):
    r = await client.put("/expedientes/99999", json=payload_expediente(version=1), headers=h_gestor)
    assert r.status_code == 404


async def test_editar_sin_version_422(client, h_gestor, payload_expediente, crear_expediente):
    exp = await crear_expediente()
    r = await client.put(f"/expedientes/{exp.id}", json=payload_expediente(), headers=h_gestor)
    assert r.status_code == 422


async def test_editar_solo_consulta_403(client, h_consultor, payload_expediente, crear_expediente):
    exp = await crear_expediente()
    r = await client.put(f"/expedientes/{exp.id}", json=payload_expediente(version=1), headers=h_consultor)
    assert r.status_code == 403

"""CRUD y consulta de involucrados."""
import pytest
from sqlalchemy import select

from db.models.involucrado import Involucrado
from db.models.auditoria import Auditoria
from tests.conftest import gateway_headers, service_headers, USER_ID

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------
# GET /involved/{id}
# --------------------------------------------------------------------------

async def test_get_por_id_sin_permiso_403(client, permisos, make_involucrado):
    inv = await make_involucrado()
    r = await client.get(f"/involved/{inv.id}", headers=gateway_headers())
    assert r.status_code == 403


async def test_get_por_id_inexistente_sin_permiso_tambien_403(client, permisos):
    """Sin permiso la respuesta es 403 exista o no el recurso: no filtra existencia."""
    r = await client.get("/involved/999999", headers=gateway_headers())
    assert r.status_code == 403


async def test_get_por_id_existente_y_no_existente_indistinguibles_sin_permiso(
    client, permisos, make_involucrado
):
    inv = await make_involucrado()
    existente = await client.get(f"/involved/{inv.id}", headers=gateway_headers())
    fantasma = await client.get("/involved/999999", headers=gateway_headers())
    assert existente.status_code == fantasma.status_code == 403
    assert existente.json() == fantasma.json()


async def test_get_por_id_con_permiso_200(client, con_gestion, make_involucrado):
    inv = await make_involucrado(nombre="Ana Gómez")
    r = await client.get(f"/involved/{inv.id}", headers=gateway_headers())
    assert r.status_code == 200
    assert r.json()["data"]["nombre"] == "Ana Gómez"


async def test_get_por_id_inexistente_con_permiso_404(client, con_gestion):
    r = await client.get("/involved/999999", headers=gateway_headers())
    assert r.status_code == 404


async def test_get_por_id_cero_es_422(client, con_gestion):
    r = await client.get("/involved/0", headers=gateway_headers())
    assert r.status_code == 422


# --------------------------------------------------------------------------
# GET /involved/search
# --------------------------------------------------------------------------

async def test_search_sin_permiso_403(client, permisos, make_involucrado):
    inv = await make_involucrado()
    r = await client.get(
        f"/involved/search/CC/{inv.numero_documento}", headers=gateway_headers()
    )
    assert r.status_code == 403


async def test_search_encuentra(client, con_gestion, make_involucrado):
    inv = await make_involucrado(nombre="Carlos Ruiz")
    r = await client.get(
        f"/involved/search/CC/{inv.numero_documento}", headers=gateway_headers()
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["nombre"] == "Carlos Ruiz"


async def test_search_no_encuentra_devuelve_ok_false(client, con_gestion):
    r = await client.get("/involved/search/CC/1111111111", headers=gateway_headers())
    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert r.json()["data"] is None


async def test_search_documento_no_numerico_400(client, con_gestion):
    r = await client.get("/involved/search/CC/abcdef", headers=gateway_headers())
    assert r.status_code == 400


async def test_search_nit_sin_dv_encuentra_igual(client, con_gestion, make_involucrado):
    inv = await make_involucrado(tipo_documento="NIT", digito_verificacion="7")
    r = await client.get(
        f"/involved/search/NIT/{inv.numero_documento}", headers=gateway_headers()
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


async def test_search_nit_con_dv_incorrecto_no_encuentra(client, con_gestion, make_involucrado):
    inv = await make_involucrado(tipo_documento="NIT", digito_verificacion="7")
    r = await client.get(
        f"/involved/search/NIT/{inv.numero_documento}?dv=3", headers=gateway_headers()
    )
    assert r.status_code == 200
    assert r.json()["ok"] is False


# --------------------------------------------------------------------------
# GET /involved/manage
# --------------------------------------------------------------------------

async def test_manage_sin_permiso_403(client, permisos):
    r = await client.get("/involved/manage", headers=gateway_headers())
    assert r.status_code == 403


async def test_manage_lista_paginada(client, con_gestion, make_involucrado):
    for i in range(3):
        await make_involucrado(nombre=f"Persona {i}")
    r = await client.get("/involved/manage", headers=gateway_headers())
    assert r.status_code == 200
    body = r.json()
    assert body["totalCount"] == 3
    assert len(body["data"]) == 3


async def test_manage_respeta_limit(client, con_gestion, make_involucrado):
    for i in range(5):
        await make_involucrado()
    r = await client.get("/involved/manage?limit=2", headers=gateway_headers())
    assert r.json()["totalCount"] == 5
    assert len(r.json()["data"]) == 2


async def test_manage_segunda_pagina(client, con_gestion, make_involucrado):
    for i in range(5):
        await make_involucrado()
    r = await client.get("/involved/manage?limit=2&page=2", headers=gateway_headers())
    assert len(r.json()["data"]) == 2


async def test_manage_filtra_por_nombre_parcial(client, con_gestion, make_involucrado):
    await make_involucrado(nombre="Mariana Lopez")
    await make_involucrado(nombre="Pedro Perez")
    r = await client.get("/involved/manage?nombre=maria", headers=gateway_headers())
    assert r.json()["totalCount"] == 1
    assert r.json()["data"][0]["nombre"] == "Mariana Lopez"


async def test_manage_filtra_por_correo_parcial(client, con_gestion, make_involucrado):
    await make_involucrado(correo="unico@dominio.com")
    await make_involucrado(correo="otro@example.com")
    r = await client.get("/involved/manage?correo=dominio", headers=gateway_headers())
    assert r.json()["totalCount"] == 1


async def test_manage_filtra_por_tipo_documento(client, con_gestion, make_involucrado):
    await make_involucrado(tipo_documento="CC")
    await make_involucrado(tipo_documento="NIT", digito_verificacion="1")
    r = await client.get("/involved/manage?tipo_documento=NIT", headers=gateway_headers())
    assert r.json()["totalCount"] == 1


async def test_manage_filtro_documento_no_numerico_devuelve_vacio(client, con_gestion, make_involucrado):
    await make_involucrado()
    r = await client.get("/involved/manage?numero_documento=abc", headers=gateway_headers())
    assert r.status_code == 200
    assert r.json()["data"] == []
    assert r.json()["totalCount"] == 0


async def test_manage_limit_fuera_de_rango_422(client, con_gestion):
    r = await client.get("/involved/manage?limit=500", headers=gateway_headers())
    assert r.status_code == 422


async def test_manage_page_cero_422(client, con_gestion):
    r = await client.get("/involved/manage?page=0", headers=gateway_headers())
    assert r.status_code == 422


# --------------------------------------------------------------------------
# POST /involved/new
# --------------------------------------------------------------------------

BASE_NUEVO = {
    "numero_documento": 1098765432,
    "tipo_documento": "CC",
    "nombre": "Nuevo Involucrado",
    "celular": 3009998877,
    "correo": "Nuevo@Test.COM",
    "direccion": "Cra 5 # 10-20",
}


async def test_crear_sin_permiso_403(client, permisos):
    r = await client.post("/involved/new", json=BASE_NUEVO, headers=gateway_headers())
    assert r.status_code == 403


async def test_crear_sin_permiso_no_persiste(client, permisos, db_session):
    await client.post("/involved/new", json=BASE_NUEVO, headers=gateway_headers())
    total = (await db_session.execute(select(Involucrado))).scalars().all()
    assert total == []


async def test_crear_ok(client, con_gestion, db_session):
    r = await client.post("/involved/new", json=BASE_NUEVO, headers=gateway_headers())
    assert r.status_code == 201, r.text
    assert r.json()["ok"] is True

    guardado = (await db_session.execute(select(Involucrado))).scalars().all()
    assert len(guardado) == 1
    assert guardado[0].nombre == "Nuevo Involucrado"


async def test_crear_normaliza_correo_a_minusculas(client, con_gestion, db_session):
    await client.post("/involved/new", json=BASE_NUEVO, headers=gateway_headers())
    inv = (await db_session.execute(select(Involucrado))).scalars().first()
    assert inv.correo == "nuevo@test.com"


async def test_crear_registra_auditoria(client, con_gestion, db_session):
    await client.post("/involved/new", json=BASE_NUEVO, headers=gateway_headers())
    auds = (await db_session.execute(select(Auditoria))).scalars().all()
    assert len(auds) == 1
    assert auds[0].tipo_evento == "CREAR_INVOLUCRADO"
    assert auds[0].usuario_id == USER_ID


async def test_crear_duplicado_400(client, con_gestion, make_involucrado):
    await make_involucrado(numero_documento=BASE_NUEVO["numero_documento"], tipo_documento="CC")
    r = await client.post("/involved/new", json=BASE_NUEVO, headers=gateway_headers())
    assert r.status_code == 400


async def test_crear_duplicado_carrera_409(client, con_gestion, make_involucrado, monkeypatch):
    """Si 2 requests concurrentes pasan el pre-check a la vez, la constraint
    UNIQUE de la BD debe frenar al segundo insert con 409, no un 500 crudo."""
    await make_involucrado(numero_documento=BASE_NUEVO["numero_documento"], tipo_documento="CC")

    async def _nunca_existe(*args, **kwargs):
        return None

    monkeypatch.setattr("routes.involved.verificar_involucrado_existe", _nunca_existe)

    r = await client.post("/involved/new", json=BASE_NUEVO, headers=gateway_headers())
    assert r.status_code == 409


async def test_crear_documento_muy_corto_422(client, con_gestion):
    payload = {**BASE_NUEVO, "numero_documento": 123}
    r = await client.post("/involved/new", json=payload, headers=gateway_headers())
    assert r.status_code == 422


async def test_crear_celular_muy_corto_422(client, con_gestion):
    payload = {**BASE_NUEVO, "celular": 123}
    r = await client.post("/involved/new", json=payload, headers=gateway_headers())
    assert r.status_code == 422


async def test_crear_correo_invalido_422(client, con_gestion):
    payload = {**BASE_NUEVO, "correo": "no-es-un-correo"}
    r = await client.post("/involved/new", json=payload, headers=gateway_headers())
    assert r.status_code == 422


async def test_crear_nombre_vacio_422(client, con_gestion):
    payload = {**BASE_NUEVO, "nombre": ""}
    r = await client.post("/involved/new", json=payload, headers=gateway_headers())
    assert r.status_code == 422


async def test_crear_sin_campos_obligatorios_422(client, con_gestion):
    r = await client.post("/involved/new", json={}, headers=gateway_headers())
    assert r.status_code == 422


async def test_crear_permite_opcionales_nulos(client, con_gestion):
    payload = {"numero_documento": 1122334455, "tipo_documento": "CC", "nombre": "Minimo"}
    r = await client.post("/involved/new", json=payload, headers=gateway_headers())
    assert r.status_code == 201, r.text


# --------------------------------------------------------------------------
# PUT /involved/{id}
# --------------------------------------------------------------------------

async def test_actualizar_sin_permiso_403(client, permisos, make_involucrado):
    inv = await make_involucrado()
    r = await client.put(f"/involved/{inv.id}", json={"nombre": "Otro"}, headers=gateway_headers())
    assert r.status_code == 403


async def test_actualizar_sin_permiso_inexistente_tambien_403(client, permisos):
    r = await client.put("/involved/999999", json={"nombre": "Otro"}, headers=gateway_headers())
    assert r.status_code == 403


async def test_actualizar_inexistente_con_permiso_404(client, con_gestion):
    r = await client.put("/involved/999999", json={"nombre": "Otro"}, headers=gateway_headers())
    assert r.status_code == 404


async def test_actualizar_ok(client, con_gestion, make_involucrado, db_session):
    inv = await make_involucrado(nombre="Antiguo")
    r = await client.put(
        f"/involved/{inv.id}", json={"nombre": "Renovado"}, headers=gateway_headers()
    )
    assert r.status_code == 200, r.text
    await db_session.refresh(inv)
    assert inv.nombre == "Renovado"


async def test_actualizar_parcial_no_borra_otros_campos(client, con_gestion, make_involucrado, db_session):
    """PUT con solo `nombre` no debe poner celular/correo/direccion en NULL."""
    inv = await make_involucrado(
        nombre="Antiguo", celular=3001112222, correo="mantener@test.com", direccion="Calle Vieja"
    )
    r = await client.put(
        f"/involved/{inv.id}", json={"nombre": "Renovado"}, headers=gateway_headers()
    )
    assert r.status_code == 200
    await db_session.refresh(inv)
    assert inv.celular == 3001112222
    assert inv.correo == "mantener@test.com"
    assert inv.direccion == "Calle Vieja"


async def test_actualizar_puede_vaciar_campo_explicitamente(client, con_gestion, make_involucrado, db_session):
    inv = await make_involucrado(correo="borrame@test.com")
    r = await client.put(
        f"/involved/{inv.id}",
        json={"nombre": inv.nombre, "correo": None},
        headers=gateway_headers(),
    )
    assert r.status_code == 200
    await db_session.refresh(inv)
    assert inv.correo is None


async def test_actualizar_normaliza_correo(client, con_gestion, make_involucrado, db_session):
    inv = await make_involucrado()
    await client.put(
        f"/involved/{inv.id}",
        json={"nombre": inv.nombre, "correo": "MAYUS@Test.CO"},
        headers=gateway_headers(),
    )
    await db_session.refresh(inv)
    assert inv.correo == "mayus@test.co"


async def test_actualizar_registra_auditoria_con_datos_anteriores(
    client, con_gestion, make_involucrado, db_session
):
    inv = await make_involucrado(nombre="Antes")
    await client.put(f"/involved/{inv.id}", json={"nombre": "Despues"}, headers=gateway_headers())
    aud = (await db_session.execute(select(Auditoria))).scalars().first()
    assert aud.tipo_evento == "ACTUALIZAR_INVOLUCRADO"
    assert aud.datos_anteriores["nombre"] == "Antes"
    assert aud.datos_nuevos["nombre"] == "Despues"


async def test_actualizar_documento_a_uno_ocupado_400(client, con_gestion, make_involucrado):
    ocupado = await make_involucrado(numero_documento=1555000111, tipo_documento="CC")
    inv = await make_involucrado(numero_documento=1555000222, tipo_documento="CC")
    r = await client.put(
        f"/involved/{inv.id}",
        json={"nombre": inv.nombre, "numero_documento": ocupado.numero_documento},
        headers=gateway_headers(),
    )
    assert r.status_code == 400


async def test_actualizar_documento_a_uno_libre_ok(client, con_gestion, make_involucrado, db_session):
    inv = await make_involucrado(numero_documento=1555000333)
    r = await client.put(
        f"/involved/{inv.id}",
        json={"nombre": inv.nombre, "numero_documento": 1555000444},
        headers=gateway_headers(),
    )
    assert r.status_code == 200, r.text
    await db_session.refresh(inv)
    assert inv.numero_documento == 1555000444


async def test_actualizar_mismo_documento_no_da_conflicto(client, con_gestion, make_involucrado):
    inv = await make_involucrado()
    r = await client.put(
        f"/involved/{inv.id}",
        json={"nombre": "Igual", "numero_documento": inv.numero_documento},
        headers=gateway_headers(),
    )
    assert r.status_code == 200


async def test_actualizar_sin_nombre_422(client, con_gestion, make_involucrado):
    inv = await make_involucrado()
    r = await client.put(f"/involved/{inv.id}", json={}, headers=gateway_headers())
    assert r.status_code == 422


async def test_actualizar_celular_invalido_422(client, con_gestion, make_involucrado):
    inv = await make_involucrado()
    r = await client.put(
        f"/involved/{inv.id}", json={"nombre": "X", "celular": 12}, headers=gateway_headers()
    )
    assert r.status_code == 422


# --------------------------------------------------------------------------
# POST /involved/bulk
# --------------------------------------------------------------------------

async def test_bulk_devuelve_los_pedidos(client, make_involucrado):
    a = await make_involucrado(nombre="A")
    b = await make_involucrado(nombre="B")
    await make_involucrado(nombre="C")
    r = await client.post(
        "/involved/bulk", json={"ids": [a.id, b.id]}, headers=service_headers()
    )
    assert r.status_code == 200
    assert r.json()["total"] == 2
    assert {d["nombre"] for d in r.json()["data"]} == {"A", "B"}


async def test_bulk_ids_inexistentes_devuelve_vacio(client):
    r = await client.post("/involved/bulk", json={"ids": [999999]}, headers=service_headers())
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_bulk_filtra_por_tipo_documento(client, make_involucrado):
    cc = await make_involucrado(tipo_documento="CC")
    nit = await make_involucrado(tipo_documento="NIT", digito_verificacion="4")
    r = await client.post(
        "/involved/bulk",
        json={"ids": [cc.id, nit.id], "tipo_documento": "NIT"},
        headers=service_headers(),
    )
    assert r.json()["total"] == 1


async def test_bulk_lista_vacia_422(client):
    r = await client.post("/involved/bulk", json={"ids": []}, headers=service_headers())
    assert r.status_code == 422

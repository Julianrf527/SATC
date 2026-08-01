"""Log de auditoría: GET /involved/log."""
from datetime import datetime, timedelta

import pytest

from tests.conftest import gateway_headers, USER_ID

pytestmark = pytest.mark.asyncio


async def test_log_sin_permiso_403(client, permisos):
    r = await client.get("/involved/log", headers=gateway_headers())
    assert r.status_code == 403


async def test_log_con_permiso_de_gestion_no_alcanza(client, con_gestion):
    """involucrado_gestionar no habilita el log: exige auditoria_involucrados."""
    r = await client.get("/involved/log", headers=gateway_headers())
    assert r.status_code == 403


async def test_log_vacio(client, con_auditoria, sin_usuarios):
    r = await client.get("/involved/log", headers=gateway_headers())
    assert r.status_code == 200
    assert r.json()["data"] == []
    assert r.json()["pagination"]["total"] == 0


async def test_log_lista_registros(client, con_auditoria, sin_usuarios, make_auditoria):
    for _ in range(3):
        await make_auditoria()
    r = await client.get("/involved/log", headers=gateway_headers())
    assert r.status_code == 200
    assert r.json()["pagination"]["total"] == 3
    assert len(r.json()["data"]) == 3


async def test_log_ordena_por_fecha_descendente(client, con_auditoria, sin_usuarios, make_auditoria):
    ahora = datetime.now()
    await make_auditoria(detalle="viejo", fecha=ahora - timedelta(days=2))
    await make_auditoria(detalle="nuevo", fecha=ahora)
    r = await client.get("/involved/log", headers=gateway_headers())
    assert r.json()["data"][0]["detalle"] == "nuevo"


async def test_log_pagina(client, con_auditoria, sin_usuarios, make_auditoria):
    for _ in range(5):
        await make_auditoria()
    r = await client.get("/involved/log?limit=2", headers=gateway_headers())
    assert len(r.json()["data"]) == 2
    assert r.json()["pagination"]["total"] == 5
    assert r.json()["pagination"]["pages"] == 3


async def test_log_offset_tiene_prioridad_sobre_page(client, con_auditoria, sin_usuarios, make_auditoria):
    for i in range(5):
        await make_auditoria(detalle=f"registro {i}")
    r = await client.get("/involved/log?limit=1&offset=0", headers=gateway_headers())
    primero = r.json()["data"][0]["id"]
    r2 = await client.get("/involved/log?limit=1&offset=1", headers=gateway_headers())
    assert r2.json()["data"][0]["id"] != primero


async def test_log_filtra_por_usuario_id(client, con_auditoria, sin_usuarios, make_auditoria):
    await make_auditoria(usuario_id=USER_ID)
    await make_auditoria(usuario_id=999)
    r = await client.get(f"/involved/log?usuario_id={USER_ID}", headers=gateway_headers())
    assert r.json()["pagination"]["total"] == 1


async def test_log_filtra_por_tipo_evento(client, con_auditoria, sin_usuarios, make_auditoria):
    await make_auditoria(tipo_evento="CREAR_INVOLUCRADO")
    await make_auditoria(tipo_evento="ACTUALIZAR_INVOLUCRADO")
    r = await client.get("/involved/log?tipo_evento=CREAR_INVOLUCRADO", headers=gateway_headers())
    assert r.json()["pagination"]["total"] == 1


async def test_log_filtra_por_resultado(client, con_auditoria, sin_usuarios, make_auditoria):
    await make_auditoria(resultado="EXITOSO")
    await make_auditoria(resultado="ERROR")
    r = await client.get("/involved/log?resultado=ERROR", headers=gateway_headers())
    assert r.json()["pagination"]["total"] == 1


async def test_log_filtra_por_rango_de_fechas(client, con_auditoria, sin_usuarios, make_auditoria):
    ahora = datetime.now()
    await make_auditoria(detalle="antiguo", fecha=ahora - timedelta(days=10))
    await make_auditoria(detalle="reciente", fecha=ahora)
    desde = (ahora - timedelta(days=1)).strftime("%Y-%m-%d")
    r = await client.get(f"/involved/log?fecha_inicio={desde}", headers=gateway_headers())
    assert r.json()["pagination"]["total"] == 1
    assert r.json()["data"][0]["detalle"] == "reciente"


async def test_log_fecha_fin_es_inclusiva(client, con_auditoria, sin_usuarios, make_auditoria):
    """Un registro creado hoy debe entrar con fecha_fin = hoy."""
    ahora = datetime.now()
    await make_auditoria(fecha=ahora)
    hoy = ahora.strftime("%Y-%m-%d")
    r = await client.get(f"/involved/log?fecha_fin={hoy}", headers=gateway_headers())
    assert r.json()["pagination"]["total"] == 1


async def test_log_fecha_inicio_invalida_400(client, con_auditoria, sin_usuarios):
    r = await client.get("/involved/log?fecha_inicio=32-13-2026", headers=gateway_headers())
    assert r.status_code == 400


async def test_log_fecha_fin_invalida_400(client, con_auditoria, sin_usuarios):
    r = await client.get("/involved/log?fecha_fin=no-es-fecha", headers=gateway_headers())
    assert r.status_code == 400


async def test_log_limit_fuera_de_rango_422(client, con_auditoria, sin_usuarios):
    r = await client.get("/involved/log?limit=9999", headers=gateway_headers())
    assert r.status_code == 422


async def test_error_inesperado_da_500_generico_sin_filtrar_detalle(
    client, con_auditoria, make_auditoria, monkeypatch
):
    """get_db_managed convierte cualquier excepción no prevista en un 500 opaco.

    get_user_info ya atrapa sus propios errores de red, así que acá se fuerza el
    peor caso para verificar que el mensaje interno no llega al cliente.
    """
    async def _explota(user_ids):
        raise RuntimeError("credenciales secretas en el mensaje")

    import routes.involved as rutas
    monkeypatch.setattr(rutas, "get_user_info", _explota)
    await make_auditoria()
    r = await client.get("/involved/log", headers=gateway_headers())
    assert r.status_code == 500
    assert r.json()["detail"] == "Error interno del servidor"
    assert "secretas" not in r.text


async def test_log_sin_info_de_usuario_usa_placeholder(client, con_auditoria, sin_usuarios, make_auditoria):
    await make_auditoria(usuario_id=777)
    r = await client.get("/involved/log", headers=gateway_headers())
    assert r.json()["data"][0]["nombre_usuario"] == "Usuario 777"


async def test_log_filtro_por_nombre_usuario(client, con_auditoria, make_auditoria, monkeypatch):
    async def _fake_get_user_info(user_ids):
        return {1: {"nombre": "Laura Diaz", "correo": "l@x.co", "numero_documento": 111},
                2: {"nombre": "Mario Solis", "correo": "m@x.co", "numero_documento": 222}}

    import routes.involved as rutas
    monkeypatch.setattr(rutas, "get_user_info", _fake_get_user_info)

    await make_auditoria(usuario_id=1)
    await make_auditoria(usuario_id=2)
    r = await client.get("/involved/log?nombre_usuario=laura", headers=gateway_headers())
    assert r.json()["pagination"]["total"] == 1
    assert r.json()["data"][0]["nombre_usuario"] == "Laura Diaz"


async def test_log_filtro_por_documento_usuario(client, con_auditoria, make_auditoria, monkeypatch):
    async def _fake_get_user_info(user_ids):
        return {1: {"nombre": "Laura Diaz", "correo": "", "numero_documento": 111},
                2: {"nombre": "Mario Solis", "correo": "", "numero_documento": 222}}

    import routes.involved as rutas
    monkeypatch.setattr(rutas, "get_user_info", _fake_get_user_info)

    await make_auditoria(usuario_id=1)
    await make_auditoria(usuario_id=2)
    r = await client.get("/involved/log?documento_usuario=222", headers=gateway_headers())
    assert r.json()["pagination"]["total"] == 1


async def test_log_oculta_el_id_en_datos_json(client, con_auditoria, sin_usuarios, make_auditoria):
    await make_auditoria(datos_nuevos={"id": 5, "nombre": "X"})
    r = await client.get("/involved/log", headers=gateway_headers())
    assert "id" not in r.json()["data"][0]["datos_nuevos"]
    assert r.json()["data"][0]["datos_nuevos"]["nombre"] == "X"


async def test_log_mapea_tipo_operacion(client, con_auditoria, sin_usuarios, make_auditoria):
    await make_auditoria(tipo_evento="CREAR_INVOLUCRADO")
    r = await client.get("/involved/log", headers=gateway_headers())
    assert r.json()["data"][0]["tipo_operacion"] == "INSERT"
    assert r.json()["data"][0]["tabla_afectada"] == "Involucrado"

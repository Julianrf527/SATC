"""Tests de routes/role.py."""
import pytest
from conftest import gateway_headers, service_headers

PERMISO_ROL = "admin_roles_y_permisos"


@pytest.mark.asyncio
async def test_all_sin_permiso_403(client, make_rol, make_usuario):
    rol = await make_rol("sin_permisos")
    u = await make_usuario(rol_id=rol.id)
    resp = await client.get("/role/all", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_all_con_permiso_200(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso(PERMISO_ROL)
    rol = await make_rol("admin", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.get("/role/all", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_permissions_con_permiso_200(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso(PERMISO_ROL)
    rol = await make_rol("admin", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.get("/role/permissions", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 200
    assert any(item["name"] == PERMISO_ROL for item in resp.json()["data"])


@pytest.mark.asyncio
async def test_add_rol_sin_permiso_403(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso("otro_permiso")
    rol = await make_rol("sin_rol_admin", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.post("/role/add", headers=gateway_headers(u.id, rol.id), json={
        "nombre": "nuevo", "permisos": [p.id],
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_add_rol_exitoso_201(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso(PERMISO_ROL)
    rol = await make_rol("admin", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.post("/role/add", headers=gateway_headers(u.id, rol.id), json={
        "nombre": "rol_nuevo", "permisos": [p.id],
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_add_rol_escalada_403(client, make_permiso, make_rol, make_usuario):
    # Intenta crear un rol con un permiso que el creador no posee.
    p_admin = await make_permiso(PERMISO_ROL)
    p_extra = await make_permiso("permiso_ajeno")
    rol = await make_rol("admin", [p_admin])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.post("/role/add", headers=gateway_headers(u.id, rol.id), json={
        "nombre": "rol_peligroso", "permisos": [p_admin.id, p_extra.id],
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_add_rol_duplicado_400(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso(PERMISO_ROL)
    rol = await make_rol("admin", [p])
    u = await make_usuario(rol_id=rol.id)
    await make_rol("repetido", [p])
    resp = await client.post("/role/add", headers=gateway_headers(u.id, rol.id), json={
        "nombre": "repetido", "permisos": [p.id],
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_verify_requiere_service_token(client):
    resp = await client.post("/role/verify", json={"permission_name": "admin_roles_y_permisos", "user_id": 1})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_verify_tiene_permiso_true(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso(PERMISO_ROL)
    rol = await make_rol("admin", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.post("/role/verify", headers=service_headers(), json={
        "permission_name": PERMISO_ROL, "user_id": u.id,
    })
    assert resp.status_code == 200
    assert resp.json()["tiene_permiso"] is True


@pytest.mark.asyncio
async def test_verify_tiene_permiso_false(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso(PERMISO_ROL)
    rol = await make_rol("admin", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.post("/role/verify", headers=service_headers(), json={
        "permission_name": "permiso_que_no_tiene", "user_id": u.id,
    })
    assert resp.status_code == 200
    assert resp.json()["tiene_permiso"] is False

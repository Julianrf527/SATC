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


# --- Lectura de catálogos por las pantallas que los usan (auditoría 2026-10, M15) ---

@pytest.mark.asyncio
@pytest.mark.parametrize("permiso", [
    "admin_gestionar_usuarios", "admin_registrar_usuarios",
    "auditoria_usuarios", "auditoria_expedientes", "auditoria_involucrados", "auditoria_infracciones",
])
async def test_all_lectura_por_pantallas_200(client, make_permiso, make_rol, make_usuario, permiso):
    p = await make_permiso(permiso)
    rol = await make_rol("lector", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.get("/role/all", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 200
    # Sigue filtrando: solo roles cuyos permisos son subconjunto de los del usuario.
    assert {r["nombre"] for r in resp.json()["data"]} == {"lector"}


@pytest.mark.asyncio
async def test_all_otro_permiso_403(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso("infraccion_gestionar")
    rol = await make_rol("operador", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.get("/role/all", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_permissions_auditor_200(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso("auditoria_expedientes")
    rol = await make_rol("auditor", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.get("/role/permissions", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_permissions_gestor_usuarios_403(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso("admin_gestionar_usuarios")
    rol = await make_rol("gestor", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.get("/role/permissions", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_auditor_no_puede_crear_roles(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso("auditoria_usuarios")
    rol = await make_rol("auditor", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.post("/role/add", headers=gateway_headers(u.id, rol.id), json={
        "nombre": "nuevo", "permisos": [p.id],
    })
    assert resp.status_code in (403, 422)

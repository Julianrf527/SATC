"""Tests de routes/auth.py (login, /me, logout, recuperación)."""
import pytest
from conftest import gateway_headers, TEST_PASSWORD


@pytest.mark.asyncio
async def test_login_exitoso(client, make_rol, make_usuario):
    rol = await make_rol("operador")
    u = await make_usuario(rol_id=rol.id, correo="login@test.com")
    resp = await client.post("/auth/login", json={
        "email": "login@test.com", "password": TEST_PASSWORD,
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert "access_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_password_incorrecto(client, make_rol, make_usuario):
    rol = await make_rol("operador")
    await make_usuario(rol_id=rol.id, correo="wrong@test.com")
    resp = await client.post("/auth/login", json={
        "email": "wrong@test.com", "password": "OtraClave99!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_usuario_inactivo(client, make_rol, make_usuario):
    rol = await make_rol("operador")
    await make_usuario(rol_id=rol.id, correo="inactivo@test.com", activo=False)
    resp = await client.post("/auth/login", json={
        "email": "inactivo@test.com", "password": TEST_PASSWORD,
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_login_usuario_inexistente(client):
    resp = await client.post("/auth/login", json={
        "email": "nadie@test.com", "password": TEST_PASSWORD,
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_email_invalido_422(client):
    resp = await client.post("/auth/login", json={
        "email": "no-es-email", "password": TEST_PASSWORD,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_me_devuelve_usuario_y_permisos(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso("admin_roles_y_permisos", "/user/role")
    rol = await make_rol("admin", [p])
    u = await make_usuario(rol_id=rol.id, correo="me@test.com")
    resp = await client.get("/auth/me", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 200
    data = resp.json()["usuario"]
    assert data["correo"] == "me@test.com"
    assert any(perm["name"] == "admin_roles_y_permisos" for perm in data["permisos"])


@pytest.mark.asyncio
async def test_me_sin_gateway_token_403(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_recovery_usuario_inexistente_respuesta_generica(client):
    # No debe revelar si el correo existe: siempre 200 con mensaje genérico.
    resp = await client.post("/auth/recovery", json={"email": "fantasma@test.com"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_logout_siempre_ok(client):
    resp = await client.post("/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

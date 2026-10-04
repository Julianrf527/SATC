"""Tests de routes/user.py."""
import pytest
from conftest import gateway_headers, service_headers, TEST_PASSWORD

PERMISO_USER = "admin_registrar_usuarios"
GESTION_USER = "admin_gestionar_usuarios"
USER_LOG = "auditoria_usuarios"


async def _rol_admin(make_permiso, make_rol):
    """Rol con los tres permisos de gestión de usuarios."""
    perms = []
    for nombre in (PERMISO_USER, GESTION_USER, USER_LOG):
        perms.append(await make_permiso(nombre))
    rol = await make_rol("admin_users", perms)
    return rol, perms


@pytest.mark.asyncio
async def test_register_sin_permiso_403(client, make_rol, make_usuario):
    rol = await make_rol("sin_permisos")
    u = await make_usuario(rol_id=rol.id)
    resp = await client.post("/user/register", headers=gateway_headers(u.id, rol.id), json={
        "first_name": "Ana", "lastname": "Perez", "document": 123456,
        "email": "ana@test.com", "rol": rol.id,
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_register_exitoso_201(client, make_permiso, make_rol, make_usuario):
    rol, _ = await _rol_admin(make_permiso, make_rol)
    admin = await make_usuario(rol_id=rol.id)
    resp = await client.post("/user/register", headers=gateway_headers(admin.id, rol.id), json={
        "first_name": "Ana", "lastname": "Perez", "document": 555111,
        "email": "ana.nueva@test.com", "rol": rol.id,
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_register_escalada_privilegios_403(client, make_permiso, make_rol, make_usuario):
    # El creador NO tiene el permiso extra que sí tiene el rol a asignar.
    p_user = await make_permiso(PERMISO_USER)
    p_extra = await make_permiso("permiso_poderoso")
    rol_creador = await make_rol("creador", [p_user])
    rol_poderoso = await make_rol("poderoso", [p_user, p_extra])
    admin = await make_usuario(rol_id=rol_creador.id)
    resp = await client.post("/user/register", headers=gateway_headers(admin.id, rol_creador.id), json={
        "first_name": "Eva", "lastname": "Lopez", "document": 777222,
        "email": "eva@test.com", "rol": rol_poderoso.id,
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_register_documento_duplicado_409(client, make_permiso, make_rol, make_usuario):
    rol, _ = await _rol_admin(make_permiso, make_rol)
    admin = await make_usuario(rol_id=rol.id)
    existente = await make_usuario(rol_id=rol.id, numero_documento=888333, correo="dup@test.com")
    resp = await client.post("/user/register", headers=gateway_headers(admin.id, rol.id), json={
        "first_name": "Otro", "lastname": "Nombre", "document": 888333,
        "email": "otrocorreo@test.com", "rol": rol.id,
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_validacion_documento_422(client, make_permiso, make_rol, make_usuario):
    rol, _ = await _rol_admin(make_permiso, make_rol)
    admin = await make_usuario(rol_id=rol.id)
    resp = await client.post("/user/register", headers=gateway_headers(admin.id, rol.id), json={
        "first_name": "Ana", "lastname": "Perez", "document": 5,  # muy corto
        "email": "corto@test.com", "rol": rol.id,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_all_sin_permiso_devuelve_403_no_500(client, make_rol, make_usuario):
    # Un permiso faltante debe salir como 403, nunca como 500.
    rol = await make_rol("sin_permisos")
    u = await make_usuario(rol_id=rol.id)
    resp = await client.get("/user/all", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_all_con_permiso_200(client, make_permiso, make_rol, make_usuario):
    rol, _ = await _rol_admin(make_permiso, make_rol)
    admin = await make_usuario(rol_id=rol.id)
    resp = await client.get("/user/all", headers=gateway_headers(admin.id, rol.id))
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_admin_update_sin_gestion_403(client, make_permiso, make_rol, make_usuario):
    # Solo tiene PERMISO_USER, no GESTION_USER.
    p = await make_permiso(PERMISO_USER)
    rol = await make_rol("solo_crear", [p])
    admin = await make_usuario(rol_id=rol.id)
    objetivo = await make_usuario(rol_id=rol.id, correo="obj@test.com")
    resp = await client.patch(f"/user/{objetivo.id}", headers=gateway_headers(admin.id, rol.id), json={"activo": False})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_update_usuario_inexistente_404(client, make_permiso, make_rol, make_usuario):
    rol, _ = await _rol_admin(make_permiso, make_rol)
    admin = await make_usuario(rol_id=rol.id)
    resp = await client.patch("/user/99999", headers=gateway_headers(admin.id, rol.id), json={"activo": False})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_update_toggle_estado_exitoso(client, make_permiso, make_rol, make_usuario):
    rol, _ = await _rol_admin(make_permiso, make_rol)
    admin = await make_usuario(rol_id=rol.id)
    objetivo = await make_usuario(rol_id=rol.id, correo="obj2@test.com", activo=True)
    resp = await client.patch(f"/user/{objetivo.id}", headers=gateway_headers(admin.id, rol.id), json={"activo": False})
    assert resp.status_code == 200
    assert resp.json()["data"]["activo"] is False


@pytest.mark.asyncio
async def test_admin_update_cambio_rol_exitoso(client, make_permiso, make_rol, make_usuario):
    rol, _ = await _rol_admin(make_permiso, make_rol)
    otro_rol = await make_rol("otro_rol")
    admin = await make_usuario(rol_id=rol.id)
    objetivo = await make_usuario(rol_id=rol.id, correo="obj3@test.com")
    resp = await client.patch(f"/user/{objetivo.id}", headers=gateway_headers(admin.id, rol.id), json={"rol_id": otro_rol.id})
    assert resp.status_code == 200
    assert resp.json()["data"]["rol_id"] == otro_rol.id


@pytest.mark.asyncio
async def test_admin_update_cambio_rol_escalada_403(client, make_permiso, make_rol, make_usuario):
    p_gestion = await make_permiso(GESTION_USER)
    p_extra = await make_permiso("permiso_poderoso")
    rol_actor = await make_rol("gestor", [p_gestion])
    rol_poderoso = await make_rol("poderoso", [p_gestion, p_extra])
    admin = await make_usuario(rol_id=rol_actor.id)
    objetivo = await make_usuario(rol_id=rol_actor.id, correo="obj4@test.com")
    resp = await client.patch(f"/user/{objetivo.id}", headers=gateway_headers(admin.id, rol_actor.id), json={"rol_id": rol_poderoso.id})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_update_datos_exitoso(client, make_permiso, make_rol, make_usuario):
    rol, _ = await _rol_admin(make_permiso, make_rol)
    admin = await make_usuario(rol_id=rol.id)
    objetivo = await make_usuario(rol_id=rol.id, correo="obj5@test.com", numero_documento=444555)
    resp = await client.patch(f"/user/{objetivo.id}", headers=gateway_headers(admin.id, rol.id), json={
        "first_name": "Nuevo", "lastname": "Apellido", "document": 444556, "email": "nuevo5@test.com",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["primer_nombre"] == "Nuevo"
    assert data["numero_documento"] == 444556
    assert data["correo"] == "nuevo5@test.com"


@pytest.mark.asyncio
async def test_admin_update_documento_duplicado_de_otro_409(client, make_permiso, make_rol, make_usuario):
    rol, _ = await _rol_admin(make_permiso, make_rol)
    admin = await make_usuario(rol_id=rol.id)
    await make_usuario(rol_id=rol.id, correo="ocupado@test.com", numero_documento=999888)
    objetivo = await make_usuario(rol_id=rol.id, correo="obj6@test.com")
    resp = await client.patch(f"/user/{objetivo.id}", headers=gateway_headers(admin.id, rol.id), json={"document": 999888})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_admin_update_mismo_documento_propio_no_409(client, make_permiso, make_rol, make_usuario):
    # Enviar el mismo documento que ya tiene el usuario no debe disparar 409.
    rol, _ = await _rol_admin(make_permiso, make_rol)
    admin = await make_usuario(rol_id=rol.id)
    objetivo = await make_usuario(rol_id=rol.id, correo="obj7@test.com", numero_documento=333222)
    resp = await client.patch(f"/user/{objetivo.id}", headers=gateway_headers(admin.id, rol.id), json={"document": 333222})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_update_sin_cambios_200(client, make_permiso, make_rol, make_usuario):
    rol, _ = await _rol_admin(make_permiso, make_rol)
    admin = await make_usuario(rol_id=rol.id)
    objetivo = await make_usuario(rol_id=rol.id, correo="obj8@test.com")
    resp = await client.patch(f"/user/{objetivo.id}", headers=gateway_headers(admin.id, rol.id), json={})
    assert resp.status_code == 200
    assert resp.json()["message"] == "No se realizaron cambios"


@pytest.mark.asyncio
async def test_resend_password_sin_gestion_403(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso(PERMISO_USER)
    rol = await make_rol("solo_crear2", [p])
    admin = await make_usuario(rol_id=rol.id)
    objetivo = await make_usuario(rol_id=rol.id, correo="rp1@test.com")
    resp = await client.post(f"/user/resend-password/{objetivo.id}", headers=gateway_headers(admin.id, rol.id))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_resend_password_usuario_inexistente_404(client, make_permiso, make_rol, make_usuario):
    rol, _ = await _rol_admin(make_permiso, make_rol)
    admin = await make_usuario(rol_id=rol.id)
    resp = await client.post("/user/resend-password/99999", headers=gateway_headers(admin.id, rol.id))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resend_password_exitoso_200(client, make_permiso, make_rol, make_usuario):
    rol, _ = await _rol_admin(make_permiso, make_rol)
    admin = await make_usuario(rol_id=rol.id)
    objetivo = await make_usuario(rol_id=rol.id, correo="rp2@test.com")
    resp = await client.post(f"/user/resend-password/{objetivo.id}", headers=gateway_headers(admin.id, rol.id))
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_password_change_actual_incorrecta_401(client, make_rol, make_usuario):
    rol = await make_rol("operador")
    u = await make_usuario(rol_id=rol.id)
    resp = await client.post("/user/password-change", headers=gateway_headers(u.id, rol.id), json={
        "current_password": "ClaveMala99!", "new_password": "NuevaClave123!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_password_change_exitoso(client, make_rol, make_usuario):
    rol = await make_rol("operador")
    u = await make_usuario(rol_id=rol.id)
    resp = await client.post("/user/password-change", headers=gateway_headers(u.id, rol.id), json={
        "current_password": TEST_PASSWORD, "new_password": "NuevaClave123!",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_log_sin_permiso_403(client, make_rol, make_usuario):
    rol = await make_rol("sin_permisos")
    u = await make_usuario(rol_id=rol.id)
    resp = await client.get("/user/log", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_log_con_permiso_200(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso(USER_LOG)
    rol = await make_rol("auditor", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.get("/user/log", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 200
    assert "pagination" in resp.json()


@pytest.mark.asyncio
async def test_batch_requiere_service_token(client, make_rol, make_usuario):
    # Sin X-Service-Token → 403.
    resp = await client.post("/user/batch", json={"user_ids": [1]})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_batch_con_service_token(client, make_rol, make_usuario):
    rol = await make_rol("operador")
    u = await make_usuario(rol_id=rol.id, correo="batch@test.com")
    resp = await client.post("/user/batch", headers=service_headers(), json={"user_ids": [u.id]})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1 and data[0]["correo"] == "batch@test.com"


@pytest.mark.asyncio
async def test_permission_por_nombre_service(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso("permiso_x")
    rol = await make_rol("rol_x", [p])
    u = await make_usuario(rol_id=rol.id, correo="permx@test.com")
    resp = await client.get("/user/permission/permiso_x", headers=service_headers())
    assert resp.status_code == 200
    assert any(item["correo"] == "permx@test.com" for item in resp.json()["data"])

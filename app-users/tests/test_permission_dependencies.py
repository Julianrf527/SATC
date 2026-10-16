"""Tests de dependencias obligatorias entre permisos en routes/role.py."""
import pytest
from sqlalchemy import select

from conftest import gateway_headers
from db.models.permiso_requiere import PermisoRequiere
from db.models.rol_permiso import RolPermiso

PERMISO_ROL = "admin_roles_y_permisos"


@pytest.fixture
def requiere(db_session):
    async def _make(permiso, requerido):
        db_session.add(PermisoRequiere(permiso_id=permiso.id, requiere_id=requerido.id))
        await db_session.flush()
    return _make


@pytest.fixture
async def escenario(make_permiso, make_rol, make_usuario, requiere):
    """Admin con roles_y_permisos + infraccion_alertas (requiere infraccion_consultar)."""
    p_rol = await make_permiso(PERMISO_ROL, "/user/role")
    alertas = await make_permiso("infraccion_alertas", "/infraction/alerts")
    consultar = await make_permiso("infraccion_consultar", "/infraction/consult")
    alertas.descripcion = "Desbloquea la pestaña Alertas. Sirve para ver vencimientos."
    await requiere(alertas, consultar)
    rol = await make_rol("admin", [p_rol, alertas, consultar])
    u = await make_usuario(rol_id=rol.id)
    return {
        "p_rol": p_rol, "alertas": alertas, "consultar": consultar,
        "rol": rol, "headers": gateway_headers(u.id, rol.id),
    }


@pytest.mark.asyncio
async def test_add_rol_sin_requerido_422(client, escenario):
    e = escenario
    resp = await client.post("/role/add", headers=e["headers"], json={
        "nombre": "solo_alertas", "permisos": [e["alertas"].id],
    })
    assert resp.status_code == 422
    assert "«infraccion_alertas» requiere «infraccion_consultar»" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_rol_con_requerido_201(client, escenario):
    e = escenario
    resp = await client.post("/role/add", headers=e["headers"], json={
        "nombre": "alertas_ok", "permisos": [e["alertas"].id, e["consultar"].id],
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_add_rol_solo_requerido_201(client, escenario):
    # Un solo sentido: tener el requerido no obliga a tener el dependiente.
    e = escenario
    resp = await client.post("/role/add", headers=e["headers"], json={
        "nombre": "solo_consulta", "permisos": [e["consultar"].id],
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_update_rol_sin_requerido_422_y_no_cambia(client, db_session, escenario, make_rol):
    e = escenario
    otro = await make_rol("otro", [e["alertas"], e["consultar"]])
    resp = await client.put(f"/role/update/{otro.id}", headers=e["headers"], json={
        "nombre": "otro", "permisos": [e["alertas"].id],
    })
    assert resp.status_code == 422
    assert "«infraccion_alertas» requiere «infraccion_consultar»" in resp.json()["detail"]
    ids = set((await db_session.execute(
        select(RolPermiso.permiso_id).where(RolPermiso.rol_id == otro.id)
    )).scalars().all())
    assert ids == {e["alertas"].id, e["consultar"].id}


@pytest.mark.asyncio
async def test_rol_existente_que_incumple_se_puede_corregir(client, escenario, make_rol):
    e = escenario
    roto = await make_rol("roto", [e["alertas"]])
    resp = await client.put(f"/role/update/{roto.id}", headers=e["headers"], json={
        "nombre": "roto", "permisos": [e["alertas"].id, e["consultar"].id],
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_permissions_incluye_descripcion_y_requiere(client, escenario):
    e = escenario
    resp = await client.get("/role/permissions", headers=e["headers"])
    assert resp.status_code == 200
    data = {p["nombre"]: p for p in resp.json()["data"]}
    assert data["infraccion_alertas"]["requiere"] == ["infraccion_consultar"]
    assert data["infraccion_alertas"]["descripcion"].startswith("Desbloquea")
    assert data["infraccion_consultar"]["requiere"] == []
    # Campos anteriores intactos.
    assert {"id", "nombre", "name", "menu_path"} <= set(data["infraccion_consultar"])


@pytest.mark.asyncio
async def test_dependencias_incumplidas_reporta_roles(client, escenario, make_rol):
    e = escenario
    roto = await make_rol("roto", [e["alertas"]])
    resp = await client.get("/role/dependencias-incumplidas", headers=e["headers"])
    assert resp.status_code == 200
    assert resp.json()["data"] == [{
        "rol_id": roto.id,
        "rol_nombre": "roto",
        "faltantes": [{"permiso": "infraccion_alertas", "requiere": ["infraccion_consultar"]}],
    }]


@pytest.mark.asyncio
async def test_dependencias_incumplidas_sin_permiso_403(client, make_permiso, make_rol, make_usuario):
    p = await make_permiso("auditoria_usuarios")
    rol = await make_rol("auditor", [p])
    u = await make_usuario(rol_id=rol.id)
    resp = await client.get("/role/dependencias-incumplidas", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_login_de_rol_que_incumple_sigue_verificando(client, escenario, make_rol, make_usuario):
    from conftest import service_headers
    e = escenario
    roto = await make_rol("roto", [e["alertas"]])
    u = await make_usuario(rol_id=roto.id)
    resp = await client.post("/role/verify", headers=service_headers(), json={
        "permission_name": "infraccion_alertas", "user_id": u.id,
    })
    assert resp.status_code == 200
    assert resp.json()["tiene_permiso"] is True

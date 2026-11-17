"""Incompatibilidades entre permisos (tabla permiso_excluye) en routes/role.py.

El técnico de concesiones no puede tener gestionar en el mismo rol, salvo los
roles que administran roles (admin_roles_y_permisos), que necesitan todos los
permisos para repartirlos (anti-escalada) y recibir los nuevos.
"""
import pytest
from sqlalchemy import select

from conftest import gateway_headers
from db.models.permiso_excluye import PermisoExcluye
from db.models.rol_permiso import RolPermiso

PERMISO_ROL = "admin_roles_y_permisos"


@pytest.fixture
async def escenario(db_session, make_permiso, make_rol, make_usuario):
    """Admin con roles_y_permisos + técnico, gestionar y consultar de concesiones."""
    p_rol = await make_permiso(PERMISO_ROL, "/user/role")
    tecnico = await make_permiso("recurso_tecnico", "/recurso/my-reports")
    gestionar = await make_permiso("recurso_gestionar", "/recurso/manage")
    consultar = await make_permiso("recurso_consultar", "/recurso/consult")
    db_session.add_all([
        PermisoExcluye(permiso_id=tecnico.id, excluye_id=gestionar.id),
        PermisoExcluye(permiso_id=gestionar.id, excluye_id=tecnico.id),
    ])
    await db_session.flush()
    rol = await make_rol("admin", [p_rol, tecnico, gestionar, consultar])
    u = await make_usuario(rol_id=rol.id)
    return {
        "p_rol": p_rol, "tecnico": tecnico, "gestionar": gestionar, "consultar": consultar,
        "rol": rol, "headers": gateway_headers(u.id, rol.id),
    }


MENSAJE = "«recurso_gestionar» no puede ir con «recurso_tecnico»"


@pytest.mark.asyncio
async def test_add_rol_tecnico_y_gestionar_422(client, escenario):
    e = escenario
    resp = await client.post("/role/add", headers=e["headers"], json={
        "nombre": "mezcla", "permisos": [e["tecnico"].id, e["gestionar"].id, e["consultar"].id],
    })
    assert resp.status_code == 422
    assert MENSAJE in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_rol_solo_uno_de_los_dos_201(client, escenario):
    e = escenario
    for nombre, permisos in (("tecnico", [e["tecnico"], e["consultar"]]), ("abogado", [e["gestionar"]])):
        resp = await client.post("/role/add", headers=e["headers"], json={
            "nombre": nombre, "permisos": [p.id for p in permisos],
        })
        assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_rol_que_administra_roles_esta_exento(client, escenario):
    e = escenario
    resp = await client.post("/role/add", headers=e["headers"], json={
        "nombre": "admin2", "permisos": [e["p_rol"].id, e["tecnico"].id, e["gestionar"].id, e["consultar"].id],
    })
    assert resp.status_code == 201, resp.text
    # Y el admin puede editarse a sí mismo sin perder ninguno.
    resp = await client.put(f"/role/update/{e['rol'].id}", headers=e["headers"], json={
        "nombre": "admin", "permisos": [e["p_rol"].id, e["tecnico"].id, e["gestionar"].id, e["consultar"].id],
    })
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_update_a_incompatible_422_y_no_cambia(client, db_session, escenario, make_rol):
    e = escenario
    tecnico = await make_rol("tecnico", [e["tecnico"], e["consultar"]])
    resp = await client.put(f"/role/update/{tecnico.id}", headers=e["headers"], json={
        "nombre": "tecnico", "permisos": [e["tecnico"].id, e["consultar"].id, e["gestionar"].id],
    })
    assert resp.status_code == 422
    assert MENSAJE in resp.json()["detail"]
    ids = set((await db_session.execute(
        select(RolPermiso.permiso_id).where(RolPermiso.rol_id == tecnico.id)
    )).scalars().all())
    assert ids == {e["tecnico"].id, e["consultar"].id}


@pytest.mark.asyncio
async def test_permissions_incluye_excluye(client, escenario):
    e = escenario
    data = {p["nombre"]: p for p in (await client.get("/role/permissions", headers=e["headers"])).json()["data"]}
    assert data["recurso_tecnico"]["excluye"] == ["recurso_gestionar"]
    assert data["recurso_gestionar"]["excluye"] == ["recurso_tecnico"]
    assert data["recurso_consultar"]["excluye"] == []


@pytest.mark.asyncio
async def test_reporte_incluye_incompatibles_salvo_admin(client, escenario, make_rol):
    e = escenario
    mezcla = await make_rol("mezcla", [e["tecnico"], e["gestionar"], e["consultar"]])
    resp = await client.get("/role/dependencias-incumplidas", headers=e["headers"])
    assert resp.status_code == 200
    # El admin tiene los dos pero administra roles: no se reporta.
    assert resp.json()["data"] == [{
        "rol_id": mezcla.id,
        "rol_nombre": "mezcla",
        "faltantes": [],
        "incompatibles": [{"permiso": "recurso_gestionar", "con": "recurso_tecnico"}],
    }]


@pytest.mark.asyncio
async def test_rol_que_ya_incumple_sigue_verificando(client, escenario, make_rol, make_usuario):
    from conftest import service_headers
    e = escenario
    mezcla = await make_rol("mezcla", [e["tecnico"], e["gestionar"], e["consultar"]])
    u = await make_usuario(rol_id=mezcla.id)
    resp = await client.post("/role/verify", headers=service_headers(), json={
        "permission_name": "recurso_gestionar", "user_id": u.id,
    })
    assert resp.status_code == 200 and resp.json()["tiene_permiso"] is True

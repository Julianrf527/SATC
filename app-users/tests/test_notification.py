"""Tests de routes/notification.py."""
import pytest
from conftest import gateway_headers, service_headers


@pytest.mark.asyncio
async def test_add_requiere_service_token(client):
    resp = await client.post("/notification/add", json={
        "mensaje": "hola", "id_vinculada": "EXP-1", "tipo": "alerta", "usuario_id": 1,
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_add_crea_notificacion(client, make_rol, make_usuario):
    rol = await make_rol("operador")
    u = await make_usuario(rol_id=rol.id)
    resp = await client.post("/notification/add", headers=service_headers(), json={
        "mensaje": "Nueva alerta", "id_vinculada": "EXP-9", "tipo": "alerta", "usuario_id": u.id,
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_add_mensaje_vacio_400(client, make_rol, make_usuario):
    rol = await make_rol("operador")
    u = await make_usuario(rol_id=rol.id)
    resp = await client.post("/notification/add", headers=service_headers(), json={
        "mensaje": "   ", "id_vinculada": "EXP-9", "tipo": "alerta", "usuario_id": u.id,
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_notificacion_inexistente_404(client, make_rol, make_usuario):
    rol = await make_rol("operador")
    u = await make_usuario(rol_id=rol.id)
    resp = await client.delete("/notification/99999", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_notificacion_ajena_rechazada(client, make_rol, make_usuario, make_notificacion):
    """404 (no 401/403) para no revelar si la notificación existe pero es de otro usuario."""
    rol = await make_rol("operador")
    dueno = await make_usuario(rol_id=rol.id, correo="dueno@test.com")
    otro = await make_usuario(rol_id=rol.id, correo="otro@test.com")
    noti = await make_notificacion(usuario_id=dueno.id)
    resp = await client.delete(f"/notification/{noti.id}", headers=gateway_headers(otro.id, rol.id))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_notificacion_propia_200(client, make_rol, make_usuario, make_notificacion):
    rol = await make_rol("operador")
    u = await make_usuario(rol_id=rol.id)
    noti = await make_notificacion(usuario_id=u.id)
    resp = await client.delete(f"/notification/{noti.id}", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_all_borra_todas(client, make_rol, make_usuario, make_notificacion):
    rol = await make_rol("operador")
    u = await make_usuario(rol_id=rol.id)
    await make_notificacion(usuario_id=u.id, id_vinculada="A")
    await make_notificacion(usuario_id=u.id, id_vinculada="B")
    resp = await client.delete("/notification/delete-all", headers=gateway_headers(u.id, rol.id))
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


# --- DELETE /notification/linked/{id}: solo las propias (auditoría 2026-10, M13) ---

@pytest.mark.asyncio
async def test_delete_linked_no_borra_las_de_otros(client, db_session, make_rol, make_usuario, make_notificacion):
    from sqlalchemy import select
    from db.models.notificacion import Notificacion

    rol = await make_rol("operador")
    yo = await make_usuario(rol_id=rol.id, correo="yo@test.com")
    otro = await make_usuario(rol_id=rol.id, correo="otro2@test.com")
    mia = await make_notificacion(usuario_id=yo.id, id_vinculada="EXP-77")
    ajena = await make_notificacion(usuario_id=otro.id, id_vinculada="EXP-77")
    mia_id, ajena_id = mia.id, ajena.id

    resp = await client.delete("/notification/linked/EXP-77", headers=gateway_headers(yo.id, rol.id))
    assert resp.status_code == 200
    assert resp.json()["ids_eliminados"] == [mia_id]

    db_session.expire_all()
    quedan = (await db_session.execute(
        select(Notificacion.id).where(Notificacion.id_vinculada == "EXP-77")
    )).scalars().all()
    assert quedan == [ajena_id]


@pytest.mark.asyncio
async def test_delete_linked_solo_ajenas_404(client, make_rol, make_usuario, make_notificacion):
    rol = await make_rol("operador")
    yo = await make_usuario(rol_id=rol.id, correo="yo3@test.com")
    otro = await make_usuario(rol_id=rol.id, correo="otro3@test.com")
    await make_notificacion(usuario_id=otro.id, id_vinculada="EXP-88")
    resp = await client.delete("/notification/linked/EXP-88", headers=gateway_headers(yo.id, rol.id))
    assert resp.status_code == 404

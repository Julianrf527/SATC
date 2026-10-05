"""
Permisos de los endpoints de expediente que antes solo exigían estar logueado:
crear expediente/quejoso (infraccion_gestionar) y reasignar encargado
(infraccion_asignar). Sin esto, cualquier usuario autenticado podía reasignar
expedientes ajenos llamando la API directamente.
"""
import pytest

import routes.file_mutations as mutations_mod
from tests.conftest import gateway_headers


def _permisos(permitidos: set[str]):
    async def _verify(user_id, permission):
        return permission in permitidos

    return _verify


@pytest.fixture
def sin_permisos(monkeypatch):
    monkeypatch.setattr(mutations_mod, "verify_permission", _permisos(set()))


@pytest.fixture
def con_permisos(monkeypatch):
    monkeypatch.setattr(
        mutations_mod, "verify_permission", _permisos({"infraccion_gestionar", "infraccion_asignar"})
    )

    async def _noop(*a, **k):
        return {"ok": True}

    async def _user_info(ids):
        return {i: {"nombre": f"Usuario {i}"} for i in ids}

    monkeypatch.setattr(mutations_mod, "create_notification", _noop)
    monkeypatch.setattr(mutations_mod, "get_user_info", _user_info)


class TestReasignarEncargado:
    async def test_sin_permiso_asignar_da_403(self, client, make_expediente, sin_permisos):
        exp = await make_expediente(abogado_responsable_id=1)
        resp = await client.patch(f"/expedientes/{exp.id}/encargado/9", headers=gateway_headers(2))
        assert resp.status_code == 403

    async def test_no_reasigna_si_no_tiene_permiso(self, client, make_expediente, db_session, sin_permisos):
        exp = await make_expediente(abogado_responsable_id=1)
        await client.patch(f"/expedientes/{exp.id}/encargado/9", headers=gateway_headers(2))
        await db_session.refresh(exp)
        assert exp.abogado_responsable_id == 1

    async def test_con_permiso_reasigna(self, client, make_expediente, db_session, con_permisos):
        exp = await make_expediente(abogado_responsable_id=1)
        resp = await client.patch(f"/expedientes/{exp.id}/encargado/9", headers=gateway_headers(2))
        assert resp.status_code == 200
        await db_session.refresh(exp)
        assert exp.abogado_responsable_id == 9

    async def test_bulk_sin_permiso_da_403(self, client, make_expediente, sin_permisos):
        exp = await make_expediente(abogado_responsable_id=1)
        resp = await client.patch(
            "/expedientes/encargado/masivo",
            json={"expediente_id": [exp.id], "encargado_id": 9},
            headers=gateway_headers(2),
        )
        assert resp.status_code == 403


class TestCrearExpediente:
    async def test_sin_permiso_gestionar_da_403(self, client, sin_permisos):
        resp = await client.post(
            "/expedientes",
            json={
                "radicado": "2026ER9999",
                "fecha_radicado": "2026-01-10",
                "vereda_id": 1,
                "abogado_responsable_id": 1,
                "direccion": "Calle 1",
                "descripcion": "Prueba",
                "tipos_afectacion_ids": [],
                "quejosos_ids": [],
                "recursos_ids": [],
                "radicados_asociados": [],
            },
            headers=gateway_headers(2),
        )
        assert resp.status_code == 403

    async def test_quejoso_sin_permiso_da_403(self, client, sin_permisos):
        resp = await client.post(
            "/expedientes/denunciantes",
            json={"nombre": "Pedro", "anonimo": False},
            headers=gateway_headers(2),
        )
        assert resp.status_code == 403

    async def test_quejoso_con_permiso_ok(self, client, con_permisos):
        resp = await client.post(
            "/expedientes/denunciantes",
            json={"nombre": "Pedro", "anonimo": False},
            headers=gateway_headers(2),
        )
        assert resp.status_code == 201

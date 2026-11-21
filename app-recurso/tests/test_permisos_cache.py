"""Caché de permisos: se vacía cuando app-users sube la versión global."""
import pytest

import services.users as users_svc
from core.permission import Permission
from satc_shared import permisos_version as pv
from satc_shared.permisos_version import SincronizadorPermisos

USUARIO = 501


@pytest.fixture
def version(monkeypatch):
    estado = {"v": None}

    async def _version():
        return estado["v"]

    monkeypatch.setattr(pv, "version_permisos", _version)
    monkeypatch.setattr(users_svc, "_sincronizador", SincronizadorPermisos())
    return estado


async def test_revocar_permiso_se_ve_al_subir_la_version(stubs, version):
    stubs.permisos.dar(USUARIO, Permission.MANAGE)
    assert await users_svc.verify_permission(USUARIO, Permission.MANAGE) is True

    # Se revoca en app-users sin tocar la caché de este worker: sigue cacheado.
    stubs.permisos._por_usuario[USUARIO].discard(Permission.MANAGE)
    assert await users_svc.verify_permission(USUARIO, Permission.MANAGE) is True

    # app-users sube la versión → la caché se vacía y se ve el cambio.
    version["v"] = "1"
    assert await users_svc.verify_permission(USUARIO, Permission.MANAGE) is False


async def test_sin_cambio_de_version_usa_la_cache(stubs, version):
    version["v"] = "7"
    stubs.permisos.dar(USUARIO, Permission.CONSULT)
    assert await users_svc.verify_permission(USUARIO, Permission.CONSULT) is True
    stubs.permisos._por_usuario[USUARIO].discard(Permission.CONSULT)
    assert await users_svc.verify_permission(USUARIO, Permission.CONSULT) is True

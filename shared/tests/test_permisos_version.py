import pytest

from satc_shared import permisos_version as pv


class RedisFalso:
    def __init__(self):
        self.datos = {}
        self.caido = False

    async def get(self, clave):
        if self.caido:
            raise ConnectionError("caído")
        return self.datos.get(clave)

    async def incr(self, clave):
        if self.caido:
            raise ConnectionError("caído")
        self.datos[clave] = str(int(self.datos.get(clave) or 0) + 1)


@pytest.fixture
def redis_falso(monkeypatch):
    r = RedisFalso()
    monkeypatch.setattr(pv, "_cliente", r)
    monkeypatch.setattr(pv, "_ultima_version", None)
    monkeypatch.setattr(pv, "_leida_en", 0.0)
    monkeypatch.setattr(pv, "_fallo_en", 0.0)
    monkeypatch.setattr(pv, "INTERVALO_LECTURA", 0.0)
    return r


async def test_detecta_cambios_de_version(redis_falso):
    s = pv.SincronizadorPermisos()
    assert await s.cambio() is False  # aún no hay versión
    await pv.incrementar_version_permisos()
    assert await s.cambio() is True
    assert await s.cambio() is False
    await pv.incrementar_version_permisos()
    assert await s.cambio() is True


async def test_redis_caido_no_lanza_ni_invalida(redis_falso):
    s = pv.SincronizadorPermisos()
    await pv.incrementar_version_permisos()
    assert await s.cambio() is True
    redis_falso.caido = True
    await pv.incrementar_version_permisos()  # no lanza
    assert await s.cambio() is False


async def test_sin_redis_configurado_es_noop(monkeypatch):
    monkeypatch.setattr(pv, "_cliente", None)
    monkeypatch.delenv("REDIS_HOST", raising=False)
    await pv.incrementar_version_permisos()
    assert await pv.SincronizadorPermisos().cambio() is False

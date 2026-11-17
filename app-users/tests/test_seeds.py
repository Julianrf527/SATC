"""Tests de db/seeds.py: el usuario administrador inicial sale del entorno (.env.user_admin)."""
import pytest
from sqlalchemy import text

from conftest import engine
from db import seeds
from utils.passwords import verify_password

ADMIN_ENV = {
    "ADMIN_NUMERO_DOCUMENTO": "900100200",
    "ADMIN_PRIMER_NOMBRE": "Ana",
    "ADMIN_PRIMER_APELLIDO": "Pérez",
    "ADMIN_CORREO": "admin@ejemplo.test",
    "ADMIN_PASSWORD": "Clave-Segura-1",
}


def test_sin_variables_no_hay_admin():
    assert seeds.admin_desde_entorno({}) is None


def test_variables_a_medias_no_hay_admin():
    incompleto = {k: v for k, v in ADMIN_ENV.items() if k != "ADMIN_CORREO"}
    assert seeds.admin_desde_entorno(incompleto) is None
    sin_clave = {k: v for k, v in ADMIN_ENV.items() if k != "ADMIN_PASSWORD"}
    assert seeds.admin_desde_entorno(sin_clave) is None
    assert seeds.admin_desde_entorno({**ADMIN_ENV, "ADMIN_NUMERO_DOCUMENTO": "abc"}) is None


def test_admin_completo_hashea_la_clave():
    datos = seeds.admin_desde_entorno(ADMIN_ENV)
    assert datos["numero_documento"] == 900100200
    assert datos["segundo_nombre"] is None and datos["correo"] == "admin@ejemplo.test"
    assert datos["hash_contrasena"] != "Clave-Segura-1"
    assert verify_password("Clave-Segura-1", datos["hash_contrasena"])


def test_admin_con_hash_ya_calculado():
    env = {k: v for k, v in ADMIN_ENV.items() if k != "ADMIN_PASSWORD"}
    datos = seeds.admin_desde_entorno({**env, "ADMIN_HASH_CONTRASENA": "$2b$12$hash"})
    assert datos["hash_contrasena"] == "$2b$12$hash"


async def _usuarios() -> list:
    async with engine.connect() as conn:
        return (await conn.execute(text("SELECT numero_documento, correo, rol_id FROM usuario"))).all()


async def _reiniciar_seed_lock():
    # seed_lock no es un modelo: el TRUNCATE de conftest no lo limpia.
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS seed_lock"))


@pytest.mark.asyncio
async def test_seed_sin_entorno_crea_permisos_pero_no_admin(monkeypatch):
    for k in seeds.ADMIN_OBLIGATORIAS + seeds.ADMIN_CLAVES:
        monkeypatch.delenv(k, raising=False)
    await _reiniciar_seed_lock()
    await seeds.seed_initial_data()
    assert await _usuarios() == []
    async with engine.connect() as conn:
        assert (await conn.execute(text("SELECT count(*) FROM permiso"))).scalar() > 0

    # Completado el .env.user_admin, el siguiente arranque crea el admin.
    for k, v in ADMIN_ENV.items():
        monkeypatch.setenv(k, v)
    await seeds.seed_initial_data()
    usuarios = await _usuarios()
    assert [(u.numero_documento, u.correo) for u in usuarios] == [(900100200, "admin@ejemplo.test")]

    # Con usuarios en la base no vuelve a crear nada.
    monkeypatch.setenv("ADMIN_NUMERO_DOCUMENTO", "123")
    await seeds.seed_initial_data()
    assert len(await _usuarios()) == 1

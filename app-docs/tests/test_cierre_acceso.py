"""
Fase 4 detrás de variables: cierre del acceso directo de usuarios a la lectura
de archivos, limpieza que respeta los dueños (file_uso) y el reporte que dice
cuándo es seguro activar cada cosa.
"""
import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from conftest import engine, gateway_headers, service_headers
from db.models.file_hash import FileHash
from db.models.file_uso import FileSubida, FileUso
from services import cleanup_scheduler

BOGOTA = ZoneInfo("America/Bogota")


@pytest.fixture
def permiso_archivos(monkeypatch):
    async def fake(user_id, permiso):
        return True
    monkeypatch.setattr("routes.files.verify_permission", fake)


@pytest.fixture
def minio_lectura(monkeypatch):
    class _Obj:
        def stream(self, n):
            yield b"%PDF"

        def close(self):
            pass

        def release_conn(self):
            pass

    monkeypatch.setattr("routes.files.abrir_objeto", lambda *a, **k: _Obj())


# --- acceso directo de usuarios ---------------------------------------------------

async def test_acceso_directo_abierto_deja_constancia(client, make_file_hash, permiso_archivos, minio_lectura, caplog):
    fh = await make_file_hash(file_size=4)
    r = await client.get(f"/files/download/{fh.id}", headers=gateway_headers(7))
    assert r.status_code == 200
    assert any(f"Acceso directo de usuario: usuario=7 file_id={fh.id}" in m for m in caplog.messages)


async def test_acceso_directo_cerrado_solo_servicios(client, make_file_hash, permiso_archivos, minio_lectura, monkeypatch):
    monkeypatch.setattr("routes.files.ACCESO_DIRECTO_USUARIOS", False)
    fh = await make_file_hash(file_size=4)
    for ruta in (f"/files/download/{fh.id}", f"/files/{fh.id}"):
        r = await client.get(ruta, headers=gateway_headers(7))
        assert r.status_code == 403, ruta
        assert "módulo" in r.json()["detail"]
        r = await client.get(ruta, headers=service_headers())
        assert r.status_code == 200, ruta


async def test_acceso_directo_cerrado_no_afecta_la_subida(client, permiso_archivos, monkeypatch):
    monkeypatch.setattr("routes.files.ACCESO_DIRECTO_USUARIOS", False)

    async def fake_validate(file_data, filename, max_size_mb):
        return {"sanitized_filename": filename, "mime_type": "application/pdf"}

    async def fake_upload(**k):
        return {"ok": True, "url": "b/x.pdf", "id": 1, "file_hash": "h" * 64, "message": "ok"}

    monkeypatch.setattr("routes.files.validate_file_complete", fake_validate)
    monkeypatch.setattr("routes.files.escanear_archivo", lambda *a, **k: {"ok": True})
    monkeypatch.setattr("routes.files.upload_file_with_deduplication", fake_upload)
    r = await client.post("/files/upload", headers=gateway_headers(7),
                          files={"archivo": ("a.pdf", io.BytesIO(b"%PDF"), "application/pdf")})
    assert r.status_code == 200


# --- limpieza que respeta los dueños ------------------------------------------------

@pytest.fixture
def borrados(monkeypatch):
    lista = []
    monkeypatch.setattr(cleanup_scheduler, "delete_file_from_minio",
                        lambda url: lista.append(url) or {"ok": True})
    return lista


async def _archivos(db_session, make_file_hash):
    viejo = datetime.now(BOGOTA) - timedelta(days=5)
    sin_nada = await make_file_hash(numero_usos=0, ultima_subida=viejo)
    contador_sin_dueno = await make_file_hash(numero_usos=2, ultima_subida=viejo)
    dueno_sin_contador = await make_file_hash(numero_usos=0, ultima_subida=viejo)
    db_session.add(FileUso(file_id=dueno_sin_contador.id, servicio="recurso", entidad="acto", entidad_id="1"))
    await db_session.commit()
    return sin_nada, contador_sin_dueno, dueno_sin_contador


async def test_limpieza_contador_no_borra_archivos_con_dueno(db_session, make_file_hash, borrados, monkeypatch):
    monkeypatch.setattr(cleanup_scheduler, "CRITERIO", "contador")
    sin_nada, contador_sin_dueno, dueno_sin_contador = await _archivos(db_session, make_file_hash)
    await cleanup_scheduler.tarea_limpieza_temporales(db_session)
    quedan = set((await db_session.execute(select(FileHash.id))).scalars().all())
    assert quedan == {contador_sin_dueno.id, dueno_sin_contador.id}
    assert borrados == [sin_nada.file_url]


async def test_limpieza_por_duenos_ignora_el_contador(db_session, make_file_hash, borrados, monkeypatch):
    monkeypatch.setattr(cleanup_scheduler, "CRITERIO", "duenos")
    sin_nada, contador_sin_dueno, dueno_sin_contador = await _archivos(db_session, make_file_hash)
    await cleanup_scheduler.tarea_limpieza_temporales(db_session)
    quedan = set((await db_session.execute(select(FileHash.id))).scalars().all())
    assert quedan == {dueno_sin_contador.id}
    assert sorted(borrados) == sorted([sin_nada.file_url, contador_sin_dueno.file_url])


# --- reporte ------------------------------------------------------------------------

async def test_reporte_archivos(db_session, make_file_hash):
    from scripts.reporte_archivos import generar

    ahora = datetime.now(BOGOTA)
    propio, ajeno, sin_dueno = [await make_file_hash(numero_usos=1, file_size=1048576) for _ in range(3)]
    db_session.add_all([
        FileSubida(file_id=propio.id, usuario_id=5, servicio_origen="gateway", fecha=ahora - timedelta(hours=1)),
        FileSubida(file_id=ajeno.id, usuario_id=8, servicio_origen="gateway", fecha=ahora - timedelta(hours=1)),
        FileUso(file_id=propio.id, servicio="infraction", entidad="acto", entidad_id="1", usuario_id=5, creado_en=ahora),
        FileUso(file_id=ajeno.id, servicio="infraction", entidad="acto", entidad_id="2", usuario_id=5, creado_en=ahora),
    ])
    await db_session.commit()

    texto = await generar(7, motor=engine)
    assert "infraction/acto: 1 de 2 se habrían rechazado" in texto
    assert "revisar antes de on" in texto
    assert "Archivos en uso sin dueño registrado: 1 (1.0 MB)" in texto
    assert "infraction: 2 archivos con dueño" in texto
    assert "NO cambiar a duenos" in texto
    assert sin_dueno.id  # el tercero es el que no tiene dueño

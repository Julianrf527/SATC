"""
Subida deduplicada (upsert, ultima_subida), periodo de gracia de la limpieza
nocturna y validación de parámetros de /docs/list.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from conftest import gateway_headers
from db.models.file_hash import FileHash
from services import cleanup_scheduler
from utils import minio_client

BOGOTA = ZoneInfo("America/Bogota")


@pytest.fixture
def minio_falso(monkeypatch):
    """Registra las subidas y borrados que llegarían a MinIO."""
    llamadas = {"subidas": [], "borrados": []}

    def fake_upload(file_data, object_name, content_type="application/octet-stream"):
        llamadas["subidas"].append(object_name)
        return {"ok": True, "url": f"{minio_client.MINIO_BUCKET}/{object_name}", "message": "ok"}

    def fake_delete(object_name):
        llamadas["borrados"].append(object_name)
        return {"ok": True, "message": "ok"}

    monkeypatch.setattr(minio_client, "upload_file_to_minio", fake_upload)
    monkeypatch.setattr(cleanup_scheduler, "delete_file_from_minio", fake_delete)
    return llamadas


# --- subida deduplicada --------------------------------------------------------

async def test_subida_nueva_y_luego_deduplicada(db_session, minio_falso):
    r1 = await minio_client.upload_file_with_deduplication(db_session, b"contenido A", "a.pdf", "application/pdf")
    assert r1["ok"] and not r1["deduplicated"] and r1["numero_usos"] == 0
    primera = (await db_session.scalar(select(FileHash.ultima_subida).where(FileHash.id == r1["id"])))

    r2 = await minio_client.upload_file_with_deduplication(db_session, b"contenido A", "otro.pdf", "application/pdf")
    assert r2["ok"] and r2["deduplicated"]
    assert r2["id"] == r1["id"] and r2["url"] == r1["url"]
    assert len(minio_falso["subidas"]) == 1  # el duplicado no vuelve a MinIO

    db_session.expire_all()
    segunda = await db_session.scalar(select(FileHash.ultima_subida).where(FileHash.id == r1["id"]))
    assert primera is not None and segunda >= primera


async def test_subida_nueva_choca_con_fila_existente_hace_upsert(db_session, minio_falso, monkeypatch):
    """Simula la carrera de dos subidas del mismo archivo nuevo: la fila aparece
    entre la consulta y el INSERT. Antes se tragaba el IntegrityError."""
    import hashlib
    datos = b"contenido carrera"
    h = hashlib.sha256(datos).hexdigest()
    previa = FileHash(file_hash=h, file_url="satc-documentos/files/xx/previa.pdf", numero_usos=2)
    db_session.add(previa)
    await db_session.commit()

    # Fuerza el camino "no existe" aunque la fila ya esté.
    from sqlalchemy.engine import Result
    original_execute = db_session.execute
    llamadas = {"n": 0}

    async def execute_sin_ver_la_primera_vez(stmt, *a, **k):
        llamadas["n"] += 1
        if llamadas["n"] == 1:  # el UPDATE de reutilización "no encuentra" la fila
            class _Vacio:
                def first(self):
                    return None
            return _Vacio()
        return await original_execute(stmt, *a, **k)

    monkeypatch.setattr(db_session, "execute", execute_sin_ver_la_primera_vez)
    r = await minio_client.upload_file_with_deduplication(db_session, datos, "c.pdf", "application/pdf")
    assert r["ok"]
    assert r["id"] == previa.id
    assert r["url"] == previa.file_url  # conserva la fila existente
    assert r["numero_usos"] == 2


# --- limpieza con periodo de gracia -------------------------------------------

async def test_limpieza_respeta_periodo_de_gracia(db_session, make_file_hash, minio_falso):
    ahora = datetime.now(BOGOTA)
    vieja = await make_file_hash(numero_usos=0, ultima_subida=ahora - timedelta(hours=48))
    reciente = await make_file_hash(numero_usos=0, ultima_subida=ahora - timedelta(minutes=1))
    vieja_resubida = await make_file_hash(
        numero_usos=0, created_at=ahora - timedelta(days=30), ultima_subida=ahora - timedelta(hours=1)
    )
    sin_marca_vieja = await make_file_hash(numero_usos=0, created_at=ahora - timedelta(days=3), ultima_subida=None)
    en_uso = await make_file_hash(numero_usos=1, ultima_subida=ahora - timedelta(days=90))
    await db_session.commit()

    await cleanup_scheduler.tarea_limpieza_temporales(db_session)

    quedan = set((await db_session.execute(select(FileHash.id))).scalars().all())
    assert quedan == {reciente.id, vieja_resubida.id, en_uso.id}
    assert sorted(minio_falso["borrados"]) == sorted([vieja.file_url, sin_marca_vieja.file_url])


# --- /docs/list: parámetros ----------------------------------------------------

@pytest.fixture
def perms_docs(monkeypatch):
    async def fake(user_id, permiso):
        return True
    monkeypatch.setattr("routes.documentos.verify_permission", fake)


@pytest.mark.parametrize("query", ["page=0", "page_size=0", "page_size=500", "fecha_desde=20-11-2026"])
async def test_list_parametros_invalidos_422(client, perms_docs, query):
    r = await client.get(f"/docs/list?{query}", headers=gateway_headers(1))
    assert r.status_code == 422


async def test_list_fecha_hasta_incluye_el_dia(client, perms_docs, make_documento, db_session):
    doc = await make_documento(creador_id=1, fecha_creacion=datetime(2026, 11, 20, 18, 30, tzinfo=BOGOTA))
    await make_documento(creador_id=1, fecha_creacion=datetime(2026, 11, 21, 0, 0, tzinfo=BOGOTA))
    await db_session.commit()
    r = await client.get("/docs/list?fecha_desde=2026-11-20&fecha_hasta=2026-11-20", headers=gateway_headers(1))
    assert r.status_code == 200
    assert [d["id"] for d in r.json()["documentos"]] == [doc.id]

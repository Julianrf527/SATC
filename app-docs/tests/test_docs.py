"""
Tests de los routers de documentos: permisos, fuga de información (403 vs 404),
reglas de negocio de revisión y endpoints service-to-service.

Los servicios externos (permisos, notificaciones, MinIO, antivirus, validación)
se monkeypatchean; la BD es real (docs_test_db).
"""
import io
import json
import pytest

from conftest import gateway_headers, service_headers

# Los nombres importados se parchean en el módulo donde se usan, así que hay
# que aplicar el patch en cada uno de los tres routers que los defina.
_MODULES = ["routes.documentos", "routes.revision", "routes.docs_service"]


def _patch_everywhere(monkeypatch, name, value):
    import importlib
    for mod in _MODULES:
        m = importlib.import_module(mod)
        if hasattr(m, name):
            monkeypatch.setattr(m, name, value)


@pytest.fixture
def perms(monkeypatch):
    """Instala un verify_permission falso manejado por un dict {(user_id, permiso): bool}."""
    table = {}

    async def fake_verify_permission(user_id, permission):
        return table.get((int(user_id), permission), False)

    _patch_everywhere(monkeypatch, "verify_permission", fake_verify_permission)
    return table


@pytest.fixture
def stub_externos(monkeypatch):
    """Neutraliza notificaciones, get_users_by_permission y el pipeline de archivo."""
    async def _noop(*a, **k):
        return {"ok": True}

    for fn in [
        "notify_assignment", "notify_new_version", "notify_document_approved",
        "notify_document_rejected", "notify_document_finalized",
    ]:
        _patch_everywhere(monkeypatch, fn, _noop)

    async def fake_users_by_permission(permission):
        return {2: {"nombre": "Revisor Dos", "correo": "r2@test.co"}}

    _patch_everywhere(monkeypatch, "get_users_by_permission", fake_users_by_permission)

    async def fake_validate(file_data, filename, max_size_mb):
        return {"sanitized_filename": filename, "mime_type": "application/pdf"}

    _patch_everywhere(monkeypatch, "validate_file_complete", fake_validate)
    _patch_everywhere(monkeypatch, "escanear_archivo", lambda *a, **k: {"ok": True, "escaneado": True})

    async def fake_upload(**k):
        return {"ok": True, "url": "satc-documentos/nuevo/archivo.pdf", "id": 99,
                "file_hash": "a" * 64, "deduplicated": False, "numero_usos": 0}

    _patch_everywhere(monkeypatch, "upload_file_with_deduplication", fake_upload)


def _pdf_upload():
    return {"archivo": ("archivo.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")}


# ---------------- /list ----------------

async def test_list_sin_permisos_403(client, perms):
    r = await client.get("/docs/list", headers=gateway_headers(1))
    assert r.status_code == 403


async def test_list_creador_ve_solo_los_suyos(client, perms, make_documento):
    perms[(1, "documento_crear")] = True
    await make_documento(creador_id=1)
    await make_documento(creador_id=99)
    r = await client.get("/docs/list", headers=gateway_headers(1))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["documentos"][0]["usuario_creador_id"] == 1


# ---------------- /detail (fuga de info) ----------------

async def test_detail_inexistente_devuelve_403_no_404(client, perms):
    """Seguridad: un ID inexistente no debe distinguirse de uno ajeno."""
    perms[(1, "documento_crear")] = True
    r = await client.get("/docs/detail/999999", headers=gateway_headers(1))
    assert r.status_code == 403


async def test_detail_ajeno_devuelve_403(client, perms, make_documento):
    perms[(1, "documento_crear")] = True
    doc = await make_documento(creador_id=42)
    r = await client.get(f"/docs/detail/{doc.id}", headers=gateway_headers(1))
    assert r.status_code == 403


async def test_detail_propio_ok(client, perms, stub_externos, make_documento):
    perms[(1, "documento_crear")] = True
    doc = await make_documento(creador_id=1)
    r = await client.get(f"/docs/detail/{doc.id}", headers=gateway_headers(1))
    assert r.status_code == 200
    assert r.json()["documento_id"] == doc.id


# ---------------- /create ----------------

async def test_create_sin_permiso_403(client, perms):
    r = await client.post("/docs/create", headers=gateway_headers(1),
                          data={"nombre": "X", "tipo_archivo": "pdf", "revisores_ids": "[2]"},
                          files=_pdf_upload())
    assert r.status_code == 403


async def test_create_tipo_invalido_400(client, perms):
    perms[(1, "documento_crear")] = True
    r = await client.post("/docs/create", headers=gateway_headers(1),
                          data={"nombre": "X", "tipo_archivo": "exe", "revisores_ids": "[2]"},
                          files=_pdf_upload())
    assert r.status_code == 400


async def test_create_revisor_sin_permiso_400(client, perms, stub_externos):
    perms[(1, "documento_crear")] = True
    # revisor 2 NO tiene permiso de revisor
    r = await client.post("/docs/create", headers=gateway_headers(1),
                          data={"nombre": "X", "tipo_archivo": "pdf", "revisores_ids": "[2]"},
                          files=_pdf_upload())
    assert r.status_code == 400


async def test_create_ok(client, perms, stub_externos, db_session):
    perms[(1, "documento_crear")] = True
    perms[(2, "documento_revisar")] = True
    r = await client.post("/docs/create", headers=gateway_headers(1),
                          data={"nombre": "Doc nuevo", "tipo_archivo": "pdf", "revisores_ids": "[2]"},
                          files=_pdf_upload())
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


# ---------------- /upload-version (fuga de info) ----------------

async def test_upload_version_inexistente_403(client, perms, stub_externos):
    perms[(1, "documento_crear")] = True
    r = await client.post("/docs/upload-version/999999", headers=gateway_headers(1),
                          files=_pdf_upload())
    assert r.status_code == 403


async def test_upload_version_ajeno_403(client, perms, stub_externos, make_documento):
    perms[(1, "documento_crear")] = True
    doc = await make_documento(creador_id=42, estado="rechazado")
    r = await client.post(f"/docs/upload-version/{doc.id}", headers=gateway_headers(1),
                          files=_pdf_upload())
    assert r.status_code == 403


# ---------------- /review ----------------

async def test_review_no_asignado_403(client, perms, make_documento):
    perms[(1, "documento_revisar")] = True
    doc = await make_documento(creador_id=42)
    r = await client.post(f"/docs/review/{doc.id}", headers=gateway_headers(1),
                          data={"estado_revision": "aprobado"})
    assert r.status_code == 403


async def test_review_aprobar_ok(client, perms, stub_externos, make_documento, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await make_documento(creador_id=1, estado="en_revision")
    await make_asignacion(doc.id, revisor_id=2)
    r = await client.post(f"/docs/review/{doc.id}", headers=gateway_headers(2),
                          data={"estado_revision": "aprobado"})
    assert r.status_code == 200
    assert r.json()["estado"] == "aprobado"


async def test_review_tres_devoluciones_finaliza(client, perms, stub_externos, make_documento, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await make_documento(creador_id=1, estado="en_revision", numero_devoluciones=2)
    await make_asignacion(doc.id, revisor_id=2)
    r = await client.post(f"/docs/review/{doc.id}", headers=gateway_headers(2),
                          data={"estado_revision": "devuelto"})
    assert r.status_code == 200
    assert r.json()["estado"] == "finalizado"


# ---------------- /download (fuga de info) ----------------

async def test_download_version_inexistente_403(client, perms):
    r = await client.get("/docs/download/999999", headers=gateway_headers(1))
    assert r.status_code == 403


async def test_download_ajeno_403(client, perms, make_documento, make_version):
    doc = await make_documento(creador_id=42)
    ver = await make_version(doc.id)
    r = await client.get(f"/docs/download/{ver.id}", headers=gateway_headers(1))
    assert r.status_code == 403


# ---------------- /stats y /reviewers ----------------

async def test_stats_sin_permisos_403(client, perms):
    r = await client.get("/docs/stats", headers=gateway_headers(1))
    assert r.status_code == 403


async def test_stats_creador_ok(client, perms, make_documento):
    perms[(1, "documento_crear")] = True
    await make_documento(creador_id=1, estado="aprobado")
    r = await client.get("/docs/stats", headers=gateway_headers(1))
    assert r.status_code == 200
    assert r.json()["stats"]["creador"]["total_creados"] == 1


async def test_reviewers_sin_acceso_403(client, perms):
    r = await client.get("/docs/reviewers", headers=gateway_headers(1))
    assert r.status_code == 403


async def test_reviewers_ok(client, perms, stub_externos):
    perms[(1, "documento_crear")] = True
    r = await client.get("/docs/reviewers", headers=gateway_headers(1))
    assert r.status_code == 200
    # el propio usuario (id 1) se excluye; revisor 2 aparece
    assert any(u["id"] == 2 for u in r.json()["usuarios"])


# ---------------- service-to-service ----------------

async def test_create_service_sin_token_403(client):
    r = await client.post("/docs/create-service",
                          json={"nombre": "X", "descripcion": "d", "creador_id": 1, "revisores_ids": [2]})
    assert r.status_code == 403


async def test_create_service_ok(client, stub_externos):
    r = await client.post("/docs/create-service", headers=service_headers(),
                          json={"nombre": "X", "descripcion": "d", "creador_id": 1, "revisores_ids": [2]})
    assert r.status_code == 200
    assert r.json()["ok"] is True


async def test_finalize_service_inexistente_404(client):
    r = await client.put("/docs/finalize-service/999999", headers=service_headers())
    assert r.status_code == 404


async def test_detail_service_ok(client, make_documento, make_version):
    doc = await make_documento(creador_id=1, estado="aprobado")
    await make_version(doc.id)
    r = await client.get(f"/docs/detail-service/{doc.id}", headers=service_headers())
    assert r.status_code == 200
    assert r.json()["estado"] == "aprobado"

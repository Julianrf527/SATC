"""
Tests de routes/files.py: subida con deduplicación, acceso interno por token,
y contadores de uso (increment/decrement).
"""
import io
import pytest

from conftest import gateway_headers, service_headers

MODULE = "routes.files"


@pytest.fixture
def stub_upload(monkeypatch):
    async def fake_validate(file_data, filename, max_size_mb):
        return {"sanitized_filename": filename, "mime_type": "application/pdf"}

    monkeypatch.setattr(f"{MODULE}.validate_file_complete", fake_validate)
    monkeypatch.setattr(f"{MODULE}.escanear_archivo", lambda *a, **k: {"ok": True, "escaneado": True})

    async def fake_upload(**k):
        return {"ok": True, "url": "satc-documentos/x/archivo.pdf", "id": 1,
                "file_hash": "b" * 64, "message": "ok", "deduplicated": False, "numero_usos": 0}

    monkeypatch.setattr(f"{MODULE}.upload_file_with_deduplication", fake_upload)


@pytest.fixture
def perms(monkeypatch):
    """verify_permission falso: {(user_id, permiso): bool}. Registra las consultas."""
    table = {}

    async def fake_verify_permission(user_id, permission):
        return table.get((int(user_id), permission), False)

    monkeypatch.setattr(f"{MODULE}.verify_permission", fake_verify_permission)
    return table


def _pdf():
    return {"archivo": ("a.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")}


@pytest.fixture
def stub_minio(monkeypatch):
    monkeypatch.setattr(f"{MODULE}.get_file_from_minio", lambda name: {"ok": True, "data": b"%PDF-1.4 x"})


# --- upload -----------------------------------------------------------------

async def test_upload_sin_token_401(client, stub_upload):
    r = await client.post("/files/upload", files=_pdf())
    assert r.status_code == 401


async def test_upload_gateway_sin_permiso_403(client, stub_upload, perms):
    r = await client.post("/files/upload", files=_pdf(), headers=gateway_headers(5))
    assert r.status_code == 403


async def test_upload_gateway_con_permiso_ok(client, stub_upload, perms):
    perms[(5, "infraccion_gestionar")] = True
    r = await client.post("/files/upload", files=_pdf(), headers=gateway_headers(5))
    assert r.status_code == 200
    assert r.json()["file_id"] == 1


async def test_upload_service_token_ok(client, stub_upload, perms):
    r = await client.post("/files/upload", files=_pdf(), headers=service_headers())
    assert r.status_code == 200


# --- download (C1) ------------------------------------------------------------

async def test_download_sin_token_401(client, make_file_hash, stub_minio):
    fh = await make_file_hash()
    r = await client.get(f"/files/download/{fh.id}")
    assert r.status_code == 401


async def test_download_gateway_sin_permiso_403(client, perms, make_file_hash, stub_minio):
    """Usuario autenticado sin ningún permiso de módulo (p. ej. solo auditoría o admin)."""
    fh = await make_file_hash()
    perms[(7, "auditoria_usuarios")] = True
    r = await client.get(f"/files/download/{fh.id}", headers=gateway_headers(7))
    assert r.status_code == 403


@pytest.mark.parametrize("permiso", [
    "sancionatorio_gestionar", "sancionatorio_consultar", "infraccion_gestionar",
    "infraccion_consultar", "infraccion_informes_subir", "infraccion_informes_revisar",
    "infraccion_asignar_informes", "infraccion_cargue", "documento_crear", "documento_revisar",
])
async def test_download_gateway_con_permiso_de_modulo_ok(client, perms, make_file_hash, stub_minio, permiso):
    fh = await make_file_hash()
    perms[(7, permiso)] = True
    r = await client.get(f"/files/download/{fh.id}", headers=gateway_headers(7))
    assert r.status_code == 200
    assert r.content == b"%PDF-1.4 x"


async def test_download_gateway_falso_403(client, perms, make_file_hash, stub_minio):
    fh = await make_file_hash()
    r = await client.get(f"/files/download/{fh.id}", headers={
        "x-gateway-token": "falso", "X-Gateway-User-Id": "1", "X-Gateway-Role-Id": "1"})
    assert r.status_code == 403


async def test_download_service_token_ok_sin_consultar_permisos(client, perms, make_file_hash, stub_minio):
    fh = await make_file_hash()
    r = await client.get(f"/files/download/{fh.id}", headers=service_headers())
    assert r.status_code == 200


async def test_download_service_token_invalido_403(client, make_file_hash, stub_minio):
    fh = await make_file_hash()
    r = await client.get(f"/files/download/{fh.id}", headers={"x-service-token": "basura"})
    assert r.status_code == 403


async def test_get_file_sin_token_401(client):
    r = await client.get("/files/999999")
    assert r.status_code == 401


async def test_get_file_inexistente_404(client):
    r = await client.get("/files/999999", headers=service_headers())
    assert r.status_code == 404


async def test_get_file_con_gateway_token_y_permiso_ok(client, perms, make_file_hash):
    fh = await make_file_hash()
    perms[(1, "sancionatorio_consultar")] = True
    r = await client.get(f"/files/{fh.id}", headers=gateway_headers(1))
    assert r.status_code == 200
    assert r.json()["data"]["id"] == fh.id


async def test_get_file_con_gateway_token_sin_permiso_403(client, perms, make_file_hash):
    fh = await make_file_hash()
    r = await client.get(f"/files/{fh.id}", headers=gateway_headers(1))
    assert r.status_code == 403


async def test_batch_sin_token_403(client):
    r = await client.post("/files/batch", json={"file_ids": [1]})
    assert r.status_code == 403


async def test_batch_con_service_token_ok(client, make_file_hash):
    fh = await make_file_hash()
    r = await client.post("/files/batch", headers=service_headers(), json={"file_ids": [fh.id]})
    assert r.status_code == 200
    assert r.json()["data"][0]["id"] == fh.id


async def test_batch_con_gateway_token_rechazado_403(client, make_file_hash):
    """/files/batch es exclusivamente service-to-service: gateway-token solo ya no alcanza."""
    fh = await make_file_hash()
    r = await client.post("/files/batch", headers=gateway_headers(1), json={"file_ids": [fh.id]})
    assert r.status_code == 403


async def test_increment_usage(client, make_file_hash, db_session):
    fh = await make_file_hash(numero_usos=0)
    r = await client.put("/files/increment-usage", headers=service_headers(), json={"file_ids": [fh.id]})
    assert r.status_code == 200
    await db_session.refresh(fh)
    assert fh.numero_usos == 1


async def test_decrement_no_baja_de_cero(client, make_file_hash, db_session):
    fh = await make_file_hash(numero_usos=0)
    r = await client.put("/files/decrement-usage", headers=service_headers(), json={"file_ids": [fh.id]})
    assert r.status_code == 200
    await db_session.refresh(fh)
    assert fh.numero_usos == 0


async def test_increment_sin_ids_400(client):
    r = await client.put("/files/increment-usage", headers=service_headers(), json={"file_ids": []})
    assert r.status_code == 400

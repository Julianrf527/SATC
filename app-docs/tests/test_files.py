"""
Tests de routes/files.py: subida con deduplicación, acceso interno por token,
y contadores de uso (increment/decrement).
"""
import io
import os
import pytest
from minio.error import S3Error

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


class _ObjetoFalso:
    """Imita la respuesta de urllib3 que devuelve minio.get_object."""

    def __init__(self, data: bytes):
        self.data = data
        self.cerrado = False

    def stream(self, n):
        for i in range(0, len(self.data), n):
            yield self.data[i:i + n]

    def close(self):
        self.cerrado = True

    def release_conn(self):
        pass


CONTENIDO = b"%PDF-1.4 0123456789"


class _NoExiste(S3Error):
    """S3Error sin depender de la firma del constructor según la versión de minio."""

    def __init__(self):
        Exception.__init__(self, "NoSuchKey")


@pytest.fixture
def stub_minio(monkeypatch):
    """MinIO falso: {file_url: bytes}; por defecto todo objeto vale CONTENIDO."""
    objetos = {}
    abiertos = []

    def fake_abrir(name, offset=0, length=0):
        data = objetos.get(name, CONTENIDO)
        if data is None:
            raise _NoExiste()
        objeto = _ObjetoFalso(data[offset:offset + length] if length else data[offset:])
        abiertos.append(objeto)
        return objeto

    monkeypatch.setattr(f"{MODULE}.abrir_objeto", fake_abrir)
    monkeypatch.setattr(f"{MODULE}.tamano_objeto", lambda name: len(objetos.get(name, CONTENIDO)))
    objetos["_abiertos"] = abiertos
    return objetos


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
    "infraccion_asignar_informes", "infraccion_super_gestion", "documento_crear", "documento_revisar",
])
async def test_download_gateway_con_permiso_de_modulo_ok(client, perms, make_file_hash, stub_minio, permiso):
    fh = await make_file_hash()
    perms[(7, permiso)] = True
    r = await client.get(f"/files/download/{fh.id}", headers=gateway_headers(7))
    assert r.status_code == 200
    assert r.content == CONTENIDO


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


# --- download: rangos y cabeceras ----------------------------------------------

async def _archivo(make_file_hash, **kw):
    return await make_file_hash(file_size=len(CONTENIDO), **kw)


async def test_download_completo_anuncia_rangos_y_longitud(client, make_file_hash, stub_minio):
    fh = await _archivo(make_file_hash)
    r = await client.get(f"/files/download/{fh.id}", headers=service_headers())
    assert r.status_code == 200
    assert r.content == CONTENIDO
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-length"] == str(len(CONTENIDO))
    assert r.headers["etag"] == f'"{fh.file_hash}"'
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert "content-encoding" not in r.headers
    assert r.headers["content-disposition"].startswith("inline;")
    assert r.headers["content-type"].startswith("application/pdf")
    assert all(o.cerrado for o in stub_minio["_abiertos"])


@pytest.mark.parametrize("rango,esperado,content_range", [
    ("bytes=0-3", CONTENIDO[0:4], "bytes 0-3/19"),
    ("bytes=9-", CONTENIDO[9:], "bytes 9-18/19"),
    ("bytes=-5", CONTENIDO[-5:], "bytes 14-18/19"),
    ("bytes=10-999", CONTENIDO[10:], "bytes 10-18/19"),
])
async def test_download_rango_206(client, make_file_hash, stub_minio, rango, esperado, content_range):
    fh = await _archivo(make_file_hash)
    r = await client.get(f"/files/download/{fh.id}", headers={**service_headers(), "Range": rango})
    assert r.status_code == 206
    assert r.content == esperado
    assert r.headers["content-range"] == content_range
    assert r.headers["content-length"] == str(len(esperado))


async def test_download_rango_fuera_del_archivo_416(client, make_file_hash, stub_minio):
    fh = await _archivo(make_file_hash)
    r = await client.get(f"/files/download/{fh.id}", headers={**service_headers(), "Range": "bytes=50-60"})
    assert r.status_code == 416
    assert r.headers["content-range"] == f"bytes */{len(CONTENIDO)}"


@pytest.mark.parametrize("rango", ["bytes=0-1,4-5", "items=0-3", "bytes=5-2"])
async def test_download_rango_no_soportado_sirve_completo(client, make_file_hash, stub_minio, rango):
    fh = await _archivo(make_file_hash)
    r = await client.get(f"/files/download/{fh.id}", headers={**service_headers(), "Range": rango})
    assert r.status_code == 200
    assert r.content == CONTENIDO


async def test_download_if_range_distinto_sirve_completo(client, make_file_hash, stub_minio):
    fh = await _archivo(make_file_hash)
    h = {**service_headers(), "Range": "bytes=0-3"}
    r = await client.get(f"/files/download/{fh.id}", headers={**h, "If-Range": '"otro"'})
    assert r.status_code == 200 and r.content == CONTENIDO
    r = await client.get(f"/files/download/{fh.id}", headers={**h, "If-Range": f'"{fh.file_hash}"'})
    assert r.status_code == 206 and r.content == CONTENIDO[:4]


async def test_download_tipo_no_seguro_va_como_adjunto(client, make_file_hash, stub_minio):
    fh = await _archivo(make_file_hash, content_type="text/plain", file_url="satc-documentos/files/ab/x.txt")
    r = await client.get(f"/files/download/{fh.id}", headers=service_headers())
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/octet-stream")
    assert r.headers["content-disposition"].startswith("attachment;")


async def test_download_sin_tamano_en_bd_lo_consulta(client, make_file_hash, stub_minio):
    fh = await make_file_hash(file_size=None)
    r = await client.get(f"/files/download/{fh.id}", headers={**service_headers(), "Range": "bytes=0-3"})
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 0-3/{len(CONTENIDO)}"


async def test_download_objeto_ausente_404(client, make_file_hash, stub_minio):
    fh = await _archivo(make_file_hash)
    stub_minio[fh.file_url] = None
    r = await client.get(f"/files/download/{fh.id}", headers=service_headers())
    assert r.status_code == 404


# --- download-unified -------------------------------------------------------

def _pdf_de(paginas: int) -> bytes:
    import io

    from pypdf import PdfWriter

    w = PdfWriter()
    for _ in range(paginas):
        w.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


@pytest.fixture
def stub_minio_a_archivo(monkeypatch):
    """MinIO simulado: url -> bytes (None = no existe)."""
    contenidos: dict[str, bytes | None] = {}

    def fake(url, ruta):
        data = contenidos.get(url)
        if data is None:
            return False
        with open(ruta, "wb") as f:
            f.write(data)
        return True

    monkeypatch.setattr(f"{MODULE}.descargar_a_archivo", fake)
    return contenidos


async def test_download_unified_une_en_orden_y_omite_faltantes(client, make_file_hash, stub_minio_a_archivo):
    import io

    from pypdf import PdfReader

    # file_hash explícito: el fixture genera el mismo hash si se crean varios en un test.
    a, b, c = [await make_file_hash(file_hash=f"{letra * 64}") for letra in "abc"]
    stub_minio_a_archivo[a.file_url] = _pdf_de(2)
    stub_minio_a_archivo[b.file_url] = None  # no está en MinIO: se omite
    stub_minio_a_archivo[c.file_url] = _pdf_de(1)
    r = await client.post("/files/download-unified", headers=service_headers(), json={"file_ids": [c.id, b.id, a.id]})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert len(PdfReader(io.BytesIO(r.content)).pages) == 3


async def test_download_unified_sin_documentos_validos_500(client, make_file_hash, stub_minio_a_archivo):
    a = await make_file_hash()
    stub_minio_a_archivo[a.file_url] = None
    r = await client.post("/files/download-unified", headers=service_headers(), json={"file_ids": [a.id]})
    assert r.status_code == 500


async def test_download_unified_solo_servicios(client, perms, make_file_hash, stub_minio_a_archivo):
    a = await make_file_hash()
    r = await client.post("/files/download-unified", headers=gateway_headers(7), json={"file_ids": [a.id]})
    assert r.status_code in (401, 403)


# --- punta a punta: FilesClient -> app-docs -> respuesta_archivo -----------------

async def test_respuesta_archivo_contra_app_docs_real(client, make_file_hash, stub_minio):
    import httpx
    import main as main_module
    from satc_shared.archivos import respuesta_archivo
    from satc_shared.clients import FilesClient

    fh = await make_file_hash(file_size=len(CONTENIDO))
    files = FilesClient(
        "http://test", service_name="sanctioning-service", secret_key=os.environ["SANCTIONING_SERVICE_SECRET"],
        transport=httpx.ASGITransport(app=main_module.app),
    )
    r = await respuesta_archivo(files, fh.id, {"range": "bytes=0-7"}, nombre="Acta nº 3.pdf")
    cuerpo = b"".join([b async for b in r.body_iterator])
    assert r.status_code == 206 and cuerpo == CONTENIDO[:8]
    assert r.headers["content-range"] == f"bytes 0-7/{len(CONTENIDO)}"
    assert r.headers["content-disposition"].startswith('inline; filename="Acta no 3.pdf"; filename*=UTF-8')

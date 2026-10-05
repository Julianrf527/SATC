"""
Tests del módulo Documentos (flujo fijo genérico sobre satc_shared.review_process):
permisos, fuga de información (403 vs 404), reglas del flujo, contrato de
/docs/detail, numero_usos y la migración de esquema.

Los servicios externos (permisos, notificaciones, MinIO, antivirus, validación)
se monkeypatchean; la BD es real (docs_test_db).
"""
import io

import pytest
from sqlalchemy import select, text

from conftest import engine, gateway_headers

# Los nombres importados se parchean en el módulo donde se usan.
_MODULES = ["routes.documentos", "routes.revision", "services.revision_documentos"]


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
    """Neutraliza notificaciones, usuarios (por permiso y por id) y el pipeline de archivo.

    Devuelve un dict de estado: ``file_id`` que devolverá la subida (None por
    defecto), ``subidas`` (nº de llamadas a MinIO) y ``notificaciones``."""
    estado = {"file_id": None, "url": "satc-documentos/nuevo/archivo.pdf", "subidas": 0, "notificaciones": []}

    def _notif(nombre):
        async def _fn(*a, **k):
            estado["notificaciones"].append((nombre, k))
            return {"ok": True}
        return _fn

    for fn in [
        "notify_assignment", "notify_new_version", "notify_document_approved",
        "notify_document_rejected", "notify_document_finalized",
    ]:
        _patch_everywhere(monkeypatch, fn, _notif(fn))

    async def fake_users_by_permission(permission):
        return {2: {"nombre": "Revisor Dos", "correo": "r2@test.co"}}

    _patch_everywhere(monkeypatch, "get_users_by_permission", fake_users_by_permission)

    # Nombres por id (POST /user/batch): no depende del permiso actual.
    nombres = {2: "Revisor Dos", 3: "Revisor Sin Permiso"}
    estado["batch"] = []

    async def fake_user_names(ids):
        estado["batch"].append(sorted(ids))
        return {i: nombres[i] for i in ids if i in nombres}

    _patch_everywhere(monkeypatch, "get_user_names", fake_user_names)

    async def fake_validate(file_data, filename, max_size_mb):
        return {"sanitized_filename": filename, "mime_type": "application/pdf"}

    _patch_everywhere(monkeypatch, "validate_file_complete", fake_validate)
    _patch_everywhere(monkeypatch, "escanear_archivo", lambda *a, **k: {"ok": True, "escaneado": True})

    async def fake_upload(**k):
        estado["subidas"] += 1
        return {"ok": True, "url": estado["url"], "id": estado["file_id"],
                "file_hash": "a" * 64, "deduplicated": False, "numero_usos": 0}

    _patch_everywhere(monkeypatch, "upload_file_with_deduplication", fake_upload)
    return estado


def _pdf_upload(nombre="archivo.pdf", campo="archivo"):
    return {campo: (nombre, io.BytesIO(b"%PDF-1.4 test"), "application/pdf")}


async def _doc_en_revision(make_documento, make_version, make_asignacion, **overrides):
    doc = await make_documento(creador_id=1, estado=overrides.pop("estado", "en_revision"), **overrides)
    await make_version(doc.id)
    await make_asignacion(doc.id, revisor_id=2)
    return doc


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
    doc = body["documentos"][0]
    assert doc["creador_id"] == 1 and "usuario_creador_id" not in doc
    assert doc["estado"] == {"codigo": "en_revision", "etiqueta": "En revisión", "tono": "info"}
    assert [e["codigo"] for e in body["estados"]] == ["en_revision", "aprobado", "rechazado", "finalizado"]
    assert "origen" not in body["documentos"][0]


async def test_list_revisor_ve_asignados(client, perms, make_documento, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await make_documento(creador_id=1)
    await make_documento(creador_id=1)
    await make_asignacion(doc.id, revisor_id=2)
    r = await client.get("/docs/list", headers=gateway_headers(2))
    assert r.status_code == 200
    assert [d["id"] for d in r.json()["documentos"]] == [doc.id]


# ---------------- /detail (fuga de info + contrato) ----------------

async def test_detail_inexistente_devuelve_403_no_404(client, perms, stub_externos):
    """Seguridad: un ID inexistente no debe distinguirse de uno ajeno."""
    perms[(1, "documento_crear")] = True
    r = await client.get("/docs/detail/999999", headers=gateway_headers(1))
    assert r.status_code == 403


async def test_detail_ajeno_devuelve_403(client, perms, stub_externos, make_documento):
    perms[(1, "documento_crear")] = True
    doc = await make_documento(creador_id=42)
    r = await client.get(f"/docs/detail/{doc.id}", headers=gateway_headers(1))
    assert r.status_code == 403


async def test_detail_sin_permisos_del_modulo_403(client, perms, stub_externos, make_documento):
    doc = await make_documento(creador_id=1)
    r = await client.get(f"/docs/detail/{doc.id}", headers=gateway_headers(1))
    assert r.status_code == 403


async def test_detail_contrato_creador(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(1, "documento_crear")] = True
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion)
    r = await client.get(f"/docs/detail/{doc.id}", headers=gateway_headers(1))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == doc.id
    assert body["estado"] == {"codigo": "en_revision", "etiqueta": "En revisión", "tono": "info"}
    assert body["max_devoluciones"] == 3
    assert body["creador_id"] == 1
    assert body["revisores"][0]["revisor_id"] == 2
    assert body["revisores"][0]["nombre"] == "Revisor Dos"
    assert body["versiones"][0]["archivo"]["nombre"] == "archivo.pdf"
    # El creador no revisa; en en_revision no puede subir versión (con motivo).
    assert body["acciones_disponibles"] == []
    assert body["subida_version"]["permitida"] is False
    assert body["subida_version"]["motivo"]


async def test_detail_nombres_por_id_aunque_pierda_el_permiso(client, perms, stub_externos, db_session, make_documento, make_version, make_asignacion):
    """El nombre de un revisor sale de /user/batch, no de la lista de usuarios con
    permiso de revisor: si lo perdió, su revisión sigue mostrando su nombre."""
    from db.models.revisiones import Revision

    perms[(1, "documento_crear")] = True
    doc = await make_documento(creador_id=1, estado="rechazado", numero_devoluciones=1)
    await make_version(doc.id)
    await make_asignacion(doc.id, revisor_id=3)  # sin documento_revisar
    db_session.add(Revision(proceso_id=doc.id, version_revisada=1, revisor_id=3, accion="devuelto", comentarios="x"))
    await db_session.commit()

    body = (await client.get(f"/docs/detail/{doc.id}", headers=gateway_headers(1))).json()
    assert body["revisores"][0]["nombre"] == "Revisor Sin Permiso"
    rev = body["revisiones"][0]
    assert (rev["revisor_nombre"], rev["accion_etiqueta"], rev["tono"]) == ("Revisor Sin Permiso", "Devuelto", "warning")
    assert stub_externos["batch"] == [[3]]


async def test_detail_auditoria_con_etiqueta_y_tono(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(1, "documento_crear")] = True
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion)
    r = await client.post(f"/docs/review/{doc.id}", headers=gateway_headers(2), data={"accion": "aprobado"})
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == {"codigo": "aprobado", "etiqueta": "Aprobado", "tono": "success"}

    body = (await client.get(f"/docs/detail/{doc.id}", headers=gateway_headers(1))).json()
    aprobar = body["auditoria"][-1]
    assert (aprobar["accion"], aprobar["accion_etiqueta"], aprobar["tono"]) == ("aprobar", "Aprobado", "success")
    assert body["revisiones"][0]["accion_etiqueta"] == "Aprobado"


async def test_detail_contrato_revisor(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion)
    r = await client.get(f"/docs/detail/{doc.id}", headers=gateway_headers(2))
    assert r.status_code == 200, r.text
    body = r.json()
    acciones = {a["codigo"]: a for a in body["acciones_disponibles"]}
    assert set(acciones) == {"aprobado", "devuelto"}
    assert acciones["aprobado"]["adjunto"]["permitido"] is False
    assert acciones["devuelto"]["adjunto"] == {"permitido": True, "extensiones": [".pdf", ".doc", ".docx"]}
    assert all(a["bloqueada"] is None for a in acciones.values())
    assert body["subida_version"] is None  # el revisor no sube versiones


async def test_detail_revisor_sin_acciones_si_ya_aprobado(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion, estado="aprobado")
    r = await client.get(f"/docs/detail/{doc.id}", headers=gateway_headers(2))
    assert r.status_code == 200
    assert r.json()["acciones_disponibles"] == []


async def test_detail_creador_puede_subir_si_rechazado(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(1, "documento_crear")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion, estado="rechazado")
    r = await client.get(f"/docs/detail/{doc.id}", headers=gateway_headers(1))
    assert r.json()["subida_version"] == {"permitida": True, "extensiones": [".pdf", ".doc", ".docx"], "motivo": None}


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
    assert stub_externos["subidas"] == 0


async def test_create_ok(client, perms, stub_externos, db_session, make_file_hash):
    from db.models.asignaciones_revisores import AsignacionRevisor
    from db.models.documentos import Documento
    from db.models.versiones_documento import VersionDocumento

    perms[(1, "documento_crear")] = True
    perms[(2, "documento_revisar")] = True
    fh = await make_file_hash()
    stub_externos["file_id"], stub_externos["url"] = fh.id, fh.file_url

    r = await client.post("/docs/create", headers=gateway_headers(1),
                          data={"nombre": "Doc nuevo", "tipo_archivo": "pdf", "revisores_ids": "[2]"},
                          files=_pdf_upload("Informe Final.pdf"))
    assert r.status_code == 200, r.text
    doc_id = r.json()["documento_id"]

    doc = await db_session.get(Documento, doc_id)
    assert (doc.estado, doc.version_actual, doc.creador_id, doc.tipo_archivo) == ("en_revision", 1, 1, "pdf")
    version = await db_session.scalar(select(VersionDocumento).where(VersionDocumento.proceso_id == doc_id))
    assert (version.numero_version, version.file_id, version.archivo_nombre) == (1, fh.id, "Informe Final.pdf")
    asig = await db_session.scalar(select(AsignacionRevisor).where(AsignacionRevisor.proceso_id == doc_id))
    assert asig.revisor_id == 2 and asig.notificado is True
    await db_session.refresh(fh)
    assert fh.numero_usos == 1
    assert [n for n, _ in stub_externos["notificaciones"]] == ["notify_assignment"]


# ---------------- /upload-version ----------------

async def test_upload_version_inexistente_403(client, perms, stub_externos):
    perms[(1, "documento_crear")] = True
    r = await client.post("/docs/upload-version/999999", headers=gateway_headers(1), files=_pdf_upload())
    assert r.status_code == 403


async def test_upload_version_ajeno_403(client, perms, stub_externos, make_documento):
    perms[(1, "documento_crear")] = True
    doc = await make_documento(creador_id=42, estado="rechazado")
    r = await client.post(f"/docs/upload-version/{doc.id}", headers=gateway_headers(1), files=_pdf_upload())
    assert r.status_code == 403
    assert stub_externos["subidas"] == 0


async def test_upload_version_en_revision_400(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(1, "documento_crear")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion)
    r = await client.post(f"/docs/upload-version/{doc.id}", headers=gateway_headers(1), files=_pdf_upload())
    assert r.status_code == 400
    assert stub_externos["subidas"] == 0


async def test_upload_version_tras_devolucion_ok(client, perms, stub_externos, db_session, make_documento, make_version, make_asignacion, make_file_hash):
    perms[(1, "documento_crear")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion, estado="rechazado", numero_devoluciones=1)
    fh = await make_file_hash()
    stub_externos["file_id"], stub_externos["url"] = fh.id, fh.file_url

    r = await client.post(f"/docs/upload-version/{doc.id}", headers=gateway_headers(1),
                          data={"comentario": "corregido"}, files=_pdf_upload())
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2
    assert r.json()["estado"]["codigo"] == "en_revision"
    await db_session.refresh(fh)
    assert fh.numero_usos == 1
    assert [n for n, _ in stub_externos["notificaciones"]] == ["notify_new_version"]


async def test_upload_version_duplicada_409(client, perms, stub_externos, make_documento, make_version, make_asignacion, make_file_hash):
    perms[(1, "documento_crear")] = True
    fh = await make_file_hash()
    doc = await make_documento(creador_id=1, estado="rechazado")
    await make_version(doc.id, file_id=fh.id, archivo_url=fh.file_url)
    await make_asignacion(doc.id, revisor_id=2)
    stub_externos["file_id"], stub_externos["url"] = fh.id, fh.file_url

    r = await client.post(f"/docs/upload-version/{doc.id}", headers=gateway_headers(1), files=_pdf_upload())
    assert r.status_code == 409


# ---------------- /review ----------------

async def test_review_no_asignado_403(client, perms, stub_externos, make_documento):
    perms[(1, "documento_revisar")] = True
    doc = await make_documento(creador_id=42)
    r = await client.post(f"/docs/review/{doc.id}", headers=gateway_headers(1), data={"accion": "aprobado"})
    assert r.status_code == 403


async def test_review_campos_historicos_no_se_aceptan(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    """Contrato único: `accion` es obligatorio; `estado_revision` ya no existe."""
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion)
    r = await client.post(f"/docs/review/{doc.id}", headers=gateway_headers(2), data={"estado_revision": "aprobado"})
    assert r.status_code == 422


async def test_review_inexistente_403(client, perms, stub_externos):
    perms[(1, "documento_revisar")] = True
    r = await client.post("/docs/review/999999", headers=gateway_headers(1), data={"accion": "aprobado"})
    assert r.status_code == 403


async def test_review_aprobar_ok(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion)
    r = await client.post(f"/docs/review/{doc.id}", headers=gateway_headers(2), data={"accion": "aprobado"})
    assert r.status_code == 200, r.text
    assert r.json()["estado"]["codigo"] == "aprobado"
    assert [n for n, _ in stub_externos["notificaciones"]] == ["notify_document_approved"]


async def test_review_campo_accion(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion)
    r = await client.post(f"/docs/review/{doc.id}", headers=gateway_headers(2), data={"accion": "devuelto", "comentario": "Falta firma"})
    assert r.status_code == 200
    assert r.json()["estado"]["codigo"] == "rechazado"
    assert r.json()["numero_devoluciones"] == 1


async def test_review_devolver_sin_comentario_400(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion)
    r = await client.post(f"/docs/review/{doc.id}", headers=gateway_headers(2), data={"accion": "devuelto"})
    assert r.status_code == 400


async def test_review_aprobado_firma_ya_no_existe_400(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion)
    r = await client.post(f"/docs/review/{doc.id}", headers=gateway_headers(2), data={"accion": "aprobado_firma"})
    assert r.status_code == 400


async def test_review_fuera_de_revision_400(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion, estado="rechazado")
    r = await client.post(f"/docs/review/{doc.id}", headers=gateway_headers(2), data={"accion": "aprobado"})
    assert r.status_code == 400


async def test_review_tres_devoluciones_finaliza(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion, numero_devoluciones=2)
    r = await client.post(f"/docs/review/{doc.id}", headers=gateway_headers(2), data={"accion": "devuelto", "comentario": "Falta firma"})
    assert r.status_code == 200
    assert r.json()["estado"]["codigo"] == "finalizado"
    assert [n for n, _ in stub_externos["notificaciones"]] == ["notify_document_finalized"]


async def test_review_devolver_con_adjunto(client, perms, stub_externos, db_session, make_documento, make_version, make_asignacion, make_file_hash):
    from db.models.revisiones import Revision

    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion)
    fh = await make_file_hash()
    stub_externos["file_id"], stub_externos["url"] = fh.id, fh.file_url

    r = await client.post(
        f"/docs/review/{doc.id}", headers=gateway_headers(2),
        data={"accion": "devuelto", "comentario": "Ver observaciones"},
        files={"adjunto": ("observaciones.docx", io.BytesIO(b"PK docx"), "application/octet-stream")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"]["codigo"] == "rechazado"
    revision = await db_session.scalar(select(Revision).where(Revision.proceso_id == doc.id))
    assert revision.accion == "devuelto"
    assert revision.adjunto_nombre == "observaciones.docx"
    assert (revision.adjunto_url, revision.adjunto_file_id) == (fh.file_url, fh.id)
    assert revision.adjunto_size == len(b"PK docx")
    await db_session.refresh(fh)
    assert fh.numero_usos == 1
    _, kwargs = stub_externos["notificaciones"][0]
    assert kwargs["con_adjunto"] is True

    # El adjunto aparece en el detalle (para el creador).
    perms[(1, "documento_crear")] = True
    detalle = (await client.get(f"/docs/detail/{doc.id}", headers=gateway_headers(1))).json()
    assert detalle["revisiones"][0]["adjunto"]["nombre"] == "observaciones.docx"
    assert detalle["subida_version"]["permitida"] is True


async def test_review_adjunto_al_aprobar_400(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion)
    r = await client.post(
        f"/docs/review/{doc.id}", headers=gateway_headers(2),
        data={"accion": "aprobado"}, files=_pdf_upload(campo="adjunto"),
    )
    assert r.status_code == 400
    assert stub_externos["subidas"] == 0  # rechazado antes de subir a MinIO


async def test_review_adjunto_formato_invalido_400(client, perms, stub_externos, make_documento, make_version, make_asignacion):
    perms[(2, "documento_revisar")] = True
    doc = await _doc_en_revision(make_documento, make_version, make_asignacion)
    r = await client.post(
        f"/docs/review/{doc.id}", headers=gateway_headers(2),
        data={"accion": "devuelto"},
        files={"adjunto": ("foto.png", io.BytesIO(b"\x89PNG"), "image/png")},
    )
    assert r.status_code == 400
    assert stub_externos["subidas"] == 0


async def test_download_revision_ajeno_403(client, perms, make_documento, db_session):
    from db.models.revisiones import Revision

    doc = await make_documento(creador_id=42)
    revision = Revision(proceso_id=doc.id, version_revisada=1, revisor_id=43, accion="devuelto",
                        adjunto_url="satc-documentos/x/obs.pdf", adjunto_nombre="obs.pdf")
    db_session.add(revision)
    await db_session.flush()
    r = await client.get(f"/docs/download-revision/{revision.id}", headers=gateway_headers(1))
    assert r.status_code == 403


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
    assert r.json()["stats"]["creador"]["aprobados"] == 1


async def test_stats_revisor_ok(client, perms, db_session, make_documento, make_asignacion):
    from db.models.revisiones import Revision

    perms[(2, "documento_revisar")] = True
    doc = await make_documento(creador_id=1, estado="en_revision")
    await make_asignacion(doc.id, revisor_id=2)
    db_session.add(Revision(proceso_id=doc.id, version_revisada=1, revisor_id=2, accion="devuelto"))
    await db_session.flush()
    r = await client.get("/docs/stats", headers=gateway_headers(2))
    assert r.status_code == 200
    assert r.json()["stats"]["revisor"] == {
        "total_asignados": 1, "pendientes": 1, "total_revisiones": 1, "aprobados": 0, "devueltos": 1,
    }


async def test_reviewers_sin_acceso_403(client, perms):
    r = await client.get("/docs/reviewers", headers=gateway_headers(1))
    assert r.status_code == 403


async def test_reviewers_ok(client, perms, stub_externos):
    perms[(1, "documento_crear")] = True
    r = await client.get("/docs/reviewers", headers=gateway_headers(1))
    assert r.status_code == 200
    # el propio usuario (id 1) se excluye; revisor 2 aparece
    assert any(u["id"] == 2 for u in r.json()["usuarios"])


# ---------------- endpoints service-to-service eliminados ----------------

@pytest.mark.parametrize("metodo,ruta", [
    ("post", "/docs/create-service"),
    ("put", "/docs/finalize-service/1"),
    ("get", "/docs/detail-service/1"),
])
async def test_endpoints_service_eliminados(client, metodo, ruta):
    r = await getattr(client, metodo)(ruta)
    assert r.status_code in (404, 405)


# ---------------- migración de esquema ----------------
# Usa conexiones propias (no db_session): el DDL necesita lock exclusivo.

async def test_migracion_backfill_e_idempotencia():
    from db.migrations import aplicar_migraciones

    async with engine.begin() as conn:
        fh_v = await conn.scalar(text(
            "INSERT INTO file_hash (file_hash, file_url, content_type, file_size, numero_usos, created_at) "
            "VALUES ('m1', 'satc-documentos/files/m1.pdf', 'application/pdf', 10, 1, now()) RETURNING id"))
        fh_a = await conn.scalar(text(
            "INSERT INTO file_hash (file_hash, file_url, content_type, file_size, numero_usos, created_at) "
            "VALUES ('m2', 'satc-documentos/files/m2.docx', 'application/msword', 77, 1, now()) RETURNING id"))
        doc = await conn.scalar(text(
            "INSERT INTO documentos (nombre, estado, usuario_creador_id, version_actual, numero_devoluciones) "
            "VALUES ('legado', 'rechazado', 1, 1, 1) RETURNING id"))
        # Filas "legadas": sin file_id / adjunto_file_id.
        await conn.execute(text(
            "INSERT INTO versiones_documento (documento_id, numero_version, archivo_url, archivo_nombre_original, usuario_subida_id) "
            "VALUES (:d, 1, 'satc-documentos/files/m1.pdf', 'legado.pdf', 1)"), {"d": doc})
        await conn.execute(text(
            "INSERT INTO revisiones (documento_id, version_revisada, revisor_id, estado_revision, archivo_adjunto_url, archivo_adjunto_nombre) "
            "VALUES (:d, 1, 2, 'devuelto', 'satc-documentos/files/m2.docx', 'obs.docx')"), {"d": doc})

    async with engine.begin() as conn:
        resumen = await aplicar_migraciones(conn)
    assert resumen["versiones_backfill"] == 1
    assert resumen["revisiones_backfill"] == 1

    async with engine.connect() as conn:
        assert await conn.scalar(text("SELECT file_id FROM versiones_documento WHERE documento_id = :d"), {"d": doc}) == fh_v
        fila = (await conn.execute(text(
            "SELECT adjunto_file_id, adjunto_size FROM revisiones WHERE documento_id = :d"), {"d": doc})).one()
        assert tuple(fila) == (fh_a, 77)
        assert await conn.scalar(text(
            "SELECT 1 FROM information_schema.columns WHERE table_name = 'documentos' AND column_name = 'origen'")) is None
        assert await conn.scalar(text("SELECT COUNT(*) FROM vista_documentos_detalle WHERE id = :d"), {"d": doc}) == 1

    # Idempotente: una segunda pasada no toca nada.
    async with engine.begin() as conn:
        resumen = await aplicar_migraciones(conn)
    assert resumen == {"versiones_backfill": 0, "revisiones_backfill": 0, "origen_eliminado": False}


async def test_migracion_no_borra_origen_si_quedan_procesos_de_otras_apps():
    from db.migrations import aplicar_migraciones

    async with engine.begin() as conn:
        await conn.execute(text("DROP VIEW IF EXISTS vista_documentos_detalle"))
        await conn.execute(text("ALTER TABLE documentos ADD COLUMN origen VARCHAR(30)"))
        await conn.execute(text(
            "INSERT INTO documentos (nombre, estado, usuario_creador_id, version_actual, numero_devoluciones, origen) "
            "VALUES ('informe', 'en_revision', 1, 1, 0, 'informe_tecnico')"))

    try:
        async with engine.begin() as conn:
            resumen = await aplicar_migraciones(conn)
        assert resumen["origen_eliminado"] is False
        async with engine.connect() as conn:
            assert await conn.scalar(text(
                "SELECT 1 FROM information_schema.columns WHERE table_name = 'documentos' AND column_name = 'origen'")) == 1
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM documentos WHERE origen IS NOT NULL"))
            resumen = await aplicar_migraciones(conn)
        assert resumen["origen_eliminado"] is True

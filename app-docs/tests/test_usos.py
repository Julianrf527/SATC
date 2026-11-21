"""
Fase 1 del acceso a archivos: dueños (file_uso), registro de subidas
(file_subida), contrato nuevo de increment/decrement, /files/registrar-usos y
la regla contra asociar archivos ajenos (modos off/log/on).
"""
import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from conftest import gateway_headers, service_headers
from db.models.file_uso import FileSubida, FileUso
from utils import minio_client

BOGOTA = ZoneInfo("America/Bogota")


@pytest.fixture
def subida_real(monkeypatch):
    """Subida con la deduplicación real; MinIO, validación y antivirus falsos."""
    async def fake_validate(file_data, filename, max_size_mb):
        return {"sanitized_filename": filename, "mime_type": "application/pdf"}

    monkeypatch.setattr("routes.files.validate_file_complete", fake_validate)
    monkeypatch.setattr("routes.files.escanear_archivo", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(
        minio_client, "upload_file_to_minio",
        lambda data, name, ct="application/octet-stream": {"ok": True, "url": f"b/{name}", "message": "ok"},
    )


@pytest.fixture
def permiso_archivos(monkeypatch):
    async def fake(user_id, permiso):
        return True
    monkeypatch.setattr("routes.files.verify_permission", fake)


def _pdf(contenido=b"%PDF-1.4 uno"):
    return {"archivo": ("a.pdf", io.BytesIO(contenido), "application/pdf")}


def _uso(file_id, entidad="acto", entidad_id=55):
    return {"file_id": file_id, "entidad": entidad, "entidad_id": entidad_id}


# --- registro de subidas -------------------------------------------------------

async def test_subida_por_gateway_registra_usuario_de_la_sesion(client, db_session, subida_real, permiso_archivos):
    # El campo del formulario no puede suplantar al usuario de la sesión.
    r = await client.post("/files/upload", headers=gateway_headers(7), files=_pdf(), data={"usuario_id": "999"})
    assert r.status_code == 200, r.text
    fila = await db_session.scalar(select(FileSubida).where(FileSubida.file_id == r.json()["file_id"]))
    assert (fila.usuario_id, fila.servicio_origen) == (7, "gateway")


async def test_subida_por_servicio_a_nombre_de_usuario_y_deduplicada(client, db_session, subida_real):
    r1 = await client.post("/files/upload", headers=service_headers(), files=_pdf(), data={"usuario_id": "5"})
    r2 = await client.post("/files/upload", headers=service_headers(), files=_pdf())
    assert r1.json()["file_id"] == r2.json()["file_id"] and r2.json()["deduplicated"]
    filas = (await db_session.execute(
        select(FileSubida.usuario_id, FileSubida.servicio_origen)
        .where(FileSubida.file_id == r1.json()["file_id"]).order_by(FileSubida.id)
    )).all()
    assert [tuple(f) for f in filas] == [(5, "sanctioning"), (None, "sanctioning")]


# --- increment / decrement con usos ---------------------------------------------

async def test_increment_con_usos_es_idempotente(client, db_session, make_file_hash):
    fh = await make_file_hash()
    await db_session.commit()
    body = {"usos": [_uso(fh.id), _uso(fh.id, "notificacion", "9"), _uso(999999)]}
    r = await client.put("/files/increment-usage", headers=service_headers(), json=body)
    assert r.status_code == 200, r.text
    assert r.json()["registrados"] == 2 and r.json()["no_encontrados"] == [999999]
    r = await client.put("/files/increment-usage", headers=service_headers(), json=body)
    assert r.json()["registrados"] == 0  # repetir no vuelve a contar

    await db_session.refresh(fh)
    assert fh.numero_usos == 2
    duenos = (await db_session.execute(
        select(FileUso.servicio, FileUso.entidad, FileUso.entidad_id)
        .where(FileUso.file_id == fh.id).order_by(FileUso.entidad)
    )).all()
    # El servicio sale del token (sanctioning-service), no del body.
    assert [tuple(d) for d in duenos] == [("sanctioning", "acto", "55"), ("sanctioning", "notificacion", "9")]


async def test_decrement_con_usos_borra_solo_esa_asociacion(client, db_session, make_file_hash):
    fh = await make_file_hash()
    await db_session.commit()
    await client.put("/files/increment-usage", headers=service_headers(),
                     json={"usos": [_uso(fh.id), _uso(fh.id, "oficio", 3)]})
    r = await client.put("/files/decrement-usage", headers=service_headers(),
                         json={"usos": [_uso(fh.id), _uso(fh.id, "inexistente", 1)]})
    assert r.status_code == 200 and r.json()["quitados"] == 1
    await db_session.refresh(fh)
    assert fh.numero_usos == 1
    entidades = (await db_session.execute(select(FileUso.entidad).where(FileUso.file_id == fh.id))).scalars().all()
    assert entidades == ["oficio"]


async def test_decrement_no_toca_usos_de_otro_servicio(client, db_session, make_file_hash):
    fh = await make_file_hash()
    db_session.add(FileUso(file_id=fh.id, servicio="recurso", entidad="acto", entidad_id="55"))
    await db_session.commit()
    r = await client.put("/files/decrement-usage", headers=service_headers(), json={"usos": [_uso(fh.id)]})
    assert r.json()["quitados"] == 0
    assert await db_session.scalar(select(FileUso.servicio).where(FileUso.file_id == fh.id)) == "recurso"


async def test_formato_anterior_sigue_funcionando(client, db_session, make_file_hash):
    fh = await make_file_hash()
    await db_session.commit()
    r = await client.put("/files/increment-usage", headers=service_headers(), json={"file_ids": [fh.id]})
    assert r.status_code == 200
    await db_session.refresh(fh)
    assert fh.numero_usos == 1
    assert await db_session.scalar(select(FileUso.id).where(FileUso.file_id == fh.id)) is None


async def test_usos_solo_con_service_token(client, make_file_hash):
    fh = await make_file_hash()
    r = await client.put("/files/increment-usage", headers=gateway_headers(1), json={"usos": [_uso(fh.id)]})
    assert r.status_code == 403
    r = await client.post("/files/registrar-usos", headers=gateway_headers(1), json={"usos": [_uso(fh.id)]})
    assert r.status_code == 403


async def test_registrar_usos_no_mueve_el_contador(client, db_session, make_file_hash):
    fh = await make_file_hash(numero_usos=3)
    await db_session.commit()
    r = await client.post("/files/registrar-usos", headers=service_headers(),
                          json={"usos": [_uso(fh.id), _uso(fh.id)]})
    assert r.status_code == 200 and r.json()["registrados"] == 1
    await db_session.refresh(fh)
    assert fh.numero_usos == 3


# --- regla contra archivos ajenos -----------------------------------------------

async def _escenario(db_session, make_file_hash):
    """propio: lo subió el usuario 5 hace 1 h. viejo: lo subió el 5 hace 3 días.
    ajeno: lo subió el usuario 8. de_la_entidad: ya es del acto 55."""
    ahora = datetime.now(BOGOTA)
    propio, viejo, ajeno, de_la_entidad = [await make_file_hash() for _ in range(4)]
    db_session.add_all([
        FileSubida(file_id=propio.id, usuario_id=5, servicio_origen="gateway", fecha=ahora - timedelta(hours=1)),
        FileSubida(file_id=viejo.id, usuario_id=5, servicio_origen="gateway", fecha=ahora - timedelta(days=3)),
        FileSubida(file_id=ajeno.id, usuario_id=8, servicio_origen="gateway", fecha=ahora),
        FileUso(file_id=de_la_entidad.id, servicio="sanctioning", entidad="acto", entidad_id="55"),
    ])
    await db_session.commit()
    return propio, viejo, ajeno, de_la_entidad


async def test_validacion_on_rechaza_el_lote(client, db_session, make_file_hash, monkeypatch):
    monkeypatch.setattr("routes.files.MODO_VALIDACION", "on")
    propio, viejo, ajeno, de_la_entidad = await _escenario(db_session, make_file_hash)
    body = {"usuario_id": 5, "usos": [_uso(propio.id), _uso(viejo.id), _uso(ajeno.id), _uso(de_la_entidad.id)]}
    r = await client.put("/files/increment-usage", headers=service_headers(), json=body)
    assert r.status_code == 403
    assert r.json()["rechazados"] == sorted([viejo.id, ajeno.id])
    # Todo o nada: ni el propio quedó registrado.
    assert await db_session.scalar(select(FileUso.id).where(FileUso.file_id == propio.id)) is None


async def test_validacion_on_acepta_propios_y_de_la_entidad(client, db_session, make_file_hash, monkeypatch):
    monkeypatch.setattr("routes.files.MODO_VALIDACION", "on")
    propio, _, _, de_la_entidad = await _escenario(db_session, make_file_hash)
    body = {"usuario_id": 5, "usos": [_uso(propio.id), _uso(de_la_entidad.id)]}
    r = await client.put("/files/increment-usage", headers=service_headers(), json=body)
    assert r.status_code == 200, r.text


async def test_validacion_on_otra_entidad_no_cuenta_como_propia(client, db_session, make_file_hash, monkeypatch):
    monkeypatch.setattr("routes.files.MODO_VALIDACION", "on")
    _, _, _, de_la_entidad = await _escenario(db_session, make_file_hash)
    r = await client.put("/files/increment-usage", headers=service_headers(),
                         json={"usuario_id": 5, "usos": [_uso(de_la_entidad.id, "acto", 77)]})
    assert r.status_code == 403


async def test_validacion_log_solo_avisa(client, db_session, make_file_hash, monkeypatch, caplog):
    monkeypatch.setattr("routes.files.MODO_VALIDACION", "log")
    _, _, ajeno, _ = await _escenario(db_session, make_file_hash)
    r = await client.put("/files/increment-usage", headers=service_headers(),
                         json={"usuario_id": 5, "usos": [_uso(ajeno.id)]})
    assert r.status_code == 200
    assert any("archivos ajenos" in m for m in caplog.messages)


async def test_validacion_sin_usuario_no_aplica(client, db_session, make_file_hash, monkeypatch):
    monkeypatch.setattr("routes.files.MODO_VALIDACION", "on")
    _, _, ajeno, _ = await _escenario(db_session, make_file_hash)
    r = await client.put("/files/increment-usage", headers=service_headers(), json={"usos": [_uso(ajeno.id)]})
    assert r.status_code == 200

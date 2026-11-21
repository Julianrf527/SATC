"""Documentos del expediente servidos por recurso y dueños de archivos en app-docs."""
from sqlalchemy import select

from db.models.auditoria import Auditoria
from services.archivos_entidades import cargar_usos_existentes
from tests.fixtures_etapas import *  # noqa: F401,F403


async def _eventos(db, exp_id):
    return (await db.execute(
        select(Auditoria.tipo_evento).where(Auditoria.expediente_id == exp_id)
    )).scalars().all()


async def test_ver_documento_del_expediente(client, rv_permisos, expediente, db_session, stubs):
    fid = expediente.doc_comprobante_pago_id
    r = await client.get(f"/expedientes/{expediente.id}/archivos/{fid}", headers=headers(LECTOR))
    assert r.status_code == 200, r.text
    assert r.content == stubs.files.contenidos[fid][0]
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["content-disposition"].startswith("inline")
    assert "Comprobante" in r.headers["content-disposition"] or "comprobante" in r.headers["content-disposition"]
    assert await _eventos(db_session, expediente.id) == ["VER_DOCUMENTO"]

    # El visor pide por rangos: se reenvía Range y no se vuelve a auditar.
    r = await client.get(f"/expedientes/{expediente.id}/archivos/{fid}",
                         headers={**headers(LECTOR), "Range": "bytes=0-3"})
    assert r.status_code == 206 and stubs.files.descargas[-1] == (fid, "bytes=0-3")
    assert await _eventos(db_session, expediente.id) == ["VER_DOCUMENTO"]


async def test_solo_documentos_del_expediente_y_con_lectura(client, rv_permisos, expediente, crear_expediente, stubs):
    otro = await crear_expediente()
    ajeno = otro.doc_comprobante_pago_id
    r = await client.get(f"/expedientes/{expediente.id}/archivos/{ajeno}", headers=headers(LECTOR))
    assert r.status_code == 404  # existe en app-docs, pero es de otro expediente
    suelto = stubs.files.registrar()
    assert (await client.get(f"/expedientes/{expediente.id}/archivos/{suelto}",
                             headers=headers(LECTOR))).status_code == 404
    fid = expediente.doc_comprobante_pago_id
    assert (await client.get(f"/expedientes/{expediente.id}/archivos/{fid}",
                             headers=headers(EXTRANO))).status_code == 403
    assert (await client.get(f"/expedientes/999999/archivos/{fid}", headers=headers(LECTOR))).status_code == 404


async def test_subida_a_nombre_del_usuario(client, rv_permisos, expediente, stubs):
    pid = (await post(client, f"/etapas/{expediente.id}/admite/asignarme")).json()["data"]["proceso_id"]
    assert (await subir(client, pid)).status_code == 200
    ultimo = max(stubs.files.subidos_por)
    assert stubs.files.subidos_por[ultimo] == ABOGADO


async def test_carga_inicial_de_usos(rv_permisos, expediente, db_session, stubs):
    total = await cargar_usos_existentes(db_session)
    assert total == len(stubs.files.usos_registrados) > 0
    assert {"file_id": expediente.doc_comprobante_pago_id, "entidad": "expediente",
            "entidad_id": expediente.id} in stubs.files.usos_registrados
    claves = [(u["file_id"], u["entidad"], u["entidad_id"]) for u in stubs.files.usos_registrados]
    assert len(claves) == len(set(claves))

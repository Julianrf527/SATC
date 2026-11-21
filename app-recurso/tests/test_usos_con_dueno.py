"""Asociaciones de archivos con dueño (entidad, fila) y usuario en app-docs."""
from sqlalchemy.ext.asyncio import AsyncSession

import services.docs as docs_svc
from db.models import Notificacion
from services.archivos_entidades import Liberacion, usos, usos_de_fila, usos_liberados
from services.usos_archivos import compensar, pendientes, registro_peticion
from tests.fixtures_etapas import *  # noqa: F401,F403


async def test_crear_expediente_asocia_con_dueno_y_usuario(client, h_gestor, payload_expediente, stubs):
    body = payload_expediente()
    r = await client.post("/expedientes", json=body, headers=h_gestor)
    assert r.status_code == 201, r.text
    exp_id = r.json()["data"]["id"]
    clave = (body["doc_comprobante_pago_id"], "expediente", str(exp_id))
    assert stubs.files.asociaciones == {clave: 10}  # 10 = usuario de h_gestor


def test_mismo_pdf_en_dos_columnas_no_se_suelta():
    n = Notificacion(id=7, documento_citacion_id=50, documento_notificacion_id=50)
    # Se reemplaza la citación por otro PDF pero la notificación sigue usando el 50.
    n.documento_citacion_id = 51
    assert usos_liberados(n, [50]) == []
    n.documento_notificacion_id = None
    assert usos_liberados(n, [50]) == [{"file_id": 50, "entidad": "notificacion", "entidad_id": 7}]
    # Con un UPDATE que no refresca el objeto se pasan los archivos actuales.
    assert usos_liberados(n, [50], actuales=[50, 51]) == []


def test_usos_sin_vacios_ni_repetidos():
    n = Notificacion(id=3, documento_citacion_id=8, documento_notificacion_id=8)
    assert usos(n, [8, None, 8, 0]) == [{"file_id": 8, "entidad": "notificacion", "entidad_id": 3}]
    assert usos_de_fila(n) == [{"file_id": 8, "entidad": "notificacion", "entidad_id": 3}]
    assert len(Liberacion().agregar(usos_de_fila(n)).agregar(Liberacion(file_ids=[9]))) == 2


async def test_compensa_solo_si_todas_las_asociaciones_eran_nuevas(db_session: AsyncSession, stubs):
    previa = {"file_id": 60, "entidad": "anexo", "entidad_id": 1}
    stubs.files.asociaciones[(60, "anexo", "1")] = None
    nueva = {"file_id": 61, "entidad": "anexo", "entidad_id": 1}

    async with registro_peticion(db_session):
        # Una ya existía: compensar la borraría estando en uso -> no se anota.
        assert (await docs_svc.increment_file_usage(usos=[previa, nueva], usuario_id=4))["ok"]
        assert pendientes() == []
        otra = {"file_id": 62, "entidad": "anexo", "entidad_id": 1}
        await docs_svc.increment_file_usage(usos=[otra], usuario_id=4)
        lotes = pendientes()
    assert lotes == [[otra]]

    stubs.files.carga_inicial = False
    await compensar(lotes)
    assert (62, "anexo", "1") not in stubs.files.asociaciones
    assert (60, "anexo", "1") in stubs.files.asociaciones and (61, "anexo", "1") in stubs.files.asociaciones

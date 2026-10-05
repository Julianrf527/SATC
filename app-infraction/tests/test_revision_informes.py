"""
Flujo PROPIO de revisión del informe técnico (/revision-informes + /informes):
asignar -> pendiente_carga, subir versiones, aprobar (exige PDF), aprobar para
firma + versión firmada auto-aprobada, devolver con adjunto, 3 devoluciones ->
finalizado + reasignación, permisos y descargas. FilesClient y UsersClient
se sustituyen por stubs (conftest.stubs_clientes).
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

import routes.reports as reports_mod
import services.users as users_svc
from core.permission import Permission
from db.models.informe_proceso import InformeProceso, InformeProcesoRevision
from db.models.informe_tecnico import InformeTecnico
from tests.conftest import gateway_headers

ASIGNADOR, PROFESIONAL, REVISOR, ABOGADO, EXTRANO = 1, 10, 20, 7, 99
PDF = ("informe.pdf", b"%PDF-1.4 informe", "application/pdf")
DOCX = ("informe.docx", b"PK word", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@pytest.fixture(autouse=True)
def _permisos(monkeypatch, stubs_clientes):
    """Solo ASIGNADOR tiene ASSIGN_REPORTS; profesional/revisor tienen sus permisos."""
    async def _verify(user_id, permission):
        if permission == Permission.ASSIGN_REPORTS:
            return int(user_id) == ASIGNADOR
        if permission == Permission.UPLOAD_REPORTS:
            return int(user_id) == PROFESIONAL or int(user_id) == 11
        if permission == Permission.REVIEW_REPORTS:
            return int(user_id) == REVISOR
        return True

    monkeypatch.setattr(reports_mod, "verify_permission", _verify)
    monkeypatch.setattr(users_svc, "verify_permission", _verify)


@pytest.fixture
def stubs(stubs_clientes):
    return stubs_clientes


@pytest.fixture
def asignar(client, make_expediente, db_session):
    async def _asignar(tipo="VISITA", profesional=PROFESIONAL):
        exp = await make_expediente(abogado_responsable_id=ABOGADO)
        informe = InformeTecnico(expediente_id=exp.id, tipo_informe=tipo)
        db_session.add(informe)
        await db_session.flush()
        resp = await client.post(
            f"/informes/{informe.id}/asignar",
            json={"profesional_id": profesional, "revisor_id": REVISOR},
            headers=gateway_headers(ASIGNADOR),
        )
        assert resp.status_code == 200, resp.text
        return informe, resp.json()["proceso_id"]

    return _asignar


async def _subir(client, pid, archivo, user=PROFESIONAL):
    return await client.post(
        f"/revision-informes/{pid}/versiones",
        files={"archivo": archivo},
        data={"comentario": "versión"},
        headers=gateway_headers(user),
    )


async def _revisar(client, pid, accion, adjunto=None, user=REVISOR, comentario="obs"):
    files = {"adjunto": adjunto} if adjunto else None
    return await client.post(
        f"/revision-informes/{pid}/revisiones",
        data={"accion": accion, "comentario": comentario},
        files=files,
        headers=gateway_headers(user),
    )


async def _detalle(client, pid, user):
    return await client.get(f"/revision-informes/{pid}", headers=gateway_headers(user))


class TestAsignacion:
    async def test_asignar_crea_proceso_pendiente_carga(self, client, asignar, stubs):
        informe, pid = await asignar()

        resp = await _detalle(client, pid, PROFESIONAL)
        assert resp.status_code == 200
        d = resp.json()
        assert d["estado"]["codigo"] == "pendiente_carga"
        assert d["informe_id"] == informe.id
        assert d["creador_id"] == PROFESIONAL
        assert [r["revisor_id"] for r in d["revisores"]] == [REVISOR]
        assert d["subida_version"]["permitida"] is True
        assert d["acciones_disponibles"] == []
        # Aviso al profesional y al revisor, con id del informe.
        assert stubs.users.para(PROFESIONAL) and stubs.users.para(REVISOR)
        assert all(n["tipo"] == "informe_tecnico" and n["id_vinculada"] == str(informe.id)
                   for n in stubs.users.notificaciones)

    async def test_segunda_asignacion_con_proceso_activo_409(self, client, asignar):
        informe, _ = await asignar()
        resp = await client.post(
            f"/informes/{informe.id}/asignar",
            json={"profesional_id": PROFESIONAL, "revisor_id": REVISOR},
            headers=gateway_headers(ASIGNADOR),
        )
        assert resp.status_code == 409

    async def test_por_informe_devuelve_vigente(self, client, asignar):
        informe, pid = await asignar()
        resp = await client.get(f"/revision-informes/por-informe/{informe.id}", headers=gateway_headers(ASIGNADOR))
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    async def test_mios_lee_estado_local(self, client, asignar):
        informe, pid = await asignar()
        resp = await client.get("/informes/mios", headers=gateway_headers(PROFESIONAL))
        assert resp.status_code == 200
        fila = resp.json()["data"][0]
        assert fila["proceso_id"] == pid
        assert fila["estado_proceso"]["codigo"] == "pendiente_carga"
        assert fila["requiere_mi_accion"] is True
        assert fila["proceso_activo"] is True


class TestSubirYAprobar:
    async def test_subir_version_pasa_a_revision_y_registra_uso(self, client, asignar, stubs):
        _, pid = await asignar()
        resp = await _subir(client, pid, DOCX)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["estado"]["codigo"] == "en_revision"
        assert body["version"] == 1
        assert stubs.files.incrementados == [101]
        assert any("Nueva versión (v1)" in m for m in stubs.users.para(REVISOR))

    async def test_aprobar_con_word_bloqueado(self, client, asignar):
        _, pid = await asignar()
        await _subir(client, pid, DOCX)

        d = (await _detalle(client, pid, REVISOR)).json()
        acciones = {a["codigo"]: a for a in d["acciones_disponibles"]}
        assert set(acciones) == {"aprobado", "devuelto", "aprobado_firma"}
        assert "PDF" in acciones["aprobado"]["bloqueada"]
        assert acciones["aprobado_firma"]["bloqueada"] is None
        assert acciones["aprobado_firma"]["icono"] == "firmar"

        resp = await _revisar(client, pid, "aprobado")
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]

    async def test_aprobar_pdf_acepta_informe_en_la_misma_transaccion(self, client, asignar, stubs, db_session):
        informe, pid = await asignar()
        await _subir(client, pid, PDF)
        resp = await _revisar(client, pid, "aprobado")
        assert resp.status_code == 200, resp.text
        assert resp.json()["informe_aceptado"] is True

        await db_session.refresh(informe)
        hoy = datetime.now(ZoneInfo("America/Bogota")).date()
        assert informe.fecha_aceptacion_informe == hoy
        assert informe.fecha_recibido_informe == hoy
        assert informe.documento_informe_id == 101
        # Uso de la versión + uso propio del informe.
        assert stubs.files.incrementados == [101, 101]
        assert any("aceptado" in m for m in stubs.users.para(ABOGADO))
        assert any("aprobado" in m for m in stubs.users.para(PROFESIONAL))

    async def test_aprobar_firma_y_firmada_pdf_auto_aprobada(self, client, asignar, stubs, db_session):
        informe, pid = await asignar()
        await _subir(client, pid, DOCX)
        resp = await _revisar(client, pid, "aprobado_firma")
        assert resp.status_code == 200
        assert resp.json()["estado"]["codigo"] == "aprobado_firma"
        assert resp.json()["informe_aceptado"] is False
        assert any("firma" in m for m in stubs.users.para(PROFESIONAL))

        # La firmada debe ser PDF.
        d = (await _detalle(client, pid, PROFESIONAL)).json()
        assert d["subida_version"] == {"permitida": True, "extensiones": [".pdf"], "motivo": None}
        resp = await _subir(client, pid, ("firmado.docx", b"PK otro", DOCX[2]))
        assert resp.status_code == 400

        resp = await _subir(client, pid, ("firmado.pdf", b"%PDF firmado", "application/pdf"))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["auto_aprobado"] is True and body["informe_aceptado"] is True
        assert body["estado"]["codigo"] == "aprobado"

        await db_session.refresh(informe)
        assert informe.fecha_aceptacion_informe is not None
        assert informe.documento_informe_id == 102  # la versión firmada

        d = (await _detalle(client, pid, REVISOR)).json()
        assert d["revisiones"][0]["accion"] == "aprobado"
        # Historial en participio y auditoría con etiqueta/tono del flujo.
        assert [(r["accion_etiqueta"], r["tono"]) for r in d["revisiones"][:2]] == [
            ("Aprobado", "success"), ("Aprobado para firma", "success"),
        ]
        eventos = {a["accion"]: (a["accion_etiqueta"], a["tono"]) for a in d["auditoria"]}
        assert eventos["aprobar_firma"] == ("Aprobado para firma", "success")
        assert eventos["aprobar"] == ("Aprobado", "success")
        assert eventos["crear"] == ("Proceso creado", "info")
        assert d["revisiones"][0]["revisor_id"] == REVISOR
        assert d["acciones_disponibles"] == []
        assert any("aceptado" in m for m in stubs.users.para(ABOGADO))


class TestDevoluciones:
    async def test_devolver_con_adjunto(self, client, asignar, stubs, db_session):
        _, pid = await asignar()
        await _subir(client, pid, DOCX)
        resp = await _revisar(client, pid, "devuelto", adjunto=("observaciones.pdf", b"%PDF obs", "application/pdf"))
        assert resp.status_code == 200, resp.text
        assert resp.json()["estado"]["codigo"] == "rechazado"
        assert resp.json()["numero_devoluciones"] == 1

        rev = await db_session.scalar(select(InformeProcesoRevision).where(InformeProcesoRevision.proceso_id == pid))
        assert rev.adjunto_nombre == "observaciones.pdf" and rev.adjunto_file_id == 102
        assert 102 in stubs.files.incrementados
        assert any("devuelto (1/3), con documento de observaciones" in m for m in stubs.users.para(PROFESIONAL))

        # El profesional sube corrección.
        resp = await _subir(client, pid, ("v2.pdf", b"%PDF v2", "application/pdf"))
        assert resp.json()["estado"]["codigo"] == "en_revision"

    async def test_adjunto_invalido_no_se_sube(self, client, asignar, stubs):
        _, pid = await asignar()
        await _subir(client, pid, DOCX)
        resp = await _revisar(client, pid, "devuelto", adjunto=("virus.exe", b"MZ", "application/octet-stream"))
        assert resp.status_code == 400
        assert stubs.files.subidos == ["informe.docx"]

    async def test_adjunto_solo_al_devolver(self, client, asignar, stubs):
        _, pid = await asignar()
        await _subir(client, pid, PDF)
        resp = await _revisar(client, pid, "aprobado", adjunto=("obs.pdf", b"%PDF", "application/pdf"))
        assert resp.status_code == 400

    async def test_tres_devoluciones_finaliza_y_permite_reasignar(self, client, asignar, stubs, db_session):
        informe, pid = await asignar()
        for i in range(3):
            await _subir(client, pid, (f"v{i}.docx", f"PK {i}".encode(), DOCX[2]))
            resp = await _revisar(client, pid, "devuelto")
            assert resp.status_code == 200
        assert resp.json()["estado"]["codigo"] == "finalizado"
        assert any("reasignar" in m for m in stubs.users.para(ASIGNADOR))
        assert any("finalizado" in m for m in stubs.users.para(PROFESIONAL))

        d = (await _detalle(client, pid, PROFESIONAL)).json()
        assert d["subida_version"]["permitida"] is False

        # Reasignación desde cero (POST asignar sirve porque el vigente terminó).
        resp = await client.post(
            f"/informes/{informe.id}/asignar",
            json={"profesional_id": 11, "revisor_id": REVISOR},
            headers=gateway_headers(ASIGNADOR),
        )
        assert resp.status_code == 200, resp.text
        nuevo = resp.json()["proceso_id"]
        assert nuevo != pid
        viejo = await db_session.get(InformeProceso, pid, populate_existing=True)
        assert viejo.activo is False
        d = (await _detalle(client, nuevo, 11)).json()
        assert d["estado"]["codigo"] == "pendiente_carga" and d["numero_devoluciones"] == 0


class TestReasignar:
    async def test_reasignar_finaliza_activo_y_crea_nuevo(self, client, asignar, stubs, db_session):
        informe, pid = await asignar()
        await _subir(client, pid, DOCX)
        resp = await client.put(
            f"/informes/{informe.id}/asignar",
            json={"profesional_id": 11, "revisor_id": REVISOR},
            headers=gateway_headers(ASIGNADOR),
        )
        assert resp.status_code == 200, resp.text
        nuevo = resp.json()["proceso_id"]

        viejo = await db_session.get(InformeProceso, pid, populate_existing=True)
        assert viejo.estado == "finalizado" and viejo.activo is False
        assert any("reasignado" in m for m in stubs.users.para(PROFESIONAL))
        await db_session.refresh(informe)
        assert informe.profesional_asignado_id == 11
        # El profesional anterior ya no puede subir.
        resp = await _subir(client, pid, PDF)
        assert resp.status_code == 400
        resp = await _subir(client, nuevo, PDF, user=PROFESIONAL)
        assert resp.status_code == 403

    async def test_cambiar_a_manual_cierra_proceso(self, client, asignar, db_session):
        informe, pid = await asignar()
        resp = await client.put(
            f"/informes/{informe.id}/cambiar-modo", json={"modo": "MANUAL"}, headers=gateway_headers(ASIGNADOR)
        )
        assert resp.status_code == 200
        proceso = await db_session.get(InformeProceso, pid, populate_existing=True)
        assert proceso.estado == "finalizado" and proceso.activo is False


class TestPermisos:
    async def test_extrano_no_ve_detalle(self, client, asignar):
        _, pid = await asignar()
        assert (await _detalle(client, pid, EXTRANO)).status_code == 403
        assert (await _detalle(client, 9999, EXTRANO)).status_code == 403
        assert (await _detalle(client, pid, ASIGNADOR)).status_code == 200

    async def test_profesional_no_revisa_y_revisor_no_sube(self, client, asignar):
        _, pid = await asignar()
        assert (await _subir(client, pid, PDF, user=REVISOR)).status_code == 403
        await _subir(client, pid, PDF)
        assert (await _revisar(client, pid, "aprobado", user=PROFESIONAL)).status_code == 403
        assert (await _revisar(client, pid, "aprobado", user=ASIGNADOR)).status_code == 403

    async def test_asignar_sin_permiso_403(self, client, make_expediente, db_session):
        exp = await make_expediente(abogado_responsable_id=ABOGADO)
        informe = InformeTecnico(expediente_id=exp.id, tipo_informe="VISITA")
        db_session.add(informe)
        await db_session.flush()
        resp = await client.post(
            f"/informes/{informe.id}/asignar",
            json={"profesional_id": PROFESIONAL, "revisor_id": REVISOR},
            headers=gateway_headers(EXTRANO),
        )
        assert resp.status_code == 403


class TestDescargas:
    async def test_descarga_version_con_permiso(self, client, asignar):
        _, pid = await asignar()
        await _subir(client, pid, PDF)
        d = (await _detalle(client, pid, REVISOR)).json()
        vid = d["versiones"][0]["version_id"]

        resp = await client.get(f"/revision-informes/{pid}/versiones/{vid}/descarga", headers=gateway_headers(REVISOR))
        assert resp.status_code == 200
        assert resp.content == PDF[1]
        assert resp.headers["content-type"].startswith("application/pdf")
        assert "informe.pdf" in resp.headers["content-disposition"]

        resp = await client.get(f"/revision-informes/{pid}/versiones/{vid}/descarga", headers=gateway_headers(EXTRANO))
        assert resp.status_code == 403

    async def test_descarga_adjunto(self, client, asignar):
        _, pid = await asignar()
        await _subir(client, pid, DOCX)
        await _revisar(client, pid, "devuelto", adjunto=("obs.docx", b"PK obs", DOCX[2]))
        d = (await _detalle(client, pid, PROFESIONAL)).json()
        rid = d["revisiones"][0]["revision_id"]
        resp = await client.get(f"/revision-informes/{pid}/revisiones/{rid}/adjunto", headers=gateway_headers(PROFESIONAL))
        assert resp.status_code == 200
        assert resp.content == b"PK obs"

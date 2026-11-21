"""
Proceso de revisión de los actos administrativos (/revision-actos) y cargue
directo de super gestión (/actos/administrativos):

- proyecta y corrige SOLO el encargado actual del expediente;
- revisa cualquier líder de proyecto (por permiso): aprobar para firma o
  devolver (comentario obligatorio, adjunto opcional); sin aprobación directa;
- la corrección vuelve a revisión (no se auto-aprueba) y no hay tope;
- en aprobado_firma la versión final (PDF + tipo/numerado/fecha) crea el acto;
- reasignar el expediente pasa el proceso al nuevo encargado (y se le avisa);
- super gestión carga directo (cierra el proceso), cambia el PDF y elimina.
"""
import pytest
from sqlalchemy import select

import routes.file_mutations as fm_mod
import services.users as users_svc
from core.permission import Permission
from db.models.acto_administrativo import ActoAdministrativo
from db.models.documento_proceso import (
    ACTO_CIERRE,
    ETAPA_CIERRE,
    ETAPA_CONCEPTO,
    ETAPA_MEDIDA,
    DocumentoProceso,
)
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.expediente import Expediente
from db.models.medida_preventiva import MedidaPreventiva
from tests.conftest import gateway_headers

ENCARGADO, NUEVO, LIDER, LIDER2, SUPER, CONSULTA, EXTRANO = 7, 8, 30, 31, 40, 50, 99
DOCX = ("acto.docx", b"PK proyecto", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
PDF = ("acto.pdf", b"%PDF-1.4 acto", "application/pdf")


@pytest.fixture(autouse=True)
def _permisos(monkeypatch, stubs_clientes):
    async def _verify(user_id, permission):
        uid = int(user_id)
        if permission == Permission.LIDER_PROYECTO:
            return uid in (LIDER, LIDER2)
        if permission == Permission.MANUAL_UPLOAD:
            return uid == SUPER
        if permission == Permission.FILE_CONSULT:
            return uid in (ENCARGADO, NUEVO, LIDER, LIDER2, SUPER, CONSULTA)
        if permission in (Permission.FILE_MANAGE, Permission.ASSIGN_PERMISSION):
            return uid in (ENCARGADO, NUEVO, SUPER)
        return False

    async def _por_permiso(permiso):
        if permiso == Permission.LIDER_PROYECTO:
            return {LIDER: {"nombre": "Líder"}, LIDER2: {"nombre": "Líder 2"}}
        return {}

    monkeypatch.setattr(users_svc, "verify_permission", _verify)
    monkeypatch.setattr(users_svc, "get_users_by_permission", _por_permiso)
    monkeypatch.setattr(fm_mod, "verify_permission", _verify)
    monkeypatch.setattr(fm_mod, "get_user_info", users_svc.get_user_info)


@pytest.fixture
def stubs(stubs_clientes):
    return stubs_clientes


@pytest.fixture
def make_cierre(make_expediente, db_session):
    async def _make(encargado=ENCARGADO):
        exp = await make_expediente(abogado_responsable_id=encargado)
        cierre = EtapaCierre(expediente_id=exp.id)
        db_session.add(cierre)
        await db_session.flush()
        return exp, cierre

    return _make


async def _proyectar(client, etapa_tipo, ref_id, archivo=DOCX, user=ENCARGADO):
    return await client.post(
        "/revision-actos/proyectar",
        data={"etapa_tipo": etapa_tipo, "etapa_ref_id": str(ref_id), "comentario": "proyecto"},
        files={"archivo": archivo},
        headers=gateway_headers(user),
    )


async def _revisar(client, pid, accion, adjunto=None, user=LIDER, comentario="obs"):
    return await client.post(
        f"/revision-actos/{pid}/revisiones",
        data={"accion": accion, "comentario": comentario},
        files={"adjunto": adjunto} if adjunto else None,
        headers=gateway_headers(user),
    )


async def _subir(client, pid, archivo=DOCX, user=ENCARGADO):
    return await client.post(
        f"/revision-actos/{pid}/versiones",
        data={"comentario": "corrección"},
        files={"archivo": archivo},
        headers=gateway_headers(user),
    )


async def _version_final(client, pid, archivo=PDF, user=ENCARGADO, numerado="15", fecha="2026-11-10", tipo="AUTO"):
    return await client.post(
        f"/revision-actos/{pid}/version-final",
        data={"tipo_acto": tipo, "numerado": numerado, "fecha_numerado": fecha},
        files={"archivo": archivo},
        headers=gateway_headers(user),
    )


async def _detalle(client, pid, user=ENCARGADO):
    return await client.get(f"/revision-actos/{pid}", headers=gateway_headers(user))


async def _aprobado_firma(client, cierre):
    pid = (await _proyectar(client, ETAPA_CIERRE, cierre.id)).json()["proceso_id"]
    assert (await _revisar(client, pid, "aprobado_firma")).status_code == 200
    return pid


class TestProyectar:
    async def test_encargado_proyecta_y_avisa_lideres(self, client, make_cierre, stubs, db_session):
        exp, cierre = await make_cierre()
        resp = await _proyectar(client, ETAPA_CIERRE, cierre.id)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["estado"]["codigo"] == "en_revision"

        proceso = await db_session.scalar(select(DocumentoProceso).where(DocumentoProceso.id == body["proceso_id"]))
        assert proceso.tipo_documento == ACTO_CIERRE
        assert proceso.expediente_id == exp.id and proceso.activo
        assert stubs.users.para(LIDER) and stubs.users.para(LIDER2)
        assert not stubs.users.para(ENCARGADO)
        assert all(n["tipo"] == "acto_infraccion" and n["id_vinculada"] == str(proceso.id)
                   for n in stubs.users.notificaciones)

    @pytest.mark.parametrize("usuario", [LIDER, SUPER, EXTRANO])
    async def test_solo_el_encargado_proyecta(self, client, make_cierre, usuario):
        _, cierre = await make_cierre()
        resp = await _proyectar(client, ETAPA_CIERRE, cierre.id, user=usuario)
        assert resp.status_code == 403

    async def test_no_dos_procesos_en_curso(self, client, make_cierre):
        _, cierre = await make_cierre()
        assert (await _proyectar(client, ETAPA_CIERRE, cierre.id)).status_code == 201
        resp = await _proyectar(client, ETAPA_CIERRE, cierre.id, archivo=("otro.docx", b"PK 2", DOCX[2]))
        assert resp.status_code == 409

    async def test_etapa_inexistente_y_tipo_invalido(self, client):
        assert (await _proyectar(client, ETAPA_CIERRE, 999999)).status_code == 404
        assert (await _proyectar(client, "informe_tecnico", 1)).status_code == 400

    async def test_formato_no_permitido(self, client, make_cierre, stubs):
        _, cierre = await make_cierre()
        resp = await _proyectar(client, ETAPA_CIERRE, cierre.id, archivo=("a.txt", b"x", "text/plain"))
        assert resp.status_code == 400
        assert stubs.files.subidos == []

    async def test_concepto_y_medida(self, client, make_expediente, make_etapa_respuesta, db_session):
        exp = await make_expediente(abogado_responsable_id=ENCARGADO)
        concepto = EtapaAcogerConcepto(expediente_id=exp.id, tipo_acogida_concepto="REQUERIMIENTO")
        respuesta = await make_etapa_respuesta(exp.id, requiere_medida_preventiva=True)
        medida = MedidaPreventiva(etapa_respuesta_id=respuesta.id)
        db_session.add_all([concepto, medida])
        await db_session.flush()

        assert (await _proyectar(client, ETAPA_CONCEPTO, concepto.id)).status_code == 201
        assert (await _proyectar(client, ETAPA_MEDIDA, medida.id)).status_code == 201


class TestRevision:
    async def test_acciones_del_lider_sin_aprobacion_directa(self, client, make_cierre):
        _, cierre = await make_cierre()
        pid = (await _proyectar(client, ETAPA_CIERRE, cierre.id)).json()["proceso_id"]

        d = (await _detalle(client, pid, LIDER)).json()
        assert {a["codigo"] for a in d["acciones_disponibles"]} == {"devuelto", "aprobado_firma"}
        assert (await _revisar(client, pid, "aprobado")).status_code == 400

        # El encargado no revisa (ni siendo quien proyectó).
        assert (await _detalle(client, pid, ENCARGADO)).json()["acciones_disponibles"] == []
        assert (await _revisar(client, pid, "aprobado_firma", user=ENCARGADO)).status_code == 403

    async def test_devolver_exige_comentario_y_admite_adjunto(self, client, make_cierre, stubs):
        _, cierre = await make_cierre()
        pid = (await _proyectar(client, ETAPA_CIERRE, cierre.id)).json()["proceso_id"]

        assert (await _revisar(client, pid, "devuelto", comentario="")).status_code == 400
        resp = await _revisar(client, pid, "devuelto", adjunto=("obs.docx", b"PK obs", DOCX[2]))
        assert resp.status_code == 200, resp.text
        assert resp.json()["estado"]["codigo"] == "rechazado"
        assert any("devuelto" in m and "observaciones" in m for m in stubs.users.para(ENCARGADO))

        d = (await _detalle(client, pid)).json()
        assert d["revisiones"][0]["adjunto"] is not None
        assert d["subida_version"]["permitida"] is True

    async def test_correccion_vuelve_a_revision_sin_tope(self, client, make_cierre, stubs):
        _, cierre = await make_cierre()
        pid = (await _proyectar(client, ETAPA_CIERRE, cierre.id)).json()["proceso_id"]

        for i in range(2, 7):  # 5 devoluciones: sin tope, nunca finaliza
            resp = await _revisar(client, pid, "devuelto", user=LIDER if i % 2 else LIDER2)
            assert resp.json()["estado"]["codigo"] == "rechazado"
            resp = await _subir(client, pid, archivo=(f"v{i}.docx", f"PK {i}".encode(), DOCX[2]))
            assert resp.status_code == 200, resp.text
            # No se auto-aprueba: el líder revisa otra vez.
            assert resp.json()["estado"]["codigo"] == "en_revision"
            assert resp.json()["version"] == i
        assert any("nueva versión (v6)" in m for m in stubs.users.para(LIDER))

    async def test_cadena_de_revision_un_paso_del_lider(self, client, make_cierre):
        _, cierre = await make_cierre()
        pid = (await _proyectar(client, ETAPA_CIERRE, cierre.id)).json()["proceso_id"]

        d = (await _detalle(client, pid)).json()
        assert (d["paso_actual"], d["total_pasos"]) == (1, 1)
        paso = d["pasos"][0]
        assert paso["numero"] == 1 and paso["estado"] == "actual"
        assert paso["permisos"][0]["permiso"] == Permission.LIDER_PROYECTO
        assert paso["permisos"][0]["revisado"] is False

        await _revisar(client, pid, "aprobado_firma", user=LIDER2)
        paso = (await _detalle(client, pid)).json()["pasos"][0]
        assert paso["estado"] == "completado"
        assert paso["permisos"][0]["revisado"] is True
        assert paso["permisos"][0]["revisor_id"] == LIDER2

    async def test_no_sube_version_en_revision(self, client, make_cierre):
        _, cierre = await make_cierre()
        pid = (await _proyectar(client, ETAPA_CIERRE, cierre.id)).json()["proceso_id"]
        d = (await _detalle(client, pid)).json()
        assert d["subida_version"]["permitida"] is False
        assert (await _subir(client, pid)).status_code == 400


class TestVersionFinal:
    async def test_aprobado_firma_y_version_final_crea_acto(self, client, make_cierre, stubs, db_session):
        _, cierre = await make_cierre()
        pid = await _aprobado_firma(client, cierre)
        assert any("aprobado para firma" in m for m in stubs.users.para(ENCARGADO))

        d = (await _detalle(client, pid)).json()
        assert d["puede_cargar_version_final"] is True
        assert d["subida_version"]["permitida"] is False
        assert (await _subir(client, pid, archivo=PDF)).status_code == 409

        resp = await _version_final(client, pid)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["estado"]["codigo"] == "aprobado"
        file_id = body["acto"]["documento_acto_id"]

        await db_session.refresh(cierre)
        acto = await db_session.scalar(select(ActoAdministrativo).where(ActoAdministrativo.id == cierre.acto_administrativo_id))
        assert (acto.tipo_acto, acto.numerado, acto.fecha_numerado.isoformat()) == ("AUTO", 15, "2026-11-10")
        assert acto.documento_acto_administrativo_id == file_id
        # Un uso por la versión del proceso y otro por el acto.
        assert stubs.files.incrementados.count(file_id) == 2
        assert any("acto creado" in m for m in stubs.users.para(LIDER))

        # Etapa con acto: no se puede proyectar otro.
        assert (await _proyectar(client, ETAPA_CIERRE, cierre.id, archivo=("x.docx", b"PK x", DOCX[2]))).status_code == 409

    async def test_validaciones_antes_de_subir(self, client, make_cierre, stubs, db_session):
        db_session.add(ActoAdministrativo(tipo_acto="RES", numerado=15, fecha_numerado=__import__("datetime").date(2026, 11, 10)))
        await db_session.flush()
        _, cierre = await make_cierre()
        pid = await _aprobado_firma(client, cierre)
        subidos = list(stubs.files.subidos)

        assert (await _version_final(client, pid, archivo=DOCX)).status_code == 400
        assert (await _version_final(client, pid, numerado="12345")).status_code == 400
        assert (await _version_final(client, pid, tipo="DECRETO")).status_code == 400
        resp = await _version_final(client, pid)  # numerado 15 + fecha ya usados
        assert resp.status_code == 400 and "ya está en uso" in resp.json()["detail"]
        assert stubs.files.subidos == subidos

    async def test_solo_encargado_y_solo_en_aprobado_firma(self, client, make_cierre):
        _, cierre = await make_cierre()
        pid = (await _proyectar(client, ETAPA_CIERRE, cierre.id)).json()["proceso_id"]
        assert (await _version_final(client, pid)).status_code == 409
        await _revisar(client, pid, "aprobado_firma")
        assert (await _version_final(client, pid, user=LIDER)).status_code == 403
        assert (await _version_final(client, pid, user=SUPER)).status_code == 403


class TestReasignacion:
    async def test_continua_el_nuevo_encargado_y_se_le_avisa(self, client, make_cierre, stubs, db_session):
        exp, cierre = await make_cierre()
        pid = (await _proyectar(client, ETAPA_CIERRE, cierre.id)).json()["proceso_id"]
        await _revisar(client, pid, "devuelto")

        resp = await client.patch(f"/expedientes/{exp.id}/encargado/{NUEVO}", headers=gateway_headers(SUPER))
        assert resp.status_code == 200, resp.text
        assert any("te corresponde continuar" in m for m in stubs.users.para(NUEVO))

        # El anterior ya no sube; el nuevo sí (aunque no creó el proceso).
        assert (await _subir(client, pid, user=ENCARGADO)).status_code == 403
        resp = await _subir(client, pid, user=NUEVO)
        assert resp.status_code == 200, resp.text

    async def test_masivo_avisa(self, client, make_cierre, stubs):
        exp, cierre = await make_cierre()
        await _proyectar(client, ETAPA_CIERRE, cierre.id)
        resp = await client.patch(
            "/expedientes/encargado/masivo",
            json={"expediente_id": [exp.id], "encargado_id": NUEVO},
            headers=gateway_headers(SUPER),
        )
        assert resp.status_code == 200, resp.text
        assert any("te corresponde continuar" in m for m in stubs.users.para(NUEVO))

    async def test_sin_proceso_en_curso_no_avisa_de_actos(self, client, make_cierre, stubs):
        exp, _ = await make_cierre()
        await client.patch(f"/expedientes/{exp.id}/encargado/{NUEVO}", headers=gateway_headers(SUPER))
        assert not any("te corresponde continuar" in m for m in stubs.users.para(NUEVO))


class TestSuperGestion:
    async def _cargue_directo(self, client, exp, cierre, user=SUPER, numerado=20):
        return await client.post(
            "/actos/administrativos",
            data={
                "expediente_id": str(exp.id), "etapa_cierre_id": str(cierre.id), "tipo_acto": "RES",
                "numerado": str(numerado), "fecha_numerado": "2026-11-11", "documento_acto_administrativo_id": "500",
            },
            headers=gateway_headers(user),
        )

    async def test_encargado_ya_no_carga_directo(self, client, make_cierre):
        exp, cierre = await make_cierre()
        assert (await self._cargue_directo(client, exp, cierre, user=ENCARGADO)).status_code == 403

    async def test_cargue_directo_cierra_proceso(self, client, make_cierre, db_session):
        exp, cierre = await make_cierre()
        pid = (await _proyectar(client, ETAPA_CIERRE, cierre.id)).json()["proceso_id"]

        resp = await self._cargue_directo(client, exp, cierre)
        assert resp.status_code == 201, resp.text

        proceso = await db_session.scalar(
            select(DocumentoProceso).where(DocumentoProceso.id == pid).execution_options(populate_existing=True)
        )
        assert proceso.estado == "finalizado" and proceso.activo is False

        estado = (await client.get(f"/revision-actos/etapa/{ETAPA_CIERRE}/{cierre.id}", headers=gateway_headers(ENCARGADO))).json()
        assert estado["acto_id"] and estado["proceso"] is None and estado["puede_proyectar"] is False

    async def test_editar_documento_solo_super_y_eliminar_solo_super(self, client, make_cierre, db_session):
        exp, cierre = await make_cierre()
        acto_id = (await self._cargue_directo(client, exp, cierre)).json()["data"]["id"]

        datos = {"tipo_acto": "AUTO", "numerado": "21", "fecha_numerado": "2026-11-11"}
        # El encargado corrige datos, pero no el PDF.
        resp = await client.put(f"/actos/administrativos/{acto_id}", data=datos, headers=gateway_headers(ENCARGADO))
        assert resp.status_code == 200, resp.text
        resp = await client.put(f"/actos/administrativos/{acto_id}", data={**datos, "documento_acto_administrativo_id": "501"},
                                headers=gateway_headers(ENCARGADO))
        assert resp.status_code == 403
        resp = await client.put(f"/actos/administrativos/{acto_id}", data={**datos, "documento_acto_administrativo_id": "501"},
                                headers=gateway_headers(SUPER))
        assert resp.status_code == 200, resp.text

        assert (await client.delete(f"/actos/administrativos/{acto_id}", headers=gateway_headers(ENCARGADO))).status_code == 403
        assert (await client.delete(f"/actos/administrativos/{acto_id}", headers=gateway_headers(SUPER))).status_code == 200

    async def test_tras_eliminar_el_acto_se_puede_proyectar_de_nuevo(self, client, make_cierre):
        exp, cierre = await make_cierre()
        pid = await _aprobado_firma(client, cierre)
        acto_id = (await _version_final(client, pid)).json()["acto"]["id"]
        assert (await client.delete(f"/actos/administrativos/{acto_id}", headers=gateway_headers(SUPER))).status_code == 200

        resp = await _proyectar(client, ETAPA_CIERRE, cierre.id, archivo=("nuevo.docx", b"PK nuevo", DOCX[2]))
        assert resp.status_code == 201, resp.text
        assert resp.json()["proceso_id"] != pid
        # El anterior queda en el histórico, visible.
        assert (await _detalle(client, pid)).json()["activo"] is False


async def _iniciar(client, etapa_tipo, ref_id, user=ENCARGADO):
    return await client.post(
        "/revision-actos/iniciar",
        data={"etapa_tipo": etapa_tipo, "etapa_ref_id": str(ref_id)},
        headers=gateway_headers(user),
    )


class TestIniciar:
    """Como recurso: el proceso se abre en pendiente de carga y la primera
    versión se sube desde el modal (``/{id}/versiones``)."""

    async def test_iniciar_y_subir_primera_version(self, client, make_cierre, stubs):
        _, cierre = await make_cierre()
        resp = await _iniciar(client, ETAPA_CIERRE, cierre.id)
        assert resp.status_code == 201, resp.text
        pid = resp.json()["proceso_id"]
        assert resp.json()["estado"]["codigo"] == "pendiente_carga"

        d = (await _detalle(client, pid)).json()
        assert d["version_actual"] == 0 and d["subida_version"]["permitida"] is True
        estado = (await client.get(f"/revision-actos/etapa/{ETAPA_CIERRE}/{cierre.id}",
                                   headers=gateway_headers(ENCARGADO))).json()
        assert estado["proceso"]["id"] == pid and estado["puede_proyectar"] is False

        # Idempotente: un segundo clic devuelve el mismo proceso.
        resp = await _iniciar(client, ETAPA_CIERRE, cierre.id)
        assert resp.status_code == 200 and resp.json()["proceso_id"] == pid

        resp = await _subir(client, pid)
        assert resp.status_code == 200, resp.text
        assert resp.json()["estado"]["codigo"] == "en_revision" and resp.json()["version"] == 1
        assert (await _revisar(client, pid, "aprobado_firma")).status_code == 200

    async def test_solo_el_encargado_sin_acto(self, client, make_cierre, stubs):
        _, cierre = await make_cierre()
        pid = await _aprobado_firma(client, cierre)
        assert (await _version_final(client, pid)).status_code == 200
        assert (await _iniciar(client, ETAPA_CIERRE, cierre.id)).status_code == 409

    async def test_otro_usuario_o_etapa_inexistente(self, client, make_cierre):
        _, cierre = await make_cierre()
        assert (await _iniciar(client, ETAPA_CIERRE, cierre.id, user=LIDER)).status_code == 403
        assert (await _iniciar(client, ETAPA_CIERRE, 999999)).status_code == 404


class TestVisibilidad:
    async def test_estado_etapa(self, client, make_cierre):
        _, cierre = await make_cierre()
        url = f"/revision-actos/etapa/{ETAPA_CIERRE}/{cierre.id}"
        d = (await client.get(url, headers=gateway_headers(ENCARGADO))).json()
        assert d["puede_proyectar"] is True and d["proceso"] is None and d["puede_cargue_directo"] is False
        assert d["encargado_id"] == ENCARGADO and d["encargado_nombre"]
        d = (await client.get(url, headers=gateway_headers(SUPER))).json()
        assert d["puede_proyectar"] is False and d["puede_cargue_directo"] is True
        assert (await client.get(url, headers=gateway_headers(EXTRANO))).status_code == 403

    async def test_detalle_y_descargas(self, client, make_cierre):
        _, cierre = await make_cierre()
        pid = (await _proyectar(client, ETAPA_CIERRE, cierre.id)).json()["proceso_id"]
        for user in (ENCARGADO, LIDER, CONSULTA, SUPER):
            assert (await _detalle(client, pid, user)).status_code == 200
        assert (await _detalle(client, pid, EXTRANO)).status_code == 403

        version_id = (await _detalle(client, pid)).json()["versiones"][0]["version_id"]
        url = f"/revision-actos/{pid}/versiones/{version_id}/descarga"
        assert (await client.get(url, headers=gateway_headers(LIDER))).status_code == 200
        assert (await client.get(url, headers=gateway_headers(EXTRANO))).status_code == 403

    async def test_proceso_de_informe_no_se_ve_por_actos(self, client, make_expediente, db_session):
        exp = await make_expediente(abogado_responsable_id=ENCARGADO)
        p = DocumentoProceso(nombre="inf", descripcion="", creador_id=ENCARGADO, estado="pendiente_carga",
                             version_actual=0, numero_devoluciones=0, expediente_id=exp.id,
                             tipo_documento="INFORME_VISITA", etapa_tipo="informe_tecnico", etapa_ref_id=1)
        db_session.add(p)
        await db_session.flush()
        assert (await _detalle(client, p.id, SUPER)).status_code == 403
        assert (await _subir(client, p.id)).status_code == 403


class TestMisActuaciones:
    async def _mis(self, client, user):
        return await client.get("/mis-actuaciones", headers=gateway_headers(user))

    async def test_sin_permisos_403(self, client):
        assert (await self._mis(client, EXTRANO)).status_code == 403

    async def test_encargado_y_lider(self, client, make_cierre):
        _, cierre = await make_cierre()
        _, otro = await make_cierre()
        pid = (await _proyectar(client, ETAPA_CIERRE, cierre.id)).json()["proceso_id"]
        pid2 = (await _proyectar(client, ETAPA_CIERRE, otro.id)).json()["proceso_id"]
        await _revisar(client, pid, "devuelto")

        d = (await self._mis(client, ENCARGADO)).json()["data"]
        filas = {f["proceso_id"]: f for f in d["actuaciones"]}
        assert set(filas) == {pid, pid2}
        assert filas[pid]["requiere_mi_accion"] is True
        assert filas[pid]["accion_pendiente"] == "Subir la versión corregida"
        assert filas[pid2]["requiere_mi_accion"] is False
        assert [r["codigo"] for r in filas[pid]["roles"]] == ["encargado"]
        assert filas[pid]["acto"]["etapa_tipo"] == ETAPA_CIERRE
        assert d["actuaciones"][0]["proceso_id"] == pid  # lo que requiere acción primero
        assert d["conteos"] == {"total": 2, "requieren_accion": 1}

        # Líder: el que revisó (devuelto, ya no requiere) y el pendiente de revisión.
        filas = {f["proceso_id"]: f for f in (await self._mis(client, LIDER)).json()["data"]["actuaciones"]}
        assert set(filas) == {pid, pid2}
        assert filas[pid2]["accion_pendiente"] == "Revisar el acto"
        assert filas[pid]["requiere_mi_accion"] is False
        # LIDER2 no participó en pid: solo ve el pendiente.
        filas = {f["proceso_id"] for f in (await self._mis(client, LIDER2)).json()["data"]["actuaciones"]}
        assert filas == {pid2}

    async def test_reasignado_ve_y_actua_el_nuevo(self, client, make_cierre, db_session):
        exp, cierre = await make_cierre()
        pid = await _aprobado_firma(client, cierre)
        exp.abogado_responsable_id = NUEVO
        await db_session.flush()

        nuevo = {f["proceso_id"]: f for f in (await self._mis(client, NUEVO)).json()["data"]["actuaciones"]}
        assert nuevo[pid]["accion_pendiente"] == "Cargar la versión firmada desde la etapa"
        # Quien lo proyectó lo conserva en su histórico, sin acción.
        antes = {f["proceso_id"]: f for f in (await self._mis(client, ENCARGADO)).json()["data"]["actuaciones"]}
        assert antes[pid]["requiere_mi_accion"] is False

    async def test_incluye_informes_del_tecnico(self, client, make_expediente, db_session, monkeypatch):
        from db.models.informe_tecnico import InformeTecnico

        exp = await make_expediente(abogado_responsable_id=ENCARGADO)
        db_session.add(InformeTecnico(expediente_id=exp.id, tipo_informe="VISITA", profesional_asignado_id=ENCARGADO))
        await db_session.flush()
        verify = users_svc.verify_permission

        async def _con_tecnico(user_id, permission):
            return permission == Permission.TECNICO or await verify(user_id, permission)

        monkeypatch.setattr(users_svc, "verify_permission", _con_tecnico)
        filas = (await self._mis(client, ENCARGADO)).json()["data"]["actuaciones"]
        assert [(f["categoria"], f["tipo_documento"]) for f in filas] == [("informe", "INFORME_VISITA")]
        assert filas[0]["roles"] == [{"codigo": "encargado", "etiqueta": "Técnico"}]
        assert filas[0]["informe"]["id"]

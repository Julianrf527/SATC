"""Regresiones de la revisión del backend de app-recurso (octubre 2026).

Cada test fija un bug corregido: tipo de notificación que no cabía en
app-users, super gestión que dejaba procesos sin encargado válido o sin
proceso, usos de archivo del concepto, V1/V3 al proyectar, bloqueo del
expediente en solicitantes y validación de PDF en /actos.
"""
import asyncio

from sqlalchemy import select

from core.permission import Permission
from db.models import Expediente
from services.revision_documentos import TIPO_NOTIFICACION
from tests.conftest import TestSessionLocal
from tests.fixtures_etapas import *  # noqa: F401,F403


# ─── 1. Tipo de notificación (app-users: notificacion.tipo String(15)) ───────

async def test_tipo_notificacion_cabe_en_app_users(client, rv_permisos, expediente):
    assert TIPO_NOTIFICACION == "recurso_doc" and len(TIPO_NOTIFICACION) <= 15
    await post(client, f"/etapas/{expediente.id}/admite/asignarme", ABOGADO)
    enviados = rv_permisos.users.notificaciones
    assert enviados and all(len(n["tipo"]) <= 15 for n in enviados)


# ─── 3. Super gestión reasigna el encargado del proceso vigente ──────────────

async def test_super_reasigna_tecnico_actualiza_proceso(client, rv_permisos, expediente):
    stubs = rv_permisos
    exp_id = expediente.id
    await admite_firmado(client, stubs, exp_id)
    NUEVO = 33
    stubs.permisos.dar(NUEVO, Permission.TECNICO)
    await post(client, f"/super-gestion/{exp_id}/admite", SUPER_G, {"tecnico_id": NUEVO})
    arbol = await etapas(client, exp_id)
    pid = arbol["concepto"]["proceso"]["proceso_id"]
    assert arbol["concepto"]["proceso"]["encargado_id"] == NUEVO
    # El técnico anterior ya no proyecta; el nuevo sí, hasta la versión final.
    assert (await subir(client, pid, user=TECNICO)).status_code == 403
    await aprobar_para_firma(client, pid, NUEVO)
    body = {"file_id": stubs.files.registrar(), "fecha_aceptacion": "2026-05-20", **CAUDALES}
    url = f"/etapas/{exp_id}/conceptos/etapa2/version-final"
    await post(client, url, TECNICO, body, esperado=403)
    await post(client, url, NUEVO, body)
    assert any("reasignaron" in m for m in stubs.users.para(NUEVO))


async def test_super_reasigna_encargado_decision_actualiza_proceso(client, rv_permisos, expediente):
    stubs = rv_permisos
    exp_id = expediente.id
    await admite_firmado(client, stubs, exp_id)
    await con_constancia(client, stubs, exp_id)
    r = await post(client, f"/etapas/{exp_id}/decision/asignarme", ABOGADO)
    pid = r.json()["data"]["proceso_id"]
    await post(client, f"/super-gestion/{exp_id}/decision", SUPER_G, {"encargado_acto_id": ABOGADO2})
    assert (await subir(client, pid, user=ABOGADO)).status_code == 403
    await aprobar_para_firma(client, pid, ABOGADO2)
    body = acto_body(stubs, decision="NEGADA")
    await post(client, f"/etapas/{exp_id}/decision/version-final", ABOGADO, body, esperado=403)
    await post(client, f"/etapas/{exp_id}/decision/version-final", ABOGADO2, body)


# ─── 4. Super gestión crea el proceso si la fila queda con encargado ─────────

async def test_super_decision_sin_acto_crea_proceso(client, rv_permisos, expediente):
    stubs = rv_permisos
    exp_id = expediente.id
    await admite_firmado(client, stubs, exp_id)
    await con_constancia(client, stubs, exp_id)
    await post(client, f"/super-gestion/{exp_id}/decision", SUPER_G, {"encargado_acto_id": ABOGADO})
    proceso = (await etapas(client, exp_id))["decision"]["proceso"]
    assert proceso["proceso_id"] and proceso["encargado_id"] == ABOGADO
    assert proceso["estado_proceso"]["codigo"] == "pendiente_carga"
    await aprobar_para_firma(client, proceso["proceso_id"], ABOGADO)
    await post(client, f"/etapas/{exp_id}/decision/version-final", ABOGADO, acto_body(stubs, decision="NEGADA"))


async def test_super_decision_con_acto_no_deja_proceso(client, rv_permisos, expediente):
    stubs = rv_permisos
    exp_id = expediente.id
    await admite_firmado(client, stubs, exp_id)
    await post(client, f"/super-gestion/{exp_id}/decision", SUPER_G, {
        "encargado_acto_id": ABOGADO, "decision": "NEGADA",
        "acto": {"clase_acto": "RES", "numerado": numerado(), "fecha_numerado": "2026-04-05", "file_id": stubs.files.registrar()},
    })
    proceso = (await etapas(client, exp_id))["decision"].get("proceso")
    assert not proceso or proceso["proceso_id"] is None


async def test_super_concepto_con_tecnico_sin_documento_crea_proceso(client, rv_permisos, expediente):
    stubs = rv_permisos
    exp_id = expediente.id
    await post(client, f"/super-gestion/{exp_id}/admite", SUPER_G, {
        "acto": {"clase_acto": "RES", "numerado": numerado(), "fecha_numerado": "2026-04-05", "file_id": stubs.files.registrar()},
    })
    await post(client, f"/super-gestion/{exp_id}/conceptos/etapa2", SUPER_G, {"tecnico_encargado_id": TECNICO})
    proceso = (await etapas(client, exp_id))["concepto"]["proceso"]
    assert proceso["proceso_id"] and proceso["encargado_id"] == TECNICO
    data = await concepto_firmado(client, stubs, exp_id, "etapa2", **CAUDALES)
    assert data["doc_concepto_tecnico_id"]


# ─── 5. El documento final del concepto suma su uso propio ───────────────────

async def test_uso_archivo_concepto_sobrevive_reemplazo_super(client, rv_permisos, expediente):
    stubs = rv_permisos
    exp_id = expediente.id
    await admite_firmado(client, stubs, exp_id)
    data = await concepto_firmado(client, stubs, exp_id, "etapa2", **CAUDALES)
    x = data["doc_concepto_tecnico_id"]
    assert stubs.files.incrementados.count(x) == 2  # versión + columna del concepto
    await post(client, f"/super-gestion/{exp_id}/conceptos/etapa2", SUPER_G, {"file_id": stubs.files.registrar()})
    # Sigue referenciado por documento_proceso_version: 1 uso vivo.
    assert stubs.files.incrementados.count(x) - stubs.files.decrementados.count(x) == 1


# ─── 6. V1/V3 se re-verifican al proyectar ───────────────────────────────────

async def test_v1_abogado_sin_gestionar_no_proyecta(client, rv_permisos, expediente):
    stubs = rv_permisos
    r = await post(client, f"/etapas/{expediente.id}/admite/asignarme", ABOGADO)
    pid = r.json()["data"]["proceso_id"]
    stubs.permisos.quitar(ABOGADO)
    assert (await subir(client, pid, user=ABOGADO)).status_code == 403
    stubs.permisos.dar(ABOGADO, Permission.SUPER_MANAGE)  # super gestión también habilita
    assert (await subir(client, pid, user=ABOGADO)).status_code == 200


async def test_v3_tecnico_sin_permiso_no_proyecta(client, rv_permisos, expediente):
    stubs = rv_permisos
    await admite_firmado(client, stubs, expediente.id)
    pid = (await etapas(client, expediente.id))["concepto"]["proceso"]["proceso_id"]
    stubs.permisos.quitar(TECNICO, Permission.TECNICO)
    stubs.permisos.dar(TECNICO, Permission.MANAGE)  # gestionar no basta para un concepto
    assert (await subir(client, pid, user=TECNICO)).status_code == 403


# ─── 7. Solicitantes bloquean el expediente ──────────────────────────────────

async def _espera_bloqueo(exp_id: int, peticion) -> int:
    """Con el expediente bloqueado por otra transacción la petición debe esperar."""
    async with TestSessionLocal() as s:
        await s.execute(select(Expediente.id).where(Expediente.id == exp_id).with_for_update())
        tarea = asyncio.create_task(peticion())
        await asyncio.sleep(0.6)
        bloqueada = not tarea.done()
        await s.rollback()
    r = await tarea
    assert bloqueada, "la petición no esperó el bloqueo del expediente"
    return r.status_code


async def test_editar_representante_bloquea_expediente(client, h_gestor, crear_expediente, vincular, stubs):
    exp = await crear_expediente()
    stubs.involved.registrar(61)
    v = await vincular(exp.id, 60)
    estado = await _espera_bloqueo(exp.id, lambda: client.patch(
        f"/involucrados/vinculos/{v.id}/representante", json={"representante_id": 61, "version": 1},
        headers=h_gestor))
    assert estado == 200


async def test_desvincular_bloquea_expediente(client, h_gestor, crear_expediente, vincular):
    exp = await crear_expediente()
    v = await vincular(exp.id, 70)
    estado = await _espera_bloqueo(exp.id, lambda: client.delete(
        f"/involucrados/vinculos/{v.id}", params={"version": 1}, headers=h_gestor))
    assert estado == 200


# ─── 9. /actos valida que los documentos existan y sean PDF ──────────────────

async def test_actos_validan_pdf(client, rv_permisos, expediente):
    stubs = rv_permisos
    exp_id = expediente.id
    acto_id = (await admite_firmado(client, stubs, exp_id))["acto_id"]
    docx = stubs.files.registrar(b"PK", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    inexistente = 987654

    form = {"expediente_id": str(exp_id), "numerado": "0777", "fecha_numerado": "2026-04-01",
            "documento_acto_administrativo_id": str(docx)}
    r = await client.put(f"/actos/administrativos/{acto_id}", data=form, headers=headers(ABOGADO))
    assert r.status_code == 400 and "PDF" in r.json()["detail"]

    com = {"expediente_id": str(exp_id), "acto_admin_id": str(acto_id), "numerado": "0003",
           "fecha_numerado": "2026-04-02", "fecha_envio": "2026-04-03", "documento_comunicacion_id": str(inexistente)}
    r = await client.post("/actos/comunicaciones", data=com, headers=headers(ABOGADO))
    assert r.status_code == 400 and "no encontrado" in r.json()["detail"]

    notif = {
        "expediente_id": exp_id, "acto_admin_id": acto_id, "involucrado_id": SOLICITANTE, "numerado": "0045",
        "fecha_numerado": "2026-04-02", "fecha_envio_citacion": "2026-04-03",
        "fecha_constancia_citacion": "2026-04-04", "documento_citacion_id": docx, "notificacion_exitosa": "false",
    }
    r = await client.post("/actos/notificaciones", data={k: str(v) for k, v in notif.items()},
                          headers=headers(ABOGADO))
    assert r.status_code == 400
    assert docx not in stubs.files.incrementados and inexistente not in stubs.files.incrementados

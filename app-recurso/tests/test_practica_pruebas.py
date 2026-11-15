"""Recurso de reposición · práctica de pruebas.

«¿Requiere práctica de pruebas?» se responde al crear el recurso. Si es Sí:
auto que admite y decreta práctica de pruebas (cualquier abogado, solo se
comunica) → al cargarlo con técnico y visita nace el concepto técnico de
pruebas → con ese concepto firmado se habilita el acto que resuelve el recurso.
"""
from sqlalchemy import func, select

from db.models import ActoAdministrativo, ConceptoTecnico, PracticaPruebas, RecursoReposicion
from db.models.documento_proceso import DocumentoProceso
from services.validaciones import MSG_PRIMERO_CONCEPTO_PRUEBAS
from tests.fixtures_etapas import *  # noqa: F401,F403

URL_AUTO = "Auto que admite y decreta práctica de pruebas"


async def _recurso(client, stubs, con_decision, catalogo, requiere: bool) -> int:
    exp_id, data = await con_decision("NEGADA", None)
    await notificar(client, stubs, catalogo, exp_id, data["acto_id"])
    r = await post(client, f"/etapas/{exp_id}/recurso", json={
        "radicado": "2026ER77", "fecha_radicado": "2026-06-10", "file_id": stubs.files.registrar(),
        "requiere_pruebas": requiere,
    }, esperado=201)
    assert r.json()["data"]["requiere_pruebas"] is requiere
    return exp_id


async def _auto_pruebas(client, stubs, exp_id: int, user: int = ABOGADO2) -> dict:
    return await acto_completo(client, stubs, f"/etapas/{exp_id}/recurso/pruebas", user,
                               tecnico_id=TECNICO, fecha_visita_tecnica="2026-06-20")


async def _cambiar(client, exp_id: int, requiere: bool, esperado: int = 200, confirmar: bool = False, user=ABOGADO):
    arbol = await etapas(client, exp_id)
    return await put(client, f"/etapas/{exp_id}/recurso/requiere-pruebas", user, {
        "version": arbol["decision"]["recurso"]["version"], "requiere_pruebas": requiere,
        "confirmar_eliminar_pruebas": confirmar,
    }, esperado=esperado)


async def test_crear_recurso_exige_la_respuesta(client, rv_permisos, con_decision, catalogo):
    stubs = rv_permisos
    exp_id, data = await con_decision("NEGADA", None)
    await notificar(client, stubs, catalogo, exp_id, data["acto_id"])
    await post(client, f"/etapas/{exp_id}/recurso", json={
        "radicado": "2026ER1", "fecha_radicado": "2026-06-10", "file_id": stubs.files.registrar()}, esperado=422)


async def test_sin_pruebas_resuelve_directo(client, rv_permisos, con_decision, catalogo):
    stubs = rv_permisos
    exp_id = await _recurso(client, stubs, con_decision, catalogo, False)
    rec = (await etapas(client, exp_id))["decision"]["recurso"]
    assert rec["datos"]["requiere_pruebas"] is False
    assert rec["pruebas"] is None
    assert "asignarme" in rec["acciones_disponibles"]
    r = await post(client, f"/etapas/{exp_id}/recurso/pruebas/asignarme", ABOGADO2, esperado=400)
    assert "no requiere práctica de pruebas" in r.json()["detail"]
    datos = await acto_completo(client, stubs, f"/etapas/{exp_id}/recurso", ABOGADO2, resultado="CONFIRMA")
    assert datos["resultado"] == "CONFIRMA"


async def test_flujo_con_pruebas(client, rv_permisos, con_decision, catalogo, db_session):
    stubs = rv_permisos
    exp_id = await _recurso(client, stubs, con_decision, catalogo, True)
    rec = (await etapas(client, exp_id))["decision"]["recurso"]
    # El acto que resuelve espera al concepto de pruebas.
    assert MSG_PRIMERO_CONCEPTO_PRUEBAS in rec["motivos_bloqueo"]
    assert "asignarme" not in rec["acciones_disponibles"]
    r = await post(client, f"/etapas/{exp_id}/recurso/asignarme", ABOGADO2, esperado=400)
    assert r.json()["detail"] == MSG_PRIMERO_CONCEPTO_PRUEBAS
    pruebas = rec["pruebas"]
    assert pruebas["etiqueta"] == URL_AUTO and pruebas["existe"] is False
    assert "asignarme" in pruebas["acciones_disponibles"]
    assert pruebas["concepto"]["habilitada"] is False
    assert pruebas["concepto"]["campos"]["obligatorios"] == ["file_id", "fecha_aceptacion"]
    # No se selecciona técnico aparte: nace con el auto.
    await post(client, f"/etapas/{exp_id}/conceptos/pruebas/tecnico", json={"tecnico_id": TECNICO}, esperado=400)

    # Auto de pruebas (cualquier abogado) con técnico y visita → nace el concepto.
    datos = await _auto_pruebas(client, stubs, exp_id)
    assert datos["concepto_tecnico_id"]
    await post(client, f"/etapas/{exp_id}/recurso/pruebas/asignarme", ABOGADO, esperado=409)
    fila = await db_session.scalar(select(PracticaPruebas))
    acto = await db_session.get(ActoAdministrativo, fila.acto_admin_id)
    assert fila.encargado_acto_id == ABOGADO2 and acto.tipo_acto.value == "AUTO_PRUEBAS"
    concepto = await db_session.get(ConceptoTecnico, fila.concepto_tecnico_id)
    assert concepto.tecnico_encargado_id == TECNICO and str(concepto.fecha_visita_tecnica) == "2026-06-20"
    assert concepto.expediente_id is None

    arbol = await etapas(client, exp_id, ABOGADO2)
    pruebas = arbol["decision"]["recurso"]["pruebas"]
    # Solo se comunica.
    assert "crear_comunicacion" in pruebas["acto"]["acciones_disponibles"]
    assert "crear_notificacion" not in pruebas["acto"]["acciones_disponibles"]
    assert pruebas["concepto"]["existe"] is True
    assert pruebas["concepto"]["proceso"]["tipo_documento"] == "CONCEPTO_PRUEBAS"
    # Sí → No bloqueado: el concepto ya existe.
    assert "editar_requiere_pruebas" not in arbol["decision"]["recurso"]["acciones_disponibles"]
    r = await _cambiar(client, exp_id, False, esperado=400)
    assert "concepto técnico" in r.json()["detail"]

    # Con el concepto firmado se habilita el acto que resuelve.
    await post(client, f"/etapas/{exp_id}/recurso/asignarme", ABOGADO2, esperado=400)
    await concepto_firmado(client, stubs, exp_id, "pruebas")
    concepto = await db_session.scalar(
        select(ConceptoTecnico).where(ConceptoTecnico.id == fila.concepto_tecnico_id)
        .execution_options(populate_existing=True))
    assert concepto.doc_concepto_tecnico_id and str(concepto.fecha_aceptacion) == "2026-05-20"
    rec = (await etapas(client, exp_id))["decision"]["recurso"]
    assert rec["motivos_bloqueo"] == [] and "asignarme" in rec["acciones_disponibles"]
    datos = await acto_completo(client, stubs, f"/etapas/{exp_id}/recurso", ABOGADO, resultado="REPONE")
    assert datos["resultado"] == "REPONE"


async def test_concepto_pruebas_mismos_revisores_que_etapa2():
    from services.revision_documentos import CADENAS

    assert CADENAS["CONCEPTO_PRUEBAS"].pasos == CADENAS["CONCEPTO_ETAPA2"].pasos
    assert CADENAS["AUTO_PRUEBAS"].pasos == CADENAS["RECURSO"].pasos
    assert CADENAS["AUTO_PRUEBAS"].etapa_tipo == "practica_pruebas"


async def test_si_a_no_elimina_la_practica_iniciada(client, rv_permisos, con_decision, catalogo, db_session):
    stubs = rv_permisos
    exp_id = await _recurso(client, stubs, con_decision, catalogo, True)
    await post(client, f"/etapas/{exp_id}/recurso/pruebas/asignarme", ABOGADO2)
    rec = (await etapas(client, exp_id))["decision"]["recurso"]
    assert "editar_requiere_pruebas" in rec["acciones_disponibles"]
    assert "ELIMINARÁ" in rec["aviso_eliminar_pruebas"]
    # Sin confirmar: 409 con el aviso.
    r = await _cambiar(client, exp_id, False, esperado=409)
    assert "ELIMINARÁ" in r.json()["detail"]
    assert await db_session.scalar(select(func.count(PracticaPruebas.id))) == 1
    # Confirmado: se borra la fila y su proceso.
    r = await _cambiar(client, exp_id, False, confirmar=True)
    assert r.json()["data"]["practica_eliminada"] is True
    assert await db_session.scalar(select(func.count(PracticaPruebas.id))) == 0
    assert await db_session.scalar(select(func.count(DocumentoProceso.id)).where(
        DocumentoProceso.etapa_tipo == "practica_pruebas")) == 0
    rec = (await etapas(client, exp_id))["decision"]["recurso"]
    assert rec["datos"]["requiere_pruebas"] is False and rec["pruebas"] is None
    assert "asignarme" in rec["acciones_disponibles"]


async def test_no_a_si_conserva_la_asignacion(client, rv_permisos, con_decision, catalogo, db_session):
    stubs = rv_permisos
    exp_id = await _recurso(client, stubs, con_decision, catalogo, False)
    await post(client, f"/etapas/{exp_id}/recurso/asignarme", ABOGADO2)
    # Cualquier abogado puede cambiarlo.
    await _cambiar(client, exp_id, True)
    rec = await db_session.scalar(select(RecursoReposicion).execution_options(populate_existing=True))
    assert rec.requiere_pruebas is True and rec.encargado_acto_id == ABOGADO2
    arbol = (await etapas(client, exp_id, ABOGADO2))["decision"]["recurso"]
    # La asignación sigue, pero la versión final espera al concepto de pruebas.
    assert MSG_PRIMERO_CONCEPTO_PRUEBAS in arbol["motivos_bloqueo"]
    assert "cargar_version_final" not in arbol["acciones_disponibles"]
    await aprobar_para_firma(client, arbol["proceso"]["proceso_id"], ABOGADO2)
    r = await post(client, f"/etapas/{exp_id}/recurso/version-final", ABOGADO2,
                   acto_body(stubs, resultado="CONFIRMA"), esperado=400)
    assert r.json()["detail"] == MSG_PRIMERO_CONCEPTO_PRUEBAS
    # Vuelve a No (sin práctica iniciada: no pide confirmación) y ya puede resolver.
    await _cambiar(client, exp_id, False)
    await post(client, f"/etapas/{exp_id}/recurso/version-final", ABOGADO2, acto_body(stubs, resultado="CONFIRMA"))
    # Con el acto que resuelve cargado ya no pasa a Sí.
    r = await _cambiar(client, exp_id, True, esperado=400)
    assert "acto que resuelve" in r.json()["detail"]


async def test_requiere_pruebas_version_optimista(client, rv_permisos, con_decision, catalogo):
    stubs = rv_permisos
    exp_id = await _recurso(client, stubs, con_decision, catalogo, False)
    rec = (await etapas(client, exp_id))["decision"]["recurso"]
    await put(client, f"/etapas/{exp_id}/recurso/requiere-pruebas", json={
        "version": rec["version"] + 5, "requiere_pruebas": True}, esperado=409)
    await put(client, f"/etapas/{exp_id}/recurso/requiere-pruebas", LECTOR, json={
        "version": rec["version"], "requiere_pruebas": True}, esperado=403)


async def test_auto_pruebas_exige_tecnico(client, rv_permisos, con_decision, catalogo):
    stubs = rv_permisos
    exp_id = await _recurso(client, stubs, con_decision, catalogo, True)
    r = await post(client, f"/etapas/{exp_id}/recurso/pruebas/asignarme", ABOGADO2)
    await aprobar_para_firma(client, r.json()["data"]["proceso_id"], ABOGADO2)
    url = f"/etapas/{exp_id}/recurso/pruebas/version-final"
    await post(client, url, ABOGADO2, acto_body(stubs), esperado=422)
    await post(client, url, ABOGADO2, acto_body(stubs, tecnico_id=ABOGADO, fecha_visita_tecnica="2026-06-20"),
               esperado=400)
    # Solo el encargado.
    await post(client, url, ABOGADO, acto_body(stubs, tecnico_id=TECNICO, fecha_visita_tecnica="2026-06-20"),
               esperado=403)


async def test_super_gestion_pruebas(client, rv_permisos, con_decision, catalogo, db_session):
    stubs = rv_permisos
    exp_id, data = await con_decision("NEGADA", None)
    S = SUPER_G
    # Recurso sin requiere_pruebas → No.
    r = await post(client, f"/super-gestion/{exp_id}/recurso", S, {
        "radicado": "2026ER9", "fecha_radicado": "2026-06-10", "file_id": stubs.files.registrar()})
    assert r.json()["data"]["requiere_pruebas"] is False
    await post(client, f"/super-gestion/{exp_id}/recurso/pruebas", S, {}, esperado=400)
    await post(client, f"/super-gestion/{exp_id}/recurso", S, {"requiere_pruebas": True})
    # Auto de pruebas con técnico: nace el concepto (sin cargar su PDF).
    await post(client, f"/super-gestion/{exp_id}/recurso/pruebas", S, {
        "acto": {"clase_acto": "AUTO", "numerado": numerado(), "fecha_numerado": "2026-06-15",
                 "file_id": stubs.files.registrar()},
        "tecnico_id": TECNICO, "fecha_visita_tecnica": "2026-06-20"})
    fila = await db_session.scalar(select(PracticaPruebas))
    assert fila.acto_admin_id and fila.concepto_tecnico_id
    # El concepto queda con proceso para el técnico.
    arbol = await etapas(client, exp_id, S)
    assert arbol["decision"]["recurso"]["pruebas"]["concepto"]["proceso"] is not None
    # Sí → No bloqueado también para super gestión.
    await post(client, f"/super-gestion/{exp_id}/recurso", S, {"requiere_pruebas": False}, esperado=400)
    # El concepto de pruebas se carga por /conceptos/pruebas.
    await post(client, f"/super-gestion/{exp_id}/conceptos/pruebas", S, {
        "fecha_aceptacion": "2026-06-25", "file_id": stubs.files.registrar()})
    concepto = await db_session.scalar(
        select(ConceptoTecnico).where(ConceptoTecnico.id == fila.concepto_tecnico_id)
        .execution_options(populate_existing=True))
    assert concepto.doc_concepto_tecnico_id


async def test_super_gestion_si_a_no_con_confirmacion(client, rv_permisos, con_decision, catalogo, db_session):
    stubs = rv_permisos
    exp_id = await _recurso(client, stubs, con_decision, catalogo, True)
    # Auto cargado por super gestión sin técnico (no nace concepto).
    acto = {"clase_acto": "AUTO", "numerado": numerado(), "fecha_numerado": "2026-06-15",
            "file_id": stubs.files.registrar()}
    await post(client, f"/super-gestion/{exp_id}/recurso/pruebas", SUPER_G, {"acto": acto})
    await post(client, f"/super-gestion/{exp_id}/recurso", SUPER_G, {"requiere_pruebas": False}, esperado=409)
    stubs.files.decrementados.clear()
    r = await post(client, f"/super-gestion/{exp_id}/recurso", SUPER_G,
                   {"requiere_pruebas": False, "confirmar_eliminar_pruebas": True})
    assert r.json()["data"]["practica_eliminada"] is True
    assert await db_session.scalar(select(func.count(PracticaPruebas.id))) == 0
    assert await db_session.scalar(select(func.count(ActoAdministrativo.id)).where(
        ActoAdministrativo.tipo_acto == "AUTO_PRUEBAS")) == 0
    assert acto["file_id"] in stubs.files.decrementados


async def test_descarga_incluye_la_practica(client, rv_permisos, con_decision, catalogo, db_session):
    from services.expediente_documentos import _recorrer
    from db.models import Expediente

    stubs = rv_permisos
    exp_id = await _recurso(client, stubs, con_decision, catalogo, True)
    await _auto_pruebas(client, stubs, exp_id)
    await concepto_firmado(client, stubs, exp_id, "pruebas")
    exp = await db_session.get(Expediente, exp_id)
    descripciones = [d["descripcion"] for d in (await _recorrer(db_session, exp)).documentos]
    i_recurso = descripciones.index("Recurso de reposición")
    i_auto = next(i for i, d in enumerate(descripciones) if d.startswith(URL_AUTO))
    i_concepto = descripciones.index("Concepto técnico de la práctica de pruebas")
    assert i_recurso < i_auto < i_concepto


async def test_migracion_recursos_existentes_quedan_en_no(con_decision, db_session):
    """Simula el esquema anterior (sin la columna): la migración la agrega con
    «No» en los recursos ya creados y el tipo_acto tiene AUTO_PRUEBAS."""
    from sqlalchemy import text

    from db.migrations import aplicar_migraciones
    from tests.conftest import engine

    exp_id, _ = await con_decision("NEGADA", None)
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE recurso_reposicion DROP COLUMN requiere_pruebas"))
        await conn.execute(text(
            "INSERT INTO recurso_reposicion (decision_id, radicado, fecha_radicado, doc_recurso_id, version) "
            "SELECT id, 'R1', DATE '2026-06-10', 1, 1 FROM decision WHERE expediente_id = :e"), {"e": exp_id})
    async with engine.begin() as conn:
        await aplicar_migraciones(conn)
    assert (await db_session.execute(text("SELECT requiere_pruebas FROM recurso_reposicion"))).scalar_one() is False
    valores = (await db_session.execute(text("SELECT unnest(enum_range(NULL::tipo_acto))::text"))).scalars().all()
    assert "AUTO_PRUEBAS" in valores

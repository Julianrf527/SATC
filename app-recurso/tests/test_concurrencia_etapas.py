"""Concurrencia de etapas (plan §7): dos peticiones simultáneas → 200 + 409,
sin etapas duplicadas ni doble asignación."""
import asyncio

from sqlalchemy import func, select

from db.models import ActoAdmite, ConceptoTecnico, MemoriasCalculo, RecursoReposicion
from db.models.documento_proceso import DocumentoProceso
from tests.fixtures_etapas import *  # noqa: F401,F403


def _codigos(*respuestas) -> list[int]:
    return sorted(r.status_code for r in respuestas)


async def _a_la_vez(client, url: str, usuarios, json=None):
    return await asyncio.gather(*(client.post(url, json=json, headers=headers(u)) for u in usuarios))


async def test_dos_asignaciones_del_auto_admite(client, rv_permisos, expediente, db_session):
    r = await _a_la_vez(client, f"/etapas/{expediente.id}/admite/asignarme", (ABOGADO, ABOGADO2))
    assert _codigos(*r) == [200, 409]
    assert await db_session.scalar(select(func.count(ActoAdmite.id))) == 1
    assert await db_session.scalar(select(func.count(DocumentoProceso.id))) == 1


async def test_dos_asignaciones_del_recurso_update_atomico(client, rv_permisos, con_decision, catalogo, db_session):
    stubs = rv_permisos
    exp_id, data = await con_decision("NEGADA", None)
    await notificar(client, stubs, catalogo, exp_id, data["acto_id"])
    await post(client, f"/etapas/{exp_id}/recurso", json={
        "radicado": "2026ER1", "fecha_radicado": "2026-06-10", "file_id": stubs.files.registrar()}, esperado=201)
    r = await _a_la_vez(client, f"/etapas/{exp_id}/recurso/asignarme", (ABOGADO, ABOGADO2))
    assert _codigos(*r) == [200, 409]
    ganador = ABOGADO if r[0].status_code == 200 else ABOGADO2
    rec = await db_session.scalar(select(RecursoReposicion))
    assert rec.encargado_acto_id == ganador
    n = await db_session.scalar(select(func.count(DocumentoProceso.id)).where(
        DocumentoProceso.etapa_tipo == "recurso_reposicion"))
    assert n == 1


async def test_dos_creaciones_de_la_misma_etapa(client, rv_permisos, con_decision, db_session):
    stubs = rv_permisos
    exp_id, _ = await con_decision("OTORGADA", True)
    r = await asyncio.gather(*(
        client.post(f"/etapas/{exp_id}/memorias", json={
            "radicado": f"2026ER10{i}", "fecha_radicado": "2026-08-01", "file_id": stubs.files.registrar()},
            headers=headers(u))
        for i, u in enumerate((ABOGADO, ABOGADO2))
    ))
    assert _codigos(*r) == [201, 409]
    assert await db_session.scalar(select(func.count(MemoriasCalculo.id))) == 1


async def test_dos_selecciones_de_tecnico(client, rv_permisos, con_decision, db_session):
    stubs = rv_permisos
    exp_id, _ = await con_decision("OTORGADA", True)
    await post(client, f"/etapas/{exp_id}/memorias", json={
        "radicado": "2026ER100", "fecha_radicado": "2026-08-01", "file_id": stubs.files.registrar()}, esperado=201)
    antes = await db_session.scalar(select(func.count(ConceptoTecnico.id)))
    r = await _a_la_vez(client, f"/etapas/{exp_id}/conceptos/memorias/tecnico", (ABOGADO, ABOGADO2),
                        {"tecnico_id": TECNICO})
    assert _codigos(*r) == [200, 409]
    assert await db_session.scalar(select(func.count(ConceptoTecnico.id))) == antes + 1


async def test_dos_terceros_asignados(client, rv_permisos, expediente, vincular):
    v = await vincular(expediente.id, TERCERO_P, tipo_vinculo=TipoVinculo.TERCERO_INTERVINIENTE)
    r = await _a_la_vez(client, f"/terceros/{v.id}/asignarme", (ABOGADO, ABOGADO2))
    assert _codigos(*r) == [200, 409]

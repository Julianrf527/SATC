"""Etapa 5 · Memorias de cálculo y Etapa 6 · Recibo de obras (V9–V12)."""
from sqlalchemy import select

from db.models import MemoriasCalculo, ReciboSatisfaccionObras
from tests.fixtures_etapas import *  # noqa: F401,F403


def radicado(stubs, n: str) -> dict:
    return {"radicado": n, "fecha_radicado": "2026-08-01", "file_id": stubs.files.registrar()}


async def test_memorias_v9(client, rv_permisos, con_decision):
    stubs = rv_permisos
    exp_id, _ = await con_decision("OTORGADA", False)
    r = await post(client, f"/etapas/{exp_id}/memorias", json=radicado(stubs, "2026ER100"), esperado=400)
    assert "V9" in r.json()["detail"]
    # Sin memorias: obras habilitadas directamente (V10)
    arbol = await etapas(client, exp_id)
    assert "registrar_informe_usuario" in arbol["obras"]["acciones_disponibles"]


async def test_memorias_ciclo_completo(client, rv_permisos, con_decision, db_session):
    stubs = rv_permisos
    exp_id, _ = await con_decision("OTORGADA", True)
    # V10: obras exige memorias aprobadas
    r = await post(client, f"/etapas/{exp_id}/obras", json=radicado(stubs, "2026ER900"), esperado=400)
    assert "V10" in r.json()["detail"]
    await post(client, f"/etapas/{exp_id}/memorias", json=radicado(stubs, "2026ER100"), esperado=201)
    await post(client, f"/etapas/{exp_id}/memorias", json=radicado(stubs, "2026ER101"), esperado=409)
    arbol = await etapas(client, exp_id)
    assert arbol["etapa_actual"] == "memorias"
    assert "seleccionar_tecnico" in arbol["memorias"]["concepto"]["acciones_disponibles"]
    # V11 / V12 antes del concepto
    await post(client, f"/etapas/{exp_id}/requerimientos/memorias/asignarme", esperado=400)
    await post(client, f"/etapas/{exp_id}/memorias/aprobacion/asignarme", esperado=400)
    # Concepto sin visita: NO cumple
    await post(client, f"/etapas/{exp_id}/conceptos/memorias/tecnico", ABOGADO2, {"tecnico_id": TECNICO})
    await post(client, f"/etapas/{exp_id}/conceptos/memorias/version-final", TECNICO,
               {"file_id": stubs.files.registrar(), "fecha_aceptacion": "2026-08-05", "cumple": False}, esperado=409)
    await concepto_firmado(client, stubs, exp_id, "memorias", cumple=False)
    # V12: el último concepto no cumple
    r = await post(client, f"/etapas/{exp_id}/memorias/aprobacion/asignarme", esperado=400)
    assert "V12" in r.json()["detail"]
    # Subsanación antes del requerimiento → 400
    await post(client, f"/etapas/{exp_id}/memorias/subsanacion", json=radicado(stubs, "2026ER102"), esperado=400)
    await acto_completo(client, stubs, f"/etapas/{exp_id}/requerimientos/memorias")
    await post(client, f"/etapas/{exp_id}/memorias/subsanacion", json=radicado(stubs, "2026ER102"), esperado=201)
    await post(client, f"/etapas/{exp_id}/memorias/subsanacion", json=radicado(stubs, "2026ER103"), esperado=409)
    await post(client, f"/etapas/{exp_id}/conceptos/subsanacion/tecnico", json={"tecnico_id": TECNICO})
    await concepto_firmado(client, stubs, exp_id, "subsanacion", cumple=True)
    arbol = await etapas(client, exp_id)
    assert "asignarme" in arbol["memorias"]["aprobacion"]["acciones_disponibles"]
    data = await acto_completo(client, stubs, f"/etapas/{exp_id}/memorias/aprobacion")
    m = await db_session.scalar(select(MemoriasCalculo).where(MemoriasCalculo.expediente_id == exp_id))
    assert m.acto_admin_id == data["acto_id"] and m.requerimiento_id and m.subsanacion_id
    arbol = await etapas(client, exp_id)
    mem = arbol["memorias"]
    assert mem["aprobacion"]["acto"]["tipo_acto"] == "APRUEBA_MEMORIAS"
    assert mem["requerimiento"]["acto"]["tipo_acto"] == "REQUERIMIENTO"
    assert mem["subsanacion"]["datos"]["radicado"] == "2026ER102"
    assert mem["subsanacion"]["concepto"]["datos"]["cumple"] is True
    # Ahora sí V10
    assert "registrar_informe_usuario" in arbol["obras"]["acciones_disponibles"]


async def test_obras_ciclo_completo(client, rv_permisos, con_decision, db_session):
    stubs = rv_permisos
    exp_id, _ = await con_decision("OTORGADA", False)
    await post(client, f"/etapas/{exp_id}/obras", json=radicado(stubs, "2026ER900"), esperado=201)
    await post(client, f"/etapas/{exp_id}/conceptos/obras/tecnico", json={"tecnico_id": TECNICO})
    # El técnico diligencia la fecha de visita (obligatoria en obras)
    arbol = await etapas(client, exp_id)
    await aprobar_para_firma(client, arbol["obras"]["concepto"]["proceso"]["proceso_id"], TECNICO)
    await post(client, f"/etapas/{exp_id}/conceptos/obras/version-final", TECNICO,
               {"file_id": stubs.files.registrar(), "fecha_aceptacion": "2026-09-01", "cumple": False}, esperado=400)
    await post(client, f"/etapas/{exp_id}/conceptos/obras/version-final", TECNICO,
               {"file_id": stubs.files.registrar(), "fecha_aceptacion": "2026-09-01", "cumple": False,
                "fecha_visita_tecnica": "2026-08-28"})
    await post(client, f"/etapas/{exp_id}/obras/aprobacion/asignarme", esperado=400)  # V12
    await post(client, f"/etapas/{exp_id}/obras/nuevo-informe", json=radicado(stubs, "2026ER901"), esperado=400)
    await acto_completo(client, stubs, f"/etapas/{exp_id}/requerimientos/obras")
    await post(client, f"/etapas/{exp_id}/conceptos/obras_segundo/tecnico", json={"tecnico_id": TECNICO}, esperado=400)
    await post(client, f"/etapas/{exp_id}/obras/nuevo-informe", json=radicado(stubs, "2026ER901"), esperado=201)
    await post(client, f"/etapas/{exp_id}/conceptos/obras_segundo/tecnico", json={"tecnico_id": TECNICO})
    await concepto_firmado(client, stubs, exp_id, "obras_segundo", cumple=True, fecha_visita_tecnica="2026-09-10")
    data = await acto_completo(client, stubs, f"/etapas/{exp_id}/obras/aprobacion")
    o = await db_session.scalar(select(ReciboSatisfaccionObras).where(ReciboSatisfaccionObras.expediente_id == exp_id))
    assert o.acto_admin_id == data["acto_id"] and o.concepto_tecnico_segundo_id and o.nuevo_informe_usuario_id
    arbol = await etapas(client, exp_id)
    ob = arbol["obras"]
    assert arbol["etapa_actual"] == "obras"
    assert ob["datos"]["radicado"] == "2026ER900" and ob["nuevo_informe"]["datos"]["radicado"] == "2026ER901"
    assert ob["concepto_segundo"]["datos"]["fecha_visita_tecnica"] == "2026-09-10"
    assert ob["aprobacion"]["acto"]["tipo_acto"] == "APRUEBA_OBRAS"


async def test_obras_v10_decision_negada(client, rv_permisos, con_decision):
    stubs = rv_permisos
    exp_id, _ = await con_decision("NEGADA", None)
    r = await post(client, f"/etapas/{exp_id}/obras", json=radicado(stubs, "2026ER900"), esperado=400)
    assert "V10" in r.json()["detail"]

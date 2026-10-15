"""Ayudas de los tests de etapas (agente C).

Conducen el flujo real por HTTP: asignarse → subir versión (B) → revisiones de
la cadena (B) → "Cargar versión final" (C). Se importan con
``from tests.fixtures_etapas import *`` (incluye ``tests.fixtures_revision``).
"""
import itertools

import pytest_asyncio

from db.models import TipoVinculo
from services.revision_documentos import CADENAS
from tests.fixtures_revision import *  # noqa: F401,F403
from tests.fixtures_revision import (
    ABOGADO, ASESORA, JURIDICO, LIDER_TECNICO, PROYECTO, SIG, TECNICO, headers, revisar, subir,
)
from core.permission import Permission

SOLICITANTE = 501
TERCERO_P = 502

REVISOR_POR_PERMISO = {
    Permission.LIDER_JURIDICO: JURIDICO,
    Permission.LIDER_PROYECTO: PROYECTO,
    Permission.ASESORA_SUBDIRECCION: ASESORA,
    Permission.LIDER_TECNICO: LIDER_TECNICO,
    Permission.SIG: SIG,
}

_numerados = itertools.count(1)


def numerado() -> str:
    return f"{next(_numerados) % 9000 + 1:04d}"


def acto_body(stubs, **extra) -> dict:
    d = {"file_id": stubs.files.registrar(), "clase_acto": "AUTO", "numerado": numerado(), "fecha_numerado": "2026-04-01"}
    d.update(extra)
    return d


async def aprobar_para_firma(client, proceso_id: int, encargado: int) -> None:
    """Sube una versión y aprueba todos los pasos de la cadena → aprobado_firma."""
    r = await subir(client, proceso_id, user=encargado)
    assert r.status_code == 200, r.text
    det = (await client.get(f"/revision-documentos/{proceso_id}", headers=headers(encargado))).json()
    for paso in CADENAS[det["tipo_documento"]].pasos:
        for permiso in paso:
            r = await revisar(client, proceso_id, "aprobado", REVISOR_POR_PERMISO[permiso])
            assert r.status_code == 200, r.text
    det = (await client.get(f"/revision-documentos/{proceso_id}", headers=headers(encargado))).json()
    assert det["estado"]["codigo"] == "aprobado_firma", det["estado"]


async def etapas(client, exp_id: int, user: int = ABOGADO) -> dict:
    r = await client.get(f"/etapas/{exp_id}", headers=headers(user))
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def post(client, url: str, user: int = ABOGADO, json=None, esperado: int | None = 200):
    r = await client.post(url, json=json, headers=headers(user))
    if esperado is not None:
        assert r.status_code == esperado, f"{url}: {r.status_code} {r.text}"
    return r


async def put(client, url: str, user: int = ABOGADO, json=None, esperado: int | None = 200):
    r = await client.put(url, json=json, headers=headers(user))
    if esperado is not None:
        assert r.status_code == esperado, f"{url}: {r.status_code} {r.text}"
    return r


async def acto_completo(client, stubs, base_url: str, user: int = ABOGADO, **extra) -> dict:
    """asignarme → revisión completa → version-final. ``base_url`` sin la acción final."""
    r = await post(client, f"{base_url}/asignarme", user)
    await aprobar_para_firma(client, r.json()["data"]["proceso_id"], user)
    return (await post(client, f"{base_url}/version-final", user, acto_body(stubs, **extra))).json()["data"]


async def admite_firmado(client, stubs, exp_id: int, tecnico: int = TECNICO) -> dict:
    return await acto_completo(client, stubs, f"/etapas/{exp_id}/admite", tecnico_id=tecnico,
                               fecha_visita_tecnica="2026-05-02")


async def concepto_firmado(client, stubs, exp_id: int, tipo: str, tecnico: int = TECNICO, **datos) -> dict:
    """El concepto ya tiene técnico (proceso creado): revisión + versión final."""
    arbol = await etapas(client, exp_id)
    nodo = buscar_concepto(arbol, tipo)
    await aprobar_para_firma(client, nodo["proceso"]["proceso_id"], tecnico)
    body = {"file_id": stubs.files.registrar(), "fecha_aceptacion": "2026-05-20", **datos}
    return (await post(client, f"/etapas/{exp_id}/conceptos/{tipo}/version-final", tecnico, body)).json()["data"]


def buscar_concepto(arbol: dict, tipo: str) -> dict:
    return {
        "etapa2": lambda a: a["concepto"],
        "adicional": lambda a: a["requerimiento"]["concepto_adicional"],
        "memorias": lambda a: a["memorias"]["concepto"],
        "subsanacion": lambda a: a["memorias"]["subsanacion"]["concepto"],
        "obras": lambda a: a["obras"]["concepto"],
        "obras_segundo": lambda a: a["obras"]["concepto_segundo"],
    }[tipo](arbol)


CAUDALES = {"caudal_fuente": 10.5, "caudal_disponible": 8, "caudal_otorgado": 1.2, "num_usuarios": 3}


async def con_constancia(client, stubs, exp_id: int) -> None:
    arbol = await etapas(client, exp_id)
    await put(client, f"/etapas/{exp_id}/admite/documentos", json={
        "version": arbol["admite"]["version"], "doc_oficio_alcaldia_id": stubs.files.registrar(),
        "doc_fijacion_aviso_id": stubs.files.registrar(),
        "doc_constancia_fijacion_aviso_id": stubs.files.registrar(),
    })


async def notificar(client, stubs, catalogo, exp_id: int, acto_id: int, involucrado_id: int = SOLICITANTE,
                    user: int = ABOGADO) -> None:
    datos = {
        "expediente_id": exp_id, "acto_admin_id": acto_id, "involucrado_id": involucrado_id,
        "numerado": numerado(), "fecha_numerado": "2026-04-02", "fecha_envio_citacion": "2026-04-03",
        "fecha_constancia_citacion": "2026-04-04", "documento_citacion_id": stubs.files.registrar(),
        "notificacion_exitosa": "true", "tipo_notificacion_id": catalogo.tipo_notificacion_ids["PERSONAL"],
        "fecha_notificacion": "2026-04-10", "documento_notificacion_id": stubs.files.registrar(),
    }
    r = await client.post("/actos/notificaciones", data={k: str(v) for k, v in datos.items()}, headers=headers(user))
    assert r.status_code in (200, 201), r.text


@pytest_asyncio.fixture
async def expediente(crear_expediente, vincular, rv_permisos):
    """Expediente con un solicitante y permisos de revisión listos."""
    exp = await crear_expediente()
    await vincular(exp.id, SOLICITANTE)
    return exp


@pytest_asyncio.fixture
async def con_decision(client, rv_permisos, expediente):
    """Fábrica: expediente con auto admite + concepto + constancia + decisión firmada."""
    stubs = rv_permisos

    async def _make(decision: str = "OTORGADA", requiere_memorias: bool | None = True):
        exp_id = expediente.id
        await admite_firmado(client, stubs, exp_id)
        await concepto_firmado(client, stubs, exp_id, "etapa2", **CAUDALES)
        await con_constancia(client, stubs, exp_id)
        extra = {"decision": decision}
        if requiere_memorias is not None:
            extra["requiere_memorias"] = requiere_memorias
        data = await acto_completo(client, stubs, f"/etapas/{exp_id}/decision", **extra)
        return exp_id, data

    return _make


__all__ = [
    "CAUDALES", "SOLICITANTE", "TERCERO_P", "TipoVinculo", "acto_body", "acto_completo", "admite_firmado",
    "aprobar_para_firma", "buscar_concepto", "con_constancia", "con_decision", "concepto_firmado", "etapas",
    "expediente", "notificar", "numerado", "post", "put",
    "ABOGADO", "ABOGADO2", "ASESORA", "DOCX", "EXTRANO", "JURIDICO", "JURIDICO2", "LECTOR", "LIDER_TECNICO",
    "PDF", "PERMISOS_REVISION", "PROYECTO", "SIG", "SUPER_G", "TECNICO", "codigos", "detalle", "headers",
    "revisar", "rv_permisos", "rv_proceso", "subir",
]

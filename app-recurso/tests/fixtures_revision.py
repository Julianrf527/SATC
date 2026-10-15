"""Fixtures de los tests de revisión, Mis informes y actos (agente B).

Se apoyan en ``tests/conftest.py`` (BD, ``client`` con una sesión por petición,
``stubs`` de users/docs/involved, ``crear_expediente``, ``vincular``). Se
importan con ``from tests.fixtures_revision import *``.
"""
import pytest
import pytest_asyncio

from core.permission import Permission
from tests.conftest import gateway_headers

# Usuarios de prueba (no chocan con GESTOR=10.. de conftest)
ABOGADO, ABOGADO2, TECNICO = 30, 31, 32
JURIDICO, JURIDICO2, PROYECTO, ASESORA, LIDER_TECNICO, SIG = 40, 41, 42, 43, 44, 45
LECTOR, SUPER_G, EXTRANO = 50, 51, 99

PERMISOS_REVISION: dict[int, tuple[str, ...]] = {
    ABOGADO: (Permission.MANAGE,),
    ABOGADO2: (Permission.MANAGE,),
    TECNICO: (Permission.TECNICO,),
    JURIDICO: (Permission.LIDER_JURIDICO,),
    JURIDICO2: (Permission.LIDER_JURIDICO,),
    PROYECTO: (Permission.LIDER_PROYECTO,),
    ASESORA: (Permission.ASESORA_SUBDIRECCION,),
    LIDER_TECNICO: (Permission.LIDER_TECNICO,),
    SIG: (Permission.SIG,),
    LECTOR: (Permission.CONSULT,),
    SUPER_G: (Permission.MANAGE, Permission.SUPER_MANAGE),
}

PDF = ("documento.pdf", b"%PDF-1.4 documento", "application/pdf")
DOCX = ("documento.docx", b"PK word", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def headers(user_id: int) -> dict:
    return gateway_headers(user_id)


@pytest.fixture
def rv_permisos(stubs):
    """Da los permisos estándar de ``PERMISOS_REVISION`` y devuelve ``stubs``."""
    for uid, permisos in PERMISOS_REVISION.items():
        stubs.permisos.dar(uid, *permisos)
    return stubs


@pytest_asyncio.fixture
async def rv_proceso(db_session, crear_expediente, rv_permisos):
    """Crea fila de etapa + proceso con ``crear_proceso`` (como lo hará C) y commit.

    ``exp, etapa, proceso = await rv_proceso("DECISION")``."""
    from db.models import ActoAdmite, ConceptoTecnico, Decision
    from services.revision_documentos import Avisos, cadena_de, crear_proceso

    async def _make(tipo_documento: str = "AUTO_ADMITE", encargado: int = ABOGADO, expediente=None):
        exp = expediente or await crear_expediente()
        etapa_tipo = cadena_de(tipo_documento).etapa_tipo
        if etapa_tipo == "acto_admite":
            etapa = ActoAdmite(expediente_id=exp.id, encargado_acto_id=encargado)
        elif etapa_tipo == "decision":
            etapa = Decision(expediente_id=exp.id, encargado_acto_id=encargado)
        elif etapa_tipo == "concepto_tecnico":
            etapa = ConceptoTecnico(expediente_id=exp.id, tecnico_encargado_id=encargado)
        else:  # pragma: no cover
            raise ValueError(etapa_tipo)
        db_session.add(etapa)
        await db_session.flush()
        proceso = await crear_proceso(
            db_session, expediente_id=exp.id, tipo_documento=tipo_documento, etapa_tipo=etapa_tipo,
            etapa_ref_id=etapa.id, encargado_id=encargado, usuario_id=ABOGADO, avisos=Avisos(),
        )
        await db_session.commit()
        return exp, etapa, proceso

    return _make


async def subir(client, pid, archivo=DOCX, user=ABOGADO):
    return await client.post(
        f"/revision-documentos/{pid}/versiones",
        files={"archivo": archivo}, data={"comentario": "versión"}, headers=headers(user),
    )


async def revisar(client, pid, accion, user, comentario="obs", adjunto=None):
    return await client.post(
        f"/revision-documentos/{pid}/revisiones",
        data={"accion": accion, "comentario": comentario},
        files={"adjunto": adjunto} if adjunto else None,
        headers=headers(user),
    )


async def detalle(client, pid, user):
    resp = await client.get(f"/revision-documentos/{pid}", headers=headers(user))
    assert resp.status_code == 200, resp.text
    return resp.json()


def codigos(det: dict) -> list[str]:
    return [a["codigo"] for a in det["acciones_disponibles"]]


__all__ = [
    "ABOGADO", "ABOGADO2", "ASESORA", "DOCX", "EXTRANO", "JURIDICO", "JURIDICO2", "LECTOR",
    "LIDER_TECNICO", "PDF", "PERMISOS_REVISION", "PROYECTO", "SIG", "SUPER_G", "TECNICO",
    "codigos", "detalle", "headers", "revisar", "rv_permisos", "rv_proceso", "subir",
]

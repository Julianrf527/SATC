"""Eliminación de la práctica de pruebas del recurso de reposición.

Ocurre cuando se cambia «¿Requiere práctica de pruebas?» de Sí a No con la
práctica ya iniciada (auto de pruebas asignado o cargado) pero SIN concepto
técnico de pruebas: con el concepto el cambio se bloquea
(``validaciones.motivo_cambio_requiere_pruebas``). Se borra:

- la fila ``practica_pruebas``;
- el auto de pruebas con su comunicación (cascada), si estaba cargado;
- los documentos anexos de la práctica;
- su proceso de revisión (versiones, revisiones, auditoría: cascada en BD).

Devuelve la ``Liberacion`` para app-docs DESPUÉS del commit
(``liberar_archivos``): usos de cada fila borrada y ``file_ids`` de las
versiones/adjuntos de revisión. No hace commit.
"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ActoAdministrativo, DocumentoAnexo, PracticaPruebas
from db.models.documento_proceso import DocumentoProceso, DocumentoProcesoRevision, DocumentoProcesoVersion
from services.archivos_entidades import Liberacion
from services.expediente_documentos import _Colector


async def eliminar_practica_pruebas(db: AsyncSession, pruebas: PracticaPruebas) -> tuple[dict, Liberacion]:
    """Borra ``pruebas`` (sin concepto) y lo que cuelga de ella.

    Devuelve ``(resumen para auditoría, Liberacion)``."""
    if pruebas.concepto_tecnico_id:
        raise ValueError("La práctica de pruebas con concepto técnico no se elimina")
    acto_id = pruebas.acto_admin_id

    colector = _Colector(db)
    await colector.practica_pruebas(pruebas)
    archivos = Liberacion(usos=list(colector.usos))

    procesos = list((await db.execute(select(DocumentoProceso.id).where(
        DocumentoProceso.etapa_tipo == "practica_pruebas", DocumentoProceso.etapa_ref_id == pruebas.id,
    ))).scalars().all())
    if procesos:
        archivos.file_ids += [f for f in (await db.execute(
            select(DocumentoProcesoVersion.file_id).where(DocumentoProcesoVersion.proceso_id.in_(procesos))
        )).scalars().all() if f]
        archivos.file_ids += [f for f in (await db.execute(
            select(DocumentoProcesoRevision.adjunto_file_id).where(DocumentoProcesoRevision.proceso_id.in_(procesos))
        )).scalars().all() if f]
        await db.execute(delete(DocumentoProceso).where(DocumentoProceso.id.in_(procesos)))
    await db.execute(delete(DocumentoAnexo).where(
        DocumentoAnexo.etapa_tipo == "practica_pruebas", DocumentoAnexo.etapa_ref_id == pruebas.id,
    ))

    resumen = {
        "practica_pruebas_id": pruebas.id,
        "acto_id": acto_id,
        "procesos_revision": procesos,
        "archivos_liberados": len(archivos),
    }
    # La práctica referencia al acto (RESTRICT): se borra primero.
    await db.delete(pruebas)
    await db.flush()
    if acto_id:
        acto = await db.get(ActoAdministrativo, acto_id)
        if acto is not None:
            resumen["acto_numerado"] = acto.numerado
            await db.delete(acto)  # comunicación en cascada
    await db.flush()
    return resumen, archivos

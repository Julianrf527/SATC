"""Eliminación de la etapa de requerimiento (etapa 3) — solo super gestión.

Ocurre cuando super gestión cambia la acción del concepto de la etapa 2 a
«Decide» con el requerimiento ya creado: la etapa deja de corresponder al
proceso y se borra entera (ver ``validaciones.aviso_eliminar_requerimiento``):

- la fila ``requerimiento``;
- su acto administrativo con la comunicación y las notificaciones (cascada);
- el concepto técnico adicional;
- los documentos anexos de ambos;
- sus procesos de revisión (versiones, revisiones, auditoría: cascada en BD).

Los archivos dejan de usarse: se devuelven los ``file_id`` a descontar en
app-docs DESPUÉS del commit (``liberar_archivos``). Cada referencia se
descuenta una vez (cada una sumó un uso al registrarse). No hace commit.
"""
from __future__ import annotations

from sqlalchemy import delete, or_, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ActoAdministrativo, ConceptoTecnico, DocumentoAnexo, Requerimiento
from db.models.documento_proceso import DocumentoProceso, DocumentoProcesoRevision, DocumentoProcesoVersion
from services.expediente_documentos import _Colector


async def eliminar_requerimiento_etapa3(db: AsyncSession, req: Requerimiento) -> tuple[dict, list[int]]:
    """Borra el requerimiento ``req`` y todo lo que cuelga de él.

    Devuelve ``(resumen para auditoría, file_ids a liberar)``."""
    concepto_id = req.concepto_tecnico_id
    acto_id = req.acto_admin_id

    # Documentos finales (acto, comunicación, notificaciones, respuesta, concepto adicional, anexos).
    colector = _Colector(db)
    await colector.requerimiento(req.id, "Requerimiento")
    archivos = [d["file_id"] for d in colector.documentos]

    # Procesos de revisión del requerimiento y del concepto adicional.
    filtro_etapas = [and_(DocumentoProceso.etapa_tipo == "requerimiento", DocumentoProceso.etapa_ref_id == req.id)]
    if concepto_id:
        filtro_etapas.append(and_(DocumentoProceso.etapa_tipo == "concepto_tecnico",
                                  DocumentoProceso.etapa_ref_id == concepto_id))
    procesos = list((await db.execute(select(DocumentoProceso.id).where(or_(*filtro_etapas)))).scalars().all())
    if procesos:
        archivos += [f for f in (await db.execute(
            select(DocumentoProcesoVersion.file_id).where(DocumentoProcesoVersion.proceso_id.in_(procesos))
        )).scalars().all() if f]
        archivos += [f for f in (await db.execute(
            select(DocumentoProcesoRevision.adjunto_file_id).where(DocumentoProcesoRevision.proceso_id.in_(procesos))
        )).scalars().all() if f]
        await db.execute(delete(DocumentoProceso).where(DocumentoProceso.id.in_(procesos)))

    filtro_anexos = [and_(DocumentoAnexo.etapa_tipo == "requerimiento", DocumentoAnexo.etapa_ref_id == req.id)]
    if concepto_id:
        filtro_anexos.append(and_(DocumentoAnexo.etapa_tipo == "concepto_tecnico",
                                  DocumentoAnexo.etapa_ref_id == concepto_id))
    await db.execute(delete(DocumentoAnexo).where(or_(*filtro_anexos)))

    resumen = {
        "requerimiento_id": req.id,
        "acto_id": acto_id,
        "concepto_adicional_id": concepto_id,
        "radicado_respuesta": req.radicado_oficio_entrada,
        "procesos_revision": procesos,
        "archivos_liberados": len(archivos),
    }

    # El requerimiento referencia al acto (RESTRICT) y al concepto: se borra primero.
    await db.delete(req)
    await db.flush()
    if acto_id:
        acto = await db.get(ActoAdministrativo, acto_id)
        if acto is not None:
            resumen["acto_numerado"] = acto.numerado
            await db.delete(acto)  # comunicación y notificaciones en cascada
    if concepto_id:
        concepto = await db.get(ConceptoTecnico, concepto_id)
        if concepto is not None:
            await db.delete(concepto)
    await db.flush()
    return resumen, archivos

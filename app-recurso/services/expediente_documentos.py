"""Recorrido de TODOS los documentos finales de un expediente, en el orden del
proceso (plan §4), para la descarga unificada (``routes/expediente_descarga.py``).

También expone ``actos_del_expediente`` (ids de ``acto_administrativo`` del
expediente, que no tiene FK directa a expediente) para quien lo necesite.

Orden:
  0. Información base: comprobante de pago.
  1. Auto admite: acto (+ comunicación, citaciones/notificaciones), oficio a la
     Alcaldía, fijación del aviso, constancia de fijación de la Alcaldía, anexos.
     Transversal: actos que reconocen a terceros intervinientes (suelen
     aparecer durante el auto admite), por fecha de vinculación.
  2. Concepto técnico (etapa 2) + anexos.
  3. Requerimiento (etapa 3): acto, oficio de respuesta, concepto adicional, anexos.
  4. Decisión: acto, anexos; recurso de reposición: escrito, acto que lo resuelve.
  5. Memorias de cálculo: planos, concepto, requerimiento, subsanación (planos
     ajustados + concepto), acto que aprueba.
  6. Recibo a satisfacción de obras: informe del usuario, concepto,
     requerimiento, nuevo informe, segundo concepto, acto que aprueba.

Solo entran documentos finales (``doc_*_id`` de las tablas de etapa y actos);
las versiones en proyección/revisión de ``documento_proceso`` no.
Los ``documentos_anexos`` se buscan con ``etapa_tipo`` = nombre de la tabla de
la fila (``acto_admite``, ``concepto_tecnico``, ``requerimiento``, ...).
Un mismo archivo aparece una sola vez (primera aparición).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    ActoAdministrativo,
    ActoAdmite,
    Comunicacion,
    ConceptoTecnico,
    Decision,
    DocumentoAnexo,
    Expediente,
    ExpedienteInvolucrado,
    InformeUsuario,
    MemoriasCalculo,
    Notificacion,
    ReciboSatisfaccionObras,
    RecursoReposicion,
    Requerimiento,
    Subsanacion,
    TipoVinculo,
)


@dataclass
class _Colector:
    db: AsyncSession
    documentos: list[dict] = field(default_factory=list)
    actos: list[int] = field(default_factory=list)
    _vistos: set[int] = field(default_factory=set)

    def doc(self, file_id: int | None, descripcion: str) -> None:
        if file_id and file_id not in self._vistos:
            self._vistos.add(file_id)
            self.documentos.append({"file_id": file_id, "descripcion": descripcion})

    async def acto(self, acto_id: int | None, nombre: str) -> None:
        if not acto_id:
            return
        acto = await self.db.get(ActoAdministrativo, acto_id)
        if acto is None:
            return
        self.actos.append(acto.id)
        self.doc(acto.documento_acto_administrativo_id, f"{nombre} No. {acto.numerado}")
        comunicacion = await self.db.scalar(
            select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto.id)
        )
        if comunicacion:
            self.doc(comunicacion.documento_comunicacion_id, f"Comunicación de {nombre}")
        notificaciones = (await self.db.execute(
            select(Notificacion).where(Notificacion.acto_admin_id == acto.id).order_by(Notificacion.id)
        )).scalars().all()
        for n in notificaciones:
            self.doc(n.documento_citacion_id, f"Citación de {nombre} (involucrado {n.involucrado_id})")
            self.doc(n.documento_notificacion_id, f"Notificación de {nombre} (involucrado {n.involucrado_id})")

    async def anexos(self, etapa_tipo: str, ref_id: int | None, nombre: str) -> None:
        if not ref_id:
            return
        anexos = (await self.db.execute(
            select(DocumentoAnexo)
            .where(DocumentoAnexo.etapa_tipo == etapa_tipo, DocumentoAnexo.etapa_ref_id == ref_id)
            .order_by(DocumentoAnexo.fecha_subida, DocumentoAnexo.id)
        )).scalars().all()
        for a in anexos:
            self.doc(a.documento_anexo_id, f"{nombre} - anexo: {a.nombre}")

    async def concepto(self, concepto_id: int | None, nombre: str) -> None:
        if not concepto_id:
            return
        concepto = await self.db.get(ConceptoTecnico, concepto_id)
        if concepto is None:
            return
        self.doc(concepto.doc_concepto_tecnico_id, nombre)
        await self.anexos("concepto_tecnico", concepto.id, nombre)

    async def requerimiento(self, requerimiento_id: int | None, nombre: str) -> None:
        if not requerimiento_id:
            return
        req = await self.db.get(Requerimiento, requerimiento_id)
        if req is None:
            return
        await self.acto(req.acto_admin_id, nombre)
        self.doc(req.doc_oficio_entrada_id, f"Respuesta al {nombre.lower()}")
        await self.concepto(req.concepto_tecnico_id, f"Concepto técnico adicional ({nombre.lower()})")
        await self.anexos("requerimiento", req.id, nombre)

    async def informe_usuario(self, informe_id: int | None, nombre: str) -> None:
        if not informe_id:
            return
        informe = await self.db.get(InformeUsuario, informe_id)
        if informe:
            self.doc(informe.doc_informe_usuario_id, nombre)
            await self.anexos("informe_usuario", informe.id, nombre)


async def _recorrer(db: AsyncSession, expediente: Expediente) -> _Colector:
    c = _Colector(db)
    exp_id = expediente.id

    # 0. Información base
    c.doc(expediente.doc_comprobante_pago_id, "Comprobante de pago")

    # 1. Auto admite
    admite = await db.scalar(select(ActoAdmite).where(ActoAdmite.expediente_id == exp_id))
    if admite:
        await c.acto(admite.acto_admin_id, "Auto que admite")
        c.doc(admite.doc_oficio_alcaldia_id, "Oficio a la Alcaldía")
        c.doc(admite.doc_fijacion_aviso_id, "Fijación del aviso")
        c.doc(admite.doc_constancia_fijacion_aviso_id, "Constancia de fijación de la Alcaldía")
        await c.anexos("acto_admite", admite.id, "Auto que admite")

    # Transversal: terceros intervinientes
    terceros = (await db.execute(
        select(ExpedienteInvolucrado)
        .where(
            ExpedienteInvolucrado.expediente_id == exp_id,
            ExpedienteInvolucrado.tipo_vinculo == TipoVinculo.TERCERO_INTERVINIENTE,
        )
        .order_by(ExpedienteInvolucrado.fecha_vinculacion, ExpedienteInvolucrado.id)
    )).scalars().all()
    for t in terceros:
        await c.acto(t.acto_admin_id, "Acto que reconoce tercero interviniente")
        await c.anexos("expediente_involucrado", t.id, "Tercero interviniente")

    # 2. Concepto técnico
    concepto_id = await db.scalar(select(ConceptoTecnico.id).where(ConceptoTecnico.expediente_id == exp_id))
    await c.concepto(concepto_id, "Concepto técnico")

    # 3. Requerimiento
    req_id = await db.scalar(select(Requerimiento.id).where(Requerimiento.expediente_id == exp_id))
    await c.requerimiento(req_id, "Requerimiento")

    # 4. Decisión y recurso
    decision = await db.scalar(select(Decision).where(Decision.expediente_id == exp_id))
    if decision:
        await c.acto(decision.acto_admin_id, "Decisión")
        await c.anexos("decision", decision.id, "Decisión")
        recurso = await db.scalar(select(RecursoReposicion).where(RecursoReposicion.decision_id == decision.id))
        if recurso:
            c.doc(recurso.doc_recurso_id, "Recurso de reposición")
            await c.acto(recurso.acto_admin_id, "Acto que resuelve el recurso")
            await c.anexos("recurso_reposicion", recurso.id, "Recurso de reposición")

    # 5. Memorias de cálculo
    memorias = await db.scalar(select(MemoriasCalculo).where(MemoriasCalculo.expediente_id == exp_id))
    if memorias:
        c.doc(memorias.doc_planos_id, "Planos (memorias de cálculo)")
        await c.concepto(memorias.concepto_tecnico_id, "Concepto técnico de memorias")
        await c.requerimiento(memorias.requerimiento_id, "Requerimiento de memorias")
        if memorias.subsanacion_id:
            sub = await db.get(Subsanacion, memorias.subsanacion_id)
            if sub:
                c.doc(sub.doc_planos_ajustados_id, "Planos ajustados (subsanación)")
                await c.concepto(sub.concepto_tecnico_id, "Concepto técnico de la subsanación")
                await c.anexos("subsanacion", sub.id, "Subsanación")
        await c.acto(memorias.acto_admin_id, "Acto que aprueba las memorias")
        await c.anexos("memorias_calculo", memorias.id, "Memorias de cálculo")

    # 6. Recibo a satisfacción de obras
    obras = await db.scalar(
        select(ReciboSatisfaccionObras).where(ReciboSatisfaccionObras.expediente_id == exp_id)
    )
    if obras:
        await c.informe_usuario(obras.informe_usuario_id, "Informe del usuario (obras)")
        await c.concepto(obras.concepto_tecnico_id, "Concepto técnico de obras")
        await c.requerimiento(obras.requerimiento_id, "Requerimiento de obras")
        await c.informe_usuario(obras.nuevo_informe_usuario_id, "Nuevo informe del usuario (obras)")
        await c.concepto(obras.concepto_tecnico_segundo_id, "Segundo concepto técnico de obras")
        await c.acto(obras.acto_admin_id, "Acto que aprueba la obra")
        await c.anexos("recibo_satisfaccion_obras", obras.id, "Recibo de obras")

    return c


async def documentos_del_expediente(db: AsyncSession, expediente: Expediente) -> list[dict]:
    """``[{"file_id", "descripcion"}, ...]`` en el orden del proceso."""
    return (await _recorrer(db, expediente)).documentos


async def actos_del_expediente(db: AsyncSession, expediente: Expediente) -> list[int]:
    """Ids de ``acto_administrativo`` del expediente (todas las etapas y terceros)."""
    return (await _recorrer(db, expediente)).actos

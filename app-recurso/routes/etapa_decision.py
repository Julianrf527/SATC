"""Etapa 4 · Decisión del proceso + recurso de reposición (plan §4-Etapa 4, fase 8).

- ``POST /etapas/{expediente_id}/decision/asignarme`` (V7)
- ``POST /etapas/{expediente_id}/decision/version-final``: acto firmado +
  ``decision`` (OTORGADA/NEGADA/DESISTIDA, una sola vez) + ``requiere_memorias`` (V8)
- ``PUT  /etapas/{expediente_id}/decision/ejecutoria``: fecha de ejecutoria
- ``POST /etapas/{expediente_id}/recurso``: el usuario radica el recurso (V13)
- ``POST /etapas/{expediente_id}/recurso/asignarme``
- ``POST /etapas/{expediente_id}/recurso/version-final``: acto que lo resuelve + ``resultado``

La citación y notificación de cada acto se gestiona en ``/actos/notificaciones`` (B).
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion
from db.deps import get_db_managed
from db.models import Decision, RecursoReposicion, ResultadoRecurso, TipoActo, TipoDecision
from services.concurrencia import MSG_ASIGNADO, actualizar_versionado, bloquear_expediente, integridad_a_409
from services.etapas import (
    ActoFinalIn,
    RadicadoIn,
    asignar_fila_existente,
    auditar,
    cargar_acto_final,
    cargar_estado,
    crear_fila_asignada,
    datos_fila,
    exigir,
    exigir_encargado,
    ok,
    registrar_archivos,
    validar_pdf,
)
from services.revision_documentos import Avisos
from services.validaciones import flujo_ejecutoria, v7_decision, v8_requiere_memorias, v13_recurso

router = APIRouter()
logger = logging.getLogger(__name__)


class DecisionFinalIn(ActoFinalIn):
    decision: TipoDecision
    requiere_memorias: Optional[bool] = Field(
        None, description="Obligatorio si la decisión es OTORGADA: true si exige planos (no solo medidor o llave)",
    )


class EjecutoriaIn(BaseModel):
    version: int = Field(..., ge=1)
    # TODO(negocio): plan §4-Etapa 4 — 10 días hábiles después de notificar si no hay
    # recurso, o cuando queda en firme. No hay calendario de días hábiles/festivos en el
    # sistema: el abogado la diligencia. Si se quiere automática, definir el calendario.
    fecha_ejecutoria: Optional[date] = None


class RecursoFinalIn(ActoFinalIn):
    resultado: ResultadoRecurso


@router.post("/{expediente_id}/decision/asignarme")
async def asignarme_decision(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.decision is not None:
        raise HTTPException(status_code=409, detail=MSG_ASIGNADO)
    exigir(v7_decision(e), usuario)
    avisos = Avisos()
    fila = Decision(expediente_id=exp.id, encargado_acto_id=usuario.user_id)
    proceso = await crear_fila_asignada(
        db, fila, etapa_tipo="decision", tipo_documento="DECISION", expediente_id=exp.id,
        usuario=usuario, avisos=avisos,
    )
    await auditar(db, usuario, exp, "ASIGNAR_DECISION", "Asignación de la decisión", request=request)
    data = {**datos_fila(fila, "encargado_acto_id"), "proceso_id": proceso.id}
    await db.commit()
    await avisos.enviar()
    return ok("Te asignaste la decisión", data)


@router.post("/{expediente_id}/decision/version-final")
async def version_final_decision(
    request: Request, expediente_id: int, body: DecisionFinalIn, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.decision is None:
        raise HTTPException(status_code=400, detail="Primero asígnate la decisión")
    if e.decision.decision is not None:
        raise HTTPException(status_code=409, detail="La decisión ya fue tomada (se toma una sola vez por expediente)")
    if body.decision == TipoDecision.OTORGADA and body.requiere_memorias is None:
        raise HTTPException(status_code=400, detail="Indica si la decisión otorgada requiere memorias de cálculo (planos)")
    exigir(v8_requiere_memorias(body.decision, body.requiere_memorias), usuario)
    avisos = Avisos()
    acto = await cargar_acto_final(
        db, fila=e.decision, etapa_tipo="decision", tipo_acto=TipoActo.DECISION,
        encargado_id=e.decision.encargado_acto_id, datos=body, usuario=usuario, avisos=avisos,
    )
    e.decision.decision = body.decision
    e.decision.requiere_memorias = bool(body.requiere_memorias)
    await db.flush()
    await auditar(db, usuario, exp, "VERSION_FINAL_DECISION", f"Decisión No. {acto.numerado}: {body.decision.value}",
                  {"acto_id": acto.id, "decision": body.decision.value, "requiere_memorias": body.requiere_memorias},
                  request)
    data = {**datos_fila(e.decision, "decision", "requiere_memorias"), "acto_id": acto.id}
    await db.commit()
    await avisos.enviar()
    return ok("Decisión cargada", data)


@router.put("/{expediente_id}/decision/ejecutoria")
async def ejecutoria_decision(
    request: Request, expediente_id: int, body: EjecutoriaIn, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.decision is None:
        raise HTTPException(status_code=404, detail="El expediente no tiene decisión")
    exigir_encargado(e.decision.encargado_acto_id, usuario, permitir_super=True)
    exigir(flujo_ejecutoria(e), usuario)
    nueva = await actualizar_versionado(
        db, Decision, e.decision.id, body.version, {"fecha_ejecutoria": body.fecha_ejecutoria},
    )
    await auditar(db, usuario, exp, "EJECUTORIA_DECISION", "Fecha de ejecutoria de la decisión",
                  {"fecha_ejecutoria": body.fecha_ejecutoria}, request)
    await db.commit()
    return ok("Fecha de ejecutoria registrada",
              {"id": e.decision.id, "version": nueva, "fecha_ejecutoria": body.fecha_ejecutoria})


@router.post("/{expediente_id}/recurso", status_code=201)
async def crear_recurso(
    request: Request, expediente_id: int, body: RadicadoIn, db: AsyncSession = Depends(get_db_managed),
):
    """El usuario radica el recurso dentro de los 10 días hábiles siguientes a
    la notificación (el plazo no se valida: el plan no lo pide). Se crea con
    radicado + PDF; el acto que lo resuelve se asigna después."""
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.decision is None:
        raise HTTPException(status_code=400, detail="Primero debe existir la decisión")
    if e.recurso is not None:
        raise HTTPException(status_code=409, detail="El expediente ya tiene recurso de reposición")
    exigir(v13_recurso(e), usuario)
    await validar_pdf(body.file_id, "Escrito del recurso")
    fila = RecursoReposicion(
        decision_id=e.decision.id, radicado=body.radicado, fecha_radicado=body.fecha_radicado,
        doc_recurso_id=body.file_id,
    )
    async with integridad_a_409(db, "El expediente ya tiene recurso de reposición"):
        db.add(fila)
        await db.flush()
    await registrar_archivos([body.file_id])
    await auditar(db, usuario, exp, "CREAR_RECURSO", f"Recurso de reposición radicado {body.radicado}",
                  body.model_dump(), request)
    data = datos_fila(fila, "radicado", "fecha_radicado", "doc_recurso_id")
    await db.commit()
    return ok("Recurso de reposición registrado", data, status_code=201)


@router.post("/{expediente_id}/recurso/asignarme")
async def asignarme_recurso(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.recurso is None:
        raise HTTPException(status_code=404, detail="El expediente no tiene recurso de reposición")
    if e.recurso.encargado_acto_id is not None:
        raise HTTPException(status_code=409, detail=MSG_ASIGNADO)
    avisos = Avisos()
    proceso = await asignar_fila_existente(
        db, RecursoReposicion, e.recurso, etapa_tipo="recurso_reposicion", tipo_documento="RECURSO",
        expediente_id=exp.id, usuario=usuario, avisos=avisos,
    )
    await auditar(db, usuario, exp, "ASIGNAR_RECURSO", "Asignación del acto que resuelve el recurso", request=request)
    data = {**datos_fila(e.recurso, "encargado_acto_id"), "proceso_id": proceso.id}
    await db.commit()
    await avisos.enviar()
    return ok("Te asignaste el acto que resuelve el recurso", data)


@router.post("/{expediente_id}/recurso/version-final")
async def version_final_recurso(
    request: Request, expediente_id: int, body: RecursoFinalIn, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.recurso is None:
        raise HTTPException(status_code=404, detail="El expediente no tiene recurso de reposición")
    avisos = Avisos()
    acto = await cargar_acto_final(
        db, fila=e.recurso, etapa_tipo="recurso_reposicion", tipo_acto=TipoActo.RECURSO,
        encargado_id=e.recurso.encargado_acto_id, datos=body, usuario=usuario, avisos=avisos,
    )
    e.recurso.resultado = body.resultado
    await db.flush()
    await auditar(db, usuario, exp, "VERSION_FINAL_RECURSO",
                  f"Acto que resuelve el recurso No. {acto.numerado}: {body.resultado.value}",
                  {"acto_id": acto.id, "resultado": body.resultado.value}, request)
    data = {**datos_fila(e.recurso, "resultado"), "acto_id": acto.id}
    await db.commit()
    await avisos.enviar()
    return ok("Acto que resuelve el recurso cargado", data)

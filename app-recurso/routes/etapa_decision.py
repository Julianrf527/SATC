"""Etapa 4 · Decisión del proceso + recurso de reposición (plan §4-Etapa 4).

- ``POST /etapas/{expediente_id}/decision/asignarme`` (V7)
- ``POST /etapas/{expediente_id}/decision/version-final``: acto firmado +
  ``decision`` (OTORGADA/NEGADA/DESISTIDA, una sola vez) + ``requiere_memorias`` (V8)
- ``PUT  /etapas/{expediente_id}/decision/ejecutoria``: fecha de ejecutoria
- ``POST /etapas/{expediente_id}/recurso``: el usuario radica el recurso (V13) y se
  responde «¿Requiere práctica de pruebas?» (``requiere_pruebas``)
- ``PUT  /etapas/{expediente_id}/recurso/requiere-pruebas``: cambia la respuesta
- ``POST /etapas/{expediente_id}/recurso/pruebas/asignarme``: auto que admite y
  decreta práctica de pruebas (solo si ``requiere_pruebas``)
- ``POST /etapas/{expediente_id}/recurso/pruebas/version-final``: auto firmado +
  técnico y fecha de visita → nace el concepto técnico de la práctica de pruebas
- ``POST /etapas/{expediente_id}/recurso/asignarme``
- ``POST /etapas/{expediente_id}/recurso/version-final``: acto que lo resuelve + ``resultado``
  (si requiere pruebas, después del concepto técnico de pruebas firmado)

La citación y notificación de cada acto se gestiona en ``/actos/notificaciones``.
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion
from db.deps import get_db_managed
from db.models import Decision, PracticaPruebas, RecursoReposicion, ResultadoRecurso, TipoDecision
from services.concurrencia import MSG_ASIGNADO, MSG_MODIFICADO, actualizar_versionado, bloquear_expediente, integridad_a_409
from services.eliminar_practica_pruebas import eliminar_practica_pruebas
from services.etapas import (
    MSG_NO_TECNICO,
    ActoFinalIn,
    RadicadoIn,
    asignar_fila_existente,
    auditar,
    cargar_acto_final,
    cargar_estado,
    crear_concepto,
    crear_fila_asignada,
    datos_fila,
    es_tecnico,
    exigir,
    exigir_encargado,
    liberar_archivos,
    ok,
    registrar_archivos,
    validar_pdf,
)
from services.revision_documentos import Avisos
from services.validaciones import (
    MSG_SIN_RECURSO,
    aviso_eliminar_practica_pruebas,
    flujo_auto_pruebas,
    flujo_ejecutoria,
    flujo_resuelve_recurso,
    motivo_cambio_requiere_pruebas,
    v7_decision,
    v8_requiere_memorias,
    v13_recurso,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class DecisionFinalIn(ActoFinalIn):
    decision: TipoDecision
    requiere_memorias: Optional[bool] = Field(
        None, description="Obligatorio si la decisión es OTORGADA: true si exige planos (no solo medidor o llave)",
    )


class EjecutoriaIn(BaseModel):
    version: int = Field(..., ge=1)
    # La diligencia el abogado.
    fecha_ejecutoria: Optional[date] = None


class RecursoFinalIn(ActoFinalIn):
    resultado: ResultadoRecurso


class RecursoIn(RadicadoIn):
    requiere_pruebas: bool = Field(..., description="«¿Requiere práctica de pruebas?»")


class RequierePruebasIn(BaseModel):
    version: int = Field(..., ge=1, description="Versión del recurso")
    requiere_pruebas: bool
    confirmar_eliminar_pruebas: bool = Field(
        False, description="Sí → No con la práctica iniciada: confirma que se elimina")


class AutoPruebasFinalIn(ActoFinalIn):
    """Además del acto: técnico y fecha de visita del concepto de pruebas."""

    tecnico_id: int = Field(..., gt=0, description="id de app-users con recurso_tecnico")
    fecha_visita_tecnica: date


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
        db, fila=e.decision, etapa_tipo="decision",
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
    request: Request, expediente_id: int, body: RecursoIn, db: AsyncSession = Depends(get_db_managed),
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
        doc_recurso_id=body.file_id, requiere_pruebas=body.requiere_pruebas,
    )
    async with integridad_a_409(db, "El expediente ya tiene recurso de reposición"):
        db.add(fila)
        await db.flush()
    await registrar_archivos(fila, [body.file_id], usuario.user_id)
    await auditar(db, usuario, exp, "CREAR_RECURSO", f"Recurso de reposición radicado {body.radicado}",
                  body.model_dump(), request)
    data = datos_fila(fila, "radicado", "fecha_radicado", "doc_recurso_id", "requiere_pruebas")
    await db.commit()
    return ok("Recurso de reposición registrado", data, status_code=201)


@router.put("/{expediente_id}/recurso/requiere-pruebas")
async def requiere_pruebas_recurso(
    request: Request, expediente_id: int, body: RequierePruebasIn, db: AsyncSession = Depends(get_db_managed),
):
    """Cambia «¿Requiere práctica de pruebas?» (cualquier abogado). Sí → No con
    la práctica iniciada la elimina previa confirmación (409 con el aviso);
    con el concepto de pruebas ya creado se bloquea. No → Sí se bloquea si el
    acto que resuelve ya está cargado; su asignación se conserva."""
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.recurso is None:
        raise HTTPException(status_code=404, detail=MSG_SIN_RECURSO)
    if e.recurso.version != body.version:
        raise HTTPException(status_code=409, detail=MSG_MODIFICADO)
    motivo = motivo_cambio_requiere_pruebas(e, body.requiere_pruebas)
    if motivo:
        raise HTTPException(status_code=400, detail=motivo)
    anterior = bool(e.recurso.requiere_pruebas)
    if anterior == body.requiere_pruebas:
        return ok("Sin cambios", datos_fila(e.recurso, "requiere_pruebas"))
    eliminado, archivos = None, None
    if not body.requiere_pruebas and e.pruebas is not None:
        if not body.confirmar_eliminar_pruebas:
            raise HTTPException(status_code=409, detail=aviso_eliminar_practica_pruebas(e.pruebas))
        eliminado, archivos = await eliminar_practica_pruebas(db, e.pruebas)
        e.pruebas = None
    nueva = await actualizar_versionado(
        db, RecursoReposicion, e.recurso.id, body.version, {"requiere_pruebas": body.requiere_pruebas},
    )
    texto = "Sí" if body.requiere_pruebas else "No"
    await auditar(db, usuario, exp, "REQUIERE_PRUEBAS_RECURSO", f"¿Requiere práctica de pruebas?: {texto}",
                  {"anterior": anterior, "requiere_pruebas": body.requiere_pruebas,
                   **({"practica_eliminada": eliminado} if eliminado else {})}, request)
    await db.commit()
    await liberar_archivos(archivos)
    return ok("Práctica de pruebas actualizada",
              {"id": e.recurso.id, "version": nueva, "requiere_pruebas": body.requiere_pruebas,
               "practica_eliminada": eliminado is not None})


@router.post("/{expediente_id}/recurso/pruebas/asignarme")
async def asignarme_auto_pruebas(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    """Cualquier abogado se asigna el auto que admite y decreta práctica de pruebas."""
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.recurso is None:
        raise HTTPException(status_code=404, detail=MSG_SIN_RECURSO)
    if e.pruebas is not None:
        raise HTTPException(status_code=409, detail=MSG_ASIGNADO)
    exigir(flujo_auto_pruebas(e), usuario)
    avisos = Avisos()
    fila = PracticaPruebas(recurso_id=e.recurso.id, encargado_acto_id=usuario.user_id)
    proceso = await crear_fila_asignada(
        db, fila, etapa_tipo="practica_pruebas", tipo_documento="AUTO_PRUEBAS", expediente_id=exp.id,
        usuario=usuario, avisos=avisos,
    )
    await auditar(db, usuario, exp, "ASIGNAR_AUTO_PRUEBAS",
                  "Asignación del auto que admite y decreta práctica de pruebas", request=request)
    data = {**datos_fila(fila, "encargado_acto_id"), "proceso_id": proceso.id}
    await db.commit()
    await avisos.enviar()
    return ok("Te asignaste el auto que admite y decreta práctica de pruebas", data)


@router.post("/{expediente_id}/recurso/pruebas/version-final")
async def version_final_auto_pruebas(
    request: Request, expediente_id: int, body: AutoPruebasFinalIn, db: AsyncSession = Depends(get_db_managed),
):
    """Auto firmado + técnico y fecha de visita: nace el concepto técnico de la
    práctica de pruebas (mismos revisores que el de la etapa 2)."""
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.pruebas is None:
        raise HTTPException(status_code=400, detail="Primero asígnate el auto que admite y decreta práctica de pruebas")
    exigir(flujo_auto_pruebas(e), usuario)
    exigir_encargado(e.pruebas.encargado_acto_id, usuario)
    concepto_previo = e.concepto("pruebas")
    # V3 antes de tocar app-docs.
    if concepto_previo is None and not await es_tecnico(body.tecnico_id):
        raise HTTPException(status_code=400, detail=MSG_NO_TECNICO)
    avisos = Avisos()
    acto = await cargar_acto_final(
        db, fila=e.pruebas, etapa_tipo="practica_pruebas",
        encargado_id=e.pruebas.encargado_acto_id, datos=body, usuario=usuario, avisos=avisos,
    )
    concepto_id = concepto_previo.id if concepto_previo is not None else None
    if concepto_previo is None:
        concepto, _ = await crear_concepto(
            db, tipo="pruebas", tecnico_id=body.tecnico_id, expediente_id=exp.id, usuario=usuario,
            avisos=avisos, padre=e.pruebas, columna="concepto_tecnico_id",
            fecha_visita=body.fecha_visita_tecnica, validar_tecnico=False,
        )
        concepto_id = concepto.id
    await auditar(
        db, usuario, exp, "VERSION_FINAL_AUTO_PRUEBAS",
        f"Auto que admite y decreta práctica de pruebas No. {acto.numerado} cargado",
        {"acto_id": acto.id, "tecnico_id": body.tecnico_id, "fecha_visita_tecnica": body.fecha_visita_tecnica},
        request,
    )
    data = {**datos_fila(e.pruebas), "acto_id": acto.id, "concepto_tecnico_id": concepto_id}
    await db.commit()
    await avisos.enviar()
    return ok("Auto de pruebas cargado; nace el concepto técnico de la práctica de pruebas", data)


@router.post("/{expediente_id}/recurso/asignarme")
async def asignarme_recurso(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.recurso is None:
        raise HTTPException(status_code=404, detail="El expediente no tiene recurso de reposición")
    if e.recurso.encargado_acto_id is not None:
        raise HTTPException(status_code=409, detail=MSG_ASIGNADO)
    exigir(flujo_resuelve_recurso(e), usuario)
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
        raise HTTPException(status_code=404, detail=MSG_SIN_RECURSO)
    exigir(flujo_resuelve_recurso(e), usuario)
    avisos = Avisos()
    acto = await cargar_acto_final(
        db, fila=e.recurso, etapa_tipo="recurso_reposicion",
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

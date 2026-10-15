"""Etapa 5 · Memorias de cálculo (plan §4-Etapa 5, fase 9; V9, V11, V12).

Ciclo: radicado de planos → concepto sin visita (``/conceptos/memorias``) →
si no cumple, requerimiento (``/requerimientos/memorias``) → subsanación →
concepto de la subsanación (``/conceptos/subsanacion``) → acto que aprueba.

- ``POST /etapas/{expediente_id}/memorias``: radicado de los planos (V9)
- ``POST /etapas/{expediente_id}/memorias/subsanacion``: planos ajustados
- ``POST /etapas/{expediente_id}/memorias/aprobacion/asignarme`` (V12)
- ``POST /etapas/{expediente_id}/memorias/aprobacion/version-final``
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion
from db.deps import get_db_managed
from db.models import MemoriasCalculo, Subsanacion, TipoActo
from services.concurrencia import MSG_ASIGNADO, bloquear_expediente, integridad_a_409
from services.etapas import (
    ActoFinalIn,
    RadicadoIn,
    asignar_fila_existente,
    auditar,
    cargar_acto_final,
    cargar_estado,
    datos_fila,
    enlazar_hijo,
    exigir,
    ok,
    registrar_archivos,
    validar_pdf,
)
from services.revision_documentos import Avisos
from services.validaciones import flujo_subsanacion, v9_memorias, v12_aprueba_memorias

router = APIRouter()
logger = logging.getLogger(__name__)

MSG_SIN_MEMORIAS = "Primero debe registrarse el radicado de los planos (memorias de cálculo)"


def msg_radicado(radicado: str) -> str:
    return f"El radicado {radicado} ya está registrado"


@router.post("/{expediente_id}/memorias", status_code=201)
async def registrar_planos(
    request: Request, expediente_id: int, body: RadicadoIn, db: AsyncSession = Depends(get_db_managed),
):
    # TODO(negocio): el plan no dice quién registra los radicados del usuario
    # (planos, subsanación, informes): cualquier usuario con recurso_gestionar.
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.memorias is not None:
        raise HTTPException(status_code=409, detail="El expediente ya tiene memorias de cálculo")
    exigir(v9_memorias(e), usuario)
    await validar_pdf(body.file_id, "Planos")
    fila = MemoriasCalculo(
        expediente_id=exp.id, radicado=body.radicado, fecha_radicado=body.fecha_radicado, doc_planos_id=body.file_id,
    )
    async with integridad_a_409(db, "Ya existe, otra persona lo creó al mismo tiempo o el radicado ya está registrado"):
        db.add(fila)
        await db.flush()
    await registrar_archivos([body.file_id])
    await auditar(db, usuario, exp, "REGISTRAR_PLANOS", f"Radicado de planos {body.radicado}", body.model_dump(), request)
    data = datos_fila(fila, "radicado", "fecha_radicado", "doc_planos_id")
    await db.commit()
    return ok("Radicado de los planos registrado", data, status_code=201)


@router.post("/{expediente_id}/memorias/subsanacion", status_code=201)
async def registrar_subsanacion(
    request: Request, expediente_id: int, body: RadicadoIn, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.memorias is None:
        raise HTTPException(status_code=400, detail=MSG_SIN_MEMORIAS)
    if e.subsanacion is not None:
        raise HTTPException(status_code=409, detail="Las memorias ya tienen subsanación registrada")
    exigir(flujo_subsanacion(e), usuario)
    await validar_pdf(body.file_id, "Planos ajustados")
    fila = Subsanacion(radicado=body.radicado, fecha_radicado=body.fecha_radicado, doc_planos_ajustados_id=body.file_id)
    async with integridad_a_409(db, msg_radicado(body.radicado)):
        db.add(fila)
        await db.flush()
        await enlazar_hijo(db, e.memorias, "subsanacion_id", fila.id)
    await registrar_archivos([body.file_id])
    await auditar(db, usuario, exp, "REGISTRAR_SUBSANACION", f"Subsanación radicado {body.radicado}",
                  body.model_dump(), request)
    data = datos_fila(fila, "radicado", "fecha_radicado", "doc_planos_ajustados_id")
    await db.commit()
    return ok("Subsanación registrada", data, status_code=201)


@router.post("/{expediente_id}/memorias/aprobacion/asignarme")
async def asignarme_aprobacion_memorias(
    request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.memorias is None:
        raise HTTPException(status_code=400, detail=MSG_SIN_MEMORIAS)
    if e.memorias.encargado_acto_id is not None:
        raise HTTPException(status_code=409, detail=MSG_ASIGNADO)
    exigir(v12_aprueba_memorias(e), usuario)
    avisos = Avisos()
    proceso = await asignar_fila_existente(
        db, MemoriasCalculo, e.memorias, etapa_tipo="memorias_calculo", tipo_documento="APRUEBA_MEMORIAS",
        expediente_id=exp.id, usuario=usuario, avisos=avisos,
    )
    await auditar(db, usuario, exp, "ASIGNAR_APRUEBA_MEMORIAS", "Asignación del acto que aprueba las memorias",
                  request=request)
    data = {**datos_fila(e.memorias, "encargado_acto_id"), "proceso_id": proceso.id}
    await db.commit()
    await avisos.enviar()
    return ok("Te asignaste el acto que aprueba las memorias", data)


@router.post("/{expediente_id}/memorias/aprobacion/version-final")
async def version_final_aprobacion_memorias(
    request: Request, expediente_id: int, body: ActoFinalIn, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.memorias is None:
        raise HTTPException(status_code=400, detail=MSG_SIN_MEMORIAS)
    avisos = Avisos()
    acto = await cargar_acto_final(
        db, fila=e.memorias, etapa_tipo="memorias_calculo", tipo_acto=TipoActo.APRUEBA_MEMORIAS,
        encargado_id=e.memorias.encargado_acto_id, datos=body, usuario=usuario, avisos=avisos,
    )
    await auditar(db, usuario, exp, "VERSION_FINAL_APRUEBA_MEM", f"Acto que aprueba las memorias No. {acto.numerado}",
                  {"acto_id": acto.id}, request)
    data = {**datos_fila(e.memorias), "acto_id": acto.id}
    await db.commit()
    await avisos.enviar()
    return ok("Acto que aprueba las memorias cargado", data)

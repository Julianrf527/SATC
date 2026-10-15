"""Requerimientos (plan §4-Etapa 3 y sub-procesos de las etapas 5 y 6; fase 7).

Ámbitos: ``etapa3`` (requerimiento del expediente, V6), ``memorias`` y
``obras`` (sub-procesos, V11: solo si el concepto dice que no cumple).

- ``POST /etapas/{expediente_id}/requerimientos/{ambito}/asignarme``
- ``POST /etapas/{expediente_id}/requerimientos/{ambito}/version-final``
- ``PUT  /etapas/{expediente_id}/requerimientos/etapa3/respuesta``: respuesta
  del usuario (radicado + fecha + PDF del oficio de entrada).

El concepto adicional de la etapa 3 se selecciona con
``POST /etapas/{expediente_id}/conceptos/adicional/tecnico``.
"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion
from db.deps import get_db_managed
from db.models import Requerimiento, TipoActo
from services.concurrencia import MSG_ASIGNADO, actualizar_versionado, bloquear_expediente
from services.etapas import (
    AMBITOS_REQUERIMIENTO,
    ETIQUETAS_REQUERIMIENTO,
    ActoFinalIn,
    auditar,
    cargar_acto_final,
    cargar_estado,
    crear_fila_asignada,
    crear_requerimiento_hijo,
    datos_fila,
    exigir,
    exigir_encargado,
    liberar_archivos,
    ok,
    registrar_archivos,
    validar_pdf,
)
from services.revision_documentos import Avisos
from services.validaciones import CONDICION_REQUERIMIENTO, flujo_respuesta_requerimiento

router = APIRouter()
logger = logging.getLogger(__name__)

PADRE = {"memorias": "memorias", "obras": "obras"}
MSG_PADRE = {
    "memorias": "Primero debe registrarse el radicado de los planos (memorias de cálculo)",
    "obras": "Primero debe registrarse el informe del usuario (recibo de obras)",
}


class RespuestaIn(BaseModel):
    version: int = Field(..., ge=1)
    radicado_oficio_entrada: str = Field(..., min_length=1, max_length=15)
    fecha_oficio_entrada: date
    doc_oficio_entrada_id: int = Field(..., gt=0)


def _ambito(ambito: str) -> str:
    if ambito not in AMBITOS_REQUERIMIENTO:
        raise HTTPException(status_code=404, detail=f"Requerimiento desconocido: {ambito}")
    return ambito


@router.post("/{expediente_id}/requerimientos/{ambito}/asignarme")
async def asignarme_requerimiento(
    request: Request, expediente_id: int, ambito: str, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    ambito = _ambito(ambito)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.requerimiento(ambito) is not None:
        raise HTTPException(status_code=409, detail=MSG_ASIGNADO)
    avisos = Avisos()
    if ambito == "etapa3":
        exigir(CONDICION_REQUERIMIENTO[ambito](e), usuario)
        req = Requerimiento(expediente_id=exp.id, encargado_acto_id=usuario.user_id)
        proceso = await crear_fila_asignada(
            db, req, etapa_tipo="requerimiento", tipo_documento="REQUERIMIENTO", expediente_id=exp.id,
            usuario=usuario, avisos=avisos,
        )
    else:
        padre = getattr(e, PADRE[ambito])
        if padre is None:
            raise HTTPException(status_code=400, detail=MSG_PADRE[ambito])
        exigir(CONDICION_REQUERIMIENTO[ambito](e), usuario)
        req, proceso = await crear_requerimiento_hijo(db, padre, expediente_id=exp.id, usuario=usuario, avisos=avisos)
    await auditar(db, usuario, exp, "ASIGNAR_REQUERIMIENTO", f"Asignación: {ETIQUETAS_REQUERIMIENTO[ambito]}",
                  {"ambito": ambito, "requerimiento_id": req.id}, request)
    data = {**datos_fila(req, "encargado_acto_id"), "proceso_id": proceso.id}
    await db.commit()
    await avisos.enviar()
    return ok(f"Te asignaste: {ETIQUETAS_REQUERIMIENTO[ambito]}", data)


@router.post("/{expediente_id}/requerimientos/{ambito}/version-final")
async def version_final_requerimiento(
    request: Request, expediente_id: int, ambito: str, body: ActoFinalIn,
    db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    ambito = _ambito(ambito)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    req = e.requerimiento(ambito)
    if req is None:
        raise HTTPException(status_code=404, detail="Este requerimiento aún no tiene encargado")
    avisos = Avisos()
    acto = await cargar_acto_final(
        db, fila=req, etapa_tipo="requerimiento", tipo_acto=TipoActo.REQUERIMIENTO,
        encargado_id=req.encargado_acto_id, datos=body, usuario=usuario, avisos=avisos,
    )
    await auditar(db, usuario, exp, "VERSION_FINAL_REQUERIMIENTO",
                  f"{ETIQUETAS_REQUERIMIENTO[ambito]} No. {acto.numerado} cargado", {"acto_id": acto.id}, request)
    data = {**datos_fila(req), "acto_id": acto.id}
    await db.commit()
    await avisos.enviar()
    return ok("Requerimiento cargado", data)


@router.put("/{expediente_id}/requerimientos/etapa3/respuesta")
async def respuesta_requerimiento(
    request: Request, expediente_id: int, body: RespuestaIn, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.req3 is None:
        raise HTTPException(status_code=404, detail="El expediente no tiene requerimiento (etapa 3)")
    exigir_encargado(e.req3.encargado_acto_id, usuario, permitir_super=True)
    exigir(flujo_respuesta_requerimiento(e), usuario)
    await validar_pdf(body.doc_oficio_entrada_id, "Oficio de respuesta del usuario")
    anterior = e.req3.doc_oficio_entrada_id
    valores = body.model_dump(exclude={"version"})
    nueva = await actualizar_versionado(db, Requerimiento, e.req3.id, body.version, valores)
    if body.doc_oficio_entrada_id != anterior:
        await registrar_archivos([body.doc_oficio_entrada_id])
    await auditar(db, usuario, exp, "RESPUESTA_REQUERIMIENTO", "Respuesta del usuario al requerimiento",
                  valores, request)
    await db.commit()
    if anterior and anterior != body.doc_oficio_entrada_id:
        await liberar_archivos([anterior])
    return ok("Respuesta del usuario registrada", {"id": e.req3.id, "version": nueva, **valores})

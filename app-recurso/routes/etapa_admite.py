"""Etapa 1 · Auto que admite (plan §4-Etapa 1, fases 5–6) + lectura del árbol.

Prefijo ``/etapas``:

- ``GET  /etapas/{expediente_id}``: árbol de etapas (mismo contenido que
  ``etapas`` en ``GET /expedientes/{id}``), para recargar solo las etapas.
- ``POST /etapas/{expediente_id}/admite/asignarme``: "Asignarme para
  diligenciar" (crea la fila con el encargado + proceso AUTO_ADMITE).
- ``POST /etapas/{expediente_id}/admite/version-final``: auto firmado y
  numerado + técnico y fecha de visita → acto AUTO_ADMITE y nace la etapa 2.
- ``PUT  /etapas/{expediente_id}/admite/documentos``: oficio a la Alcaldía,
  fijación del aviso y constancia de fijación (nullable, llega después).
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion, requiere_lectura
from db.deps import get_db_managed
from db.models import ActoAdmite, TipoActo
from services.concurrencia import MSG_ASIGNADO, actualizar_versionado, bloquear_expediente
from services.etapas import (
    MSG_NO_TECNICO,
    ActoFinalIn,
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
from services.etapas_lectura import leer_etapas
from services.expediente import cargar_expediente
from services.revision_documentos import Avisos
from services.validaciones import flujo_documentos_admite

router = APIRouter()
logger = logging.getLogger(__name__)


class AdmiteFinalIn(ActoFinalIn):
    """Además del acto: técnico y fecha de visita escritos en el auto (V5)."""

    tecnico_id: int = Field(..., gt=0, description="id de app-users con recurso_tecnico")
    fecha_visita_tecnica: date


class DocumentosAdmiteIn(BaseModel):
    version: int = Field(..., ge=1)
    doc_oficio_alcaldia_id: Optional[int] = Field(None, gt=0)
    doc_fijacion_aviso_id: Optional[int] = Field(None, gt=0)
    doc_constancia_fijacion_aviso_id: Optional[int] = Field(None, gt=0)


CAMPOS_DOCUMENTOS = {
    "doc_oficio_alcaldia_id": "Oficio a la Alcaldía",
    "doc_fijacion_aviso_id": "Fijación del aviso",
    "doc_constancia_fijacion_aviso_id": "Constancia de fijación de la Alcaldía",
}


@router.get("/{expediente_id:int}")
async def obtener_etapas(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    usuario = await requiere_lectura(request)
    expediente = await cargar_expediente(db, expediente_id)
    return {"ok": True, "data": await leer_etapas(db, expediente, usuario)}


@router.post("/{expediente_id}/admite/asignarme")
async def asignarme_admite(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.admite is not None:
        raise HTTPException(status_code=409, detail=MSG_ASIGNADO)
    avisos = Avisos()
    fila = ActoAdmite(expediente_id=exp.id, encargado_acto_id=usuario.user_id)
    proceso = await crear_fila_asignada(
        db, fila, etapa_tipo="acto_admite", tipo_documento="AUTO_ADMITE", expediente_id=exp.id,
        usuario=usuario, avisos=avisos,
    )
    await auditar(db, usuario, exp, "ASIGNAR_AUTO_ADMITE", f"Asignación del auto que admite ({exp.expediente})",
                  request=request)
    data = {**datos_fila(fila, "encargado_acto_id"), "proceso_id": proceso.id}
    await db.commit()
    await avisos.enviar()
    return ok("Te asignaste el auto que admite", data)


@router.post("/{expediente_id}/admite/version-final")
async def version_final_admite(
    request: Request, expediente_id: int, body: AdmiteFinalIn, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.admite is None:
        raise HTTPException(status_code=400, detail="Primero asígnate el auto que admite")
    exigir_encargado(e.admite.encargado_acto_id, usuario)
    # V3 antes de tocar app-docs.
    if e.concepto2 is None and not await es_tecnico(body.tecnico_id):
        raise HTTPException(status_code=400, detail=MSG_NO_TECNICO)
    avisos = Avisos()
    acto = await cargar_acto_final(
        db, fila=e.admite, etapa_tipo="acto_admite", tipo_acto=TipoActo.AUTO_ADMITE,
        encargado_id=e.admite.encargado_acto_id, datos=body, usuario=usuario, avisos=avisos,
    )
    # Nace la etapa 2 (V5) con el técnico y la fecha de visita escritos en el auto.
    concepto_id = e.concepto2.id if e.concepto2 is not None else None
    if e.concepto2 is None:
        concepto, _ = await crear_concepto(
            db, tipo="etapa2", tecnico_id=body.tecnico_id, expediente_id=exp.id, usuario=usuario,
            avisos=avisos, fecha_visita=body.fecha_visita_tecnica, validar_tecnico=False,
        )
        concepto_id = concepto.id
    await auditar(
        db, usuario, exp, "VERSION_FINAL_AUTO_ADMITE", f"Auto que admite No. {acto.numerado} cargado",
        {"acto_id": acto.id, "tecnico_id": body.tecnico_id, "fecha_visita_tecnica": body.fecha_visita_tecnica},
        request,
    )
    data = {**datos_fila(e.admite), "acto_id": acto.id, "concepto_tecnico_id": concepto_id}
    await db.commit()
    await avisos.enviar()
    return ok("Auto que admite cargado; nace el concepto técnico", data)


@router.put("/{expediente_id}/admite/documentos")
async def documentos_admite(
    request: Request, expediente_id: int, body: DocumentosAdmiteIn, db: AsyncSession = Depends(get_db_managed),
):
    """Carga (o reemplaza) los documentos posteriores al auto. Solo los campos
    enviados; bloqueo optimista con ``version`` de la fila ``acto_admite``."""
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.admite is None:
        raise HTTPException(status_code=404, detail="El expediente no tiene auto que admite")
    exigir_encargado(e.admite.encargado_acto_id, usuario, permitir_super=True)
    exigir(flujo_documentos_admite(e), usuario)
    enviados = {k: getattr(body, k) for k in CAMPOS_DOCUMENTOS if getattr(body, k) is not None}
    if not enviados:
        raise HTTPException(status_code=400, detail="Envía al menos un documento")
    for campo, file_id in enviados.items():
        await validar_pdf(file_id, CAMPOS_DOCUMENTOS[campo])
    anteriores = {k: getattr(e.admite, k) for k in enviados}
    nueva = await actualizar_versionado(db, ActoAdmite, e.admite.id, body.version, enviados)
    await registrar_archivos(v for k, v in enviados.items() if v != anteriores[k])
    await auditar(db, usuario, exp, "DOCUMENTOS_AUTO_ADMITE", "Documentos del auto que admite", enviados, request)
    await db.commit()
    await liberar_archivos(v for k, v in anteriores.items() if v and v != enviados[k])
    return ok("Documentos del auto que admite guardados", {"id": e.admite.id, "version": nueva, **enviados})

"""Etapa 6 · Recibo a satisfacción de obras (plan §4-Etapa 6, fase 9; V10–V12).

Ciclo: informe del usuario → concepto con visita (``/conceptos/obras``) → si
no cumple, requerimiento (``/requerimientos/obras``) → nuevo informe →
segundo concepto (``/conceptos/obras_segundo``) → acto que aprueba la obra.

- ``POST /etapas/{expediente_id}/obras``: informe del usuario (V10)
- ``POST /etapas/{expediente_id}/obras/nuevo-informe``
- ``POST /etapas/{expediente_id}/obras/aprobacion/asignarme`` (V12)
- ``POST /etapas/{expediente_id}/obras/aprobacion/version-final``
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion
from db.deps import get_db_managed
from db.models import InformeUsuario, ReciboSatisfaccionObras, TipoActo
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
from services.validaciones import flujo_nuevo_informe, v10_obras, v12_aprueba_obras

router = APIRouter()
logger = logging.getLogger(__name__)

MSG_SIN_OBRAS = "Primero debe registrarse el informe del usuario (recibo de obras)"


@router.post("/{expediente_id}/obras", status_code=201)
async def registrar_informe(
    request: Request, expediente_id: int, body: RadicadoIn, db: AsyncSession = Depends(get_db_managed),
):
    # TODO(negocio): el plan no dice quién registra el informe: cualquier usuario con recurso_gestionar.
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.obras is not None:
        raise HTTPException(status_code=409, detail="El expediente ya tiene recibo de obras")
    exigir(v10_obras(e), usuario)
    await validar_pdf(body.file_id, "Informe del usuario")
    informe = InformeUsuario(radicado=body.radicado, fecha_radicado=body.fecha_radicado,
                             doc_informe_usuario_id=body.file_id)
    async with integridad_a_409(db, "Ya existe, otra persona lo creó al mismo tiempo o el radicado ya está registrado"):
        db.add(informe)
        await db.flush()
        fila = ReciboSatisfaccionObras(expediente_id=exp.id, informe_usuario_id=informe.id)
        db.add(fila)
        await db.flush()
    await registrar_archivos([body.file_id])
    await auditar(db, usuario, exp, "REGISTRAR_INFORME_OBRAS", f"Informe del usuario radicado {body.radicado}",
                  body.model_dump(), request)
    data = {**datos_fila(fila, "informe_usuario_id"), "informe": datos_fila(informe, "radicado", "fecha_radicado")}
    await db.commit()
    return ok("Informe del usuario registrado", data, status_code=201)


@router.post("/{expediente_id}/obras/nuevo-informe", status_code=201)
async def registrar_nuevo_informe(
    request: Request, expediente_id: int, body: RadicadoIn, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.obras is None:
        raise HTTPException(status_code=400, detail=MSG_SIN_OBRAS)
    if e.obras.nuevo_informe_usuario_id is not None:
        raise HTTPException(status_code=409, detail="El recibo de obras ya tiene nuevo informe del usuario")
    exigir(flujo_nuevo_informe(e), usuario)
    await validar_pdf(body.file_id, "Nuevo informe del usuario")
    informe = InformeUsuario(radicado=body.radicado, fecha_radicado=body.fecha_radicado,
                             doc_informe_usuario_id=body.file_id)
    async with integridad_a_409(db, f"El radicado {body.radicado} ya está registrado"):
        db.add(informe)
        await db.flush()
        await enlazar_hijo(db, e.obras, "nuevo_informe_usuario_id", informe.id)
    await registrar_archivos([body.file_id])
    await auditar(db, usuario, exp, "REGISTRAR_NUEVO_INFORME", f"Nuevo informe del usuario radicado {body.radicado}",
                  body.model_dump(), request)
    data = datos_fila(informe, "radicado", "fecha_radicado", "doc_informe_usuario_id")
    await db.commit()
    return ok("Nuevo informe del usuario registrado", data, status_code=201)


@router.post("/{expediente_id}/obras/aprobacion/asignarme")
async def asignarme_aprobacion_obras(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.obras is None:
        raise HTTPException(status_code=400, detail=MSG_SIN_OBRAS)
    if e.obras.encargado_acto_id is not None:
        raise HTTPException(status_code=409, detail=MSG_ASIGNADO)
    exigir(v12_aprueba_obras(e), usuario)
    avisos = Avisos()
    proceso = await asignar_fila_existente(
        db, ReciboSatisfaccionObras, e.obras, etapa_tipo="recibo_satisfaccion_obras", tipo_documento="APRUEBA_OBRAS",
        expediente_id=exp.id, usuario=usuario, avisos=avisos,
    )
    await auditar(db, usuario, exp, "ASIGNAR_APRUEBA_OBRAS", "Asignación del acto que aprueba la obra", request=request)
    data = {**datos_fila(e.obras, "encargado_acto_id"), "proceso_id": proceso.id}
    await db.commit()
    await avisos.enviar()
    return ok("Te asignaste el acto que aprueba la obra", data)


@router.post("/{expediente_id}/obras/aprobacion/version-final")
async def version_final_aprobacion_obras(
    request: Request, expediente_id: int, body: ActoFinalIn, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    if e.obras is None:
        raise HTTPException(status_code=400, detail=MSG_SIN_OBRAS)
    avisos = Avisos()
    acto = await cargar_acto_final(
        db, fila=e.obras, etapa_tipo="recibo_satisfaccion_obras", tipo_acto=TipoActo.APRUEBA_OBRAS,
        encargado_id=e.obras.encargado_acto_id, datos=body, usuario=usuario, avisos=avisos,
    )
    await auditar(db, usuario, exp, "VERSION_FINAL_APRUEBA_OBRAS", f"Acto que aprueba la obra No. {acto.numerado}",
                  {"acto_id": acto.id}, request)
    data = {**datos_fila(e.obras), "acto_id": acto.id}
    await db.commit()
    await avisos.enviar()
    return ok("Acto que aprueba la obra cargado", data)

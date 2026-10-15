"""Transversal · Tercero interviniente (plan §4 transversal, §3 punto 4; fase 6).

Se vincula en ``expediente_involucrado`` con ``tipo_vinculo =
TERCERO_INTERVINIENTE`` (servicio de A) y se le expide un acto que lo reconoce
(``RECONOCE_TERCERO``, enlazado en ``expediente_involucrado.acto_admin_id``).
Sus notificaciones de las actuaciones se registran en ``/actos/notificaciones`` (B).

TODO(negocio): plan §4 — no se sabe si la solicitud del tercero llega con
radicado y documento; hoy solo se vincula la persona.
TODO(negocio): el tercero aparece "en cualquier momento"; no se exige el auto admite (V4).

Prefijo ``/terceros``:

- ``GET    /terceros/expediente/{expediente_id}``
- ``POST   /terceros``  ``{expediente_id, involucrado_id, representante_id?}``
- ``PATCH  /terceros/{vinculo_id}/representante``
- ``DELETE /terceros/{vinculo_id}?version=N``
- ``POST   /terceros/{vinculo_id}/asignarme``
- ``POST   /terceros/{vinculo_id}/version-final``
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion, requiere_lectura
from db.deps import get_db_managed
from db.models import TipoActo, TipoVinculo
from services.concurrencia import MSG_ASIGNADO, bloquear_expediente, integridad_a_409
from services.etapas import (
    ActoFinalIn,
    MSG_SIN_PROCESO,
    auditar,
    cargar_acto_final,
    crear_proceso_etapa,
    ok,
)
from services.etapas_lectura import leer_etapas
from services.expediente import cargar_expediente
from services.expediente_involucrados import (
    cambiar_representante,
    desvincular_involucrado,
    obtener_vinculo,
    serializar_vinculos,
    vincular_involucrado,
)
from services.revision_documentos import Avisos, proceso_vigente

router = APIRouter()
logger = logging.getLogger(__name__)

ETAPA_TIPO = "expediente_involucrado"


class VincularTercero(BaseModel):
    expediente_id: int = Field(..., gt=0)
    involucrado_id: int = Field(..., gt=0, description="id de app-involved")
    representante_id: int | None = Field(None, gt=0, description="Obligatorio si es NIT (V14)")


class EditarRepresentante(BaseModel):
    representante_id: int | None = Field(None, gt=0)
    version: int = Field(..., ge=1)


async def _tercero(db: AsyncSession, vinculo_id: int, *, bloquear: bool = False):
    """(vínculo, expediente). Con ``bloquear`` toma el expediente FOR UPDATE y
    recarga el vínculo después del bloqueo."""
    vinculo = await obtener_vinculo(db, vinculo_id)
    if vinculo.tipo_vinculo != TipoVinculo.TERCERO_INTERVINIENTE:
        raise HTTPException(status_code=400, detail="Este vínculo no es de un tercero interviniente")
    if bloquear:
        exp = await bloquear_expediente(db, vinculo.expediente_id)
        vinculo = await obtener_vinculo(db, vinculo_id)
    else:
        exp = await cargar_expediente(db, vinculo.expediente_id)
    return vinculo, exp


@router.get("/expediente/{expediente_id}")
async def listar_terceros(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    """Terceros con su acto, proceso y acciones (misma forma que ``etapas.terceros``)."""
    usuario = await requiere_lectura(request)
    expediente = await cargar_expediente(db, expediente_id)
    etapas = await leer_etapas(db, expediente, usuario)
    return {"ok": True, "data": etapas["terceros"]}


@router.post("", status_code=201)
async def vincular_tercero(request: Request, body: VincularTercero, db: AsyncSession = Depends(get_db_managed)):
    usuario = await requiere_gestion(request)
    exp = await bloquear_expediente(db, body.expediente_id)
    vinculo = await vincular_involucrado(
        db, expediente=exp, involucrado_id=body.involucrado_id, usuario=usuario,
        tipo_vinculo=TipoVinculo.TERCERO_INTERVINIENTE, representante_id=body.representante_id, request=request,
    )
    vinculo_id = vinculo.id
    await db.commit()
    data = next(
        (v for v in await serializar_vinculos(db, exp.id, TipoVinculo.TERCERO_INTERVINIENTE) if v["id"] == vinculo_id),
        {"id": vinculo_id},
    )
    return ok("Tercero interviniente vinculado", data, status_code=201)


@router.patch("/{vinculo_id}/representante")
async def editar_representante(
    request: Request, vinculo_id: int, body: EditarRepresentante, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    vinculo, exp = await _tercero(db, vinculo_id, bloquear=True)
    nueva = await cambiar_representante(
        db, vinculo=vinculo, expediente=exp, representante_id=body.representante_id, version=body.version,
        usuario=usuario, request=request,
    )
    await db.commit()
    return ok("Representante actualizado", {"id": vinculo_id, "representante_id": body.representante_id,
                                            "version": nueva})


@router.delete("/{vinculo_id}")
async def desvincular_tercero(
    request: Request, vinculo_id: int, version: int = Query(..., ge=1), db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    vinculo, exp = await _tercero(db, vinculo_id, bloquear=True)
    if await proceso_vigente(db, ETAPA_TIPO, vinculo.id) is not None:
        raise HTTPException(
            status_code=409, detail="No se puede desvincular: el acto que lo reconoce está en proyección",
        )
    await desvincular_involucrado(db, vinculo=vinculo, expediente=exp, version=version, usuario=usuario,
                                  request=request)
    await db.commit()
    return ok("Tercero interviniente desvinculado", {"id": vinculo_id})


@router.post("/{vinculo_id}/asignarme")
async def asignarme_reconocimiento(request: Request, vinculo_id: int, db: AsyncSession = Depends(get_db_managed)):
    """"Asignarme" el acto que reconoce al tercero: no hay columna de encargado,
    el encargado es el creador del proceso (B); el índice único parcial del
    proceso vigente resuelve la carrera (409)."""
    usuario = await requiere_gestion(request)
    vinculo, exp = await _tercero(db, vinculo_id, bloquear=True)
    if vinculo.acto_admin_id is not None or await proceso_vigente(db, ETAPA_TIPO, vinculo.id) is not None:
        raise HTTPException(status_code=409, detail=MSG_ASIGNADO)
    avisos = Avisos()
    async with integridad_a_409(db, MSG_ASIGNADO):
        proceso = await crear_proceso_etapa(
            db, expediente_id=exp.id, tipo_documento="RECONOCE_TERCERO", etapa_tipo=ETAPA_TIPO,
            etapa_ref_id=vinculo.id, encargado_id=usuario.user_id, usuario=usuario, avisos=avisos,
        )
    await auditar(db, usuario, exp, "ASIGNAR_RECONOCE_TERCERO",
                  f"Asignación del acto que reconoce al tercero {vinculo.involucrado_id}", request=request)
    data = {"id": vinculo.id, "version": vinculo.version, "encargado_id": usuario.user_id, "proceso_id": proceso.id}
    await db.commit()
    await avisos.enviar()
    return ok("Te asignaste el acto que reconoce al tercero interviniente", data)


@router.post("/{vinculo_id}/version-final")
async def version_final_reconocimiento(
    request: Request, vinculo_id: int, body: ActoFinalIn, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    vinculo, exp = await _tercero(db, vinculo_id, bloquear=True)
    proceso = await proceso_vigente(db, ETAPA_TIPO, vinculo.id)
    if proceso is None and vinculo.acto_admin_id is None:
        raise HTTPException(status_code=409, detail=MSG_SIN_PROCESO)
    avisos = Avisos()
    acto = await cargar_acto_final(
        db, fila=vinculo, etapa_tipo=ETAPA_TIPO, tipo_acto=TipoActo.RECONOCE_TERCERO,
        encargado_id=proceso.creador_id if proceso else None, datos=body, usuario=usuario, avisos=avisos,
    )
    await auditar(db, usuario, exp, "VERSION_FINAL_RECONOCE_TER",
                  f"Acto que reconoce al tercero {vinculo.involucrado_id} No. {acto.numerado}",
                  {"acto_id": acto.id}, request)
    data = {"id": vinculo.id, "version": vinculo.version, "acto_id": acto.id}
    await db.commit()
    await avisos.enviar()
    return ok("Acto que reconoce al tercero interviniente cargado", data)

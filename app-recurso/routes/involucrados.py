"""Solicitantes del expediente (plan §3 "Involucrados", fase 4).

Prefijo en main.py: ``/involucrados``. Se vinculan y desvinculan como los
"posibles infractores" de app-infraction; puede haber varios por expediente.
El tercero interviniente se vincula por ``routes/tercero_interviniente.py``
(agente C) reutilizando ``services/expediente_involucrados.py``.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion, requiere_lectura, tiene_permiso
from core.permission import Permission
from db.deps import get_db_managed
from db.models import Expediente, TipoVinculo
from services.concurrencia import bloquear_expediente
from services.expediente_involucrados import (
    cambiar_representante,
    desvincular_involucrado,
    obtener_vinculo,
    serializar_vinculos,
    vincular_involucrado,
)

router = APIRouter()


class VincularSolicitante(BaseModel):
    expediente_id: int = Field(..., gt=0)
    involucrado_id: int = Field(..., gt=0, description="id de app-involved")
    representante_id: int | None = Field(
        None, gt=0, description="id de app-involved. Obligatorio si el involucrado es NIT (V14)"
    )


class EditarRepresentante(BaseModel):
    representante_id: int | None = Field(None, gt=0)
    version: int = Field(..., ge=1)


async def _expediente(db: AsyncSession, expediente_id: int) -> Expediente:
    expediente = await db.get(Expediente, expediente_id)
    if expediente is None:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    return expediente


async def _vinculo_bloqueado(db: AsyncSession, vinculo_id: int):
    """Bloquea el expediente del vínculo ANTES de validar (como ``/terceros``):
    serializa con ``POST /actos/notificaciones`` y las transiciones de etapa,
    que leen los solicitantes con el expediente bloqueado. Relee el vínculo
    tras el bloqueo para validar sobre el estado vigente."""
    vinculo = await obtener_vinculo(db, vinculo_id)
    await bloquear_expediente(db, vinculo.expediente_id)
    return await obtener_vinculo(db, vinculo_id)


def _solo_solicitante(vinculo) -> None:
    if vinculo.tipo_vinculo != TipoVinculo.SOLICITANTE:
        raise HTTPException(
            status_code=400,
            detail="Este vínculo no es de un solicitante; se gestiona desde tercero interviniente",
        )


@router.get("/expediente/{expediente_id}")
async def listar_involucrados(
    request: Request,
    expediente_id: int,
    tipo_vinculo: TipoVinculo | None = Query(None),
    db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_lectura(request)
    await _expediente(db, expediente_id)
    puede_gestionar = usuario.super_gestion or await tiene_permiso(usuario.user_id, Permission.MANAGE)
    data = await serializar_vinculos(db, expediente_id, tipo_vinculo, puede_gestionar)
    return {"ok": True, "data": data}


@router.post("/vinculos")
async def vincular_solicitante(
    request: Request,
    body: VincularSolicitante,
    db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    expediente = await _expediente(db, body.expediente_id)
    vinculo = await vincular_involucrado(
        db,
        expediente=expediente,
        involucrado_id=body.involucrado_id,
        representante_id=body.representante_id,
        tipo_vinculo=TipoVinculo.SOLICITANTE,
        usuario=usuario,
        request=request,
    )
    await db.commit()
    data = next(v for v in await serializar_vinculos(db, expediente.id, puede_gestionar=True) if v["id"] == vinculo.id)
    return JSONResponse(status_code=201, content={"ok": True, "message": "Solicitante vinculado", "data": data})


@router.patch("/vinculos/{vinculo_id}/representante")
async def editar_representante(
    request: Request,
    vinculo_id: int,
    body: EditarRepresentante,
    db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    vinculo = await _vinculo_bloqueado(db, vinculo_id)
    _solo_solicitante(vinculo)
    expediente = await _expediente(db, vinculo.expediente_id)
    nueva = await cambiar_representante(
        db,
        vinculo=vinculo,
        expediente=expediente,
        representante_id=body.representante_id,
        version=body.version,
        usuario=usuario,
        request=request,
    )
    await db.commit()
    return {
        "ok": True,
        "message": "Representante legal actualizado",
        "data": {"id": vinculo_id, "representante_id": body.representante_id, "version": nueva},
    }


@router.delete("/vinculos/{vinculo_id}")
async def desvincular_solicitante(
    request: Request,
    vinculo_id: int,
    version: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    vinculo = await _vinculo_bloqueado(db, vinculo_id)
    _solo_solicitante(vinculo)
    expediente = await _expediente(db, vinculo.expediente_id)
    await desvincular_involucrado(
        db, vinculo=vinculo, expediente=expediente, version=version, usuario=usuario, request=request
    )
    await db.commit()
    return {"ok": True, "message": "Solicitante desvinculado", "data": {"id": vinculo_id}}

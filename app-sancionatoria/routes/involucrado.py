from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from pydantic import BaseModel, EmailStr

from db.deps import get_db_managed
from db.models.expediente import Expediente
from db.models.notificacion import Notificacion
from db.models.etapa_indagacion import EtapaIndagacion
from db.models.etapa_medida_preventiva import EtapaMedidaPreventiva
from db.models.etapa_inicio_sancionatorio import EtapaInicioSancionatorio
from db.models.etapa_cesacion import EtapaCesacion
from db.models.etapa_formulacion_cargos import EtapaFormulacionCargos
from db.models.etapa_apertura_probatoria import EtapaAperturaProbatoria
from db.models.etapa_cierre_probatoria import EtapaCierreProbatoria
from db.models.etapa_decision_fondo import EtapaDecisionFondo
from db.models.etapa_probatoria_recurso import EtapaProbatoriaRecurso
from db.models.expediente_involucrado import ExpedienteInvolucrado

router = APIRouter()

class InvolucradoUpdate(BaseModel):
    nombre: str
    celular: str
    correo: EmailStr
    digito_verificacion: str | None = None

class InvolucradoExpedienteCreate(BaseModel):
    expediente_id: int
    involucrado_id: int

from utils.verify_token import verify_gateway_token
from services.auditoria import insert_auditoria
from services.involucrado import get_involucrado_by_id, get_involucrados_by_ids
from services.etapas import get_expediente_con_permiso

@router.post("/involved-file")
async def vincular_involucrado_a_expediente(
    request: Request,
    link_data: InvolucradoExpedienteCreate,
    db: AsyncSession = Depends(get_db_managed),
):
    """Vincula un involucrado existente a un expediente."""
    token_data = verify_gateway_token(request)
    usuario_id = token_data["user_id"]

    expediente = await get_expediente_con_permiso(db, link_data.expediente_id, usuario_id)

    stmt_existing = select(ExpedienteInvolucrado).where(
        and_(
            ExpedienteInvolucrado.involucrado_id == link_data.involucrado_id,
            ExpedienteInvolucrado.expediente_id == link_data.expediente_id
        )
    )
    result_existing = await db.execute(stmt_existing)
    existing_link = result_existing.scalar_one_or_none()
    if existing_link:
        raise HTTPException(
            status_code=400,
            detail="El involucrado ya está vinculado a este expediente"
        )

    datos_involucrado = await get_involucrado_by_id(db, link_data.involucrado_id)

    datos_expediente = {
        "id": expediente.id,
        "radicado": expediente.radicado,
    }

    new_link = ExpedienteInvolucrado(
        involucrado_id=link_data.involucrado_id,
        expediente_id=link_data.expediente_id
    )
    db.add(new_link)
    await db.flush()
    await db.refresh(new_link)

    await insert_auditoria(
        db=db,
        tipo_evento="VINCULAR_INVOLUCRADO",
        resultado="EXITOSO",
        usuario_id=int(usuario_id),
        expediente_id=link_data.expediente_id,
        expediente_radicado=datos_expediente.get("radicado"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        detalle=f"Vinculación de involucrado_id={link_data.involucrado_id} a expediente_id={link_data.expediente_id}",
        datos_nuevos={
            "involucrado": datos_involucrado,
            "expediente": datos_expediente
        }
    )
    await db.commit()

    return {
        "ok": True,
        "data": {
            "involucrado_id": link_data.involucrado_id,
            "expediente_id": link_data.expediente_id,
            "message": "Involucrado vinculado exitosamente al expediente"
        }
    }

@router.delete("/involved-file/{involucrado_id}")
async def desvincular_involucrado_a_expediente(
    request: Request,
    involucrado_id: int,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """Desvincula un involucrado de un expediente."""
    token_data = verify_gateway_token(request)
    usuario_id = token_data["user_id"]
    expediente_radicado = (await get_expediente_con_permiso(db, expediente_id, int(usuario_id))).radicado

    acto_ids: set = set()
    for Model in [EtapaIndagacion, EtapaMedidaPreventiva, EtapaInicioSancionatorio,
                  EtapaCesacion, EtapaFormulacionCargos, EtapaAperturaProbatoria,
                  EtapaCierreProbatoria, EtapaProbatoriaRecurso]:
        val = await db.scalar(select(Model.acto_administrativo_id).where(Model.expediente_id == expediente_id))
        if val:
            acto_ids.add(val)
    # EtapaDecisionFondo puede tener 2 actos
    dec = (await db.execute(
        select(EtapaDecisionFondo.acto_administrativo_id, EtapaDecisionFondo.acto_recurso_id)
        .where(EtapaDecisionFondo.expediente_id == expediente_id)
    )).fetchone()
    if dec:
        if dec[0]: acto_ids.add(dec[0])
        if dec[1]: acto_ids.add(dec[1])
    # Filtra por involucrado_id: sin ese filtro se borrarían también notificaciones
    # de otros involucrados vinculados a los mismos actos administrativos
    if acto_ids:
        await db.execute(delete(Notificacion).where(
            Notificacion.acto_administrativo_id.in_(acto_ids),
            Notificacion.involucrado_id == involucrado_id
        ))

    stmt_old = select(ExpedienteInvolucrado).where(
        ExpedienteInvolucrado.expediente_id == expediente_id,
        ExpedienteInvolucrado.involucrado_id == involucrado_id,
    )
    old_link = (await db.execute(stmt_old)).scalar_one_or_none()
    if not old_link:
        raise HTTPException(status_code=404, detail="No existe vinculación entre este involucrado y expediente")

    datos_involucrado = await get_involucrado_by_id(db, old_link.involucrado_id)
    stmt_exp = select(Expediente).where(Expediente.id == old_link.expediente_id)
    exp_obj = (await db.execute(stmt_exp)).scalar_one_or_none()
    datos_expediente = {
        "id": exp_obj.id if exp_obj else old_link.expediente_id,
        "radicado": exp_obj.radicado if exp_obj else None,
        "nombre_expediente": exp_obj.expediente if exp_obj else None,
    }
    datos_anteriores = {
        "involucrado": datos_involucrado,
        "expediente": datos_expediente
    }

    stmt_delete = delete(ExpedienteInvolucrado).where(
        ExpedienteInvolucrado.expediente_id == expediente_id,
        ExpedienteInvolucrado.involucrado_id == involucrado_id,
    )
    result = await db.execute(stmt_delete)
    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="No existe vinculación entre este involucrado y expediente"
        )

    await insert_auditoria(
        db=db,
        tipo_evento="DESVINCULAR_INVOLUCRADO",
        resultado="EXITOSO",
        usuario_id=int(usuario_id),
        expediente_id=expediente_id,
        expediente_radicado=expediente_radicado,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        detalle=f"Desvinculación de involucrado del expediente_id={expediente_id}",
        datos_anteriores=datos_anteriores
    )
    await db.commit()

    return {
        "ok": True,
        "data": {
            "message": "Involucrado desvinculado exitosamente del expediente"
        }
    }

@router.get("/involved-list/{expediente_id}")
async def obtener_involucrados_por_expediente(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """Obtener todos los involucrados de un expediente (consulta centralizada al microservicio involved)"""
    verify_gateway_token(request)

    stmt = select(ExpedienteInvolucrado).where(ExpedienteInvolucrado.expediente_id == expediente_id)
    result = await db.execute(stmt)
    relaciones = result.scalars().all()
    if not relaciones:
        return {
            "ok": True,
            "data": {
                "expediente_id": expediente_id,
                "involucrados": [],
                "total": 0
            }
        }

    involucrado_ids = [rel.involucrado_id for rel in relaciones]

    involucrados_data = await get_involucrados_by_ids(db, involucrado_ids)

    return {
        "ok": True,
        "data": {
            "expediente_id": expediente_id,
            "involucrados": involucrados_data,
            "total": len(involucrados_data)
        }
    }

@router.get("/file-list/{involved_id}")
async def obtener_expedientes_por_involucrado(
    request:Request,
    involved_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """Obtener todos los expedientes donde está involucrada una persona."""
    token_data = verify_gateway_token(request)
    usuario_id = token_data["user_id"]
    stmt = (
        select(ExpedienteInvolucrado).where(ExpedienteInvolucrado.involucrado_id == involved_id)
    )
    result = await db.execute(stmt)
    expedientes_ids = result.scalars().all()

    if not expedientes_ids:
        raise HTTPException(status_code=404, detail="Sin expedientes asociados a este involucrado")

    all_expedientes = []
    for exp_involucrado in expedientes_ids:
        stmt = select(Expediente).where(Expediente.id == exp_involucrado.expediente_id)
        result = await db.execute(stmt)
        expediente = result.scalar_one_or_none()
        if expediente:
            all_expedientes.append({
                "id": expediente.id,
                "radicado": expediente.radicado,
                "nombre_expediente": expediente.expediente,
                "motivo_afectacion": expediente.motivo_afectacion,
                "fecha_creacion": expediente.fecha_creacion.isoformat() if expediente.fecha_creacion else None
            })

    await insert_auditoria(
        db=db,
        tipo_evento="CONSULTA_EXPEDIENTES_INVOLUCRADO",
        resultado="EXITOSO",
        usuario_id=int(usuario_id),
        detalle=f"Consulta de expedientes para involucrado_id={involved_id}",
        datos_nuevos={"involucrado_id": involved_id, "expedientes": [e["id"] for e in all_expedientes]}
    )

    return {
        "ok": True,
        "data": {
            "expedientes": all_expedientes,
            "total": len(all_expedientes)
        }
    }


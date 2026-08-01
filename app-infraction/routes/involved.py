from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from pydantic import BaseModel, EmailStr
import logging
import os


from db.deps import get_db_managed
from db.models.expediente import Expediente
from db.models.acto_administrativo import ActoAdministrativo
from db.models.notificacion import Notificacion
from db.models.expediente_involucrado import ExpedienteInvolucrado
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.medida_preventiva import MedidaPreventiva
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre

router = APIRouter()

#LOGGER 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

#MODELOS PYDANTIC
from .models.involved_models import (
    InvolucradoExpedienteCreate,
)

#FUNCIONES HELPER

from utils.log import insert_log
from utils.verify_token import verify_gateway_token
from services.involved import get_involucrado_by_id, get_involucrados_by_ids


@router.post("/involved-file")
async def vincular_involucrado_a_expediente(
    request: Request,
    link_data: InvolucradoExpedienteCreate,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Vincular un involucrado existente a un expediente.
    Para NITs, el DV es requerido para identificar correctamente al involucrado.
    """
    try:
        token_data = verify_gateway_token(request)
        user_id = token_data["user_id"]

        # Verificar que el expediente existe y el usuario tiene permisos
        stmt_expediente = select(Expediente).where(
            Expediente.id == link_data.expediente_id,
            Expediente.abogado_responsable_id == int(user_id)
        )
        result_expediente = await db.execute(stmt_expediente)
        expediente = result_expediente.scalar_one_or_none()
        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")

        # Verificar si ya existe la relación
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

        # Obtener datos completos del involucrado y expediente para auditoría
        involucrado = await get_involucrado_by_id(db, link_data.involucrado_id)
        if not involucrado:
            raise HTTPException(status_code=404, detail="Involucrado no encontrado")

        if isinstance(involucrado, dict):
            involucrado_data = involucrado
        else:
            involucrado_data = {
                "id": getattr(involucrado, "id", link_data.involucrado_id),
                "numero_documento": getattr(involucrado, "numero_documento", None),
                "digito_verificacion": getattr(involucrado, "digito_verificacion", None),
                "tipo_documento": getattr(involucrado, "tipo_documento", None),
                "nombre": getattr(involucrado, "nombre", None),
                "celular": getattr(involucrado, "celular", None),
                "correo": getattr(involucrado, "correo", None),
            }

        datos_involucrado = {
            "id": involucrado_data.get("id", link_data.involucrado_id),
            "numero_documento": involucrado_data.get("numero_documento"),
            "digito_verificacion": involucrado_data.get("digito_verificacion"),
            "tipo_documento": involucrado_data.get("tipo_documento"),
            "nombre": involucrado_data.get("nombre"),
            "celular": involucrado_data.get("celular"),
            "correo": involucrado_data.get("correo")
        }

        # Datos del expediente
        _fecha_radicado = getattr(expediente, "fecha_radicado", None)
        datos_expediente = {
            "id": expediente.id,
            "radicado": getattr(expediente, "radicado", None),
            "fecha_radicado": _fecha_radicado.isoformat() if _fecha_radicado else None
        }

        # Crear la relación
        new_link = ExpedienteInvolucrado(
            involucrado_id=link_data.involucrado_id,
            expediente_id=link_data.expediente_id
        )
        db.add(new_link)
        await db.flush()
        await db.refresh(new_link)

        # Auditoría con datos completos
        audit_result = await insert_log(
            db=db,
            tipo_evento="VINCULAR_INVOLUCRADO",
            resultado="EXITOSO",
            usuario_id=int(user_id),
            expediente_id=link_data.expediente_id,
            expediente_radicado=getattr(expediente, "radicado", None),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detalle=f"Vinculación de involucrado_id={link_data.involucrado_id} a expediente_id={link_data.expediente_id}",
            datos_nuevos={
                "involucrado": datos_involucrado,
                "expediente": datos_expediente
            }
        )
        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

        await db.commit()

        return {
            "ok": True,
            "data": {
                "involucrado_id": link_data.involucrado_id,
                "expediente_id": link_data.expediente_id,
                "message": "Involucrado vinculado exitosamente al expediente"
            }
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error vinculando involucrado a expediente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/involved-file/{involucrado_id}")
async def desvincular_involucrado_a_expediente(
    request: Request,
    involucrado_id: int,
    expediente_id: int = Query(...),
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Desvincular un involucrado de un expediente.
    Nota: Para NITs con el mismo número pero diferente DV, esto puede causar ambigüedad.
    Considera agregar el DV como parámetro opcional si es necesario.
    """
    try:
        token_data = verify_gateway_token(request)
        user_id = token_data["user_id"]
        stmr = select(Expediente).where(
            Expediente.id == expediente_id,
            Expediente.abogado_responsable_id == int(user_id)
        )
        res = await db.execute(stmr)
        expediente_radicado = res.scalar_one_or_none()

        if not expediente_radicado:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")

        stmt_old = select(ExpedienteInvolucrado).where(
            ExpedienteInvolucrado.expediente_id == expediente_id,
            ExpedienteInvolucrado.involucrado_id == involucrado_id,
        )
        old_link = (await db.execute(stmt_old)).scalar_one_or_none()
        if not old_link:
            raise HTTPException(status_code=404, detail="No existe vinculación entre este involucrado y expediente")

        # Eliminar notificaciones asociadas — recolectar actos administrativos
        # reales del expediente a través de sus etapas (ActoAdministrativo no
        # tiene FK directa a expediente en este servicio).
        actos_ids = []

        resp = await db.scalar(
            select(EtapaRespuesta).where(EtapaRespuesta.expediente_id == expediente_id)
        )
        if resp:
            medida = await db.scalar(
                select(MedidaPreventiva).where(MedidaPreventiva.etapa_respuesta_id == resp.id)
            )
            if medida and medida.acto_administrativo_id:
                actos_ids.append(medida.acto_administrativo_id)

        concepto = await db.scalar(
            select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.expediente_id == expediente_id)
        )
        if concepto and concepto.acto_administrativo_id:
            actos_ids.append(concepto.acto_administrativo_id)

        cierre = await db.scalar(
            select(EtapaCierre).where(EtapaCierre.expediente_id == expediente_id)
        )
        if cierre and cierre.acto_administrativo_id:
            actos_ids.append(cierre.acto_administrativo_id)

        if actos_ids:
            stmt_notif = delete(Notificacion).where(
                and_(
                    Notificacion.acto_administrativo_id.in_(actos_ids),
                    Notificacion.involucrado_id == involucrado_id,
                )
            )
            await db.execute(stmt_notif)

        # Obtener datos anteriores completos para auditoría
        datos_anteriores = None
        if old_link:
            # Obtener datos del involucrado
            involucrado = await get_involucrado_by_id(db, old_link.involucrado_id)
            if isinstance(involucrado, dict):
                involucrado_data = involucrado
            else:
                involucrado_data = {
                    "id": getattr(involucrado, "id", involucrado_id),
                    "numero_documento": getattr(involucrado, "numero_documento", None),
                    "digito_verificacion": getattr(involucrado, "digito_verificacion", None),
                    "tipo_documento": getattr(involucrado, "tipo_documento", None),
                    "nombre": getattr(involucrado, "nombre", None),
                    "celular": getattr(involucrado, "celular", None),
                    "correo": getattr(involucrado, "correo", None),
                }
            datos_involucrado = {
                "id": involucrado_data.get("id", involucrado_id),
                "numero_documento": involucrado_data.get("numero_documento"),
                "digito_verificacion": involucrado_data.get("digito_verificacion"),
                "tipo_documento": involucrado_data.get("tipo_documento"),
                "nombre": involucrado_data.get("nombre"),
                "celular": involucrado_data.get("celular"),
                "correo": involucrado_data.get("correo")
            }

            # Datos del expediente (corregido campo nombre_expediente)
            stmt_exp = select(Expediente).where(Expediente.id == old_link.expediente_id)
            exp_obj = (await db.execute(stmt_exp)).scalar_one_or_none()
            _fecha_radicado = getattr(exp_obj, "fecha_radicado", None) if exp_obj else None
            datos_expediente = {
                "id": exp_obj.id if exp_obj else old_link.expediente_id,
                "radicado": getattr(exp_obj, "radicado", None) if exp_obj else None,
                "fecha_radicado": _fecha_radicado.isoformat() if _fecha_radicado else None
            }
            datos_anteriores = {
                "involucrado": datos_involucrado,
                "expediente": datos_expediente
            }

        # Eliminar la relación involucrado-expediente
        stmt_delete = delete(ExpedienteInvolucrado).where(
            ExpedienteInvolucrado.expediente_id == expediente_id,
            ExpedienteInvolucrado.involucrado_id == involucrado_id,
        )
        result = await db.execute(stmt_delete)
        if result.rowcount == 0:
            await db.rollback()
            raise HTTPException(
                status_code=404,
                detail="No existe vinculación entre este involucrado y expediente"
            )

        # Auditoría con datos reales
        audit_result = await insert_log(
            db=db,
            tipo_evento="DESVINCULAR_INVOLUCRADO",
            resultado="EXITOSO",
            usuario_id=int(user_id),
            expediente_id=expediente_id,
            expediente_radicado=getattr(expediente_radicado, "radicado", None),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detalle=f"Desvinculación de involucrado del expediente_id={expediente_id}",
            datos_anteriores=datos_anteriores
        )
        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

        await db.commit()

        return {
            "ok": True,
            "data": {
                "message": "Involucrado desvinculado exitosamente del expediente"
            }
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error desvinculando involucrado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/involved-list/{expediente_id}")
async def obtener_involucrados_por_expediente(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """Obtener todos los involucrados de un expediente (consulta centralizada al microservicio involved)"""

    try:
        user_id = verify_gateway_token(request)["user_id"]

        # Buscar expediente con involucrados
        stmt = select(ExpedienteInvolucrado.involucrado_id).where(
            ExpedienteInvolucrado.expediente_id == expediente_id
        )
        result = await db.execute(stmt)
        involucrado_ids = [row[0] for row in result.all()]

        if not involucrado_ids:
            return {
                "ok": True,
                "data": {
                    "expediente_id": expediente_id,
                    "involucrados": []
                }
            }

        # Llamar al microservicio involved para obtener la info real
        involved_data = await get_involucrados_by_ids(db, involucrado_ids)

        return {
            "ok": True,
            "data": {
                "expediente_id": expediente_id,
                "involucrados": involved_data
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo involucrados del expediente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/file-list/{involved_id}")
async def obtener_expedientes_por_involucrado(
    request:Request,
    involved_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Obtener todos los expedientes donde está involucrada una persona.

    """
    try:
        user_id = verify_gateway_token(request)["user_id"]
        # Buscar involucrado con expedientes
        stmt = (
            select(ExpedienteInvolucrado.expediente_id).where(ExpedienteInvolucrado.involucrado_id == involved_id)
        )
        expediente_ids = await db.execute(stmt)
        expediente_ids = expediente_ids.all()

        if not expediente_ids:
            raise HTTPException(status_code=404, detail="Sin expedientes asociados a este involucrado")

        all_expedientes = []
        for exp_involucrado in expediente_ids:
            stmt = select(Expediente.id, Expediente.radicado, Expediente.fecha_radicado, Expediente.fecha_creacion).where(Expediente.id == exp_involucrado.expediente_id)
            result = await db.execute(stmt)
            expediente = result.first()
            if expediente:
                all_expedientes.append({
                    "id": expediente.id,
                    "radicado": expediente.radicado,
                    "fecha_radicado": expediente.fecha_radicado.isoformat() if expediente.fecha_radicado else None,
                    "fecha_creacion": expediente.fecha_creacion.isoformat() if expediente.fecha_creacion else None
                })

        return {
            "ok": True,
            "data": {
                "expedientes": all_expedientes,
                "total": len(all_expedientes)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo expedientes del involucrado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

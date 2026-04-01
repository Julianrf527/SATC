from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from pydantic import BaseModel, EmailStr
import logging

#----- DB -----

from db.deps import get_db
from db.models.expediente import Expediente
from db.models.etapa import Etapa
from db.models.acto_admin import ActoAdministrativo
from db.models.notificacion import Notificacion
from db.models.expediente_involucrado import ExpedienteInvolucrado

router = APIRouter()

# ---------- LOGGER ------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Modelos Pydantic
class InvolucradoUpdate(BaseModel):
    nombre: str
    celular: str
    correo: EmailStr
    digito_verificacion: str | None = None

class InvolucradoExpedienteCreate(BaseModel):
    expediente_id: int
    involucrado_id: int

#----------- FUNCIONES ------------

from services.crud_file_operations import insert_auditoria
from utils.verify_gateway_token import verify_gateway_token

# -------- ENDPOINTS ---------

import httpx
import os

# Configuración de URL del microservicio involved
INVOLVED_URL = os.getenv("INVOLVED_SERVICE_URL", "http://app-involved:8000")

@router.post("/involved-file")
async def vincular_involucrado_a_expediente(
    request: Request,
    link_data: InvolucradoExpedienteCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Vincular un involucrado existente a un expediente.
    Para NITs, el DV es requerido para identificar correctamente al involucrado.
    """
    try:
        usuario_id = verify_gateway_token(request)

        # Verificar que el expediente existe y el usuario tiene permisos
        stmt_expediente = select(Expediente).where(
            Expediente.id == link_data.expediente_id,
            Expediente.encargado_id == usuario_id
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
        async with httpx.AsyncClient() as client:
            headers = {"X-Gateway-Token": request.headers.get("X-Gateway-Token", "")}
            resp = await client.post(
                f"{INVOLVED_URL}/bulk",
                json={"ids": [link_data.involucrado_id]},
                headers=headers,
                timeout=10.0
            )
            if resp.status_code == 200:
                inv_data = resp.json().get("data", [])
                datos_involucrado = inv_data[0] if inv_data else {"id": link_data.involucrado_id}
            else:
                datos_involucrado = {"id": link_data.involucrado_id}

        # Datos del expediente (corregido campo nombre_expediente)
        datos_expediente = {
            "id": expediente.id,
            "radicado": getattr(expediente, "radicado", None),
            "nombre_expediente": getattr(expediente, "nombre_expediente", None)
        }

        # Crear la relación
        new_link = ExpedienteInvolucrado(
            involucrado_id=link_data.involucrado_id,
            expediente_id=link_data.expediente_id
        )
        db.add(new_link)
        await db.commit()
        await db.refresh(new_link)

        # Auditoría con datos completos
        await insert_auditoria(
            db=db,
            tipo_evento="VINCULAR_INVOLUCRADO_EXPEDIENTE",
            resultado="EXITOSO",
            usuario_id=int(usuario_id),
            expediente_id=link_data.expediente_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detalle=f"Vinculación de involucrado_id={link_data.involucrado_id} a expediente_id={link_data.expediente_id}",
            datos_nuevos={
                "involucrado": datos_involucrado,
                "expediente": datos_expediente
            }
        )

        return {
            "ok": True,
            "data": {
                "involucrado_id": link_data.involucrado_id,
                "expediente_id": link_data.expediente_id,
                "message": "Involucrado vinculado exitosamente al expediente"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error vinculando involucrado a expediente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/involved-file/{expediente_involucrado_id}")
async def desvincular_involucrado_a_expediente(
    request: Request,
    expediente_id: int,
    expediente_involucrado_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Desvincular un involucrado de un expediente.
    Nota: Para NITs con el mismo número pero diferente DV, esto puede causar ambigüedad.
    Considera agregar el DV como parámetro opcional si es necesario.
    """
    try:
        usuario_id = verify_gateway_token(request)
        stmr = select(Expediente.radicado).where(
            Expediente.id == expediente_id,
            Expediente.encargado_id == int(usuario_id)
        )
        res = await db.execute(stmr)
        expediente_radicado = res.scalar_one_or_none()

        if not expediente_radicado:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")

        # Eliminar notificaciones asociadas (igual que antes)
        stmt = select(Etapa.id).where(Etapa.expediente_id == expediente_id)
        etapas = (await db.execute(stmt)).scalars().all()
        for etapa_id in etapas:
            stmt = select(ActoAdmin.id).where(ActoAdmin.etapa_id == etapa_id)
            acto_admin = (await db.execute(stmt)).scalars().all()
            for ad_id in acto_admin:
                stmt = select(Notificacion.id).where(Notificacion.acto_admin_id == ad_id)
                notificaciones = (await db.execute(stmt)).scalars().all()
                for notif_id in notificaciones:
                    stmt = delete(Notificacion).where(
                        Notificacion.id == notif_id
                    )
                    await db.execute(stmt)


        # Obtener datos anteriores completos para auditoría
        stmt_old = select(ExpedienteInvolucrado).where(ExpedienteInvolucrado.id == expediente_involucrado_id)
        old_link = (await db.execute(stmt_old)).scalar_one_or_none()
        datos_anteriores = None
        if old_link:
            # Obtener datos del involucrado
            async with httpx.AsyncClient() as client:
                headers = {"X-Gateway-Token": request.headers.get("X-Gateway-Token", "")}
                resp = await client.post(
                    f"{INVOLVED_URL}/bulk",
                    json={"ids": [old_link.involucrado_id]},
                    headers=headers,
                    timeout=10.0
                )
                if resp.status_code == 200:
                    inv_data = resp.json().get("data", [])
                    datos_involucrado = inv_data[0] if inv_data else {"id": old_link.involucrado_id}
                else:
                    datos_involucrado = {"id": old_link.involucrado_id}
            # Datos del expediente (corregido campo nombre_expediente)
            stmt_exp = select(Expediente).where(Expediente.id == old_link.expediente_id)
            exp_obj = (await db.execute(stmt_exp)).scalar_one_or_none()
            datos_expediente = {
                "id": exp_obj.id if exp_obj else old_link.expediente_id,
                "radicado": getattr(exp_obj, "radicado", None) if exp_obj else None,
                "nombre_expediente": getattr(exp_obj, "nombre_expediente", None) if exp_obj else None
            }
            datos_anteriores = {
                "involucrado": datos_involucrado,
                "expediente": datos_expediente
            }

        # Eliminar la relación involucrado-expediente
        stmt_delete = delete(ExpedienteInvolucrado).where(
            ExpedienteInvolucrado.id == expediente_involucrado_id,
        )
        result = await db.execute(stmt_delete)
        if result.rowcount == 0:
            await db.rollback()
            raise HTTPException(
                status_code=404,
                detail="No existe vinculación entre este involucrado y expediente"
            )
        await db.commit()

        # Auditoría con datos reales
        await insert_auditoria(
            db=db,
            tipo_evento="DESVINCULAR_INVOLUCRADO_EXPEDIENTE",
            resultado="EXITOSO",
            usuario_id=int(usuario_id),
            expediente_id=expediente_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detalle=f"Desvinculación de involucrado del expediente_id={expediente_id}",
            datos_anteriores=datos_anteriores
        )

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
    db: AsyncSession = Depends(get_db),
):
    """Obtener todos los involucrados de un expediente (consulta centralizada al microservicio involved)"""
    try:
        usuario_id = verify_gateway_token(request)

        # Buscar expediente con involucrados
        stmt = select(ExpedienteInvolucrado).where(ExpedienteInvolucrado.expediente_id == expediente_id)
        result = await db.execute(stmt)
        relaciones = result.scalars().all()
        if not relaciones:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin involucrados")

        involucrado_ids = [rel.involucrado_id for rel in relaciones]

        # Llamar al microservicio involved para obtener la info real
        async with httpx.AsyncClient() as client:
            headers = {"X-Gateway-Token": request.headers.get("X-Gateway-Token", "")}
            response = await client.post(
                f"{INVOLVED_URL}/bulk",
                json={"ids": involucrado_ids},
                headers=headers,
                timeout=10.0
            )
            if response.status_code != 200:
                logger.error(f"Error llamando a involved: {response.text}")
                raise HTTPException(status_code=502, detail="Error consultando microservicio involved")
            data = response.json()
            involucrados_data = data.get("data", [])

        return {
            "ok": True,
            "data": {
                "expediente_id": expediente_id,
                "involucrados": involucrados_data,
                "total": len(involucrados_data)
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
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener todos los expedientes donde está involucrada una persona.

    """
    try:
        usuario_id = verify_gateway_token(request)
        # Buscar involucrado con expedientes
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
                    "nombre_expediente": expediente.nombre_expediente,
                    "motivo_afectacion": expediente.motivo_afectacion,
                    "fecha_creacion": expediente.fecha_creacion.isoformat() if expediente.fecha_creacion else None
                })

        # Auditoría de consulta
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo expedientes del involucrado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


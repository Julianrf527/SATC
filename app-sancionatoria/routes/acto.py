from fastapi import Request, APIRouter, Depends, HTTPException, Form, Body, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,  delete, and_
from datetime import datetime
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional
import logging
import os
import pytz

#----- DB -----

from db.deps import get_db
from db.models.expediente import Expediente
from db.models.acto_admin import ActoAdministrativo
from db.models.etapa import Etapa
from db.models.comunicacion import Comunicacion
from db.models.notificacion import Notificacion
from db.models.tipo_notificacion import TipoNotificacion


router = APIRouter()
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_DAYS = os.getenv("JWT_EXP_DAYS")
ENCARGADO_PERMISSION = os.getenv("ENCARGADO_PERMISSION")
FILE_PERMISSION = os.getenv("FILE_PERMISSION")
LOG_PERMISSION = os.getenv("LOG_PERMISSION")
GATEWAY_URL = os.getenv("API_GATEWAY_URL")


bogota_tz = pytz.timezone("America/Bogota")

BASE_DIR = Path(__file__).resolve().parent.parent.parent 
DOCS_DIR = BASE_DIR / "uploads" / "expedientes"

# ---------- LOGGER ------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- MODELOS ----------
class Decision(BaseModel):
    tipo_sancion_id: int
    detalle: str
    etapa_id: int

#----------- FUNCIONES ------------

from utils.verify_gateway_token import verify_gateway_token, get_user_info_from_headers
from utils.involved_client import get_involucrados_por_radicados
from utils.docs_client import decrement_file_usage, increment_file_usage

from services.crud_file_operations import (
    insert_auditoria,
)

# Acto Admin
@router.post("/acto-admin")
async def crear_acto_admin(
    request: Request,
    expediente_id: int = Form(...),
    radicado_expediente: str = Form(...),
    etapa_id: int = Form(...),
    tipo_acto: str = Form(...),
    numerado: int= Form(...),
    fecha_numerado: str = Form(...),
    nivel_auxiliar: bool = Form(None),
    documento_acto_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()

        if not numerado or len(str(numerado)) > 4:
            raise HTTPException(status_code=400, detail="El numerado debe tener como maximo 4 numeros")

        if tipo_acto not in ["AUTO", "RES"]:
            raise HTTPException(status_code=400, detail="El tipo de acto debe ser AUTO o RES")

        stmt = select(Expediente.encargado_id).where(Expediente.id == expediente_id)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para modificar este expediente")

        if nivel_auxiliar:
            stmt = select(ActoAdministrativo.id).where(ActoAdministrativo.etapa_id == etapa_id, ActoAdministrativo.nivel_auxiliar == nivel_auxiliar)
        else:
            stmt = select(ActoAdministrativo.id).where(ActoAdministrativo.etapa_id == etapa_id, ActoAdministrativo.nivel_auxiliar == False)
        
        if await db.scalar(stmt):
            raise HTTPException(status_code=400, detail="El acto administrativo ya existe")

        # Validación de numerado + fecha_numerado según año
        año_numerado = fecha_numerado_date.year
        
        if año_numerado > 2012:
            # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
            stmt = (
                select(Expediente.id)
                .join(Etapa, Etapa.expediente_id == Expediente.id)
                .join(ActoAdministrativo, ActoAdministrativo.etapa_id == Etapa.id)
                .where(
                    ActoAdministrativo.numerado == numerado,
                    ActoAdministrativo.fecha_numerado == fecha_numerado_date
                )
            )
            radicado_existente = await db.scalar(stmt)
            
            if radicado_existente:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en el expediente {radicado_existente}"
                )
        else:
            # Para años ≤ 2012: solo verificar en OTROS expedientes (permitir duplicados en mismo expediente)
            stmt = (
                select(Expediente.radicado)
                .join(Etapa, Etapa.expediente_id == Expediente.id)
                .join(ActoAdministrativo, ActoAdministrativo.etapa_id == Etapa.id)
                .where(
                    ActoAdministrativo.numerado == numerado,
                    ActoAdministrativo.fecha_numerado == fecha_numerado_date,
                    Expediente.radicado != radicado_expediente
                )
            )
            radicado_expediente_existente = await db.scalar(stmt)
            
            if radicado_expediente_existente:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en el expediente {radicado_expediente_existente}"
                )

        if nivel_auxiliar:
            acto_etapa = await db.scalar(
                select(ActoAdministrativo).where(
                    ActoAdministrativo.etapa_id == etapa_id,
                    ActoAdministrativo.nivel_auxiliar == False
                )
            )
            if not acto_etapa:
                raise HTTPException(
                    status_code=400,
                    detail="Debe crear primero el acto administrativo de etapa antes de crear el acto de recurso"
                )

        nuevo_acto = ActoAdministrativo(
            etapa_id=etapa_id,
            tipo_acto=tipo_acto,
            numerado=numerado,
            fecha_numerado=fecha_numerado_date,
            documento_acto_id=documento_acto_id,
            nivel_auxiliar=nivel_auxiliar
        )

        db.add(nuevo_acto)
        await db.flush()

        await increment_file_usage(GATEWAY_URL, [documento_acto_id])

        datos_nuevos = {
            "id": nuevo_acto.id,
            "etapa_id": etapa_id,
            "tipo_acto": tipo_acto,
            "numerado": numerado,
            "fecha_radicado": fecha_numerado,
            "documento_acto_id": documento_acto_id,
            "fecha_creacion": str(nuevo_acto.fecha_creacion),
            "nivel_auxiliar": nivel_auxiliar
        }

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="acto_admin",
            tipo_operacion="INSERT",
            descripcion=f"Creación de acto administrativo {tipo_acto} {numerado}{nivel_auxiliar}",
            expediente_id=expediente_id,
            expediente_radicado=radicado_expediente,
            id_registro=str(nuevo_acto.id),
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

        await db.commit()
        await db.refresh(nuevo_acto)

        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": nuevo_acto.id,
                    "numerado": nuevo_acto.numerado,
                    "fecha_numerado": str(nuevo_acto.fecha_numerado),
                    "documento_acto_id": nuevo_acto.documento_acto_id,
                    "tipo_acto": nuevo_acto.tipo_acto,
                    "fecha_creacion": str(nuevo_acto.fecha_creacion),
                    "etapa_id": nuevo_acto.etapa_id,
                    "nivel_auxiliar": nuevo_acto.nivel_auxiliar
                }
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error creando acto admin: {e}")
        raise HTTPException(status_code=500, detail="Error al crear acto administrativo")

@router.put("/acto-admin/{acto_id}")
async def actualizar_acto_admin(
    request: Request,
    acto_id: int,
    radicado_expediente: str = Form(...),
    etapa_id: int = Form(...),
    tipo_acto: str = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    nivel_auxiliar: bool = Form(None), 
    documento_acto_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()

        if not numerado or len(str(numerado)) > 4:
            raise HTTPException(status_code=400, detail="El numerado debe tener como maximo 4 numeros")

        if tipo_acto not in ["AUTO", "RES"]:
            raise HTTPException(status_code=400, detail="El tipo de acto debe ser AUTO o RES")

        stmt = select(Expediente.encargado_id, Expediente.id).where(Expediente.radicado == radicado_expediente)
        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        encargado_id, expediente_id = row

        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para modificar este expediente")

        acto_admin = await db.scalar(select(ActoAdministrativo).where(ActoAdministrativo.id == acto_id))
        if not acto_admin:
            raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

        datos_anteriores = {
            "id": acto_admin.id,
            "tipo_acto": acto_admin.tipo_acto,
            "numerado": acto_admin.numerado,
            "fecha_numerado": str(acto_admin.fecha_numerado) if acto_admin.fecha_numerado else None,
            "documento_acto_id": acto_admin.documento_acto_id,
            "etapa_id": acto_admin.etapa_id,
            "fecha_creacion": str(acto_admin.fecha_creacion) if acto_admin.fecha_creacion else None,
            "nivel_auxiliar": acto_admin.nivel_auxiliar
        }

        # Validación de numerado + fecha_numerado según año
        año_numerado = fecha_numerado_date.year
        
        if año_numerado > 2012:
            # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
            stmt = (
                select(Expediente.id)
                .join(Etapa, Etapa.expediente_id == Expediente.id)
                .join(ActoAdministrativo, ActoAdministrativo.etapa_id == Etapa.id)
                .where(
                    ActoAdministrativo.numerado == int(numerado),
                    ActoAdministrativo.fecha_numerado == fecha_numerado_date,
                    ActoAdministrativo.id != acto_id
                )
            )
            radicado_existente = await db.scalar(stmt)

            if radicado_existente:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en el expediente {radicado_existente}"
                )
        else:
            # Para años ≤ 2012: solo verificar en OTROS expedientes (permitir duplicados en mismo expediente)
            stmt = (
                select(Expediente.id)
                .join(Etapa, Etapa.expediente_id == Expediente.id)
                .join(ActoAdministrativo, ActoAdministrativo.etapa_id == Etapa.id)
                .where(
                    ActoAdministrativo.numerado == int(numerado),
                    ActoAdministrativo.fecha_numerado == fecha_numerado_date,
                    ActoAdministrativo.id != acto_id,
                    Expediente.id != radicado_expediente
                )
            )
            radicado_expediente_existente = await db.scalar(stmt)

            if radicado_expediente_existente:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en el expediente {radicado_expediente_existente}"
                )

        if nivel_auxiliar:
            acto_etapa = await db.scalar(
                select(ActoAdministrativo).where(
                    ActoAdministrativo.etapa_id == etapa_id,
                    ActoAdministrativo.nivel_auxiliar == False,
                    ActoAdministrativo.id != acto_id
                )
            )
            if not acto_etapa:
                raise HTTPException(
                    status_code=400,
                    detail="Debe existir un acto administrativo de etapa antes de modificar el acto de recurso"
                )

        # Update with new documento_id if provided
        acto_admin.tipo_acto = tipo_acto
        acto_admin.numerado = int(numerado)
        acto_admin.fecha_numerado = fecha_numerado_date
        if datos_anteriores["documento_acto_id"] and documento_acto_id != datos_anteriores["documento_acto_id"]:
            await decrement_file_usage(GATEWAY_URL, [datos_anteriores["documento_acto_id"]])
            await increment_file_usage(GATEWAY_URL, [documento_acto_id])
            acto_admin.documento_acto_id = documento_acto_id

        acto_admin.nivel_auxiliar = nivel_auxiliar

        await db.flush()

        datos_nuevos = {
            "id": acto_admin.id,
            "tipo_acto": acto_admin.tipo_acto,
            "numerado": acto_admin.numerado,
            "fecha_numerado": str(acto_admin.fecha_numerado),
            "documento_acto_id": acto_admin.documento_acto_id,
            "etapa_id": acto_admin.etapa_id,
            "fecha_creacion": str(acto_admin.fecha_creacion) if acto_admin.fecha_creacion else None,
            "nivel_auxiliar": acto_admin.nivel_auxiliar
        }

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="acto_admin",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de acto administrativo {tipo_acto} {numerado}{nivel_auxiliar}",
            expediente_id=expediente_id,
            expediente_radicado=radicado_expediente,
            id_registro=str(acto_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

        await db.commit()
        await db.refresh(acto_admin)

        stmt = select(Comunicacion).where(Comunicacion.acto_admin_id == acto_admin.id)
        comunicacion = await db.scalar(stmt)

        comunicacion_data = None
        if comunicacion:
            comunicacion_data = {
                "id": comunicacion.id,
                "numerado": comunicacion.numerado,
                "fecha_numerado": str(comunicacion.fecha_numerado),
                "fecha_envio": str(comunicacion.fecha_envio),
                "fecha_creacion": str(comunicacion.fecha_creacion)
            }

        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": acto_admin.id,
                    "numerado": acto_admin.numerado,
                    "fecha_numerado": str(acto_admin.fecha_numerado),
                    "documento_acto_id": acto_admin.documento_acto_id,
                    "tipo_acto": acto_admin.tipo_acto,
                    "fecha_creacion": str(acto_admin.fecha_creacion),
                    "etapa_id": acto_admin.etapa_id,
                    "nivel_auxiliar": acto_admin.nivel_auxiliar,
                    "comunicacion": comunicacion_data
                }
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error al actualizar acto administrativo: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar acto administrativo")

@router.delete("/acto-admin/{acto_id}")
async def delete_acto_admin(
    request: Request,
    acto_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        stmr = (
            select(ActoAdministrativo, Expediente.radicado, Expediente.id)
            .join(Etapa, ActoAdministrativo.etapa_id == Etapa.id)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(ActoAdministrativo.id == acto_id, Expediente.encargado_id == usuario_id)
        )
        res = await db.execute(stmr)
        row = res.first()

        if not row:
            raise HTTPException(status_code=404, detail="Acto administrativo no encontrado o sin permisos")

        acto_admin, radicado_expediente, expediente_id = row

        datos_acto = {
            "id": acto_admin.id,
            "numerado": acto_admin.numerado,
            "fecha_numerado": str(acto_admin.fecha_numerado) if acto_admin.fecha_numerado else None,
            "documento_acto_id": acto_admin.documento_acto_id,
            "tipo_acto": acto_admin.tipo_acto,
            "etapa_id": acto_admin.etapa_id,
            "fecha_creacion": str(acto_admin.fecha_creacion) if acto_admin.fecha_creacion else None
        }

        comunicacion = await db.scalar(
            select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto_id)
        )

        datos_comunicacion = None
        notificaciones_eliminadas = []
        involucrados_notificacion_eliminados = []

        if comunicacion:
            datos_comunicacion = {
                "id": comunicacion.id,
                "numerado": comunicacion.numerado,
                "fecha_numerado": str(comunicacion.fecha_numerado) if comunicacion.fecha_numerado else None,
                "fecha_envio": str(comunicacion.fecha_envio) if comunicacion.fecha_envio else None,
                "acto_administrativo_id": comunicacion.acto_administrativo_id,
                "documento_comunicacion_id": comunicacion.documento_comunicacion_id,
                "fecha_creacion": str(comunicacion.fecha_creacion) if comunicacion.fecha_creacion else None
            }
            await db.execute(delete(Comunicacion).where(Comunicacion.id == comunicacion.id))
        else:
            notificaciones = (await db.execute(
                select(Notificacion).where(Notificacion.acto_administrativo_id == acto_id)
            )).scalars().all()

            for notificacion in notificaciones:
                notificaciones_eliminadas.append({
                    "id": notificacion.id,
                    "tipo_notificacion_id": notificacion.tipo_notificacion_id,
                    "numerado": notificacion.numerado,
                    "fecha_numerado": str(notificacion.fecha_numerado) if notificacion.fecha_numerado else None,
                    "fecha_envio_citacion": str(notificacion.fecha_envio_citacion) if notificacion.fecha_envio_citacion else None,
                    "fecha_constancia_citacion": str(notificacion.fecha_constancia_citacion) if notificacion.fecha_constancia_citacion else None,
                    "notificacion_exitosa": notificacion.notificacion_exitosa,
                    "tipo_notificacion_id": (await db.execute(
                        select(TipoNotificacion.nombre).where(TipoNotificacion.id == notificacion.tipo_notificacion_id)
                    )).scalar() if notificacion.tipo_notificacion_id else None  ,
                    "fecha_notificacion": str(notificacion.fecha_notificacion) if notificacion.fecha_notificacion else None,
                    "fecha_creacion": str(notificacion.fecha_creacion) if notificacion.fecha_creacion else None,

                })

                await db.execute(delete(Notificacion).where(Notificacion.id == notificacion.id))

        await db.execute(delete(ActoAdministrativo).where(ActoAdministrativo.id == acto_id))
        await db.flush()

        descripcion_partes = [
            f"Eliminación de acto administrativo {datos_acto['tipo_acto']} {datos_acto['numerado']}"
        ]
        
        if datos_comunicacion:
            descripcion_partes.append(f"con comunicación (ID: {datos_comunicacion['id']})")
        
        if notificaciones_eliminadas:
            descripcion_partes.append(f"{len(notificaciones_eliminadas)} notificación(es)")
        
        if involucrados_notificacion_eliminados:
            descripcion_partes.append(f"{len(involucrados_notificacion_eliminados)} involucrado(s) en notificaciones")

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="acto_admin",
            tipo_operacion="DELETE",
            descripcion=" - ".join(descripcion_partes),
            expediente_id=expediente_id,
            expediente_radicado=radicado_expediente,
            id_registro=str(acto_id),
            datos_anteriores={
                "acto_admin": datos_acto,
                "comunicacion": datos_comunicacion,
                "notificaciones": notificaciones_eliminadas,
                "involucrados_notificacion": involucrados_notificacion_eliminados,
            },
            datos_nuevos={}
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "message": "Acto administrativo y registros relacionados eliminados correctamente",
                "deleted": {
                    "acto_admin": 1,
                    "comunicacion": 1 if datos_comunicacion else 0,
                    "notificaciones": len(notificaciones_eliminadas),
                    "involucrados_notificacion": len(involucrados_notificacion_eliminados),
                }
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error eliminando acto administrativo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# Comunicacion
@router.post("/comunication")
async def crear_comunicacion(
    request:Request,
    radicado: str = Form(...),
    acto_admin_id: int = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio: str = Form(...),
    documento_comunicacion_id: Optional[int] = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
        fecha_envio_date = datetime.strptime(fecha_envio, "%Y-%m-%d").date()

        # Validar numerado
        if not numerado.isdigit() or len(numerado) != 4:
            raise HTTPException(
                status_code=400,
                detail="El numerado debe tener exactamente 4 dígitos"
            )

        # Validar tipo de archivo
        allowed_types = ["application/pdf", "image/jpeg", "image/png"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Solo se permiten archivos PDF, JPG o PNG"
            )

        # Verificar que el acto admin existe
        stmt = select(ActoAdministrativo).where(ActoAdministrativo.id == acto_admin_id)
        acto_admin = await db.scalar(stmt)
        if not acto_admin:
            raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

        # Verificar permisos
        stmt = select(Expediente.encargado_id, Expediente.id).where(Expediente.radicado == radicado)
        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        encargado_id, expediente_id = row

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para crear comunicación en este expediente"
            )

        # Validación de numerado + fecha_numerado según año
        año_numerado = fecha_numerado_date.year
        
        if año_numerado > 2012:
            # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
            stmt = (
                select(Comunicacion.id)
                .where(
                    Comunicacion.numerado == int(numerado),
                    Comunicacion.fecha_numerado == fecha_numerado_date
                )
            )
            existe_comunicacion = await db.scalar(stmt)
            
            if existe_comunicacion:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra comunicación"
                )

        # Crear comunicación
        nueva_comunicacion = Comunicacion(
            acto_admin_id=acto_admin_id,
            numerado=int(numerado),
            fecha_numerado=fecha_numerado_date,
            fecha_envio=fecha_envio_date,
            fecha_creacion=datetime.now().date(),
            documento_comunicacion_id=documento_comunicacion_id,
        )

        db.add(nueva_comunicacion)
        await db.flush()

        await increment_file_usage(GATEWAY_URL, [documento_comunicacion_id])

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": nueva_comunicacion.id,
            "acto_admin_id": acto_admin_id,
            "numerado": int(numerado),
            "fecha_numerado": fecha_numerado,
            "fecha_envio": fecha_envio,
            "documento_comunicacion_id": documento_comunicacion_id,
            "fecha_creacion": str(nueva_comunicacion.fecha_creacion)
        }

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="comunicacion",
            tipo_operacion="INSERT",
            descripcion=f"Creación de comunicación {numerado} para acto admin {acto_admin_id}",
            expediente_id=expediente_id,
            expediente_radicado=radicado,
            id_registro=str(nueva_comunicacion.id),
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        await db.refresh(nueva_comunicacion)

        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": nueva_comunicacion.id,
                    "numerado": nueva_comunicacion.numerado,
                    "fecha_numerado": str(nueva_comunicacion.fecha_numerado),
                    "fecha_envio": str(nueva_comunicacion.fecha_envio),
                    "fecha_creacion": str(nueva_comunicacion.fecha_creacion),
                    "documento_comunicacion_id": nueva_comunicacion.documento_comunicacion_id,
                },
            },
            status_code=201,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error creando comunicación: {e}")
        raise HTTPException(status_code=500, detail="Error al crear comunicación")

@router.put("/comunication/{comunicacion_id}")
async def actualizar_comunicacion(
    request:Request,
    comunicacion_id: int,
    radicado: str = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio: str = Form(...),
    documento_comunicacion_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
        fecha_envio_date = datetime.strptime(fecha_envio, "%Y-%m-%d").date()

        # Validar numerado
        if not numerado.isdigit() or len(numerado) != 4:
            raise HTTPException(
                status_code=400,
                detail="El numerado debe tener exactamente 4 dígitos"
            )

        # Buscar la comunicación existente
        stmt = select(Comunicacion).where(Comunicacion.id == comunicacion_id)
        comunicacion = await db.scalar(stmt)
        
        if not comunicacion:
            raise HTTPException(status_code=404, detail="Comunicación no encontrada")
        
        # Guardar datos anteriores para auditoría
        datos_anteriores = {
            "id": comunicacion.id,
            "acto_admin_id": comunicacion.acto_admin_id,
            "numerado": comunicacion.numerado,
            "fecha_numerado": str(comunicacion.fecha_numerado) if comunicacion.fecha_numerado else None,
            "fecha_envio": str(comunicacion.fecha_envio) if comunicacion.fecha_envio else None,
            "documento_comunicacion_id": comunicacion.documento_comunicacion_id,
            "fecha_creacion": str(comunicacion.fecha_creacion) if comunicacion.fecha_creacion else None
        }

        # Obtener el acto admin asociado
        stmt = select(ActoAdministrativo).where(ActoAdministrativo.id == comunicacion.acto_admin_id)
        acto_admin = await db.scalar(stmt)

        if not acto_admin:
            raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

        # Verificar permisos
        stmt = select(Expediente.encargado_id, Expediente.id).where(Expediente.radicado == radicado)
        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        encargado_id, expediente_id = row

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para editar esta comunicación"
            )
        
        # Validación de numerado + fecha_numerado según año
        año_numerado = fecha_numerado_date.year
        
        if año_numerado > 2012:
            # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
            stmt = (
                select(Comunicacion.id)
                .where(
                    Comunicacion.numerado == int(numerado),
                    Comunicacion.fecha_numerado == fecha_numerado_date,
                    Comunicacion.id != comunicacion_id
                )
            )
            existe_comunicacion = await db.scalar(stmt)
            
            if existe_comunicacion:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra comunicación"
                )
        # Para años ≤ 2012: se permite duplicados en el mismo expediente, no validar
        
        if datos_anteriores["documento_comunicacion_id"] and documento_comunicacion_id != datos_anteriores["documento_comunicacion_id"]:
            decrement_file_usage(GATEWAY_URL, [datos_anteriores["documento_comunicacion_id"]])
            increment_file_usage(GATEWAY_URL, [documento_comunicacion_id])
            comunicacion.documento_comunicacion_id = documento_comunicacion_id

        # Actualizar comunicación
        comunicacion.numerado = int(numerado)
        comunicacion.fecha_numerado = fecha_numerado_date
        comunicacion.fecha_envio = fecha_envio_date
        
        await db.flush()

        # Preparar datos nuevos para auditoría
        datos_nuevos = {
            "id": comunicacion.id,
            "acto_admin_id": comunicacion.acto_admin_id,
            "numerado": comunicacion.numerado,
            "fecha_numerado": str(comunicacion.fecha_numerado),
            "fecha_envio": str(comunicacion.fecha_envio),
            "url_documento": comunicacion.url_documento,
            "fecha_creacion": str(comunicacion.fecha_creacion) if comunicacion.fecha_creacion else None
        }

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="comunicacion",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de comunicación {numerado}",
            expediente_id=expediente_id,
            expediente_radicado=radicado,
            id_registro=str(comunicacion_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        await db.refresh(comunicacion)
        
        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": comunicacion.id,
                    "numerado": comunicacion.numerado,
                    "fecha_numerado": str(comunicacion.fecha_numerado),
                    "fecha_envio": str(comunicacion.fecha_envio),
                    "fecha_creacion": str(comunicacion.fecha_creacion),
                    "url_documento": comunicacion.url_documento,
                },
            },
            status_code=200,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error actualizando comunicación: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar comunicación")

@router.delete("/comunication/{comunicacion_id}")
async def eliminar_comunicacion(
    request:Request,
    comunicacion_id: int,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        radicado = data.get("radicado")

        # Buscar la comunicación existente
        stmt = select(Comunicacion).where(Comunicacion.id == comunicacion_id)
        comunicacion = await db.scalar(stmt)
        
        if not comunicacion:
            raise HTTPException(status_code=404, detail="Comunicación no encontrada")
        
        # Guardar datos anteriores para auditoría
        datos_anteriores = {
            "id": comunicacion.id,
            "acto_admin_id": comunicacion.acto_admin_id,
            "numerado": comunicacion.numerado,
            "fecha_numerado": str(comunicacion.fecha_numerado) if comunicacion.fecha_numerado else None,
            "fecha_envio": str(comunicacion.fecha_envio) if comunicacion.fecha_envio else None,
            "url_documento": comunicacion.url_documento,
            "fecha_creacion": str(comunicacion.fecha_creacion) if comunicacion.fecha_creacion else None
        }

        # Obtener el acto admin asociado
        stmt = select(ActoAdministrativo).where(ActoAdministrativo.id == comunicacion.acto_admin_id)
        acto_admin = await db.scalar(stmt)

        if not acto_admin:
            raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

        # Verificar permisos
        stmt = select(Expediente.encargado_id, Expediente.id).where(Expediente.radicado == radicado)
        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        encargado_id, expediente_id = row

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        
        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para eliminar esta comunicación"
            )
        
        await db.delete(comunicacion)
        await db.flush()

        await decrement_file_usage(GATEWAY_URL, [comunicacion.documento_comunicacion_id])

        # Obtener información del usuario para auditor ía
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="comunicacion",
            tipo_operacion="DELETE",
            descripcion=f"Eliminación de comunicación {datos_anteriores['numerado']}",
            expediente_id=expediente_id,
            expediente_radicado=radicado,
            id_registro=str(comunicacion_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos={}
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        
        return JSONResponse(
            content={
                "ok": True,
                "message": "Comunicación eliminada exitosamente"
            },
            status_code=200,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error eliminando comunicación: {e}")
        raise HTTPException(status_code=500, detail="Error al eliminar comunicación")

# Notificacion
@router.post("/notificacion")
async def crear_notificacion(
    request: Request,
    radicado: str = Form(...),
    acto_admin_id: int = Form(...),
    involucrado_id: int = Form(...),
    numerado: int = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio_citacion: str = Form(...),
    fecha_constancia_citacion: str = Form(None),
    documento_citacion_id: int = Form(...),
    notificacion_exitosa: bool = Form(False),
    tipo_notificacion_id: int = Form(None),
    documento_notificacion_id: int = Form(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        # Convertir fechas
        fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
        fecha_envio_date = datetime.strptime(fecha_envio_citacion, "%Y-%m-%d").date()
        fecha_constancia_date = None
        if fecha_constancia_citacion and fecha_constancia_citacion.strip() and fecha_constancia_citacion != "None":
            fecha_constancia_date = datetime.strptime(fecha_constancia_citacion, "%Y-%m-%d").date()

        # Validar numerado
        if not str(numerado).isdigit() or len(str(numerado)) > 4:
            raise HTTPException(
                status_code=400,
                detail="El numerado debe tener como máximo 4 dígitos"
            )

        # Validar notificacion_exitosa
        if notificacion_exitosa and not tipo_notificacion_id:
            raise HTTPException(
                status_code=400,
                detail="Debe seleccionar un tipo de notificación si marca como exitosa"
            )

        if notificacion_exitosa and not documento_notificacion_id:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar un documento de notificación si marca como exitosa"
            )

        # Verificar permisos
        stmt = select(Expediente.encargado_id, Expediente.id).where(Expediente.radicado == radicado)
        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        encargado_id, expediente_id = row

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )

        # Verificar que el acto admin existe
        stmt = select(ActoAdministrativo).where(ActoAdministrativo.id == acto_admin_id)
        acto_admin = await db.scalar(stmt)

        if not acto_admin:
            raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")

        # Verificar involucrado en expediente con el nuevo involved gateway
        involucrados_map = await get_involucrados_por_radicados(db, [radicado], GATEWAY_URL)
        involucrados_radicado = involucrados_map.get(radicado, [])
        inv_exp = any(inv.get("id") == involucrado_id for inv in involucrados_radicado)

        if not inv_exp:
            raise HTTPException(status_code=404, detail="El involucrado no pertenece a este expediente")

        # Verificar duplicado por acto_admin + involucrado
        stmt = select(Notificacion.id).where(
            and_(
                Notificacion.acto_administrativo_id == acto_admin_id,
                Notificacion.involucrado_id == involucrado_id
            )
        )
        existe = await db.scalar(stmt)

        if existe:
            raise HTTPException(
                status_code=400,
                detail="Ya existe una notificación para este involucrado en este acto administrativo"
            )

        # Validación de numerado + fecha_numerado según año
        año_numerado = fecha_numerado_date.year

        if año_numerado > 2012:
            # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE
            stmt = (
                select(Notificacion.id)
                .where(
                    Notificacion.numerado == numerado,
                    Notificacion.fecha_numerado == fecha_numerado_date
                )
            )
            existe_notificacion = await db.scalar(stmt)

            if existe_notificacion:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra notificación"
                )

        # Crear notificación
        nueva_notificacion = Notificacion(
            acto_administrativo_id=acto_admin_id,
            involucrado_id=involucrado_id,
            numerado=numerado,
            fecha_numerado=fecha_numerado_date,
            fecha_envio_citacion=fecha_envio_date,
            fecha_constancia_citacion=fecha_constancia_date,
            documento_citacion_id=documento_citacion_id,
            notificacion_exitosa=notificacion_exitosa,
            tipo_notificacion_id=tipo_notificacion_id if tipo_notificacion_id else None,
            documento_notificacion_id=documento_notificacion_id if notificacion_exitosa else None,
            fecha_notificacion=datetime.now().date() if notificacion_exitosa else None
        )

        db.add(nueva_notificacion)
        await db.flush()

        # Incrementar uso de documentos en app-docs
        doc_ids_to_increment = [documento_citacion_id]
        if documento_notificacion_id and notificacion_exitosa:
            doc_ids_to_increment.append(documento_notificacion_id)

        await increment_file_usage(GATEWAY_URL, doc_ids_to_increment)

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": nueva_notificacion.id,
            "acto_administrativo_id": acto_admin_id,
            "involucrado_id": involucrado_id,
            "numerado": numerado,
            "fecha_numerado": fecha_numerado,
            "fecha_envio_citacion": fecha_envio_citacion,
            "fecha_constancia_citacion": fecha_constancia_citacion,
            "documento_citacion_id": documento_citacion_id,
            "notificacion_exitosa": notificacion_exitosa,
            "tipo_notificacion_id": tipo_notificacion_id,
            "documento_notificacion_id": documento_notificacion_id,
            "fecha_creacion": str(nueva_notificacion.fecha_creacion)
        }

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="notificacion",
            tipo_operacion="INSERT",
            descripcion=f"Creación de notificación {numerado} para involucrado {involucrado_id}",
            expediente_id=expediente_id,
            expediente_radicado=radicado,
            id_registro=str(nueva_notificacion.id),
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        await db.refresh(nueva_notificacion)

        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": nueva_notificacion.id,
                    "acto_administrativo_id": nueva_notificacion.acto_administrativo_id,
                    "involucrado_id": nueva_notificacion.involucrado_id,
                    "numerado": nueva_notificacion.numerado,
                    "fecha_numerado": str(nueva_notificacion.fecha_numerado),
                    "fecha_envio_citacion": str(nueva_notificacion.fecha_envio_citacion),
                    "fecha_constancia_citacion": str(nueva_notificacion.fecha_constancia_citacion) if nueva_notificacion.fecha_constancia_citacion else None,
                    "documento_citacion_id": nueva_notificacion.documento_citacion_id,
                    "notificacion_exitosa": nueva_notificacion.notificacion_exitosa,
                    "tipo_notificacion_id": nueva_notificacion.tipo_notificacion_id,
                    "documento_notificacion_id": nueva_notificacion.documento_notificacion_id,
                    "fecha_notificacion": str(nueva_notificacion.fecha_notificacion) if nueva_notificacion.fecha_notificacion else None,
                    "fecha_creacion": str(nueva_notificacion.fecha_creacion)
                }
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error creando notificación: {e}")
        raise HTTPException(status_code=500, detail="Error al crear notificación")

@router.put("/notificacion/{notificacion_id}")
async def actualizar_notificacion(
    request: Request,
    notificacion_id: int,
    radicado: str = Form(...),
    numerado: int = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio_citacion: str = Form(...),
    fecha_constancia_citacion: str = Form(None),
    documento_citacion_id: int = Form(...),
    notificacion_exitosa: bool = Form(False),
    tipo_notificacion_id: int = Form(None),
    documento_notificacion_id: int = Form(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        usuario_id = verify_gateway_token(request)

        # Convertir fechas
        fecha_numerado_date = datetime.strptime(fecha_numerado, "%Y-%m-%d").date()
        fecha_envio_date = datetime.strptime(fecha_envio_citacion, "%Y-%m-%d").date()
        fecha_constancia_date = None
        if fecha_constancia_citacion and fecha_constancia_citacion.strip() and fecha_constancia_citacion != "None":
            fecha_constancia_date = datetime.strptime(fecha_constancia_citacion, "%Y-%m-%d").date()

        # Validar numerado
        if not str(numerado).isdigit() or len(str(numerado)) > 4:
            raise HTTPException(
                status_code=400,
                detail="El numerado debe tener como máximo 4 dígitos"
            )

        # Validar notificacion_exitosa
        if notificacion_exitosa and not tipo_notificacion_id:
            raise HTTPException(
                status_code=400,
                detail="Debe seleccionar un tipo de notificación si marca como exitosa"
            )

        if notificacion_exitosa and not documento_notificacion_id:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar un documento de notificación si marca como exitosa"
            )

        # Verificar permisos
        stmt = select(Expediente.encargado_id, Expediente.id).where(Expediente.radicado == radicado)
        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        encargado_id, expediente_id = row

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )

        # Buscar notificación existente
        stmt = select(Notificacion).where(Notificacion.id == notificacion_id)
        notificacion = await db.scalar(stmt)

        if not notificacion:
            raise HTTPException(status_code=404, detail="Notificación no encontrada")

        # Guardar datos anteriores para auditoría
        datos_anteriores = {
            "id": notificacion.id,
            "acto_administrativo_id": notificacion.acto_administrativo_id,
            "involucrado_id": notificacion.involucrado_id,
            "numerado": notificacion.numerado,
            "fecha_numerado": str(notificacion.fecha_numerado) if notificacion.fecha_numerado else None,
            "fecha_envio_citacion": str(notificacion.fecha_envio_citacion) if notificacion.fecha_envio_citacion else None,
            "fecha_constancia_citacion": str(notificacion.fecha_constancia_citacion) if notificacion.fecha_constancia_citacion else None,
            "documento_citacion_id": notificacion.documento_citacion_id,
            "notificacion_exitosa": notificacion.notificacion_exitosa,
            "tipo_notificacion_id": notificacion.tipo_notificacion_id,
            "fecha_notificacion": str(notificacion.fecha_notificacion) if notificacion.fecha_notificacion else None,
            "documento_notificacion_id": notificacion.documento_notificacion_id
        }

        # Validación de numerado + fecha_numerado según año
        año_numerado = fecha_numerado_date.year

        if año_numerado > 2012:
            # Para años > 2012: numerado+fecha debe ser único GLOBALMENTE (excepto este registro)
            stmt = (
                select(Notificacion.id)
                .where(
                    Notificacion.numerado == numerado,
                    Notificacion.fecha_numerado == fecha_numerado_date,
                    Notificacion.id != notificacion_id
                )
            )
            existe_notificacion = await db.scalar(stmt)

            if existe_notificacion:
                raise HTTPException(
                    status_code=400,
                    detail=f"El numerado {numerado} con fecha {fecha_numerado} ya está en uso en otra notificación"
                )

        # Gestión de documentos - increment/decrement según cambios
        docs_to_increment = []
        docs_to_decrement = []

        # Documento de citación
        if documento_citacion_id != datos_anteriores["documento_citacion_id"]:
            if datos_anteriores["documento_citacion_id"]:
                docs_to_decrement.append(datos_anteriores["documento_citacion_id"])
            docs_to_increment.append(documento_citacion_id)

        # Documento de notificación
        if notificacion_exitosa:
            # Si ahora es exitosa y cambió el documento o antes no tenía
            if documento_notificacion_id != datos_anteriores["documento_notificacion_id"]:
                if datos_anteriores["documento_notificacion_id"]:
                    docs_to_decrement.append(datos_anteriores["documento_notificacion_id"])
                if documento_notificacion_id:
                    docs_to_increment.append(documento_notificacion_id)
        else:
            # Si ya no es exitosa pero antes sí tenía documento de notificación
            if datos_anteriores["documento_notificacion_id"]:
                docs_to_decrement.append(datos_anteriores["documento_notificacion_id"])

        # Aplicar increment/decrement
        if docs_to_decrement:
            await decrement_file_usage(GATEWAY_URL, docs_to_decrement)
        if docs_to_increment:
            await increment_file_usage(GATEWAY_URL, docs_to_increment)

        # Actualizar campos
        notificacion.numerado = numerado
        notificacion.fecha_numerado = fecha_numerado_date
        notificacion.fecha_envio_citacion = fecha_envio_date
        notificacion.fecha_constancia_citacion = fecha_constancia_date
        notificacion.documento_citacion_id = documento_citacion_id
        notificacion.notificacion_exitosa = notificacion_exitosa
        notificacion.tipo_notificacion_id = tipo_notificacion_id if tipo_notificacion_id else None
        notificacion.documento_notificacion_id = documento_notificacion_id if notificacion_exitosa else None

        if notificacion_exitosa and not datos_anteriores["notificacion_exitosa"]:
            # Si ahora es exitosa y antes no lo era, establecer fecha de notificación
            notificacion.fecha_notificacion = datetime.now().date()

        await db.flush()

        # Preparar datos nuevos para auditoría
        datos_nuevos = {
            "id": notificacion.id,
            "acto_administrativo_id": notificacion.acto_administrativo_id,
            "involucrado_id": notificacion.involucrado_id,
            "numerado": notificacion.numerado,
            "fecha_numerado": str(notificacion.fecha_numerado),
            "fecha_envio_citacion": str(notificacion.fecha_envio_citacion),
            "fecha_constancia_citacion": str(notificacion.fecha_constancia_citacion) if notificacion.fecha_constancia_citacion else None,
            "documento_citacion_id": notificacion.documento_citacion_id,
            "notificacion_exitosa": notificacion.notificacion_exitosa,
            "tipo_notificacion_id": notificacion.tipo_notificacion_id,
            "fecha_notificacion": str(notificacion.fecha_notificacion) if notificacion.fecha_notificacion else None,
            "documento_notificacion_id": notificacion.documento_notificacion_id
        }

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="notificacion",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de notificación {numerado} para involucrado {notificacion.involucrado_id}",
            expediente_id=expediente_id,
            expediente_radicado=radicado,
            id_registro=str(notificacion_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        await db.refresh(notificacion)

        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": notificacion.id,
                    "acto_administrativo_id": notificacion.acto_administrativo_id,
                    "involucrado_id": notificacion.involucrado_id,
                    "numerado": notificacion.numerado,
                    "fecha_numerado": str(notificacion.fecha_numerado),
                    "fecha_envio_citacion": str(notificacion.fecha_envio_citacion),
                    "fecha_constancia_citacion": str(notificacion.fecha_constancia_citacion) if notificacion.fecha_constancia_citacion else None,
                    "documento_citacion_id": notificacion.documento_citacion_id,
                    "notificacion_exitosa": notificacion.notificacion_exitosa,
                    "tipo_notificacion_id": notificacion.tipo_notificacion_id,
                    "documento_notificacion_id": notificacion.documento_notificacion_id,
                    "fecha_notificacion": str(notificacion.fecha_notificacion) if notificacion.fecha_notificacion else None
                }
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"Error actualizando notificación: {e}")
        raise HTTPException(status_code=500, detail=f"Error al actualizar notificación: {str(e)}")

@router.delete("/notificacion/{notificacion_id}")
async def eliminar_notificacion(
    request: Request,
    notificacion_id: int,
    radicado: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        # Verificar permisos
        stmt = select(Expediente.encargado_id, Expediente.id).where(Expediente.radicado == radicado)
        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        encargado_id, expediente_id = row

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )

        # Buscar notificación
        stmt = select(Notificacion).where(Notificacion.id == notificacion_id)
        notificacion = await db.scalar(stmt)

        if not notificacion:
            raise HTTPException(status_code=404, detail="Notificación no encontrada")

        # Guardar datos de la notificación para auditoría
        datos_notificacion = {
            "id": notificacion.id,
            "acto_administrativo_id": notificacion.acto_administrativo_id,
            "numerado": notificacion.numerado,
            "involucrado_id": notificacion.involucrado_id,
            "fecha_numerado": str(notificacion.fecha_numerado) if notificacion.fecha_numerado else None,
            "fecha_envio_citacion": str(notificacion.fecha_envio_citacion) if notificacion.fecha_envio_citacion else None,
            "fecha_constancia_citacion": str(notificacion.fecha_constancia_citacion) if notificacion.fecha_constancia_citacion else None,
            "documento_citacion_id": notificacion.documento_citacion_id,
            "notificacion_exitosa": notificacion.notificacion_exitosa,
            "tipo_notificacion_id": notificacion.tipo_notificacion_id,
            "fecha_notificacion": str(notificacion.fecha_notificacion) if notificacion.fecha_notificacion else None,
            "documento_notificacion_id": notificacion.documento_notificacion_id,
            "fecha_creacion": str(notificacion.fecha_creacion) if notificacion.fecha_creacion else None
        }

        # Recolectar IDs de documentos para decrement
        doc_ids_to_decrement = []
        if notificacion.documento_citacion_id:
            doc_ids_to_decrement.append(notificacion.documento_citacion_id)
        if notificacion.documento_notificacion_id:
            doc_ids_to_decrement.append(notificacion.documento_notificacion_id)

        # Eliminar notificación
        await db.execute(
            delete(Notificacion).where(Notificacion.id == notificacion_id)
        )

        await db.flush()

        # Decrementar uso de documentos en app-docs
        if doc_ids_to_decrement:
            await decrement_file_usage(GATEWAY_URL, doc_ids_to_decrement)

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="notificacion",
            tipo_operacion="DELETE",
            descripcion=f"Eliminación de notificación (ID: {notificacion_id}) - numerado {datos_notificacion['numerado']}",
            expediente_id=expediente_id,
            expediente_radicado=radicado,
            id_registro=str(notificacion_id),
            datos_anteriores=datos_notificacion,
            datos_nuevos={}
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "message": "Notificación eliminada correctamente",
                "documentos_decrementados": len(doc_ids_to_decrement)
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error eliminando notificación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

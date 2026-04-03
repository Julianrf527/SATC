from fastapi import Request, APIRouter, Depends, HTTPException, Form, Path as PathParam
from fastapi.responses import JSONResponse
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from datetime import datetime, date
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
from typing import List, Optional
import logging
import os
import pytz

#----- DB -----

from db.deps import get_db
from db.models.expediente_recurso import ExpedienteRecurso
from db.models.expediente import Expediente
from db.models.vereda import Vereda
from db.models.etapa import Etapa
from db.models.tipo_etapa import TipoEtapa
from db.models.medida_preventiva import MedidaPreventiva
from db.models.cesacion import Cesacion
from db.models.formulacion_cargos import FormulacionCargos
from db.models.decision_fondo import DecisionFondo
from db.models.ejecucion_sancion import EjecucionSancion
from db.models.tipo_notificacion import TipoNotificacion
from db.models.notificacion import Notificacion
from db.models.acto_admin import ActoAdministrativo
from db.models.documento_anexo import DocumentoAnexo

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

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Subir a ApiCorp
DOCS_DIR = BASE_DIR / "uploads" / "expedientes"

# ---------- LOGGER ------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- MODELOS ----------

class Measure(BaseModel):
    tipo_medida_id: int
    cantidad: str
    especie: str
    estado_medida: bool | None
    etapa_id: int

class CesacionData(BaseModel):
    id: int | None = None
    tipo_cesacion_id: int
    etapa_id: int

class Decision(BaseModel):
    tipo_sancion_id: int
    detalle: str
    etapa_id: int

class Execution(BaseModel):
    cobro_coactivo: bool
    disposicion: bool
    ruia: bool
    act_admin: str
    fecha_act: date
    etapa_id: int

#----------- FUNCIONES ------------

from utils.verify_gateway_token import verify_gateway_token
from utils.involved_client import get_involucrados_por_radicados
from utils.docs_client import increment_file_usage, decrement_file_usage

from services.crud_file_operations import (
    get_indagacion_preliminar,
    get_medida_preventiva,
    get_inicio_proceso_sancionatorio,
    get_cesacion,
    get_formulacion_cargos,
    get_apertura_etapa_probatoria,
    get_cierre_etapa_probatoria,
    get_decision_fondo,
    get_recurso,
    insert_auditoria,
)


@router.post("/{expediente_id}/stage/{type}")
async def crear_etapa(
    request: Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    type: int = PathParam(..., description="Tipo etapa a crear"),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        # Verificar permisos
        stmr = select(Expediente.radicado).where(
            Expediente.id == expediente_id,
            Expediente.encargado_id == int(usuario_id)
        )
        res = await db.execute(stmr)
        expediente = res.scalar_one_or_none()

        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")

        # Crear nueva etapa
        stmt = (
            insert(Etapa)
            .values(
                expediente_id=expediente.id,
                tipo_etapa_id=type,
                fecha_inicio=datetime.now().replace(tzinfo=None)
            )
            .returning(Etapa.id)
        )
        etapa_id = await db.scalar(stmt)
        await db.flush()

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": etapa_id,
            "expediente_id": expediente.id,
            "tipo_etapa_id": type,
            "fecha_inicio": str(datetime.now().replace(tzinfo=None))
        }

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="etapa",
            tipo_operacion="INSERT",
            descripcion=f"Creación de etapa tipo {type}",
            expediente_id=expediente.id,
            id_registro=str(etapa_id),
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

        return JSONResponse(content={"ok": True, "etapa_id": etapa_id}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al crear etapa: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

#Indagacion Preliminar
@router.get("/investigation/{expediente_id}")
async def obtener_indagacion_preliminar(
    request: Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)

        select_stmt = select(Expediente.encargado_id).where(Expediente.id == expediente_id)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != user_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_indagacion_preliminar(expediente_id, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Indagación preliminar no encontrada")
        return JSONResponse(content={"ok": True, "indagacion": data["indagacion"]}, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#Medida Preventiva
@router.get("/measure/{expediente_id}")
async def obtener_medida_preventiva(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != user_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_medida_preventiva(radicado, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Medida preventiva no encontrada")
        return JSONResponse(content={"ok": True, "medida": data["medida"]}, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/measure")
async def create_measure(
    request:Request,
    data: Measure,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        stmr = (
            select(Etapa, Expediente.radicado)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                Etapa.id == data.etapa_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        row = res.first()

        if not row:
            raise HTTPException(
                status_code=404, 
                detail="Etapa no encontrada o sin permisos"
            )

        etapa, radicado = row

        stmt_check = select(MedidaPreventiva).where(
            MedidaPreventiva.etapa_id == data.etapa_id
        )
        existing = await db.scalar(stmt_check)
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Ya existe una medida preventiva para esta etapa"
            )

        nueva_medida = MedidaPreventiva(
            tipo_medida_id=data.tipo_medida_id,
            cantidad=data.cantidad,
            especie=data.especie,
            estado_medida=data.estado_medida,
            etapa_id=data.etapa_id
        )
        
        db.add(nueva_medida)
        await db.flush()

        datos_nuevos = {
            "id": nueva_medida.id,
            "tipo_medida_id": nueva_medida.tipo_medida_id,
            "cantidad": nueva_medida.cantidad,
            "especie": nueva_medida.especie,
            "estado_medida": nueva_medida.estado_medida,
            "etapa_id": nueva_medida.etapa_id
        }

        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="medida_preventiva",
            tipo_operacion="INSERT",
            descripcion=f"Creación de medida preventiva ID {nueva_medida.id}",
            expediente_radicado=radicado,
            id_registro=str(nueva_medida.id),
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "id": nueva_medida.id,
                "message": "Medida preventiva creada correctamente"
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/measure/{medida_id}")
async def update_measure(
    request: Request,
    medida_id: int,
    data: Measure,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        stmr = (
            select(MedidaPreventiva, Expediente.radicado)
            .join(Etapa, MedidaPreventiva.etapa_id == Etapa.id)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                MedidaPreventiva.id == medida_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        row = res.first()

        if not row:
            raise HTTPException(status_code=404, detail="Medida preventiva no encontrada o sin permisos")

        medida, radicado = row

        datos_anteriores = {
            "id": medida.id,
            "tipo_medida_id": medida.tipo_medida_id,
            "cantidad": medida.cantidad,
            "especie": medida.especie,
            "estado_medida": medida.estado_medida,
            "etapa_id": medida.etapa_id
        }

        stmt = (
            update(MedidaPreventiva)
            .where(MedidaPreventiva.id == medida_id)
            .values(
                tipo_medida_id=data.tipo_medida_id,
                cantidad=data.cantidad,
                especie=data.especie,
                estado_medida=data.estado_medida,
            )
        )
        await db.execute(stmt)

        datos_nuevos = {
            "id": medida_id,
            "tipo_medida_id": data.tipo_medida_id,
            "cantidad": data.cantidad,
            "especie": data.especie,
            "estado_medida": data.estado_medida,
            "etapa_id": medida.etapa_id
        }

        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="medida_preventiva",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de medida preventiva ID {medida_id}",
            expediente_radicado=radicado,
            id_registro=str(medida_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "id": medida_id,
                "message": "Medida preventiva actualizada correctamente"
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

#Inicio de proceso sancionatorio
@router.get("/start-process/{expediente_id}")
async def obtener_inicio_proceso_sancionatorio(
    request :Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.id == expediente_id)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_inicio_proceso_sancionatorio(expediente_id, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Inicio proceso sancionatorio no encontrada")
        return JSONResponse(content={"ok": True, "inicio_proceso": data["inicio_proceso"]}, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#Cesacion
@router.get("/cessation/{expediente_id}")
async def obtener_cesacion(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != user_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_cesacion(radicado, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Cesacion no encontrada")
        return JSONResponse(content={"ok": True, "cesacion": data["cesacion"]}, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cessation")
async def create_law(
    request: Request,
    data: CesacionData,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        stmr = (
            select(Expediente.radicado)
            .join(Etapa, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                Etapa.id == data.etapa_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        radicado = res.scalar_one_or_none()

        if not radicado:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")

        stmt = (
            insert(Cesacion)
            .values(
                tipo_cesacion_id=data.tipo_cesacion_id,
                etapa_id=data.etapa_id
            )
            .returning(Cesacion.id)
        )
        result = await db.execute(stmt)
        cesacion_id = result.scalar_one()

        datos_nuevos = {
            "id": cesacion_id,
            "tipo_cesacion_id": data.tipo_cesacion_id,
            "etapa_id": data.etapa_id
        }

        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="cesacion",
            tipo_operacion="INSERT",
            descripcion=f"Creación de cesación ID {cesacion_id}",
            expediente_radicado=radicado,
            id_registro=str(cesacion_id),
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "id": cesacion_id,
                "message": "Ley 1333/2009 creada correctamente"
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/cessation/{cessation_id}")
async def update_law(
    request:Request,
    cessation_id: int,
    data: CesacionData,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        stmr = (
            select(Cesacion, Etapa.expediente_radicado, Expediente.id)
            .join(Etapa, Cesacion.etapa_id == Etapa.id)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                Cesacion.id == cessation_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        row = res.first()

        if not row:
            raise HTTPException(status_code=404, detail="Ley no encontrada o sin permisos")

        cesacion, radicado, expediente_id = row

        datos_anteriores = {
            "id": cesacion.id,
            "tipo_cesacion_id": cesacion.tipo_cesacion_id,
            "etapa_id": cesacion.etapa_id
        }

        stmt = (
            update(Cesacion)
            .where(Cesacion.id == cessation_id)
            .values(tipo_cesacion_id=data.tipo_cesacion_id)
        )
        await db.execute(stmt)

        datos_nuevos = {
            "id": cessation_id,
            "tipo_cesacion_id": data.tipo_cesacion_id,
            "etapa_id": cesacion.etapa_id
        }

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="cesacion",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de cesación ID {cessation_id}",
            expediente_id=expediente_id,
            expediente_radicado=radicado,
            id_registro=str(cessation_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "id": cessation_id,
                "message": "Ley 1333/2009 actualizada correctamente"
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Formulacion de cargos
@router.get("/formulation/{expediente_id}")
async def obtener_formulacion_cargos(
    request: Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.id == expediente_id)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_formulacion_cargos(expediente_id, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Formulacion de cargos no encontrada")
        return JSONResponse(content={"ok": True, "formulacion": data["formulacion_cargos"]}, status_code=200)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al obtener formulacion de cargos': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al consultar formulacion de cargos")

@router.post("/formulation")
async def create_formulation(
    request: Request,
    etapa_id: int = Form(...),
    descargos: str = Form(...),
    documento_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),

):
    try:
        usuario_id = verify_gateway_token(request)
        
        # Convertir string a boolean o None
        descargos_bool: bool | None = None
        if descargos == "true":
            descargos_bool = True
        elif descargos == "false":
            descargos_bool = False
        elif descargos == "null":
            descargos_bool = None

        # Validar que el expediente corresponde al usuario y etapa
        stmr = (
            select(Expediente.radicado, Expediente.id)
            .join(Etapa, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                Etapa.id == etapa_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        result = res.first()

        if not result:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")

        expediente, expediente_id = result

        # Insertar formulación
        stmt = (
            insert(FormulacionCargos)
            .values(
                descargos=descargos_bool,
                documento_id=documento_id,
                etapa_id=etapa_id
            )
            .returning(FormulacionCargos.id)
        )
        result = await db.execute(stmt)
        formulacion_id = result.scalar_one()

        # Incrementar uso de documento en app-docs
        if documento_id:
            await increment_file_usage(GATEWAY_URL, [documento_id])

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": formulacion_id,
            "descargos": descargos_bool,
            "documento_id": documento_id,
            "etapa_id": etapa_id
        }

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="FormulacionCargos",
            tipo_operacion="INSERT",
            descripcion=f"Creación de formulación de cargos ID {formulacion_id}",
            expediente_id=expediente_id,
            expediente_radicado=expediente,
            id_registro=str(formulacion_id),
            datos_anteriores=None,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "id": formulacion_id,
                "message": "Formulación de cargos creada correctamente"
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando Formulación de cargos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/formulation/{formulation_id}")
async def update_formulation(
    request: Request,
    formulation_id: int,
    etapa_id: int = Form(...),
    descargos: str = Form(...),
    documento_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        
        # Convertir string a boolean o None
        descargos_bool: bool | None = None
        if descargos == "true":
            descargos_bool = True
        elif descargos == "false":
            descargos_bool = False
        elif descargos == "null":
            descargos_bool = None

        # Obtener datos anteriores y validar permisos
        stmr = (
            select(
                FormulacionCargos.id,
                FormulacionCargos.descargos,
                FormulacionCargos.documento_id,
                FormulacionCargos.etapa_id,
                Expediente.radicado,
                Expediente.id
            )
            .join(Etapa, FormulacionCargos.etapa_id == Etapa.id)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                FormulacionCargos.id == formulation_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        registro = res.first()

        if not registro:
            raise HTTPException(status_code=404, detail="Formulación de cargos no encontrada o sin permisos")

        expediente_id = registro[5]  # El id del expediente está en la posición 5

        # Preparar datos anteriores
        datos_anteriores = {
            "id": registro.id,
            "descargos": registro.descargos,
            "documento_id": registro.documento_id,
            "etapa_id": registro.etapa_id
        }

        # Gestión de documentos - increment/decrement según cambios
        doc_anterior = registro.documento_id
        if documento_id != doc_anterior:
            if doc_anterior:
                await decrement_file_usage(GATEWAY_URL, [doc_anterior])
            if documento_id:
                await increment_file_usage(GATEWAY_URL, [documento_id])

        # Actualizar registro
        stmt = (
            update(FormulacionCargos)
            .where(FormulacionCargos.id == formulation_id)
            .values(
                descargos=descargos_bool,
                documento_id=documento_id
            )
        )
        await db.execute(stmt)

        # Preparar datos nuevos
        datos_nuevos = {
            "id": formulation_id,
            "descargos": descargos_bool,
            "documento_id": documento_id,
            "etapa_id": registro.etapa_id
        }

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="FormulacionCargos",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de formulación de cargos ID {formulation_id}",
            expediente_id=expediente_id,
            expediente_radicado=registro.radicado,
            id_registro=str(formulation_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "id": formulation_id,
                "message": "Formulación de cargos actualizada correctamente"
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error actualizando Formulación de cargos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# Apertura Etapa Probatoria
@router.get("/opening/{expediente_id}")
async def obtener_apertura_etapa_probatoria(
    request: Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.id == expediente_id)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_apertura_etapa_probatoria(expediente_id, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Apertura etapa probatoria no encontrada")
        return JSONResponse(content={"ok": True, "apertura_etapa_probatoria": data["apertura_etapa_probatoria"]}, status_code=200)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al obtener apertura etapa probatoria para expediente ID {expediente_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al consultar apertura etapa probatoria")

# Cierre Etapa Probatoria
@router.get("/closing/{expediente_id}")
async def obtener_cierre_etapa_probatoria(
    request: Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.id == expediente_id)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_cierre_etapa_probatoria(expediente_id, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Cierre etapa probatoria no encontrada")
        return JSONResponse(content={"ok": True, "cierre_etapa_probatoria": data["cierre_etapa_probatoria"]}, status_code=200)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al obtener cierre etapa probatoria para expediente ID {expediente_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al consultar cierre etapa probatoria")

# Decision de Fondo
@router.get("/decision/{expediente_id}")
async def obtener_decision(
    request:Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    db: AsyncSession = Depends(get_db),
):
    try:
        logger.info(f"[DECISION] Iniciando consulta para expediente ID: {expediente_id}")
        usuario_id = verify_gateway_token(request)
        logger.info(f"[DECISION] Usuario autenticado: {usuario_id}")

        select_stmt = select(Expediente.encargado_id).where(Expediente.id == expediente_id)
        encargado_id = await db.scalar(select_stmt)
        logger.info(f"[DECISION] Encargado del expediente: {encargado_id}")
        
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        logger.info(f"[DECISION] Llamando a get_decision_fondo...")
        data = await get_decision_fondo(expediente_id, db)
        logger.info(f"[DECISION] Respuesta de get_decision_fondo: ok={data.get('ok')}, tiene decision_fondo={('decision_fondo' in data)}")
        
        # Verificar si hubo un error interno
        if not data.get("ok", False):
            logger.error(f"[DECISION] Error en get_decision_fondo: {data.get('error', 'Sin mensaje de error')}")
            raise HTTPException(status_code=500, detail="Error al consultar decisión de fondo")
        
        # Siempre devolver la respuesta, incluso si no hay decisión de fondo todavía
        logger.info(f"[DECISION] Devolviendo respuesta exitosa")
        return JSONResponse(content={"ok": True, "decision_fondo": data.get("decision_fondo", {})}, status_code=200)
    except HTTPException as he:
        logger.error(f"[DECISION] HTTPException: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Error al obtener decision de fondo para expediente ID {expediente_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al consultar decision de fondo")

@router.post("/decision")
async def crear_decision(
    request:Request,
    data: Decision,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        # Validar que el expediente corresponde al usuario y etapa
        stmr = (
            select(Expediente.radicado, Expediente.id)
            .join(Etapa, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                Etapa.id == data.etapa_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        result = res.first()

        if not result:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")

        expediente, expediente_id = result

        # Insertar Decision de Fondo
        stmt = (
            insert(DecisionFondo)
            .values(
                tipo_sancion_id=data.tipo_sancion_id,
                detalle=data.detalle,
                etapa_id=data.etapa_id
            )
            .returning(DecisionFondo.id)
        )
        result = await db.execute(stmt)
        de_id = result.scalar_one()

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": de_id,
            "tipo_sancion_id": data.tipo_sancion_id,
            "detalle": data.detalle,
            "etapa_id": data.etapa_id
        }

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="DecisionFondo",
            tipo_operacion="INSERT",
            descripcion=f"Creación de decisión de fondo ID {de_id}",
            expediente_id=expediente_id,
            expediente_radicado=expediente,
            id_registro=str(de_id),
            datos_anteriores=None,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "id": de_id,
                "message": "Decisión de fondo creada correctamente"
            },
            status_code=201
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando Decisión de fondo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/decision/{decision_id}")
async def update_decision(
    request: Request,
    decision_id: int,
    data: Decision,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        # Obtener datos anteriores y validar permisos
        stmr = (
            select(
                DecisionFondo.id,
                DecisionFondo.tipo_sancion_id,
                DecisionFondo.detalle,
                DecisionFondo.etapa_id,
                Expediente.radicado,
                Expediente.id
            )
            .join(Etapa, DecisionFondo.etapa_id == Etapa.id)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                DecisionFondo.id == decision_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        row = res.first()

        if not row:
            raise HTTPException(status_code=404, detail="Decisión de fondo no encontrada o sin permisos")

        expediente_id = row[5]  # El id del expediente está en la posición 5

        # Preparar datos anteriores
        datos_anteriores = {
            "id": row.id,
            "tipo_sancion_id": row.tipo_sancion_id,
            "detalle": row.detalle,
            "etapa_id": row.etapa_id
        }

        # Actualizar registro
        stmt = (
            update(DecisionFondo)
            .where(DecisionFondo.id == decision_id)
            .values(
                tipo_sancion_id=data.tipo_sancion_id,
                detalle=data.detalle
            )
        )
        await db.execute(stmt)

        # Preparar datos nuevos
        datos_nuevos = {
            "id": decision_id,
            "tipo_sancion_id": data.tipo_sancion_id,
            "detalle": data.detalle,
            "etapa_id": row.etapa_id
        }

        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="DecisionFondo",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de decisión de fondo ID {decision_id}",
            expediente_id=expediente_id,
            expediente_radicado=row.radicado,
            id_registro=str(decision_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "id": decision_id,
                "message": "Decisión de fondo actualizada correctamente"
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error actualizando Decisión de fondo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# Recurso
@router.get("/resource/{expediente_id}")
async def obtener_formulacion_cargos(
    request: Request,
    expediente_id: int = PathParam(..., description="ID del expediente"),
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)
        select_stmt = select(Expediente.encargado_id).where(Expediente.id == expediente_id)
        encargado_id = await db.scalar(select_stmt)
        if encargado_id is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        if encargado_id != usuario_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para ver este expediente")

        data = await get_recurso(expediente_id, db)
        if data["ok"] is False:
            raise HTTPException(status_code=404, detail="Recurso no encontrada")
        return JSONResponse(content={"ok": True, "recurso": data["recurso"]}, status_code=200)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al obtener recurso para expediente ID {expediente_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al consultar recurso")

# Ejecucion Sancion
@router.get("/execution/{expediente_id}")
async def get_ejecucion_sancion(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        usuario_id = verify_gateway_token(request)
        stmr = select(Expediente.radicado).where(Expediente.radicado == radicado)
        res = await db.execute(stmr)
        expediente = res.scalar_one_or_none()

        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        # Buscar etapa "EJECUCION DE LA SANCION"
        stmt = select(TipoEtapa.id).where(TipoEtapa.nombre == "EJECUCION DE LA SANCION")
        tipo_etapa = await db.scalar(stmt)

        if not tipo_etapa:
            raise HTTPException(status_code=500, detail="Tipo de etapa 'EJECUCION DE LA SANCION' no configurado")
        
        stmt = select(Etapa.id).where(
            Etapa.tipo_etapa_id == tipo_etapa,
            Etapa.expediente_radicado == radicado
        )
        etapa_id = await db.execute(stmt)
        etapa_id = etapa_id.scalar_one_or_none()
        
        # Permisos de creacion
        stmt = (
            select(Etapa.id)
            .join(TipoEtapa, Etapa.tipo_etapa_id == TipoEtapa.id)
            .where(
                Etapa.expediente_radicado == radicado,
                TipoEtapa.nombre == "DECISION DE FONDO"
            )
        )
        decision_id = await db.scalar(stmt)

        stmt = select(ActoAdministrativo.id).where(ActoAdministrativo.etapa_id == decision_id, ActoAdministrativo.nivel_auxiliar == False)
        ad_id = await db.scalar(stmt)

        if ad_id:
            # Consultar documentos
            stmt = select(DocumentoAnexo.id).where(DocumentoAnexo.etapa_id == decision_id, DocumentoAnexo.nombre == "Recurso")
            doc_id = (await db.execute(stmt)).scalars().all()

            if doc_id:
                stmt = select(ActoAdministrativo.id).where(ActoAdministrativo.etapa_id == decision_id, ActoAdministrativo.nivel_auxiliar == True)
                ad_recurso_id = await db.scalar(stmt)

                if ad_recurso_id:
                    stmt = (
                        select(Etapa.id)
                        .join(TipoEtapa, Etapa.tipo_etapa_id == TipoEtapa.id)
                        .where(
                            Etapa.expediente_radicado == radicado,
                            TipoEtapa.nombre == "PROBATORIA DE RECURSO"
                        )
                    )
                    recurso_id = await db.scalar(stmt)
                    if recurso_id:
                        stmt = select(ActoAdministrativo.id).where(ActoAdministrativo.etapa_id == recurso_id, ActoAdministrativo.nivel_auxiliar == True)
                        ad_decision_id = await db.scalar(stmt)
                        if ad_decision_id:
                            stmt = (
                                select(Notificacion.notificacion_exitosa)
                                .where(Notificacion.acto_administrativo_id == ad_decision_id)
                            )
                            result = await db.execute(stmt)
                            notificaciones = result.scalars().all()

                            if not notificaciones or not any(notificaciones):
                                creable = {
                                    "status": False,
                                    "msg":
                                    f'No se ha notificado exitosamente a ningún involucrado del acto administrativa de decision de la etapa: "Probatoria del Recurso".'
                                }
                            else:
                                creable = {"status": True}

                        else:
                            creable = {
                                "status": False,
                                "msg":
                                f'No se ha creado un acto administrativa de decision para la etapa: "Probatoria del Recurso".'
                            }
                        
                    else:
                        stmt = (
                            select(Notificacion.notificacion_exitosa)
                            .where(Notificacion.acto_administrativo_id == ad_recurso_id)
                        )
                        result = await db.execute(stmt)
                        notificaciones = result.scalars().all()

                        if not notificaciones or not any(notificaciones):
                            creable = {
                                "status": False,
                                "msg":
                                f'No se ha notificado exitosamente a ningún involucrado del acto administrativa de recurso en la etapa: "Decision de Fondo".'
                            }
                        else:
                            creable = {"status": True}

                        stmt = (
                            select(Notificacion.notificacion_exitosa)
                            .where(Notificacion.acto_administrativo_id == ad_id)
                        )
                        result = await db.execute(stmt)
                        notificaciones = result.scalars().all()
                        if not notificaciones or not any(notificaciones):
                            creable = {
                                "status": False,
                                "msg":
                                f'No se ha notificado exitosamente a ningún involucrado del acto administrativa de la etapa: "Decision de Fondo".'
                            }
                        else:
                            creable = {"status": True}

                else:
                    creable = {
                        "status": False,
                        "msg":
                        f'No se ha creado un acto administrativa de recurso para la etapa: "Decision de Fondo".'
                    }

            else:
                stmt = (
                    select(Notificacion.notificacion_exitosa)
                    .where(Notificacion.acto_administrativo_id == ad_id)
                )
                result = await db.execute(stmt)
                notificaciones = result.scalars().all()

                if not notificaciones or not any(notificaciones):
                    creable = {
                        "status": False,
                        "msg":
                        f'No se ha notificado exitosamente a ningún involucrado del acto administrativa de la etapa: "Decision de Fondo".'
                    }
                else:
                    creable = {"status": True}
        else:
            creable = {
                    "status": False,
                    "msg":
                    f'No se ha creado un acto administrativa para la etapa: "Decision de fondo".'
                }

        # EJECUCION DE LA SANCION (puede no existir)
        stmr = select(EjecucionSancion).where(EjecucionSancion.etapa_id == etapa_id)
        result = await db.execute(stmr)
        es = result.scalar_one_or_none()

        decision = {}
        if es:
            decision = {
                "id": es.id,
                "cobro_coactivo": es.cobro_coactivo,
                "documento_cobro_id": es.documento_cobro_id,
                "disposicion": es.disposicion,
                "ruia": es.ruia,
                "documento_ruia_id": es.documento_ruia_id,
                "memorando": es.memorando,
                "documento_memorando_id": es.documento_memorando_id,
                "tipo_acto": es.tipo_acto,
                "fecha_auto": es.fecha_auto.isoformat() if es.fecha_auto else None,
                "documento_acto_id": es.documento_acto_id,
            }
        decision["creable"] = creable
        decision["tipo_etapa_id"] = tipo_etapa

        return JSONResponse(
            content={
                "ok": True,
                "etapa_id": etapa_id,
                "ejecucion_sancion": decision,
            },
            status_code=200
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error obteniendo ejecucion de la sancion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/execution")
async def crear_ejecucion(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # Campos requeridos
    etapa_id: int = Form(...),
    auto_admin: str = Form(...),
    fecha_auto: str = Form(...),
    
    # Campos booleanos
    cobro_coactivo: str = Form("false"),
    disposicion: str = Form("false"),
    ruia: str = Form("false"),
    memorando: str = Form("false"),
    
    # Document IDs from app-docs
    documento_acto_id: Optional[int] = Form(None),
    documento_cobro_id: Optional[int] = Form(None),
    documento_ruia_id: Optional[int] = Form(None),
    documento_memorando_id: Optional[int] = Form(None),
):
    """
    Crea un nuevo registro de ejecución de la sanción.
    """
    try:
        usuario_id = verify_gateway_token(request)
        
        # Convertir strings de booleanos
        cobro_coactivo_bool = cobro_coactivo.lower() == "true"
        disposicion_bool = disposicion.lower() == "true"
        ruia_bool = ruia.lower() == "true"
        memorando_bool = memorando.lower() == "true"
        
        # Validar que el expediente corresponde al usuario y etapa
        stmr = (
            select(Expediente.radicado, Expediente.id)
            .join(Etapa, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                Etapa.id == etapa_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        result = res.first()

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Expediente no encontrado o sin permisos"
            )

        expediente, expediente_id = result
        
        # Validar que no exista ya una ejecución para esta etapa
        stmt = select(EjecucionSancion.id).where(EjecucionSancion.etapa_id == etapa_id)
        existe = await db.scalar(stmt)
        
        if existe:
            raise HTTPException(
                status_code=400, 
                detail="Ya existe una ejecución registrada para esta etapa"
            )
        
        # Document IDs validation moved to frontend
        
        # Parsear fecha
        try:
            fecha_auto_date = date.fromisoformat(fecha_auto)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )
        
        # Document IDs are now passed directly from app-docs
        # No file handling needed
        
        # Insertar ejecución
        stmt = (
            insert(EjecucionSancion)
            .values(
                etapa_id=etapa_id,
                cobro_coactivo=cobro_coactivo_bool,
                documento_cobro_id=documento_cobro_id,
                disposicion=disposicion_bool,
                ruia=ruia_bool,
                documento_ruia_id=documento_ruia_id,
                memorando=memorando_bool,
                documento_memorando_id=documento_memorando_id,
                tipo_acto=auto_admin,
                fecha_auto=fecha_auto_date,
                documento_acto_id=documento_acto_id,
            )
            .returning(EjecucionSancion.id)
        )
        result = await db.execute(stmt)
        ejecucion_id = result.scalar_one()

        # Incrementar uso de documentos en app-docs
        doc_ids_to_increment = [d for d in [documento_acto_id, documento_cobro_id, documento_ruia_id, documento_memorando_id] if d]
        if doc_ids_to_increment:
            await increment_file_usage(GATEWAY_URL, doc_ids_to_increment)

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": ejecucion_id,
            "etapa_id": etapa_id,
            "cobro_coactivo": cobro_coactivo_bool,
            "documento_cobro_id": documento_cobro_id,
            "disposicion": disposicion_bool,
            "ruia": ruia_bool,
            "documento_ruia_id": documento_ruia_id,
            "memorando": memorando_bool,
            "documento_memorando_id": documento_memorando_id,
            "tipo_acto": auto_admin,
            "fecha_auto": fecha_auto,
            "documento_acto_id": documento_acto_id,
        }
        
        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="EjecucionSancion",
            tipo_operacion="INSERT",
            descripcion=f"Creación de ejecución de sanción ID {ejecucion_id}",
            expediente_id=expediente_id,
            expediente_radicado=expediente,
            id_registro=str(ejecucion_id),
            datos_anteriores=None,
            datos_nuevos=datos_nuevos
        )
        
        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )
        
        await db.commit()
        
        return JSONResponse(
            content={
                "ok": True,
                "id": ejecucion_id,
                "message": "Ejecución de la sanción creada correctamente"
            },
            status_code=201
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando ejecución de sanción: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.put("/execution/{ejecucion_id}")
async def actualizar_ejecucion(
    request: Request,
    ejecucion_id: int,
    db: AsyncSession = Depends(get_db),
    # Campos requeridos
    etapa_id: int = Form(...),
    auto_admin: str = Form(...),
    fecha_auto: str = Form(...),
    
    # Campos booleanos
    cobro_coactivo: str = Form("false"),
    disposicion: str = Form("false"),
    ruia: str = Form("false"),
    memorando: str = Form("false"),
    
    # Document IDs from app-docs
    documento_acto_id: Optional[int] = Form(None),
    documento_cobro_id: Optional[int] = Form(None),
    documento_ruia_id: Optional[int] = Form(None),
    documento_memorando_id: Optional[int] = Form(None),
):
    """
    Actualiza un registro existente de ejecución de la sanción.
    """
    try:
        usuario_id = verify_gateway_token(request)
        
        # Convertir strings de booleanos
        cobro_coactivo_bool = cobro_coactivo.lower() == "true"
        disposicion_bool = disposicion.lower() == "true"
        ruia_bool = ruia.lower() == "true"
        memorando_bool = memorando.lower() == "true"
        
        # Obtener datos anteriores y validar permisos
        stmr = (
            select(
                EjecucionSancion.id,
                EjecucionSancion.etapa_id,
                EjecucionSancion.cobro_coactivo,
                EjecucionSancion.documento_cobro_id,
                EjecucionSancion.disposicion,
                EjecucionSancion.ruia,
                EjecucionSancion.documento_ruia_id,
                EjecucionSancion.memorando,
                EjecucionSancion.documento_memorando_id,
                EjecucionSancion.tipo_acto,
                EjecucionSancion.fecha_auto,
                EjecucionSancion.documento_acto_id,
                Expediente.radicado,
                Expediente.id
            )
            .join(Etapa, EjecucionSancion.etapa_id == Etapa.id)
            .join(Expediente, Etapa.expediente_radicado == Expediente.radicado)
            .where(
                EjecucionSancion.id == ejecucion_id,
                Expediente.encargado_id == usuario_id
            )
        )
        res = await db.execute(stmr)
        registro = res.first()

        if not registro:
            raise HTTPException(
                status_code=404,
                detail="Ejecución de sanción no encontrada o sin permisos"
            )

        expediente_id = registro[13]  # El id del expediente está en la posición 13

        # Preparar datos anteriores
        datos_anteriores = {
            "id": registro.id,
            "etapa_id": registro.etapa_id,
            "cobro_coactivo": registro.cobro_coactivo,
            "documento_cobro_id": registro.documento_cobro_id,
            "disposicion": registro.disposicion,
            "ruia": registro.ruia,
            "documento_ruia_id": registro.documento_ruia_id,
            "memorando": registro.memorando,
            "documento_memorando_id": registro.documento_memorando_id,
            "tipo_acto": registro.tipo_acto,
            "fecha_auto": registro.fecha_auto.isoformat() if registro.fecha_auto else None,
            "documento_acto_id": registro.documento_acto_id,
        }

        # Gestión de documentos - increment/decrement según cambios
        docs_to_decrement = []
        docs_to_increment = []

        doc_fields = [
            ('documento_acto_id', documento_acto_id),
            ('documento_cobro_id', documento_cobro_id),
            ('documento_ruia_id', documento_ruia_id),
            ('documento_memorando_id', documento_memorando_id),
        ]

        for field_name, new_value in doc_fields:
            old_value = datos_anteriores.get(field_name)
            if new_value != old_value:
                if old_value:
                    docs_to_decrement.append(old_value)
                if new_value:
                    docs_to_increment.append(new_value)

        if docs_to_decrement:
            await decrement_file_usage(GATEWAY_URL, docs_to_decrement)
        if docs_to_increment:
            await increment_file_usage(GATEWAY_URL, docs_to_increment)

        # Parsear fecha
        try:
            fecha_auto_date = date.fromisoformat(fecha_auto)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )
        
        # Document IDs now replace URLs - no file handling needed

        # Actualizar registro
        stmt = (
            update(EjecucionSancion)
            .where(EjecucionSancion.id == ejecucion_id)
            .values(
                cobro_coactivo=cobro_coactivo_bool,
                documento_cobro_id=documento_cobro_id,
                disposicion=disposicion_bool,
                ruia=ruia_bool,
                documento_ruia_id=documento_ruia_id,
                memorando=memorando_bool,
                documento_memorando_id=documento_memorando_id,
                tipo_acto=auto_admin,
                fecha_auto=fecha_auto_date,
                documento_acto_id=documento_acto_id,
            )
        )
        await db.execute(stmt)

        # Preparar datos nuevos
        datos_nuevos = {
            "id": ejecucion_id,
            "etapa_id": registro.etapa_id,
            "cobro_coactivo": cobro_coactivo_bool,
            "documento_cobro_id": documento_cobro_id,
            "disposicion": disposicion_bool,
            "ruia": ruia_bool,
            "documento_ruia_id": documento_ruia_id,
            "memorando": memorando_bool,
            "documento_memorando_id": documento_memorando_id,
            "tipo_acto": auto_admin,
            "fecha_auto": fecha_auto,
            "documento_acto_id": documento_acto_id,
        }
        
        # Obtener información del usuario para auditoría
        user_info = get_user_info_from_headers(request)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=usuario_id,
            documento_usuario=user_info["documento"],
            nombre_usuario=user_info["nombre"],
            tabla_afectada="EjecucionSancion",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de ejecución de sanción ID {ejecucion_id}",
            expediente_id=expediente_id,
            expediente_radicado=registro.radicado,
            id_registro=str(ejecucion_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )
        
        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )
        
        await db.commit()
        
        return JSONResponse(
            content={
                "ok": True,
                "id": ejecucion_id,
                "message": "Ejecución de la sanción actualizada correctamente"
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error actualizando ejecución de sanción: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.post("/audit/batch")
async def obtener_etapas_batch(
    request: Request,
    etapa_ids: list[int],
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene información de múltiples etapas por sus IDs.
    Retorna {etapa_id: nombre_tipo_etapa}
    """
    try:
        verify_gateway_token(request)
        
        if not etapa_ids or len(etapa_ids) == 0:
            return JSONResponse(
                content={"ok": True, "data": {}},
                status_code=200
            )
        
        if len(etapa_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="Máximo 100 etapas por solicitud"
            )
        
        # Consultar etapas con su tipo
        stmt = select(
            Etapa.id,
            TipoEtapa.nombre
        ).join(
            TipoEtapa, Etapa.tipo_etapa_id == TipoEtapa.id, isouter=True
        ).where(Etapa.id.in_(etapa_ids))
        
        result = await db.execute(stmt)
        etapas = result.fetchall()
        
        etapas_map = {
            etapa.id: etapa.nombre or f"Etapa {etapa.id}"
            for etapa in etapas
        }
        
        return JSONResponse(
            content={"ok": True, "data": etapas_map},
            status_code=200
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo etapas batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error al obtener información de etapas"
        )


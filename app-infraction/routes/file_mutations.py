from fastapi import Request, APIRouter, Depends, HTTPException, Query, Path as PathParam
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func, desc, union_all, literal
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime, date, timedelta
from pydantic import BaseModel
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv
from typing import List
import logging
import os
import pytz
import re
import holidays

from db.deps import get_db_managed
from db.models.recurso_afectado import RecursoAfectado
from db.models.expediente_recurso import ExpedienteRecurso
from db.models.expediente_tipo_afectacion import ExpedienteTipoAfectacion
from db.models.tipo_afectacion import TipoAfectacion
from db.models.quejoso_expediente import QuejosoExpediente
from db.models.expediente import Expediente
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.informe_tecnico import InformeTecnico
from db.models.medida_preventiva import MedidaPreventiva
from db.models.notificacion import Notificacion
from db.models.comunicacion import Comunicacion
from db.models.acto_administrativo import ActoAdministrativo
from db.models.vereda import Vereda
from db.models.municipio import Municipio
from db.models.radicado_asociado import RadicadoAsociado
from db.models.oficio_remite import OficioRemite
from db.models.solicitud_informacion import SolicitudInformacion
from db.models.quejoso import Quejoso
from db.models.auditoria import Auditoria

from core.permission import Permission
ASSIGN_PERMISSION = Permission.ASSIGN_PERMISSION
FILE_MANAGE = Permission.FILE_MANAGE
LOG_PERMISSION = Permission.LOG_PERMISSION

router = APIRouter()
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_DAYS = os.getenv("JWT_EXP_DAYS")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://api-gateway:8000")

bogota_tz = pytz.timezone("America/Bogota")
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = BASE_DIR / "uploads" / "expedientes"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from .models.file_models import (
    ExpedienteSchema,
    QuejosoSchema,
    BulkEncargadoRequest,
    FiltroAvanzado,
)

from utils.verify_token import verify_gateway_token
from utils.log import insert_log
from services.notification import create_notification
from services.users import get_users_by_permission, get_user_info, verify_permission
from services.involved import get_involved_by_expedientes_ids
from services.docs import download_unified_pdf


def normalize_radicados_asociados(radicados: List[str]) -> List[str]:
    """Normaliza, limpia y deduplica radicados asociados preservando orden."""
    normalized: List[str] = []
    seen = set()

    for radicado in radicados or []:
        value = str(radicado).strip().upper()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)

    return normalized


@router.post("/complainer/add")
async def crear_quejoso(
    request: Request,
    quejoso: QuejosoSchema,
    db: AsyncSession = Depends(get_db_managed),
):
    verify_gateway_token(request)

    if quejoso.anonimo:
        new_quejoso = Quejoso(anonimo=True)
    else:
        nombre = quejoso.nombre.strip() if quejoso.nombre else None
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre del quejoso es obligatorio")

        _nombre_norm = re.sub(r"[áàäâ]", "a", nombre.lower())
        if re.search(r"\banon[io]", _nombre_norm):
            raise HTTPException(status_code=400, detail="El nombre no puede hacer referencia a un quejoso anónimo")

        telefono = quejoso.telefono.strip() if quejoso.telefono else None
        correo = quejoso.correo.strip() if quejoso.correo else None

        if telefono and not telefono.isdigit():
            raise HTTPException(status_code=400, detail="El teléfono debe contener solo números")

        if telefono and len(telefono) > 10:
            raise HTTPException(status_code=400, detail="El teléfono no puede tener más de 10 dígitos")

        if correo and not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", correo):
            raise HTTPException(status_code=400, detail="El correo no tiene un formato válido")

        new_quejoso = Quejoso(
            nombre=nombre,
            telefono=telefono,
            correo=correo,
            anonimo=False,
        )

    db.add(new_quejoso)
    await db.commit()
    await db.refresh(new_quejoso)

    data = {
        "id": new_quejoso.id,
        "nombre": new_quejoso.nombre,
        "telefono": new_quejoso.telefono,
        "correo": new_quejoso.correo,
        "anonimo": new_quejoso.anonimo,
    }

    return JSONResponse(content={"ok": True, "data": data}, status_code=201)


@router.put("/{expediente_id}/basic-data")
async def actualizar_informacion_expediente(
    request: Request,
    expediente_id: int,
    expediente: ExpedienteSchema,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Endpoint optimizado para actualizar información básica del expediente.
    Guarda TODOS los datos anteriores y nuevos en auditoría sin eliminar información.
    """
    try:
        token_data = verify_gateway_token(request)
        user_id = token_data["user_id"] if isinstance(token_data, dict) else token_data

        # VERIFICAR EXPEDIENTE Y PERMISOS
        stmt_check = select(Expediente).where(Expediente.id == expediente_id)
        res_check = await db.execute(stmt_check)
        expediente_actual = res_check.scalar_one_or_none()

        if expediente_actual is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        
        if expediente_actual.abogado_responsable_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para actualizar este expediente"
            )

        # RECOPILAR DATOS ANTERIORES COMPLETOS
        
        # Obtener recursos anteriores con nombres
        stmt_recursos_ant = (
            select(RecursoAfectado.id, RecursoAfectado.nombre)
            .join(ExpedienteRecurso, ExpedienteRecurso.recurso_id == RecursoAfectado.id)
            .where(ExpedienteRecurso.expediente_id == expediente_actual.id)
        )
        res_recursos_ant = await db.execute(stmt_recursos_ant)
        recursos_anteriores = [row[1] for row in res_recursos_ant.fetchall()]

        # Obtener quejosos anteriores
        stmt_quejosos_ant = (
            select(Quejoso.nombre, Quejoso.telefono, Quejoso.anonimo)
            .join(QuejosoExpediente, QuejosoExpediente.quejoso_id == Quejoso.id)
            .where(QuejosoExpediente.expediente_id == expediente_actual.id)
        )
        res_quejosos_ant = await db.execute(stmt_quejosos_ant)
        quejosos_anteriores = [
            {"nombre": row[0] or ("Anónimo" if row[2] else "Sin nombre"), "telefono": row[1]}
            for row in res_quejosos_ant.fetchall()
        ]

        # Obtener radicados asociados anteriores
        stmt_radicados_ant = select(RadicadoAsociado.id, RadicadoAsociado.radicado).where(
            RadicadoAsociado.expediente_id == expediente_actual.id
        )
        res_radicados_ant = await db.execute(stmt_radicados_ant)
        radicados_anteriores = [row[1] for row in res_radicados_ant.fetchall()]

        # Obtener tipos de afectación anteriores
        stmt_tipos_ant = (
            select(TipoAfectacion.nombre)
            .join(ExpedienteTipoAfectacion, ExpedienteTipoAfectacion.tipo_afectacion_id == TipoAfectacion.id)
            .where(ExpedienteTipoAfectacion.expediente_id == expediente_actual.id)
        )
        res_tipos_ant = await db.execute(stmt_tipos_ant)
        tipos_anteriores = res_tipos_ant.scalars().all()

        # Obtener nombre de vereda anterior
        vereda_anterior_nombre = None
        if expediente_actual.vereda_id:
            res_vereda_ant = await db.execute(
                select(Vereda.nombre).where(Vereda.id == expediente_actual.vereda_id)
            )
            vereda_anterior_nombre = res_vereda_ant.scalar_one_or_none()

        abogado_ant_info = {}
        if expediente_actual.abogado_responsable_id:
            abogado_ant_info = (await get_user_info([expediente_actual.abogado_responsable_id])).get(
                expediente_actual.abogado_responsable_id, {}
            )

        datos_anteriores = {
            "radicado": expediente_actual.radicado,
            "fecha_radicado": expediente_actual.fecha_radicado.isoformat() if expediente_actual.fecha_radicado else None,
            "direccion": expediente_actual.direccion,
            "descripcion": expediente_actual.descripcion,
            "vereda": vereda_anterior_nombre,
            "abogado_responsable": abogado_ant_info.get("nombre", f"ID {expediente_actual.abogado_responsable_id}"),
            "recursos": recursos_anteriores,
            "tipos_afectacion": list(tipos_anteriores),
            "quejosos": quejosos_anteriores,
            "radicados_asociados": radicados_anteriores,
        }
        
        # 3. VALIDAR RADICADO ÚNICO
        if expediente.radicado != expediente_actual.radicado:
            stmt_duplicado = select(Expediente).where(
                and_(
                    Expediente.radicado == expediente.radicado,
                    Expediente.id != expediente_id
                )
            )
            result_duplicado = await db.execute(stmt_duplicado)
            if result_duplicado.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="El radicado ya está en uso")

        # 4. ACTUALIZAR EXPEDIENTE
        stmt_update = (
            update(Expediente)
            .where(Expediente.id == expediente_id)
            .values(
                radicado=expediente.radicado,
                fecha_radicado=expediente.fecha_radicado,
                direccion=expediente.direccion,
                vereda_id=expediente.vereda_id,
                descripcion=expediente.descripcion,
            )
        )
        await db.execute(stmt_update)
        
        # 5. ACTUALIZAR RELACIONES (Quejosos)
        quejosos_nuevos = []
        await db.execute(
            delete(QuejosoExpediente).where(
                QuejosoExpediente.expediente_id == expediente_actual.id
            )
        )
        if expediente.quejosos_ids:
            for quejoso_id in expediente.quejosos_ids:
                insert_stmt = pg_insert(QuejosoExpediente).values(
                    expediente_id=expediente_actual.id,
                    quejoso_id=quejoso_id
                ).on_conflict_do_nothing()
                await db.execute(insert_stmt)
            
            # Obtener lista completa actualizada
            stmt_quejosos_new = (
                select(Quejoso.nombre, Quejoso.telefono, Quejoso.anonimo)
                .join(QuejosoExpediente, QuejosoExpediente.quejoso_id == Quejoso.id)
                .where(QuejosoExpediente.expediente_id == expediente_actual.id)
            )
            res_quejosos_new = await db.execute(stmt_quejosos_new)
            quejosos_nuevos = [
                {"nombre": row[0] or ("Anónimo" if row[2] else "Sin nombre"), "telefono": row[1]}
                for row in res_quejosos_new.fetchall()
            ]
    
        # ACTUALIZAR RELACIONES (Radicados Asociados)
        radicados_nuevos = []
        radicados_normalizados = normalize_radicados_asociados(expediente.radicados_asociados)
        await db.execute(
            delete(RadicadoAsociado).where(
                RadicadoAsociado.expediente_id == expediente_actual.id
            )
        )
        if radicados_normalizados:
            for radicado in radicados_normalizados:
                insert_stmt = pg_insert(RadicadoAsociado).values(
                    expediente_id=expediente_actual.id,
                    radicado=radicado
                ).on_conflict_do_nothing()
                await db.execute(insert_stmt)
            
            # Obtener lista completa actualizada
            stmt_radicados_new = select(RadicadoAsociado.id, RadicadoAsociado.radicado).where(
                RadicadoAsociado.expediente_id == expediente_actual.id
            )
            res_radicados_new = await db.execute(stmt_radicados_new)
            radicados_nuevos = [row[1] for row in res_radicados_new.fetchall()]
        
        # ACTUALIZAR RELACIONES (Recursos)
        recursos_nuevos = []
        await db.execute(
            delete(ExpedienteRecurso).where(
                ExpedienteRecurso.expediente_id == expediente_actual.id
            )
        )
        if expediente.recursos_ids:
            for recurso_id in expediente.recursos_ids:
                insert_stmt = pg_insert(ExpedienteRecurso).values(
                    expediente_id=expediente_actual.id,
                    recurso_id=recurso_id
                ).on_conflict_do_nothing()
                await db.execute(insert_stmt)

            stmt_recursos_new = (
                select(RecursoAfectado.id, RecursoAfectado.nombre)
                .join(ExpedienteRecurso, ExpedienteRecurso.recurso_id == RecursoAfectado.id)
                .where(ExpedienteRecurso.expediente_id == expediente_actual.id)
            )
            res_recursos_new = await db.execute(stmt_recursos_new)
            recursos_nuevos = [row[1] for row in res_recursos_new.fetchall()]

        # ACTUALIZAR RELACIONES (Tipos de afectación)
        tipos_nuevos = []
        await db.execute(
            delete(ExpedienteTipoAfectacion).where(
                ExpedienteTipoAfectacion.expediente_id == expediente_actual.id
            )
        )
        if expediente.tipos_afectacion_ids:
            for tipo_id in expediente.tipos_afectacion_ids:
                insert_stmt = pg_insert(ExpedienteTipoAfectacion).values(
                    expediente_id=expediente_actual.id,
                    tipo_afectacion_id=tipo_id
                ).on_conflict_do_nothing()
                await db.execute(insert_stmt)

            stmt_tipos_new = (
                select(TipoAfectacion.nombre)
                .join(ExpedienteTipoAfectacion, ExpedienteTipoAfectacion.tipo_afectacion_id == TipoAfectacion.id)
                .where(ExpedienteTipoAfectacion.expediente_id == expediente_actual.id)
            )
            res_tipos_new = await db.execute(stmt_tipos_new)
            tipos_nuevos = res_tipos_new.scalars().all()

        # Nombre de vereda nueva
        res_vereda_new = await db.execute(
            select(Vereda.nombre).where(Vereda.id == expediente.vereda_id)
        )
        vereda_nueva_nombre = res_vereda_new.scalar_one_or_none()

        datos_nuevos = {
            "radicado": expediente.radicado,
            "fecha_radicado": expediente.fecha_radicado.isoformat() if expediente.fecha_radicado else None,
            "direccion": expediente.direccion,
            "descripcion": expediente.descripcion,
            "vereda": vereda_nueva_nombre,
            "abogado_responsable": abogado_ant_info.get("nombre", f"ID {expediente_actual.abogado_responsable_id}"),
            "recursos": recursos_nuevos,
            "tipos_afectacion": list(tipos_nuevos),
            "quejosos": quejosos_nuevos,
            "radicados_asociados": radicados_nuevos,
        }

        
        # REGISTRAR AUDITORÍA COMPLETA
        audit_result = await insert_log(
            db=db,
            tipo_evento="UPDATE_EXPEDIENTE_BASICO",
            resultado="OK",
            usuario_id=user_id,
            detalle=f"Actualización completa de expediente '{expediente_actual.radicado}' → '{expediente.radicado}'",
            expediente_id=expediente_actual.id,
            expediente_radicado=expediente.radicado,
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
                "message": "Expediente actualizado exitosamente",
                "expediente_id": expediente_actual.id,
                "radicado": expediente.radicado
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al actualizar expediente {expediente_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/add")
async def agregar_expediente(
    request: Request,
    expediente: ExpedienteSchema,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    # Validar radicado duplicado
    duplicado = await db.execute(
        select(Expediente.id).where(Expediente.radicado == expediente.radicado)
    )
    if duplicado.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="El radicado ya existe")

    # Crear expediente
    nuevo_expediente = Expediente(
        radicado=expediente.radicado,
        fecha_radicado=expediente.fecha_radicado,
        vereda_id=expediente.vereda_id,
        abogado_responsable_id=expediente.abogado_responsable_id,
        direccion=expediente.direccion,
        descripcion=expediente.descripcion,
    )
    db.add(nuevo_expediente)
    await db.flush()
    expediente_id = nuevo_expediente.id  # SQLAlchemy lo popula tras el flush

    # Agregar relaciones en batch
    radicados_normalizados = normalize_radicados_asociados(expediente.radicados_asociados)

    for quejoso_id in expediente.quejosos_ids:
        db.add(QuejosoExpediente(
            expediente_id=expediente_id,
            quejoso_id=quejoso_id,
        ))

    for recurso_id in expediente.recursos_ids:
        db.add(ExpedienteRecurso(
            expediente_id=expediente_id,
            recurso_id=recurso_id,
        ))

    for tipo_id in expediente.tipos_afectacion_ids:
        db.add(ExpedienteTipoAfectacion(
            expediente_id=expediente_id,
            tipo_afectacion_id=tipo_id,
        ))

    for radicado in radicados_normalizados:
        db.add(RadicadoAsociado(
            expediente_id=expediente_id,
            radicado=radicado,
        ))

    await db.flush()  # Un solo flush para todas las relaciones

    # Obtener datos relacionados para auditoría
    quejosos_audit = (await db.execute(
        select(Quejoso.nombre, Quejoso.telefono, Quejoso.correo, Quejoso.anonimo)
        .join(QuejosoExpediente)
        .where(QuejosoExpediente.expediente_id == expediente_id)
    )).fetchall()
    quejosos_audit = [
        {
            "nombre": q[0] or ("Anónimo" if q[3] else "Sin nombre"),
            "telefono": q[1],
            "correo": q[2],
        }
        for q in quejosos_audit
    ]

    recursos_audit = (await db.execute(
        select(RecursoAfectado.nombre)
        .join(ExpedienteRecurso)
        .where(ExpedienteRecurso.expediente_id == expediente_id)
    )).scalars().all()

    tipos_audit = (await db.execute(
        select(TipoAfectacion.nombre)
        .join(ExpedienteTipoAfectacion, ExpedienteTipoAfectacion.tipo_afectacion_id == TipoAfectacion.id)
        .where(ExpedienteTipoAfectacion.expediente_id == expediente_id)
    )).scalars().all()

    vereda_nombre_audit = None
    if expediente.vereda_id:
        vereda_nombre_audit = (await db.execute(
            select(Vereda.nombre).where(Vereda.id == expediente.vereda_id)
        )).scalar_one_or_none()

    abogado_info = {}
    if expediente.abogado_responsable_id:
        abogado_info = (await get_user_info([expediente.abogado_responsable_id])).get(
            expediente.abogado_responsable_id, {}
        )

    audit_result = await insert_log(
        db=db,
        tipo_evento="INSERT_EXPEDIENTE",
        resultado="OK",
        usuario_id=user_id,
        expediente_id=expediente_id,
        expediente_radicado=expediente.radicado,
        detalle=f"Creación de expediente {expediente.radicado}",
        datos_nuevos={
            "radicado": expediente.radicado,
            "fecha_radicado": expediente.fecha_radicado.isoformat() if expediente.fecha_radicado else None,
            "abogado_responsable": abogado_info.get("nombre", f"ID {expediente.abogado_responsable_id}"),
            "direccion": expediente.direccion,
            "descripcion": expediente.descripcion,
            "vereda": vereda_nombre_audit,
            "recursos": list(recursos_audit),
            "tipos_afectacion": list(tipos_audit),
            "quejosos": quejosos_audit,
            "radicados_asociados": radicados_normalizados,
        }
    )

    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse(
        content={"ok": True, "expediente_id": expediente_id},
        status_code=200
    )


@router.patch("/{expediente_id}/charge/{encargado_id}")
async def actualizar_encargado_de_expediente(
    request: Request,
    expediente_id: int,
    encargado_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]


    # Obtener datos anteriores
    stmt_check = select(Expediente).where(Expediente.id == expediente_id)
    res_check = await db.execute(stmt_check)
    expediente = res_check.scalar_one_or_none()

    if expediente is None:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")

    enc_ant_nombre = None
    if expediente.abogado_responsable_id:
        enc_ant_info = (await get_user_info([expediente.abogado_responsable_id])).get(expediente.abogado_responsable_id, {})
        enc_ant_nombre = enc_ant_info.get("nombre")

    datos_anteriores = {
        "radicado": expediente.radicado,
        "encargado": enc_ant_nombre or f"ID {expediente.abogado_responsable_id}" if expediente.abogado_responsable_id else None,
    }

    new_value = None if encargado_id == 0 else encargado_id

    # Actualizar encargado
    stmt = (
        update(Expediente)
        .where(Expediente.id == expediente_id)
        .values({"abogado_responsable_id": new_value})
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(stmt)

    if result.rowcount == 0:
        raise HTTPException(status_code=400, detail="Expediente no encontrado")

    enc_nuevo_nombre = None
    if new_value:
        enc_nuevo_info = (await get_user_info([new_value])).get(new_value, {})
        enc_nuevo_nombre = enc_nuevo_info.get("nombre")

    datos_nuevos = {
        "radicado": expediente.radicado,
        "encargado": enc_nuevo_nombre or f"ID {new_value}" if new_value else None,
    }

    # Guardar auditoría
    audit_result = await insert_log(
        db=db,
        tipo_evento="UPDATE_ENCARGADO_EXPEDIENTE",
        resultado="OK",
        usuario_id=user_id,
        detalle=f"Actualización de encargado del expediente {expediente.radicado}",
        expediente_id=expediente.id,
        expediente_radicado=expediente.radicado,
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

    # Crear notificación si se asignó un encargado
    if encargado_id != 0:
        notif_result = await create_notification(
            mensaje=f"Se te ha asignado el expediente de infraccion {expediente.radicado}",
            id_vinculada=str(expediente_id),
            tipo="expediente",
            usuario_id=encargado_id
        )
        
        # Solo loguear si falla, no interrumpir el flujo
        if not notif_result["ok"]:
            logger.warning(
                f"No se pudo crear notificación para usuario {encargado_id}: {notif_result['message']}"
            )

    return JSONResponse(
        content={"ok": True, "message": "Encargado actualizado"},
        status_code=200
    )


@router.patch("/charge/bulk")
async def actualizar_encargado_bulk(
    request: Request,
    data: BulkEncargadoRequest,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]



    expediente_ids = list(dict.fromkeys(data.expediente_id or []))
    if not expediente_ids:
        raise HTTPException(status_code=400, detail="Debe enviar al menos un expediente_id")

    new_value = None if data.encargado_id == 0 else data.encargado_id
    updated = []

    # Cargar expedientes existentes en una sola consulta.
    res_check = await db.execute(
        select(Expediente).where(Expediente.id.in_(expediente_ids))
    )
    expedientes = res_check.scalars().all()

    if not expedientes:
        return JSONResponse(
            content={"ok": True, "updated": [], "msg": "No se encontraron expedientes para actualizar"},
            status_code=200,
        )

    ids_existentes = [exp.id for exp in expedientes]

    # Actualización masiva en una sola sentencia SQL.
    await db.execute(
        update(Expediente)
        .where(Expediente.id.in_(ids_existentes))
        .values({"abogado_responsable_id": new_value})
        .execution_options(synchronize_session=False)
    )

    # Se mantiene auditoría por cada expediente actualizado.
    enc_bulk_nombre = None
    if new_value:
        enc_bulk_info = (await get_user_info([new_value])).get(new_value, {})
        enc_bulk_nombre = enc_bulk_info.get("nombre")

    for expediente in expedientes:
        enc_ant_bulk = None
        if expediente.abogado_responsable_id:
            enc_ant_bulk_info = (await get_user_info([expediente.abogado_responsable_id])).get(expediente.abogado_responsable_id, {})
            enc_ant_bulk = enc_ant_bulk_info.get("nombre") or f"ID {expediente.abogado_responsable_id}"
        datos_anteriores = {
            "radicado": expediente.radicado,
            "encargado": enc_ant_bulk,
        }

        await insert_log(
            db=db,
            tipo_evento="BULK_UPDATE_ENCARGADO",
            resultado="OK",
            usuario_id=user_id,
            detalle=f"Actualización masiva de encargado del expediente {expediente.radicado}",
            expediente_id=expediente.id,
            expediente_radicado=expediente.radicado,
            datos_anteriores=datos_anteriores,
            datos_nuevos={"radicado": expediente.radicado, "encargado": enc_bulk_nombre or f"ID {new_value}" if new_value else None},
        )
        updated.append({"id": expediente.id, "radicado": expediente.radicado})

    await db.commit()

    if new_value:
        for expediente_actualizado in updated:
            await create_notification(
                mensaje=f"Se te ha asignado el expediente de infraccion {expediente_actualizado['radicado']}",
                id_vinculada=str(expediente_actualizado['id']),
                tipo="expediente",
                usuario_id=new_value
            )

    return JSONResponse(
        content={"ok": True, "updated": updated, "msg": f"Se actualizaron {len(updated)} expedientes"},
        status_code=200
    )


# Archivar expediente
@router.patch("/{expediente_id}/archive")
async def archivar_expediente(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Archiva un expediente. Solo disponible cuando se ha completado la etapa de Ejecución de la Sanción.
    Esta acción no se puede revertir.
    """
    try:
        token_data = verify_gateway_token(request)
        user_id = token_data["user_id"]

        # Obtener datos anteriores
        stmt_check = select(Expediente).where(Expediente.id == expediente_id)
        res_check = await db.execute(stmt_check)
        expediente = res_check.scalar_one_or_none()

        if expediente is None:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        # Verificar que el usuario es el encargado
        if expediente.abogado_responsable_id != user_id:
            raise HTTPException(status_code=403, detail="No tiene permisos para archivar este expediente")

        # Verificar si ya está archivado
        if expediente.archivado:
            raise HTTPException(status_code=400, detail="El expediente ya está archivado")

        datos_anteriores = {
            "radicado": expediente.radicado,
            "archivado": expediente.archivado
        }

        # Archivar expediente
        stmt = (
            update(Expediente)
            .where(Expediente.id == expediente_id)
            .values(archivado=True)
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt)

        if result.rowcount == 0:
            raise HTTPException(status_code=400, detail="No se pudo archivar el expediente")

        datos_nuevos = {
            "radicado": expediente.radicado,
            "archivado": True
        }

        # Guardar auditoría
        audit_result = await insert_log(
            db=db,
            tipo_evento="UPDATE_ARCHIVE_EXPEDIENTE",
            resultado="OK",
            usuario_id=user_id,
            detalle=f"Archivado del expediente {expediente.radicado}",
            expediente_id=expediente.id,
            expediente_radicado=expediente.radicado,
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
            content={"ok": True, "message": "Expediente archivado exitosamente"},
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error archivando expediente: {e}")
        raise HTTPException(status_code=500, detail="Error al archivar expediente")


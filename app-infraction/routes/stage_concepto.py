from fastapi import Request, APIRouter, Depends, HTTPException, Path as PathParam
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
import holidays
import logging
import os
import pytz
import re

from db.deps import get_db_managed
from db.models.expediente import Expediente
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.informe_tecnico import InformeTecnico
from db.models.medida_preventiva import MedidaPreventiva
from db.models.tipo_medida import TipoMedida
from db.models.acto_administrativo import ActoAdministrativo
from db.models.comunicacion import Comunicacion
from db.models.notificacion import Notificacion
from db.models.oficio_remite import OficioRemite
from db.models.solicitud_informacion import SolicitudInformacion
from db.models.expediente_involucrado import ExpedienteInvolucrado

router = APIRouter()
load_dotenv()

bogota_tz = pytz.timezone("America/Bogota")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from utils.verify_token import verify_gateway_token
from services.users import get_user_info
from services.involved import get_involucrados_by_ids
from services.docs import decrement_file_usage
from services.etapas import build_acto_for_frontend as _build_acto_for_frontend
from services.etapas import get_expediente_con_permiso
from utils.log import insert_log


class ConceptoCreateBody(BaseModel):
    tipo_acogida_concepto: str


class ConceptoUpdateBody(BaseModel):
    tipo_acogida_concepto: str
    dias_termino: Optional[int] = None


class OficioRemiteBody(BaseModel):
    radicado: str
    fecha_radicado: str
    fecha_remitido: str
    archivo_remite_id: int


class SolicitudInformacionBody(BaseModel):
    radicado: str
    fecha_radicado: str
    archivo_solicitud_id: int


RADICADO_EE_REGEX = re.compile(r"^\d{4}EE\d{4,5}$")


def validar_radicado_ee(radicado: str) -> None:
    if not RADICADO_EE_REGEX.match(radicado.strip()):
        raise HTTPException(
            status_code=400,
            detail="El radicado debe tener el formato: 4 dígitos + EE + 4 o 5 dígitos (ej: 2024EE0001)",
        )


def validar_fecha_no_futura(fecha_str: str, campo: str) -> None:
    try:
        fecha = datetime.strptime(fecha_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{campo} no tiene un formato de fecha válido (YYYY-MM-DD)")
    if fecha > date.today():
        raise HTTPException(status_code=400, detail=f"{campo} no puede ser una fecha futura")


VALID_TIPOS_CONCEPTO = {"AUTO_REQUERIMIENTO", "OFICIO", "RESOLUCION_ARCHIVO"}
VALID_DIAS_TERMINO = {10, 15, 30, 60, 120}


def calcular_fecha_termino_habiles(fecha_inicio: date, dias_habiles: int) -> date:
    co_holidays = holidays.Colombia(years=range(fecha_inicio.year, fecha_inicio.year + 2))
    contador = 0
    current = fecha_inicio
    while contador < dias_habiles:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in co_holidays:
            contador += 1
    return current


async def _build_concepto_response(db: AsyncSession, etapa: EtapaAcogerConcepto) -> dict:
    """Construye el dict de respuesta enriquecido para una EtapaAcogerConcepto."""
    acto_data = None
    if etapa.acto_administrativo_id:
        acto = await db.scalar(
            select(ActoAdministrativo).where(ActoAdministrativo.id == etapa.acto_administrativo_id)
        )
        if acto:
            acto_data = await _build_acto_for_frontend(db, acto)

    # Explicit query to avoid lazy-load in async context
    oficio_row = await db.scalar(
        select(OficioRemite).where(OficioRemite.etapa_acoger_concepto_id == etapa.id)
    )
    oficio_data = None
    if oficio_row:
        oficio_data = {
            "id": oficio_row.id,
            "radicado": oficio_row.radicado,
            "fecha_radicado": oficio_row.fecha_radicado,
            "fecha_remitido": oficio_row.fecha_remitido,
            "archivo_remite_id": oficio_row.archivo_remite_id,
        }

    solicitud_row = await db.scalar(
        select(SolicitudInformacion).where(SolicitudInformacion.etapa_acoger_concepto_id == etapa.id)
    )
    solicitud_data = None
    if solicitud_row:
        solicitud_data = {
            "id": solicitud_row.id,
            "radicado": solicitud_row.radicado,
            "fecha_radicado": solicitud_row.fecha_radicado,
            "archivo_solicitud_id": solicitud_row.archivo_solicitud_id,
        }

    return {
        "id": etapa.id,
        "expediente_id": etapa.expediente_id,
        "tipo_acogida_concepto": etapa.tipo_acogida_concepto,
        "dias_termino": etapa.dias_termino,
        "fecha_termino_calculada": etapa.fecha_termino_calculada.isoformat() if etapa.fecha_termino_calculada else None,
        "acto_administrativo_id": etapa.acto_administrativo_id,
        "fecha_creacion": etapa.fecha_creacion.isoformat(),
        "acto_admin": acto_data,
        "oficio_remite": oficio_data,
        "solicitud_informacion": solicitud_data,
    }


# ── ETAPA CONCEPTO ────────────────────────────────────────────────────────────

@router.get("/concepto/{expediente_id}", status_code=200)
async def obtener_concepto(
    request: Request,
    expediente_id: int = PathParam(...),
    db: AsyncSession = Depends(get_db_managed),
):
    verify_gateway_token(request)

    etapa = await db.scalar(
        select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.expediente_id == expediente_id)
    )

    if not etapa:
        # Check if creable
        informe_visita = await db.scalar(
            select(InformeTecnico).where(
                InformeTecnico.expediente_id == expediente_id,
                InformeTecnico.tipo_informe == "VISITA",
                InformeTecnico.fecha_aceptacion_informe.isnot(None),
            )
        )
        creable = informe_visita is not None
        creable_msg = None if creable else 'El informe técnico de "VISITA" aún no ha sido aceptado'
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "detail": "Etapa concepto no encontrada",
                "creable": creable,
                "creable_msg": creable_msg,
            },
        )

    data = await _build_concepto_response(db, etapa)
    return JSONResponse(content={"ok": True, "data": data}, status_code=200)


@router.post("/concepto/{expediente_id}", status_code=201)
async def crear_concepto(
    request: Request,
    expediente_id: int = PathParam(...),
    body: ConceptoCreateBody = ...,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    if body.tipo_acogida_concepto not in VALID_TIPOS_CONCEPTO:
        raise HTTPException(status_code=400, detail="tipo_acogida_concepto inválido")

    _eid, exp_radicado, _abg = await get_expediente_con_permiso(db, expediente_id, user_id)

    if await db.scalar(select(EtapaAcogerConcepto.id).where(EtapaAcogerConcepto.expediente_id == expediente_id)):
        raise HTTPException(status_code=409, detail="La etapa concepto ya existe para este expediente")

    informe_visita = await db.scalar(
        select(InformeTecnico).where(
            InformeTecnico.expediente_id == expediente_id,
            InformeTecnico.tipo_informe == "VISITA",
            InformeTecnico.fecha_aceptacion_informe.isnot(None),
        )
    )
    if not informe_visita:
        raise HTTPException(status_code=400, detail='El informe técnico de "VISITA" aún no ha sido aceptado')

    nueva = EtapaAcogerConcepto(
        expediente_id=expediente_id,
        tipo_acogida_concepto=body.tipo_acogida_concepto,
    )
    db.add(nueva)
    await db.flush()

    audit_result = await insert_log(
        db=db,
        tipo_evento="CREAR_ETAPA_CONCEPTO",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle="Creación Etapa concepto",
        expediente_id=expediente_id,
        expediente_radicado=exp_radicado,
        datos_nuevos={"tipo_acogida_concepto": body.tipo_acogida_concepto},
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()
    await db.refresh(nueva)

    data = await _build_concepto_response(db, nueva)
    return JSONResponse(content={"ok": True, "data": data, "message": "Etapa concepto creada correctamente"}, status_code=201)


@router.put("/concepto/{etapa_concepto_id}", status_code=200)
async def actualizar_concepto(
    request: Request,
    etapa_concepto_id: int = PathParam(...),
    body: ConceptoUpdateBody = ...,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    if body.tipo_acogida_concepto not in VALID_TIPOS_CONCEPTO:
        raise HTTPException(status_code=400, detail="tipo_acogida_concepto inválido")

    etapa = await db.scalar(select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.id == etapa_concepto_id))
    if not etapa:
        raise HTTPException(status_code=404, detail="Etapa concepto no encontrada")

    exp_row = (await db.execute(
        select(Expediente.radicado, Expediente.abogado_responsable_id)
        .where(Expediente.id == etapa.expediente_id)
    )).fetchone()
    if not exp_row:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")
    exp_radicado, abogado_id = exp_row
    if abogado_id != user_id:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

    tipo_anterior = etapa.tipo_acogida_concepto
    tipo_nuevo = body.tipo_acogida_concepto
    datos_anteriores = {
        "tipo_acogida_concepto": tipo_anterior,
        "dias_termino": etapa.dias_termino,
    }

    cierre_eliminado = False

    # Si cambia el tipo: eliminar toda la data asociada
    if tipo_anterior != tipo_nuevo:
        if etapa.acto_administrativo_id:
            acto = await db.scalar(
                select(ActoAdministrativo).where(ActoAdministrativo.id == etapa.acto_administrativo_id)
            )
            if acto:
                docs_dec = []
                if acto.documento_acto_administrativo_id:
                    docs_dec.append(acto.documento_acto_administrativo_id)
                notifs = (await db.execute(
                    select(Notificacion).where(Notificacion.acto_administrativo_id == acto.id)
                )).scalars().all()
                for n in notifs:
                    if n.documento_citacion_id:
                        docs_dec.append(n.documento_citacion_id)
                    if n.documento_notificacion_id:
                        docs_dec.append(n.documento_notificacion_id)
                com = await db.scalar(
                    select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto.id)
                )
                if com and com.documento_comunicacion_id:
                    docs_dec.append(com.documento_comunicacion_id)
                if docs_dec:
                    await decrement_file_usage(list(set(docs_dec)))
                etapa.acto_administrativo_id = None
                await db.delete(acto)
                await db.flush()

        oficio = await db.scalar(
            select(OficioRemite).where(OficioRemite.etapa_acoger_concepto_id == etapa_concepto_id)
        )
        if oficio:
            if oficio.archivo_remite_id:
                await decrement_file_usage([oficio.archivo_remite_id])
            await db.delete(oficio)
            await db.flush()

        # También eliminar EtapaCierre si existe
        cierre = await db.scalar(
            select(EtapaCierre).where(EtapaCierre.expediente_id == etapa.expediente_id)
        )
        if cierre:
            if cierre.acto_administrativo_id:
                acto_cierre = await db.scalar(
                    select(ActoAdministrativo).where(ActoAdministrativo.id == cierre.acto_administrativo_id)
                )
                if acto_cierre:
                    docs_cierre = []
                    if acto_cierre.documento_acto_administrativo_id:
                        docs_cierre.append(acto_cierre.documento_acto_administrativo_id)
                    notifs_cierre = (await db.execute(
                        select(Notificacion).where(Notificacion.acto_administrativo_id == acto_cierre.id)
                    )).scalars().all()
                    for n in notifs_cierre:
                        if n.documento_citacion_id:
                            docs_cierre.append(n.documento_citacion_id)
                        if n.documento_notificacion_id:
                            docs_cierre.append(n.documento_notificacion_id)
                    com_cierre = await db.scalar(
                        select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto_cierre.id)
                    )
                    if com_cierre and com_cierre.documento_comunicacion_id:
                        docs_cierre.append(com_cierre.documento_comunicacion_id)
                    if docs_cierre:
                        await decrement_file_usage(list(set(docs_cierre)))
                    cierre.acto_administrativo_id = None
                    await db.delete(acto_cierre)
                    await db.flush()
            await db.delete(cierre)
            await db.flush()
            cierre_eliminado = True

        etapa.dias_termino = None
        etapa.fecha_termino_calculada = None

    etapa.tipo_acogida_concepto = tipo_nuevo

    if body.dias_termino is not None:
        if body.dias_termino not in VALID_DIAS_TERMINO:
            raise HTTPException(status_code=400, detail="dias_termino debe ser 10, 15, 30, 60 o 120")
        if tipo_nuevo != "AUTO_REQUERIMIENTO":
            raise HTTPException(status_code=400, detail="dias_termino solo aplica para AUTO_REQUERIMIENTO")
        etapa.dias_termino = body.dias_termino
        etapa.fecha_termino_calculada = calcular_fecha_termino_habiles(date.today(), body.dias_termino)

    await db.flush()

    audit_result = await insert_log(
        db=db,
        tipo_evento="ACTUALIZAR_ETAPA_CONCEPTO",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle="Actualización Etapa concepto",
        expediente_id=etapa.expediente_id,
        expediente_radicado=exp_radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos={"tipo_acogida_concepto": tipo_nuevo, "dias_termino": body.dias_termino},
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()
    await db.refresh(etapa)

    data = await _build_concepto_response(db, etapa)
    msg = "Etapa concepto actualizada correctamente"
    if cierre_eliminado:
        msg = "Tipo de acogida actualizado. La etapa de Cierre fue eliminada por el cambio de tipo."
    return JSONResponse(content={"ok": True, "data": data, "message": msg, "cierre_eliminado": cierre_eliminado}, status_code=200)


# ── OFICIO REMITE ─────────────────────────────────────────────────────────────

@router.post("/oficio-remite/{etapa_concepto_id}", status_code=201)
async def crear_oficio_remite(
    request: Request,
    etapa_concepto_id: int = PathParam(...),
    body: OficioRemiteBody = ...,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    etapa = await db.scalar(select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.id == etapa_concepto_id))
    if not etapa:
        raise HTTPException(status_code=404, detail="Etapa concepto no encontrada")
    if etapa.tipo_acogida_concepto != "OFICIO":
        raise HTTPException(status_code=400, detail="La etapa concepto no es de tipo OFICIO")

    exp_row = (await db.execute(
        select(Expediente.radicado, Expediente.abogado_responsable_id)
        .where(Expediente.id == etapa.expediente_id)
    )).fetchone()
    if not exp_row:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")
    exp_radicado, abogado_id = exp_row
    if abogado_id != user_id:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

    existing = await db.scalar(
        select(OficioRemite).where(OficioRemite.etapa_acoger_concepto_id == etapa_concepto_id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="El oficio remite ya existe para esta etapa")

    validar_radicado_ee(body.radicado)
    validar_fecha_no_futura(body.fecha_radicado, "Fecha Radicado")
    validar_fecha_no_futura(body.fecha_remitido, "Fecha Remitido")

    nuevo = OficioRemite(
        etapa_acoger_concepto_id=etapa_concepto_id,
        radicado=body.radicado,
        fecha_radicado=body.fecha_radicado,
        fecha_remitido=body.fecha_remitido,
        archivo_remite_id=body.archivo_remite_id,
    )
    db.add(nuevo)
    await db.flush()

    from services.docs import increment_file_usage
    await increment_file_usage([body.archivo_remite_id])

    audit_result = await insert_log(
        db=db,
        tipo_evento="CREAR_OFICIO_REMITE",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle="Creación oficio remite",
        expediente_id=etapa.expediente_id,
        expediente_radicado=exp_radicado,
        datos_nuevos={"radicado": body.radicado, "fecha_radicado": body.fecha_radicado, "fecha_remitido": body.fecha_remitido},
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "data": {"id": nuevo.id, "radicado": nuevo.radicado, "fecha_radicado": nuevo.fecha_radicado, "fecha_remitido": nuevo.fecha_remitido, "archivo_remite_id": nuevo.archivo_remite_id},
            "message": "Oficio remite creado correctamente",
        },
        status_code=201,
    )


@router.put("/oficio-remite/{oficio_id}", status_code=200)
async def actualizar_oficio_remite(
    request: Request,
    oficio_id: int = PathParam(...),
    body: OficioRemiteBody = ...,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    oficio = await db.scalar(select(OficioRemite).where(OficioRemite.id == oficio_id))
    if not oficio:
        raise HTTPException(status_code=404, detail="Oficio remite no encontrado")

    etapa = await db.scalar(select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.id == oficio.etapa_acoger_concepto_id))
    exp_row = (await db.execute(
        select(Expediente.radicado, Expediente.abogado_responsable_id)
        .where(Expediente.id == etapa.expediente_id)
    )).fetchone()
    if not exp_row:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")
    exp_radicado, abogado_id = exp_row
    if abogado_id != user_id:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

    validar_radicado_ee(body.radicado)
    validar_fecha_no_futura(body.fecha_radicado, "Fecha Radicado")
    validar_fecha_no_futura(body.fecha_remitido, "Fecha Remitido")

    datos_anteriores = {"radicado": oficio.radicado, "fecha_radicado": oficio.fecha_radicado, "fecha_remitido": oficio.fecha_remitido, "archivo_remite_id": oficio.archivo_remite_id}

    if body.archivo_remite_id != oficio.archivo_remite_id:
        from services.docs import increment_file_usage
        await decrement_file_usage([oficio.archivo_remite_id])
        await increment_file_usage([body.archivo_remite_id])

    oficio.radicado = body.radicado
    oficio.fecha_radicado = body.fecha_radicado
    oficio.fecha_remitido = body.fecha_remitido
    oficio.archivo_remite_id = body.archivo_remite_id
    await db.flush()

    audit_result = await insert_log(
        db=db,
        tipo_evento="ACTUALIZAR_OFICIO_REMITE",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle="Actualización oficio remite",
        expediente_id=etapa.expediente_id,
        expediente_radicado=exp_radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos={"radicado": body.radicado, "fecha_radicado": body.fecha_radicado, "fecha_remitido": body.fecha_remitido},
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "data": {"id": oficio.id, "radicado": oficio.radicado, "fecha_radicado": oficio.fecha_radicado, "fecha_remitido": oficio.fecha_remitido, "archivo_remite_id": oficio.archivo_remite_id},
            "message": "Oficio remite actualizado correctamente",
        },
        status_code=200,
    )


@router.post("/solicitud-informacion/{etapa_concepto_id}", status_code=201)
async def crear_solicitud_informacion(
    request: Request,
    etapa_concepto_id: int = PathParam(...),
    body: SolicitudInformacionBody = ...,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Crea la solicitud de información de la etapa de concepto.
    Independiente del tipo_acogida_concepto — se puede agregar en cualquier momento.
    """
    try:
        token_data = verify_gateway_token(request)
        user_id = token_data["user_id"]

        etapa = await db.scalar(select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.id == etapa_concepto_id))
        if not etapa:
            raise HTTPException(status_code=404, detail="Etapa concepto no encontrada")

        exp_row = (await db.execute(
            select(Expediente.radicado, Expediente.abogado_responsable_id)
            .where(Expediente.id == etapa.expediente_id)
        )).fetchone()
        if not exp_row:
            raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")
        exp_radicado, abogado_id = exp_row
        if abogado_id != user_id:
            raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

        existing = await db.scalar(
            select(SolicitudInformacion).where(SolicitudInformacion.etapa_acoger_concepto_id == etapa_concepto_id)
        )
        if existing:
            raise HTTPException(status_code=409, detail="La solicitud de información ya existe para esta etapa")

        validar_radicado_ee(body.radicado)
        validar_fecha_no_futura(body.fecha_radicado, "Fecha Radicado")

        nueva = SolicitudInformacion(
            etapa_acoger_concepto_id=etapa_concepto_id,
            radicado=body.radicado,
            fecha_radicado=body.fecha_radicado,
            archivo_solicitud_id=body.archivo_solicitud_id,
        )
        db.add(nueva)
        await db.flush()

        from services.docs import increment_file_usage
        await increment_file_usage([body.archivo_solicitud_id])

        audit_result = await insert_log(
            db=db,
            tipo_evento="CREAR_SOLICITUD_INFO",
            resultado="EXITOSO",
            usuario_id=user_id,
            detalle="Creación solicitud de información",
            expediente_id=etapa.expediente_id,
            expediente_radicado=exp_radicado,
            datos_nuevos={"radicado": body.radicado, "fecha_radicado": body.fecha_radicado},
        )
        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "data": {
                    "id": nueva.id,
                    "radicado": nueva.radicado,
                    "fecha_radicado": nueva.fecha_radicado,
                    "archivo_solicitud_id": nueva.archivo_solicitud_id,
                },
                "message": "Solicitud de información creada correctamente",
            },
            status_code=201,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando solicitud de información: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.put("/solicitud-informacion/{solicitud_id}", status_code=200)
async def actualizar_solicitud_informacion(
    request: Request,
    solicitud_id: int = PathParam(...),
    body: SolicitudInformacionBody = ...,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    solicitud = await db.scalar(select(SolicitudInformacion).where(SolicitudInformacion.id == solicitud_id))
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud de información no encontrada")

    etapa = await db.scalar(select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.id == solicitud.etapa_acoger_concepto_id))
    exp_row = (await db.execute(
        select(Expediente.radicado, Expediente.abogado_responsable_id)
        .where(Expediente.id == etapa.expediente_id)
    )).fetchone()
    if not exp_row:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")
    exp_radicado, abogado_id = exp_row
    if abogado_id != user_id:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

    validar_radicado_ee(body.radicado)
    validar_fecha_no_futura(body.fecha_radicado, "Fecha Radicado")

    datos_anteriores = {"radicado": solicitud.radicado, "fecha_radicado": solicitud.fecha_radicado, "archivo_solicitud_id": solicitud.archivo_solicitud_id}

    if body.archivo_solicitud_id != solicitud.archivo_solicitud_id:
        from services.docs import increment_file_usage
        await decrement_file_usage([solicitud.archivo_solicitud_id])
        await increment_file_usage([body.archivo_solicitud_id])

    solicitud.radicado = body.radicado
    solicitud.fecha_radicado = body.fecha_radicado
    solicitud.archivo_solicitud_id = body.archivo_solicitud_id
    await db.flush()

    audit_result = await insert_log(
        db=db,
        tipo_evento="ACTUALIZAR_SOLICITUD_INFO",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle="Actualización solicitud de información",
        expediente_id=etapa.expediente_id,
        expediente_radicado=exp_radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos={"radicado": body.radicado, "fecha_radicado": body.fecha_radicado},
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": solicitud.id,
                "radicado": solicitud.radicado,
                "fecha_radicado": solicitud.fecha_radicado,
                "archivo_solicitud_id": solicitud.archivo_solicitud_id,
            },
            "message": "Solicitud de información actualizada correctamente",
        },
        status_code=200,
    )


@router.delete("/solicitud-informacion/{solicitud_id}", status_code=200)
async def eliminar_solicitud_informacion(
    request: Request,
    solicitud_id: int = PathParam(...),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    solicitud = await db.scalar(select(SolicitudInformacion).where(SolicitudInformacion.id == solicitud_id))
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud de información no encontrada")

    etapa = await db.scalar(select(EtapaAcogerConcepto).where(EtapaAcogerConcepto.id == solicitud.etapa_acoger_concepto_id))
    exp_row = (await db.execute(
        select(Expediente.radicado, Expediente.abogado_responsable_id)
        .where(Expediente.id == etapa.expediente_id)
    )).fetchone()
    if not exp_row:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")
    exp_radicado, abogado_id = exp_row
    if abogado_id != user_id:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")

    datos_anteriores = {"radicado": solicitud.radicado, "fecha_radicado": solicitud.fecha_radicado, "archivo_solicitud_id": solicitud.archivo_solicitud_id}
    archivo_id = solicitud.archivo_solicitud_id

    await db.delete(solicitud)
    await db.flush()

    await decrement_file_usage([archivo_id])

    audit_result = await insert_log(
        db=db,
        tipo_evento="ELIMINAR_SOLICITUD_INFO",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle="Eliminación solicitud de información",
        expediente_id=etapa.expediente_id,
        expediente_radicado=exp_radicado,
        datos_anteriores=datos_anteriores,
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse(
        content={"ok": True, "message": "Solicitud de información eliminada correctamente"},
        status_code=200,
    )


from fastapi import Request, APIRouter, Depends, HTTPException, Path as PathParam
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
import holidays
import logging
import pytz
import re

from db.deps import get_db_managed
from db.models.expediente import Expediente
from db.models.etapa_acoger_concepto import INSTANCIA_SEGUIMIENTO, INSTANCIA_VISITA, EtapaAcogerConcepto
from db.models.informe_tecnico import InformeTecnico
from db.models.acto_administrativo import ActoAdministrativo
from db.models.oficio_remite import OficioRemite
from db.models.solicitud_informacion import SolicitudInformacion

router = APIRouter()
load_dotenv()

bogota_tz = pytz.timezone("America/Bogota")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from utils.verify_token import verify_gateway_token
from services.docs import decrement_file_usage
from services.etapas import build_acto_for_frontend as _build_acto_for_frontend
from services.etapas import get_expediente_con_permiso, exigir_lectura_expediente
from utils.log import insert_log
from services.cascada_etapas import (
    Cascada,
    aplicar_restas,
    eliminar_cierre,
    eliminar_concepto_seguimiento,
    eliminar_datos_concepto,
)
from services.conceptos import INFORME_HABILITANTE, NOMBRE_ETAPA, concepto_de


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
    # Respuesta del usuario (opcional): si llega uno de los tres, van los tres.
    radicado_respuesta: Optional[str] = None
    fecha_radicado_respuesta: Optional[str] = None
    archivo_respuesta_id: Optional[int] = None


RADICADO_EE_REGEX = re.compile(r"^\d{4}EE\d{4,5}$")


def validar_radicado_ee(radicado: str) -> None:
    if not RADICADO_EE_REGEX.match(radicado.strip()):
        raise HTTPException(
            status_code=400,
            detail="El radicado debe tener el formato: 4 dígitos + EE + 4 o 5 dígitos (ej: 2024EE0001)",
        )


RADICADO_ER_REGEX = re.compile(r"^\d{4}ER\d{4,5}$")


def respuesta_solicitud(body: "SolicitudInformacionBody") -> tuple[Optional[str], Optional[str], Optional[int]]:
    """Respuesta del usuario a la solicitud, normalizada: los tres datos o
    ninguno (vacíos = None). Radicado 4 dígitos + ER + 4 o 5 dígitos y fecha
    no futura. 400 si falta alguno de los tres o el formato no es válido."""
    radicado = (body.radicado_respuesta or "").strip().upper() or None
    fecha = (body.fecha_radicado_respuesta or "").strip() or None
    archivo = body.archivo_respuesta_id or None
    datos = (radicado, fecha, archivo)
    if all(d is None for d in datos):
        return None, None, None
    if any(d is None for d in datos):
        raise HTTPException(
            status_code=400,
            detail="Si registra la respuesta, indique el radicado, la fecha de radicado y el documento de respuesta",
        )
    if not RADICADO_ER_REGEX.match(radicado):
        raise HTTPException(
            status_code=400,
            detail="El radicado de la respuesta debe tener el formato: 4 dígitos + ER + 4 o 5 dígitos (ej: 2024ER0001)",
        )
    validar_fecha_no_futura(fecha, "Fecha Radicado de la respuesta")
    return radicado, fecha, archivo


def solicitud_a_dict(s: SolicitudInformacion) -> dict:
    return {
        "id": s.id,
        "radicado": s.radicado,
        "fecha_radicado": s.fecha_radicado,
        "archivo_solicitud_id": s.archivo_solicitud_id,
        "radicado_respuesta": s.radicado_respuesta,
        "fecha_radicado_respuesta": s.fecha_radicado_respuesta,
        "archivo_respuesta_id": s.archivo_respuesta_id,
    }


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
    solicitud_data = solicitud_a_dict(solicitud_row) if solicitud_row else None

    return {
        "id": etapa.id,
        "expediente_id": etapa.expediente_id,
        "instancia": etapa.instancia,
        "tipo_acogida_concepto": etapa.tipo_acogida_concepto,
        "dias_termino": etapa.dias_termino,
        "fecha_termino_calculada": etapa.fecha_termino_calculada.isoformat() if etapa.fecha_termino_calculada else None,
        "acto_administrativo_id": etapa.acto_administrativo_id,
        "fecha_creacion": etapa.fecha_creacion.isoformat(),
        "acto_admin": acto_data,
        "oficio_remite": oficio_data,
        "solicitud_informacion": solicitud_data,
    }


# ── ETAPA CONCEPTO (visita) y CONCEPTO SEGUIMIENTO ───────────────────────────
#
# Las dos instancias funcionan igual (misma tabla, columna ``instancia``):
# GET/POST por expediente cambian de ruta; PUT, oficio remite y solicitud de
# información van por id de la etapa y sirven para ambas.

def _msg_no_aceptado(instancia: str) -> str:
    return f'El informe técnico de "{INFORME_HABILITANTE[instancia]}" aún no ha sido aceptado'


async def _informe_habilitante_aceptado(db: AsyncSession, expediente_id: int, instancia: str) -> bool:
    """La instancia se crea cuando existe el informe final (aceptado) de su visita."""
    return await db.scalar(
        select(InformeTecnico.id).where(
            InformeTecnico.expediente_id == expediente_id,
            InformeTecnico.tipo_informe == INFORME_HABILITANTE[instancia],
            InformeTecnico.fecha_aceptacion_informe.isnot(None),
        ).limit(1)
    ) is not None


async def _obtener(request: Request, db: AsyncSession, expediente_id: int, instancia: str) -> JSONResponse:
    user_id = verify_gateway_token(request)["user_id"]
    await exigir_lectura_expediente(db, expediente_id, user_id)

    etapa = await concepto_de(db, expediente_id, instancia)
    if not etapa:
        creable = await _informe_habilitante_aceptado(db, expediente_id, instancia)
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "detail": f"{NOMBRE_ETAPA[instancia]} no encontrada",
                "creable": creable,
                "creable_msg": None if creable else _msg_no_aceptado(instancia),
            },
        )

    data = await _build_concepto_response(db, etapa)
    return JSONResponse(content={"ok": True, "data": data}, status_code=200)


async def _crear(
    request: Request, db: AsyncSession, expediente_id: int, body: ConceptoCreateBody, instancia: str
) -> JSONResponse:
    user_id = verify_gateway_token(request)["user_id"]

    if body.tipo_acogida_concepto not in VALID_TIPOS_CONCEPTO:
        raise HTTPException(status_code=400, detail="tipo_acogida_concepto inválido")

    _eid, exp_radicado, _abg = await get_expediente_con_permiso(db, expediente_id, user_id)

    nombre = NOMBRE_ETAPA[instancia]
    if await concepto_de(db, expediente_id, instancia):
        raise HTTPException(status_code=409, detail=f"La {nombre.lower()} ya existe para este expediente")
    if not await _informe_habilitante_aceptado(db, expediente_id, instancia):
        raise HTTPException(status_code=400, detail=_msg_no_aceptado(instancia))

    nueva = EtapaAcogerConcepto(
        expediente_id=expediente_id,
        instancia=instancia,
        tipo_acogida_concepto=body.tipo_acogida_concepto,
    )
    db.add(nueva)
    await db.flush()

    sufijo = "_SEG" if instancia == INSTANCIA_SEGUIMIENTO else ""  # tipo_evento: máx. 30
    audit_result = await insert_log(
        db=db,
        tipo_evento=f"CREAR_ETAPA_CONCEPTO{sufijo}",
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Creación {nombre}",
        expediente_id=expediente_id,
        expediente_radicado=exp_radicado,
        datos_nuevos={"tipo_acogida_concepto": body.tipo_acogida_concepto, "instancia": instancia},
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()
    await db.refresh(nueva)

    data = await _build_concepto_response(db, nueva)
    return JSONResponse(content={"ok": True, "data": data, "message": f"{nombre} creada correctamente"}, status_code=201)


@router.get("/concepto/{expediente_id}", status_code=200)
async def obtener_concepto(
    request: Request,
    expediente_id: int = PathParam(...),
    db: AsyncSession = Depends(get_db_managed),
):
    return await _obtener(request, db, expediente_id, INSTANCIA_VISITA)


@router.post("/concepto/{expediente_id}", status_code=201)
async def crear_concepto(
    request: Request,
    expediente_id: int = PathParam(...),
    body: ConceptoCreateBody = ...,
    db: AsyncSession = Depends(get_db_managed),
):
    return await _crear(request, db, expediente_id, body, INSTANCIA_VISITA)


@router.get("/concepto-seguimiento/{expediente_id}", status_code=200)
async def obtener_concepto_seguimiento(
    request: Request,
    expediente_id: int = PathParam(...),
    db: AsyncSession = Depends(get_db_managed),
):
    """Acoger concepto de la visita de seguimiento (etapa 5)."""
    return await _obtener(request, db, expediente_id, INSTANCIA_SEGUIMIENTO)


@router.post("/concepto-seguimiento/{expediente_id}", status_code=201)
async def crear_concepto_seguimiento(
    request: Request,
    expediente_id: int = PathParam(...),
    body: ConceptoCreateBody = ...,
    db: AsyncSession = Depends(get_db_managed),
):
    """Se habilita cuando el informe técnico de SEGUIMIENTO está aceptado."""
    return await _crear(request, db, expediente_id, body, INSTANCIA_SEGUIMIENTO)


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
    nombre = NOMBRE_ETAPA[etapa.instancia]

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
    concepto_seguimiento_eliminado = False
    cascada = Cascada()

    # Si cambia el tipo: eliminar la data asociada al tipo anterior (acto,
    # notificaciones, comunicaciones y oficio; la solicitud de información es
    # independiente del tipo y se conserva) y la etapa de Cierre. En el
    # concepto de la visita también el acoger concepto · seguimiento.
    if tipo_anterior != tipo_nuevo:
        await eliminar_datos_concepto(db, etapa, cascada, incluir_solicitud=False)
        cierre_eliminado = await eliminar_cierre(db, etapa.expediente_id, cascada)
        if etapa.instancia == INSTANCIA_VISITA:
            concepto_seguimiento_eliminado = await eliminar_concepto_seguimiento(db, etapa.expediente_id, cascada)

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
        tipo_evento="ACTUALIZAR_ETAPA_CONCEPTO" + ("_SEG" if etapa.es_seguimiento else ""),
        resultado="EXITOSO",
        usuario_id=user_id,
        detalle=f"Actualización {nombre}",
        expediente_id=etapa.expediente_id,
        expediente_radicado=exp_radicado,
        datos_anteriores=datos_anteriores,
        datos_nuevos={"tipo_acogida_concepto": tipo_nuevo, "dias_termino": body.dias_termino},
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    # Como antes: la resta de usos es best-effort (no aborta el cambio de tipo).
    await aplicar_restas(cascada.usos, decrement_file_usage, estricto=False)
    await db.commit()
    await db.refresh(etapa)

    data = await _build_concepto_response(db, etapa)
    msg = f"{nombre} actualizada correctamente"
    eliminadas = [n for n, si in (("Acoger concepto · seguimiento", concepto_seguimiento_eliminado),
                                  ("Cierre", cierre_eliminado)) if si]
    if eliminadas:
        msg = f"Tipo de acogida actualizado. Por el cambio de tipo se eliminó: {', '.join(eliminadas)}."
    return JSONResponse(
        content={
            "ok": True, "data": data, "message": msg,
            "cierre_eliminado": cierre_eliminado,
            "concepto_seguimiento_eliminado": concepto_seguimiento_eliminado,
        },
        status_code=200,
    )


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
        radicado_resp, fecha_resp, archivo_resp = respuesta_solicitud(body)

        nueva = SolicitudInformacion(
            etapa_acoger_concepto_id=etapa_concepto_id,
            radicado=body.radicado,
            fecha_radicado=body.fecha_radicado,
            archivo_solicitud_id=body.archivo_solicitud_id,
            radicado_respuesta=radicado_resp,
            fecha_radicado_respuesta=fecha_resp,
            archivo_respuesta_id=archivo_resp,
        )
        db.add(nueva)
        await db.flush()

        from services.docs import increment_file_usage
        await increment_file_usage([f for f in (body.archivo_solicitud_id, archivo_resp) if f])

        audit_result = await insert_log(
            db=db,
            tipo_evento="CREAR_SOLICITUD_INFO",
            resultado="EXITOSO",
            usuario_id=user_id,
            detalle="Creación solicitud de información",
            expediente_id=etapa.expediente_id,
            expediente_radicado=exp_radicado,
            datos_nuevos={
                "radicado": body.radicado, "fecha_radicado": body.fecha_radicado,
                "radicado_respuesta": radicado_resp, "fecha_radicado_respuesta": fecha_resp,
            },
        )
        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

        await db.commit()

        return JSONResponse(
            content={
                "ok": True,
                "data": solicitud_a_dict(nueva),
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
    radicado_resp, fecha_resp, archivo_resp = respuesta_solicitud(body)

    datos_anteriores = solicitud_a_dict(solicitud)

    from services.docs import increment_file_usage
    if body.archivo_solicitud_id != solicitud.archivo_solicitud_id:
        await decrement_file_usage([solicitud.archivo_solicitud_id])
        await increment_file_usage([body.archivo_solicitud_id])
    # Respuesta: nueva, reemplazada o quitada (los tres datos vacíos).
    if archivo_resp != solicitud.archivo_respuesta_id:
        if solicitud.archivo_respuesta_id:
            await decrement_file_usage([solicitud.archivo_respuesta_id])
        if archivo_resp:
            await increment_file_usage([archivo_resp])

    solicitud.radicado = body.radicado
    solicitud.fecha_radicado = body.fecha_radicado
    solicitud.archivo_solicitud_id = body.archivo_solicitud_id
    solicitud.radicado_respuesta = radicado_resp
    solicitud.fecha_radicado_respuesta = fecha_resp
    solicitud.archivo_respuesta_id = archivo_resp
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
        datos_nuevos={
            "radicado": body.radicado, "fecha_radicado": body.fecha_radicado,
            "radicado_respuesta": radicado_resp, "fecha_radicado_respuesta": fecha_resp,
        },
    )
    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "data": solicitud_a_dict(solicitud),
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

    datos_anteriores = solicitud_a_dict(solicitud)
    archivos = [f for f in (solicitud.archivo_solicitud_id, solicitud.archivo_respuesta_id) if f]

    await db.delete(solicitud)
    await db.flush()

    await decrement_file_usage(archivos)

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


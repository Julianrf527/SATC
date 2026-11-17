from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Type
import pytz

from db.deps import get_db_managed
from db.models.expediente import Expediente
from db.models.acto_administrativo import ActoAdministrativo
from db.models.notificacion import Notificacion
from db.models.comunicacion import Comunicacion
from db.models.documento_anexo import DocumentoAnexo
from db.models.tipo_sancion import TipoSancion
from db.models.tipo_cesacion import TipoCesacion
from db.models.tipo_medida import TipoMedida
from db.models.tipo_notificacion import TipoNotificacion
from db.models.etapa_indagacion import EtapaIndagacion
from db.models.etapa_medida_preventiva import EtapaMedidaPreventiva
from db.models.etapa_inicio_sancionatorio import EtapaInicioSancionatorio
from db.models.etapa_cesacion import EtapaCesacion
from db.models.etapa_formulacion_cargos import EtapaFormulacionCargos
from db.models.etapa_apertura_probatoria import EtapaAperturaProbatoria
from db.models.etapa_cierre_probatoria import EtapaCierreProbatoria
from db.models.etapa_decision_fondo import EtapaDecisionFondo
from db.models.etapa_probatoria_recurso import EtapaProbatoriaRecurso
from db.models.etapa_ejecucion_sancion import EtapaEjecucionSancion

from utils.verify_token import verify_gateway_token
from utils.functions import calcular_dias_laborales
from services.docs import increment_file_usage, decrement_file_usage
from services.involucrado import get_involucrados_by_expedientes_ids
from services.auditoria import insert_auditoria
from services.etapas import (
    ETAPA_LABELS,
    ETAPA_LEGACY_ID,
    ETAPA_MODELS,
    get_expediente_con_permiso as _get_expediente_con_permiso,
)
from services.permisos import exigir_lectura_expediente, exigir_escritura_expediente

router = APIRouter()
bogota_tz = pytz.timezone("America/Bogota")

# ── Helpers ────────────────────────────────────────────────────────────────────

def _serialize_acto(acto: ActoAdministrativo, notifs=None, com=None, nivel_auxiliar: bool = False) -> dict:
    return {
        "id": acto.id,
        "tipo_acto": acto.tipo_acto,
        "numerado": str(acto.numerado) if acto.numerado is not None else "",
        "fecha_numerado": acto.fecha_numerado.isoformat() if acto.fecha_numerado else None,
        "documento_acto_administrativo_id": acto.documento_acto_administrativo_id,
        "fecha_creacion": acto.fecha_creacion.isoformat() if acto.fecha_creacion else "",
        "etapa_id": 0,  # compatibilidad frontend
        "nivel_auxiliar": nivel_auxiliar,
        "notificacion": {
            "id": 0,
            "fecha_creacion": "",
            "involucrados": [_serialize_notif(n) for n in (notifs or [])],
        } if notifs is not None else None,
        "comunicacion": _serialize_com(com) if com else None,
    }

def _serialize_notif(n) -> dict:
    return {
        "id": n.id,
        "involucrado_id": n.involucrado_id,
        "numerado": str(n.numerado) if n.numerado is not None else "",
        "fecha_numerado": n.fecha_numerado.isoformat() if n.fecha_numerado else None,
        "fecha_envio_citacion": n.fecha_envio_citacion.isoformat() if n.fecha_envio_citacion else None,
        "fecha_constancia_citacion": n.fecha_constancia_citacion.isoformat() if n.fecha_constancia_citacion else None,
        "documento_citacion_id": n.documento_citacion_id,
        "notificacion_exitosa": n.notificacion_exitosa,
        "documento_notificacion_id": n.documento_notificacion_id,
        "tipo_notificacion_id": n.tipo_notificacion_id,
        "fecha_notificacion": n.fecha_notificacion.isoformat() if n.fecha_notificacion else None,
        "fecha_creacion": n.fecha_creacion.isoformat() if n.fecha_creacion else "",
    }

def _serialize_com(c) -> dict:
    return {
        "id": c.id,
        "numerado": str(c.numerado) if c.numerado is not None else "",
        "fecha_numerado": c.fecha_numerado.isoformat() if c.fecha_numerado else None,
        "fecha_envio": c.fecha_envio.isoformat() if c.fecha_envio else None,
        "documento_comunicacion_id": c.documento_comunicacion_id,
        "fecha_creacion": c.fecha_creacion.isoformat() if c.fecha_creacion else "",
    }

def _serialize_anexo(a) -> dict:
    return {
        "id": a.id,
        "nombre": a.nombre,
        "documento_anexo_id": a.documento_anexo_id,
        "fecha_subida": a.fecha_subida.isoformat() if a.fecha_subida else None,
    }

async def _acto_con_notif_exitosa(db: AsyncSession, acto_id: int | None) -> bool:
    """True si el acto existe y tiene al menos una notificación exitosa."""
    if not acto_id:
        return False
    return bool(await db.scalar(
        select(Notificacion.id).where(
            Notificacion.acto_administrativo_id == acto_id,
            Notificacion.notificacion_exitosa == True,
        )
    ))

async def _creable_requiere_notif(db, modelo, expediente_id, etapa_nombre, msg_no_etapa, msg_sin_notif):
    """Creable: la etapa previa debe existir y tener acto administrativo con notificación exitosa."""
    previa = await db.scalar(select(modelo).where(modelo.expediente_id == expediente_id))
    if not previa:
        return {"status": False, "msg": msg_no_etapa}
    if not await _acto_con_notif_exitosa(db, previa.acto_administrativo_id):
        return {"status": False, "msg": msg_sin_notif}
    return {"status": True}

async def _creable_requiere_etapa(db, modelo, expediente_id, msg_no_etapa, requiere_acto=False, msg_sin_acto=None):
    """Creable: la etapa previa debe existir (opcionalmente con acto administrativo)."""
    previa = await db.scalar(select(modelo).where(modelo.expediente_id == expediente_id))
    if not previa:
        return {"status": False, "msg": msg_no_etapa}
    if requiere_acto and not previa.acto_administrativo_id:
        return {"status": False, "msg": msg_sin_acto}
    return {"status": True}

async def _get_acto_full(db: AsyncSession, acto_id: int | None, nivel_auxiliar: bool = False) -> dict | None:
    if not acto_id:
        return None
    acto = await db.scalar(select(ActoAdministrativo).where(ActoAdministrativo.id == acto_id))
    if not acto:
        return None
    notifs = (await db.execute(
        select(Notificacion).where(Notificacion.acto_administrativo_id == acto.id)
    )).scalars().all()
    com = await db.scalar(select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto.id))
    return _serialize_acto(acto, notifs, com, nivel_auxiliar=nivel_auxiliar)

async def _get_anexos(db: AsyncSession, etapa_tipo: str, etapa_ref_id: int) -> list:
    rows = (await db.execute(
        select(DocumentoAnexo)
        .where(DocumentoAnexo.etapa_tipo == etapa_tipo, DocumentoAnexo.etapa_ref_id == etapa_ref_id)
    )).scalars().all()
    return [_serialize_anexo(a) for a in rows]


# ── CONTRATO DE LAS ETAPAS ─────────────────────────────────────────────────────
# Una sola forma para las 10 etapas:
#
#   GET  /<etapa>/{expediente_id} → {"ok": true, "<clave>": Etapa | null, "creable"?: {status, msg?}}
#        Etapa = {id, etapa_id, tipo_etapa_id, expediente_id, fecha_creacion,
#                 acto_admin, documentos_anexos, ...campos propios de la etapa (planos)}
#        `creable` va en la raíz (no dentro de la etapa): es justo cuando la
#        etapa NO existe que el frontend lo necesita.
#   POST /<etapa>/{expediente_id} → 201 {"ok": true, "id", "etapa_id"}. En las
#        etapas con datos propios el body es opcional (mismo esquema que el PUT).
#   PUT  /<etapa>/{expediente_id} → body obligatorio → {"ok": true, "id", "etapa_id"}.
#
# Los bodies rechazan campos desconocidos (extra="forbid"): una forma vieja del
# contrato da 422 en vez de guardarse a medias.


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── MOTOR GENÉRICO DE ETAPAS ───────────────────────────────────────────────────
# 8 de las 10 etapas comparten el mismo esqueleto CRUD (permiso → creable →
# mutar → auditar → responder): indagación, medida preventiva, inicio del
# proceso, cesación, apertura probatoria, cierre probatoria, decisión de fondo
# y probatoria de recurso. Quedan como rutas propias formulación (documento de
# descargos con contador de usos) y ejecución (4 documentos independientes).

from dataclasses import dataclass
from typing import Callable

@dataclass
class EtapaConfig:
    modelo: Type
    etapa_tipo: str
    tipo_etapa_id: int
    respuesta_key: str
    accion: str
    msg_ya_existe: str
    msg_no_encontrada: str = ""
    creable: Optional[Callable] = None
    extra_get: Optional[Callable] = None
    on_create: Optional[Callable] = None
    on_update: Optional[Callable] = None
    create_message: Optional[str] = None


async def _creable_cesacion(db, expediente_id):
    return await _creable_requiere_etapa(
        db, EtapaInicioSancionatorio, expediente_id,
        msg_no_etapa="El inicio del proceso sancionatorio debe existir para crear la cesación",
    )

async def _creable_formulacion(db, expediente_id):
    return await _creable_requiere_notif(
        db, EtapaInicioSancionatorio, expediente_id, "Inicio Proceso Sancionatorio",
        msg_no_etapa="El inicio del proceso debe existir para crear la formulación de cargos",
        msg_sin_notif="El inicio del proceso debe tener acto administrativo con notificación exitosa",
    )

async def _creable_apertura(db, expediente_id):
    return await _creable_requiere_notif(
        db, EtapaFormulacionCargos, expediente_id, "Formulacion de Cargos",
        msg_no_etapa="La formulación de cargos debe existir para crear la apertura etapa probatoria",
        msg_sin_notif="La formulación de cargos debe tener acto administrativo con notificación exitosa",
    )

async def _creable_cierre(db, expediente_id):
    return await _creable_requiere_etapa(
        db, EtapaAperturaProbatoria, expediente_id,
        msg_no_etapa="La apertura etapa probatoria debe existir para crear el cierre etapa probatoria",
        requiere_acto=True,
        msg_sin_acto="La apertura etapa probatoria debe tener acto administrativo",
    )

async def _creable_decision(db, expediente_id):
    return await _creable_requiere_notif(
        db, EtapaCierreProbatoria, expediente_id, "Cierre Etapa Probatoria",
        msg_no_etapa="El cierre etapa probatoria debe existir para crear la decisión de fondo",
        msg_sin_notif="El cierre etapa probatoria debe tener acto administrativo con notificación exitosa",
    )

async def _creable_recurso(db, expediente_id):
    """Mismo requisito que exigía el POST: la decisión de fondo con acto de recurso."""
    decision = await db.scalar(select(EtapaDecisionFondo).where(EtapaDecisionFondo.expediente_id == expediente_id))
    if not decision:
        return {"status": False, "msg": "La decisión de fondo debe existir para crear la probatoria de recurso"}
    if not decision.acto_recurso_id:
        return {"status": False, "msg": "La decisión de fondo debe tener acto de recurso para crear probatoria de recurso"}
    return {"status": True}

async def _creable_ejecucion(db, expediente_id):
    """Regla única del GET (`creable`) y del POST de la ejecución:
      - Si hay recurso (existe la etapa probatoria de recurso), el acto que lo
        decide (`acto_decision_id`) debe estar notificado con éxito.
      - Si no hay recurso, basta la decisión de fondo con su acto notificado.
    """
    decision = await db.scalar(select(EtapaDecisionFondo).where(EtapaDecisionFondo.expediente_id == expediente_id))
    if not decision:
        return {"status": False, "msg": "La decisión de fondo debe existir para crear la ejecución de la sanción"}
    recurso = await db.scalar(select(EtapaProbatoriaRecurso).where(EtapaProbatoriaRecurso.expediente_id == expediente_id))
    if recurso:
        if not await _acto_con_notif_exitosa(db, recurso.acto_decision_id):
            return {"status": False, "msg": "Hay un recurso en curso: el acto que decide el recurso debe estar notificado con éxito para crear la ejecución de la sanción"}
        return {"status": True}
    if not await _acto_con_notif_exitosa(db, decision.acto_administrativo_id):
        return {"status": False, "msg": "La decisión de fondo debe tener acto administrativo con notificación exitosa"}
    return {"status": True}


async def _nombre_catalogo(db, modelo, id_):
    return await db.scalar(select(modelo.nombre).where(modelo.id == id_)) if id_ else None


# Medida preventiva
class MedidaBody(_Body):
    tipo_medida_id: int
    cantidad: str
    especie: str
    estado_medida: Optional[bool] = None

async def _medida_extra_get(db, etapa):
    return {
        "tipo_medida_id": etapa.tipo_medida_id,
        "cantidad": etapa.cantidad,
        "especie": etapa.especie,
        "estado_medida": etapa.estado_medida,
    }

async def _medida_on_create(db, body):
    if not body:
        return {}, {"tipo_medida": None}
    return body.model_dump(), {"tipo_medida": await _nombre_catalogo(db, TipoMedida, body.tipo_medida_id)}

async def _medida_on_update(db, etapa, body):
    datos_ant = {"tipo_medida": await _nombre_catalogo(db, TipoMedida, etapa.tipo_medida_id),
                 "cantidad": etapa.cantidad, "especie": etapa.especie, "estado_medida": etapa.estado_medida}
    for campo, valor in body.model_dump().items():
        setattr(etapa, campo, valor)
    return datos_ant, {"tipo_medida": await _nombre_catalogo(db, TipoMedida, body.tipo_medida_id)}


# Cesación
class CesacionBody(_Body):
    tipo_cesacion_id: int

async def _cesacion_extra_get(db, etapa):
    return {"tipo_cesacion_id": etapa.tipo_cesacion_id,
            "tipo_cesacion_nombre": await _nombre_catalogo(db, TipoCesacion, etapa.tipo_cesacion_id)}

async def _cesacion_on_create(db, body):
    tipo_id = body.tipo_cesacion_id if body else None
    return {"tipo_cesacion_id": tipo_id}, {"tipo_cesacion": await _nombre_catalogo(db, TipoCesacion, tipo_id)}

async def _cesacion_on_update(db, etapa, body):
    datos_ant = {"tipo_cesacion": await _nombre_catalogo(db, TipoCesacion, etapa.tipo_cesacion_id)}
    etapa.tipo_cesacion_id = body.tipo_cesacion_id
    return datos_ant, {"tipo_cesacion": await _nombre_catalogo(db, TipoCesacion, body.tipo_cesacion_id)}


# Decisión de fondo
class DecisionBody(_Body):
    tipo_sancion_id: int
    detalle: str

# Días hábiles desde la subida del documento "Recurso" para crear el acto de recurso.
PLAZO_ACTO_RECURSO_DIAS_HABILES = 15

async def _creable_acto_recurso(db, etapa) -> dict:
    """¿Se puede gestionar el acto de recurso de la decisión de fondo?
    Si ya existe, siempre (para verlo/editarlo). Si no: hace falta el acto de
    la etapa, un documento anexo "Recurso" y no haber vencido el plazo desde su subida."""
    if etapa.acto_recurso_id:
        return {"status": True}
    if not etapa.acto_administrativo_id:
        return {"status": False, "msg": "Debe crear primero el acto administrativo de la etapa."}
    fecha_subida = await db.scalar(
        select(DocumentoAnexo.fecha_subida)
        .where(DocumentoAnexo.etapa_tipo == "etapa_decision_fondo",
               DocumentoAnexo.etapa_ref_id == etapa.id,
               DocumentoAnexo.nombre == "Recurso")
        .order_by(DocumentoAnexo.fecha_subida).limit(1)
    )
    if not fecha_subida:
        return {"status": False, "msg": "Debe subir un documento de tipo 'Recurso' para crear este acto."}
    if fecha_subida.tzinfo:
        fecha_subida = fecha_subida.astimezone(bogota_tz)
    if calcular_dias_laborales(fecha_subida.date(), datetime.now(bogota_tz).date()) > PLAZO_ACTO_RECURSO_DIAS_HABILES:
        return {"status": False, "msg": f"Pasaron más de {PLAZO_ACTO_RECURSO_DIAS_HABILES} días hábiles desde la fecha de subida del documento Recurso"}
    return {"status": True}

async def _decision_extra_get(db, etapa):
    return {
        "tipo_sancion_id": etapa.tipo_sancion_id,
        "detalle": etapa.detalle,
        "acto_recurso": await _get_acto_full(db, etapa.acto_recurso_id, nivel_auxiliar=True),
        "creable_acto_recurso": await _creable_acto_recurso(db, etapa),
    }

async def _decision_on_create(db, body):
    if not body:
        return {}, {"tipo_sancion": None, "detalle": None}
    return body.model_dump(), {"tipo_sancion": await _nombre_catalogo(db, TipoSancion, body.tipo_sancion_id), "detalle": body.detalle}

async def _decision_on_update(db, etapa, body):
    datos_ant = {"tipo_sancion": await _nombre_catalogo(db, TipoSancion, etapa.tipo_sancion_id), "detalle": etapa.detalle}
    etapa.tipo_sancion_id = body.tipo_sancion_id
    etapa.detalle = body.detalle
    return datos_ant, {"tipo_sancion": await _nombre_catalogo(db, TipoSancion, body.tipo_sancion_id), "detalle": body.detalle}


# Probatoria de recurso
async def _recurso_extra_get(db, etapa):
    return {"acto_decision": await _get_acto_full(db, etapa.acto_decision_id, nivel_auxiliar=True)}


ETAPAS: dict[str, EtapaConfig] = {
    "indagacion": EtapaConfig(
        modelo=EtapaIndagacion, etapa_tipo="etapa_indagacion", tipo_etapa_id=2,
        respuesta_key="indagacion", accion="INDAGACION",
        msg_ya_existe="La indagación preliminar ya existe",
        create_message="Indagación creada",
    ),
    "inicio_sancionatorio": EtapaConfig(
        modelo=EtapaInicioSancionatorio, etapa_tipo="etapa_inicio_sancionatorio", tipo_etapa_id=9,
        respuesta_key="inicio_proceso", accion="INICIO_PROCESO",
        msg_ya_existe="El inicio de proceso ya existe",
    ),
    "apertura": EtapaConfig(
        modelo=EtapaAperturaProbatoria, etapa_tipo="etapa_apertura_probatoria", tipo_etapa_id=5,
        respuesta_key="apertura_etapa_probatoria", accion="APERTURA_PROBATORIA",
        msg_ya_existe="La apertura etapa probatoria ya existe",
        creable=_creable_apertura,
    ),
    "cierre": EtapaConfig(
        modelo=EtapaCierreProbatoria, etapa_tipo="etapa_cierre_probatoria", tipo_etapa_id=11,
        respuesta_key="cierre_etapa_probatoria", accion="CIERRE_PROBATORIA",
        msg_ya_existe="El cierre etapa probatoria ya existe",
        creable=_creable_cierre,
    ),
    "medida_preventiva": EtapaConfig(
        modelo=EtapaMedidaPreventiva, etapa_tipo="etapa_medida_preventiva", tipo_etapa_id=1,
        respuesta_key="medida", accion="MEDIDA_PREVENTIVA",
        msg_ya_existe="La medida preventiva ya existe",
        msg_no_encontrada="Medida preventiva no encontrada",
        extra_get=_medida_extra_get, on_create=_medida_on_create, on_update=_medida_on_update,
    ),
    "cesacion": EtapaConfig(
        modelo=EtapaCesacion, etapa_tipo="etapa_cesacion", tipo_etapa_id=10,
        respuesta_key="cesacion", accion="CESACION",
        msg_ya_existe="La cesación ya existe",
        msg_no_encontrada="Cesación no encontrada",
        creable=_creable_cesacion,
        extra_get=_cesacion_extra_get, on_create=_cesacion_on_create, on_update=_cesacion_on_update,
    ),
    "decision_fondo": EtapaConfig(
        modelo=EtapaDecisionFondo, etapa_tipo="etapa_decision_fondo", tipo_etapa_id=6,
        respuesta_key="decision_fondo", accion="DECISION_FONDO",
        msg_ya_existe="La decisión de fondo ya existe",
        msg_no_encontrada="Decisión de fondo no encontrada",
        creable=_creable_decision,
        extra_get=_decision_extra_get, on_create=_decision_on_create, on_update=_decision_on_update,
    ),
    "recurso": EtapaConfig(
        modelo=EtapaProbatoriaRecurso, etapa_tipo="etapa_probatoria_recurso", tipo_etapa_id=12,
        respuesta_key="recurso", accion="PROBATORIA_RECURSO",
        msg_ya_existe="La probatoria de recurso ya existe",
        creable=_creable_recurso,
        extra_get=_recurso_extra_get,
    ),
}


async def _datos_base(db: AsyncSession, etapa, etapa_tipo: str, tipo_etapa_id: int, expediente_id: int) -> dict:
    """Campos comunes de toda etapa existente."""
    return {
        "id": etapa.id, "etapa_id": etapa.id, "tipo_etapa_id": tipo_etapa_id,
        "expediente_id": expediente_id,
        "fecha_creacion": etapa.fecha_creacion.isoformat() if etapa.fecha_creacion else None,
        "acto_admin": await _get_acto_full(db, getattr(etapa, "acto_administrativo_id", None)),
        "documentos_anexos": await _get_anexos(db, etapa_tipo, etapa.id),
    }


def _respuesta_get(respuesta_key: str, datos: dict | None, creable: dict | None) -> JSONResponse:
    payload = {"ok": True, respuesta_key: datos}
    if creable is not None:
        payload["creable"] = creable
    return JSONResponse(content=payload, status_code=200)


async def _get_etapa(cfg: "EtapaConfig", db: AsyncSession, expediente_id: int, user_id: int):
    await _get_expediente_con_permiso(db, expediente_id, user_id, require_owner=False)
    etapa = await db.scalar(select(cfg.modelo).where(cfg.modelo.expediente_id == expediente_id))
    creable = await cfg.creable(db, expediente_id) if cfg.creable else None
    if not etapa:
        return _respuesta_get(cfg.respuesta_key, None, creable)
    data = await _datos_base(db, etapa, cfg.etapa_tipo, cfg.tipo_etapa_id, expediente_id)
    if cfg.extra_get:
        data.update(await cfg.extra_get(db, etapa))
    return _respuesta_get(cfg.respuesta_key, data, creable)


async def _post_etapa(cfg: "EtapaConfig", db: AsyncSession, expediente_id: int, user_id: int, body):
    row = await _get_expediente_con_permiso(db, expediente_id, user_id)
    if await db.scalar(select(cfg.modelo.id).where(cfg.modelo.expediente_id == expediente_id)):
        raise HTTPException(status_code=409, detail=cfg.msg_ya_existe)
    if cfg.creable:
        creable = await cfg.creable(db, expediente_id)
        if not creable["status"]:
            raise HTTPException(status_code=400, detail=creable["msg"])
    kwargs, datos_nuevos = await cfg.on_create(db, body) if cfg.on_create else ({}, {"radicado": row.radicado})
    nueva = cfg.modelo(expediente_id=expediente_id, **kwargs)
    db.add(nueva)
    await db.flush()
    await insert_auditoria(db, f"CREAR_{cfg.accion}", "EXITOSO", user_id,
        expediente_id, row.radicado, detalle=f"Creación {cfg.respuesta_key}", datos_nuevos=datos_nuevos)
    await db.commit()
    content = {"ok": True, "id": nueva.id, "etapa_id": nueva.id}
    if cfg.create_message:
        content["message"] = cfg.create_message
    return JSONResponse(content=content, status_code=201)


async def _put_etapa(cfg: "EtapaConfig", db: AsyncSession, expediente_id: int, user_id: int, body):
    row = await _get_expediente_con_permiso(db, expediente_id, user_id)
    etapa = await db.scalar(select(cfg.modelo).where(cfg.modelo.expediente_id == expediente_id))
    if not etapa:
        raise HTTPException(status_code=404, detail=cfg.msg_no_encontrada)
    datos_ant, datos_nuevos = await cfg.on_update(db, etapa, body)
    await db.flush()
    await insert_auditoria(db, f"ACTUALIZAR_{cfg.accion}", "EXITOSO", user_id,
        expediente_id, row.radicado, detalle=f"Actualización {cfg.respuesta_key}",
        datos_anteriores=datos_ant, datos_nuevos=datos_nuevos)
    await db.commit()
    return JSONResponse(content={"ok": True, "id": etapa.id, "etapa_id": etapa.id})


def _catalogo(filas) -> JSONResponse:
    return JSONResponse(content={"ok": True, "data": [{"id": t.id, "nombre": t.nombre} for t in filas]})


# ── INDAGACIÓN PRELIMINAR ─────────────────────────────────────────────────────

@router.get("/investigation/{expediente_id}")
async def obtener_indagacion(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _get_etapa(ETAPAS["indagacion"], db, expediente_id, user_id)


@router.post("/investigation/{expediente_id}", status_code=201)
async def crear_indagacion(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _post_etapa(ETAPAS["indagacion"], db, expediente_id, user_id, None)


# ── MEDIDA PREVENTIVA ─────────────────────────────────────────────────────────

@router.get("/measure-type", status_code=200)
async def listar_tipos_medida(request: Request, db: AsyncSession = Depends(get_db_managed)):
    verify_gateway_token(request)
    return _catalogo((await db.execute(select(TipoMedida).order_by(TipoMedida.id))).scalars().all())


@router.get("/measure/{expediente_id}")
async def obtener_medida(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _get_etapa(ETAPAS["medida_preventiva"], db, expediente_id, user_id)


@router.post("/measure/{expediente_id}", status_code=201)
async def crear_medida(request: Request, expediente_id: int, body: Optional[MedidaBody] = None, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _post_etapa(ETAPAS["medida_preventiva"], db, expediente_id, user_id, body)


@router.put("/measure/{expediente_id}")
async def actualizar_medida(request: Request, expediente_id: int, body: MedidaBody, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _put_etapa(ETAPAS["medida_preventiva"], db, expediente_id, user_id, body)


# ── INICIO PROCESO SANCIONATORIO ──────────────────────────────────────────────

@router.get("/start-process/{expediente_id}")
async def obtener_inicio_proceso(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _get_etapa(ETAPAS["inicio_sancionatorio"], db, expediente_id, user_id)


@router.post("/start-process/{expediente_id}", status_code=201)
async def crear_inicio_proceso(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _post_etapa(ETAPAS["inicio_sancionatorio"], db, expediente_id, user_id, None)


# ── CESACIÓN ──────────────────────────────────────────────────────────────────

@router.get("/cessation-type", status_code=200)
async def listar_tipos_cesacion(request: Request, db: AsyncSession = Depends(get_db_managed)):
    verify_gateway_token(request)
    return _catalogo((await db.execute(select(TipoCesacion).order_by(TipoCesacion.id))).scalars().all())


@router.get("/cessation/{expediente_id}")
async def obtener_cesacion(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _get_etapa(ETAPAS["cesacion"], db, expediente_id, user_id)


@router.post("/cessation/{expediente_id}", status_code=201)
async def crear_cesacion(request: Request, expediente_id: int, body: Optional[CesacionBody] = None, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _post_etapa(ETAPAS["cesacion"], db, expediente_id, user_id, body)


@router.put("/cessation/{expediente_id}")
async def actualizar_cesacion(request: Request, expediente_id: int, body: CesacionBody, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _put_etapa(ETAPAS["cesacion"], db, expediente_id, user_id, body)

# ── FORMULACIÓN DE CARGOS ─────────────────────────────────────────────────────
# Body JSON (no form-data): {"descargos": bool | null, "documento_id": int | null}.

class FormulacionInfoBody(_Body):
    descargos: Optional[bool] = None
    documento_id: Optional[int] = None


@router.get("/formulation/{expediente_id}")
async def obtener_formulacion(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    await _get_expediente_con_permiso(db, expediente_id, user_id, require_owner=False)
    etapa = await db.scalar(select(EtapaFormulacionCargos).where(EtapaFormulacionCargos.expediente_id == expediente_id))
    creable = await _creable_formulacion(db, expediente_id)
    if not etapa:
        return _respuesta_get("formulacion_cargos", None, creable)
    data = await _datos_base(db, etapa, "etapa_formulacion_cargos", 4, expediente_id)
    data.update({"descargos": etapa.descargos, "documento_id": etapa.documento_id})
    return _respuesta_get("formulacion_cargos", data, creable)


@router.post("/formulation/{expediente_id}", status_code=201)
async def crear_formulacion(
    request: Request, expediente_id: int, body: Optional[FormulacionInfoBody] = None,
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = verify_gateway_token(request)["user_id"]
    row = await _get_expediente_con_permiso(db, expediente_id, user_id)
    if await db.scalar(select(EtapaFormulacionCargos.id).where(EtapaFormulacionCargos.expediente_id == expediente_id)):
        raise HTTPException(status_code=409, detail="La formulación de cargos ya existe")
    creable = await _creable_formulacion(db, expediente_id)
    if not creable["status"]:
        raise HTTPException(status_code=400, detail=creable["msg"])
    descargos_bool = body.descargos if body else None
    documento_id = body.documento_id if body else None
    nueva = EtapaFormulacionCargos(expediente_id=expediente_id, descargos=descargos_bool, documento_id=documento_id)
    db.add(nueva)
    await db.flush()
    if documento_id:
        await increment_file_usage([documento_id])
    await insert_auditoria(db, "CREAR_FORMULACION_CARGOS", "EXITOSO", user_id,
        expediente_id, row.radicado,
        detalle="Creación formulación de cargos",
        datos_nuevos={"descargos": descargos_bool})
    await db.commit()
    return JSONResponse(content={"ok": True, "id": nueva.id, "etapa_id": nueva.id}, status_code=201)


@router.put("/formulation/{expediente_id}")
async def actualizar_formulacion(
    request: Request, expediente_id: int, body: FormulacionInfoBody,
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = verify_gateway_token(request)["user_id"]
    row = await _get_expediente_con_permiso(db, expediente_id, user_id)
    etapa = await db.scalar(select(EtapaFormulacionCargos).where(EtapaFormulacionCargos.expediente_id == expediente_id))
    if not etapa:
        raise HTTPException(status_code=404, detail="Formulación de cargos no encontrada")
    descargos_bool = body.descargos
    documento_id = body.documento_id
    datos_ant = {"descargos": etapa.descargos}
    if documento_id != etapa.documento_id:
        if etapa.documento_id: await decrement_file_usage([etapa.documento_id])
        if documento_id: await increment_file_usage([documento_id])
    etapa.descargos = descargos_bool
    etapa.documento_id = documento_id
    await db.flush()
    await insert_auditoria(db, "ACTUALIZAR_FORMULACION_CARGOS", "EXITOSO", user_id,
        expediente_id, row.radicado,
        detalle="Actualización formulación de cargos",
        datos_anteriores=datos_ant, datos_nuevos={"descargos": descargos_bool})
    await db.commit()
    return JSONResponse(content={"ok": True, "id": etapa.id, "etapa_id": etapa.id})


# ── APERTURA ETAPA PROBATORIA ─────────────────────────────────────────────────

@router.get("/opening/{expediente_id}")
async def obtener_apertura(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _get_etapa(ETAPAS["apertura"], db, expediente_id, user_id)


@router.post("/opening/{expediente_id}", status_code=201)
async def crear_apertura(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _post_etapa(ETAPAS["apertura"], db, expediente_id, user_id, None)


# ── CIERRE ETAPA PROBATORIA ───────────────────────────────────────────────────

@router.get("/closing/{expediente_id}")
async def obtener_cierre(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _get_etapa(ETAPAS["cierre"], db, expediente_id, user_id)


@router.post("/closing/{expediente_id}", status_code=201)
async def crear_cierre(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _post_etapa(ETAPAS["cierre"], db, expediente_id, user_id, None)


# ── DECISIÓN DE FONDO ─────────────────────────────────────────────────────────

@router.get("/sanction-type", status_code=200)
async def listar_tipos_sancion(request: Request, db: AsyncSession = Depends(get_db_managed)):
    verify_gateway_token(request)
    return _catalogo((await db.execute(select(TipoSancion).order_by(TipoSancion.id))).scalars().all())


@router.get("/decision/{expediente_id}")
async def obtener_decision(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _get_etapa(ETAPAS["decision_fondo"], db, expediente_id, user_id)


@router.post("/decision/{expediente_id}", status_code=201)
async def crear_decision(request: Request, expediente_id: int, body: Optional[DecisionBody] = None, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _post_etapa(ETAPAS["decision_fondo"], db, expediente_id, user_id, body)


@router.put("/decision/{expediente_id}")
async def actualizar_decision(request: Request, expediente_id: int, body: DecisionBody, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _put_etapa(ETAPAS["decision_fondo"], db, expediente_id, user_id, body)


# ── PROBATORIA DE RECURSO ─────────────────────────────────────────────────────

@router.get("/resource/{expediente_id}")
async def obtener_recurso(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _get_etapa(ETAPAS["recurso"], db, expediente_id, user_id)


@router.post("/resource/{expediente_id}", status_code=201)
async def crear_probatoria_recurso(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    return await _post_etapa(ETAPAS["recurso"], db, expediente_id, user_id, None)


# ── EJECUCIÓN DE LA SANCIÓN ───────────────────────────────────────────────────

class EjecucionBody(_Body):
    # Acto de la ejecución: "AUTO" | "RES" + numerado de 4 dígitos (p. ej. "AUTO0123").
    tipo_acto: str = Field(pattern=r"^(AUTO|RES)\d{4}$")
    fecha_auto: date
    documento_acto_administrativo_id: Optional[int] = None
    cobro_coactivo: bool = False
    documento_cobro_id: Optional[int] = None
    disposicion: bool = False
    ruia: bool = False
    documento_ruia_id: Optional[int] = None
    memorando: bool = False
    documento_memorando_id: Optional[int] = None

    @field_validator("fecha_auto")
    @classmethod
    def fecha_no_futura(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("La fecha no puede ser mayor a la fecha actual")
        return v


_CAMPOS_DOC_EJECUCION = ("documento_acto_administrativo_id", "documento_cobro_id", "documento_ruia_id", "documento_memorando_id")


def _auditoria_ejecucion(d: dict) -> dict:
    return {
        "tipo_acto": d.get("tipo_acto"),
        "fecha_auto": str(d["fecha_auto"]) if d.get("fecha_auto") else None,
        "cobro_coactivo": d.get("cobro_coactivo"),
        "disposicion": d.get("disposicion"),
        "ruia": d.get("ruia"),
        "memorando": d.get("memorando"),
    }


@router.get("/execution/{expediente_id}")
async def obtener_ejecucion(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    await _get_expediente_con_permiso(db, expediente_id, user_id, require_owner=False)
    etapa = await db.scalar(select(EtapaEjecucionSancion).where(EtapaEjecucionSancion.expediente_id == expediente_id))
    creable = await _creable_ejecucion(db, expediente_id)
    if not etapa:
        return _respuesta_get("ejecucion_sancion", None, creable)
    data = await _datos_base(db, etapa, "etapa_ejecucion_sancion", 7, expediente_id)
    data.update({
        "tipo_acto": etapa.tipo_acto,
        "fecha_auto": etapa.fecha_auto.isoformat() if etapa.fecha_auto else None,
        "documento_acto_administrativo_id": etapa.documento_acto_administrativo_id,
        "cobro_coactivo": etapa.cobro_coactivo,
        "documento_cobro_id": etapa.documento_cobro_id,
        "disposicion": etapa.disposicion,
        "ruia": etapa.ruia,
        "documento_ruia_id": etapa.documento_ruia_id,
        "memorando": etapa.memorando,
        "documento_memorando_id": etapa.documento_memorando_id,
    })
    return _respuesta_get("ejecucion_sancion", data, creable)


@router.post("/execution/{expediente_id}", status_code=201)
async def crear_ejecucion(request: Request, expediente_id: int, body: Optional[EjecucionBody] = None, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    row = await _get_expediente_con_permiso(db, expediente_id, user_id)
    if await db.scalar(select(EtapaEjecucionSancion.id).where(EtapaEjecucionSancion.expediente_id == expediente_id)):
        raise HTTPException(status_code=409, detail="La ejecución de la sanción ya existe")
    creable = await _creable_ejecucion(db, expediente_id)
    if not creable["status"]:
        raise HTTPException(status_code=400, detail=creable["msg"])
    datos = body.model_dump() if body else {}
    nueva = EtapaEjecucionSancion(expediente_id=expediente_id, **datos)
    db.add(nueva)
    await db.flush()
    docs = [datos[c] for c in _CAMPOS_DOC_EJECUCION if datos.get(c)]
    if docs:
        await increment_file_usage(docs)
    await insert_auditoria(db, "CREAR_EJECUCION_SANCION", "EXITOSO", user_id,
        expediente_id, row.radicado,
        detalle="Creación ejecución de la sanción",
        datos_nuevos=_auditoria_ejecucion(datos))
    await db.commit()
    return JSONResponse(content={"ok": True, "id": nueva.id, "etapa_id": nueva.id}, status_code=201)


@router.put("/execution/{expediente_id}")
async def actualizar_ejecucion(request: Request, expediente_id: int, body: EjecucionBody, db: AsyncSession = Depends(get_db_managed)):
    user_id = verify_gateway_token(request)["user_id"]
    row = await _get_expediente_con_permiso(db, expediente_id, user_id)
    etapa = await db.scalar(select(EtapaEjecucionSancion).where(EtapaEjecucionSancion.expediente_id == expediente_id))
    if not etapa:
        raise HTTPException(status_code=404, detail="Ejecución de la sanción no encontrada")
    datos_ant = _auditoria_ejecucion({
        "tipo_acto": etapa.tipo_acto, "fecha_auto": etapa.fecha_auto,
        "cobro_coactivo": etapa.cobro_coactivo, "disposicion": etapa.disposicion,
        "ruia": etapa.ruia, "memorando": etapa.memorando,
    })
    datos = body.model_dump()
    for campo in _CAMPOS_DOC_EJECUCION:
        viejo, nuevo = getattr(etapa, campo), datos[campo]
        if nuevo != viejo:
            if viejo: await decrement_file_usage([viejo])
            if nuevo: await increment_file_usage([nuevo])
    for campo, valor in datos.items():
        setattr(etapa, campo, valor)
    await db.flush()
    await insert_auditoria(db, "ACTUALIZAR_EJECUCION_SANCION", "EXITOSO", user_id,
        expediente_id, row.radicado,
        detalle="Actualización ejecución de la sanción",
        datos_anteriores=datos_ant, datos_nuevos=_auditoria_ejecucion(datos))
    await db.commit()
    return JSONResponse(content={"ok": True, "id": etapa.id, "etapa_id": etapa.id})


# ── FULL EXPEDIENTE (para DetalleExpediente) ──────────────────────────────────

@router.get("/full/{expediente_id}")
async def obtener_expediente_completo(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    # DetalleExpediente (gestión y consulta): consultar, o gestionar + encargado.
    user_id = verify_gateway_token(request)["user_id"]
    await exigir_lectura_expediente(db, expediente_id, user_id)
    from db.models.expediente_recurso import ExpedienteRecurso
    from db.models.recurso_afectado import RecursoAfectado
    from db.models.vereda import Vereda
    from db.models.municipio import Municipio

    row = (await db.execute(
        select(Expediente).where(Expediente.id == expediente_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")

    recursos = (await db.execute(
        select(RecursoAfectado.id, RecursoAfectado.nombre)
        .join(ExpedienteRecurso, ExpedienteRecurso.recurso_id == RecursoAfectado.id)
        .where(ExpedienteRecurso.expediente_id == expediente_id)
    )).all()

    vereda_row = None
    municipio_row = None
    if row.vereda_id:
        vereda_row = await db.scalar(select(Vereda).where(Vereda.id == row.vereda_id))
        if vereda_row:
            municipio_row = await db.scalar(select(Municipio).where(Municipio.id == vereda_row.municipio_id))

    from services.involucrado import get_involucrados_by_expedientes_ids
    involucrados_map = await get_involucrados_by_expedientes_ids(db, [expediente_id])

    # Determinar etapas existentes (IDs numéricos legacy → nombres de tabla)
    # y la última etapa registrada (la de fecha_creacion más reciente)
    etapas_existentes = []
    ultima_etapa = None
    ultima_etapa_fecha = None
    stage_checks = [
        (Model, ETAPA_LEGACY_ID[Model], ETAPA_LABELS[Model])
        for Model in ETAPA_LABELS
    ]
    for ModelClass, legacy_id, nombre_etapa in stage_checks:
        fecha_creacion = await db.scalar(
            select(ModelClass.fecha_creacion).where(ModelClass.expediente_id == expediente_id)
        )
        if fecha_creacion is not None:
            etapas_existentes.append(legacy_id)
            if ultima_etapa_fecha is None or fecha_creacion > ultima_etapa_fecha:
                ultima_etapa_fecha = fecha_creacion
                ultima_etapa = nombre_etapa

    tipo_notificaciones = (await db.execute(
        select(TipoNotificacion.id, TipoNotificacion.nombre).order_by(TipoNotificacion.id)
    )).all()

    return JSONResponse(content={
        "ok": True,
        "data": {
            "id": row.id,
            "radicado": row.radicado,
            "expediente": row.expediente,
            "fecha_creacion": row.fecha_creacion.isoformat(),
            "direccion": row.direccion,
            "motivo_afectacion": row.motivo_afectacion,
            "archivado": row.archivado,
            "vereda": {"id": vereda_row.id, "nombre": vereda_row.nombre} if vereda_row else None,
            "municipio": {"id": municipio_row.id, "nombre": municipio_row.nombre} if municipio_row else None,
            "recurso_afectado": [{"id": r[0], "nombre": r[1]} for r in recursos],
            "involucrados": involucrados_map.get(expediente_id, []),
            "ultima_etapa": ultima_etapa,
        },
        "tipo_notificacion": [{"id": t[0], "nombre": t[1]} for t in tipo_notificaciones],
        "etapas_existentes": sorted(etapas_existentes),
    })


# ── DOCUMENTOS ANEXOS ─────────────────────────────────────────────────────────

class DocumentoAnexoBody(_Body):
    nombre: str
    documento_anexo_id: int
    # Tabla de la etapa (p. ej. "etapa_medida_preventiva"). Obligatorio: los ids
    # de etapa se repiten entre tablas, así que el id del path solo no basta.
    etapa_tipo: str


async def _exigir_escritura_etapa(db: AsyncSession, Model, etapa_id: int, user_id: int):
    """Anexos: sancionatorio_gestionar y ser el encargado del expediente de la
    etapa (la misma regla que crear/editar la etapa). 403 si la etapa no existe,
    para no revelar ids."""
    expediente_id = await db.scalar(select(Model.expediente_id).where(Model.id == etapa_id))
    if expediente_id is None:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")
    return await exigir_escritura_expediente(db, expediente_id, user_id)


@router.post("/doc-attached/{etapa_id}", status_code=201)
async def crear_documento_anexo(
    request: Request,
    etapa_id: int,
    body: DocumentoAnexoBody,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    Model = ETAPA_MODELS.get(body.etapa_tipo)
    if not Model:
        raise HTTPException(status_code=400, detail="Tipo de etapa no válido")
    row = await _exigir_escritura_etapa(db, Model, etapa_id, user_id)
    etapa_tipo_str = body.etapa_tipo

    nuevo = DocumentoAnexo(
        etapa_tipo=etapa_tipo_str,
        etapa_ref_id=etapa_id,
        nombre=body.nombre,
        documento_anexo_id=body.documento_anexo_id,
    )
    db.add(nuevo)
    await db.flush()
    await increment_file_usage([body.documento_anexo_id])
    await insert_auditoria(db, "CREAR_DOCUMENTO_ANEXO", "EXITOSO", user_id,
        row.id, row.radicado,
        detalle=f"Documento anexo '{body.nombre}' en {etapa_tipo_str}",
        datos_nuevos={"nombre": body.nombre, "etapa_tipo": etapa_tipo_str})
    await db.commit()
    return JSONResponse(content={"ok": True, "documento_anexo": {
        "id": nuevo.id, "nombre": nuevo.nombre,
        "documento_anexo_id": nuevo.documento_anexo_id,
        "fecha_subida": nuevo.fecha_subida.isoformat() if nuevo.fecha_subida else None,
    }}, status_code=201)


@router.put("/doc-attached/{etapa_id}/{documento_id}", status_code=200)
async def actualizar_documento_anexo(
    request: Request,
    etapa_id: int,
    documento_id: int,
    body: DocumentoAnexoBody,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]
    Model = ETAPA_MODELS.get(body.etapa_tipo)
    if not Model:
        raise HTTPException(status_code=400, detail="Tipo de etapa no válido")
    row = await _exigir_escritura_etapa(db, Model, etapa_id, user_id)
    doc = await db.scalar(select(DocumentoAnexo).where(
        DocumentoAnexo.id == documento_id,
        DocumentoAnexo.etapa_ref_id == etapa_id,
        DocumentoAnexo.etapa_tipo == body.etapa_tipo,
    ))
    if not doc:
        raise HTTPException(status_code=404, detail="Documento anexo no encontrado")
    if body.documento_anexo_id != doc.documento_anexo_id:
        await decrement_file_usage([doc.documento_anexo_id])
        await increment_file_usage([body.documento_anexo_id])
    doc.nombre = body.nombre
    doc.documento_anexo_id = body.documento_anexo_id
    await db.flush()
    await insert_auditoria(db, "ACTUALIZAR_DOCUMENTO_ANEXO", "EXITOSO", user_id,
        row.id, row.radicado,
        detalle=f"Actualización documento '{body.nombre}'", datos_nuevos={"nombre": body.nombre})
    await db.commit()
    return JSONResponse(content={"ok": True, "documento_anexo": {
        "id": doc.id, "nombre": doc.nombre, "documento_anexo_id": doc.documento_anexo_id,
    }})


@router.delete("/doc-attached/{etapa_id}/{documento_id}", status_code=200)
async def eliminar_documento_anexo(
    request: Request,
    etapa_id: int,
    documento_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]
    # El DELETE no trae etapa_tipo: se toma del propio anexo. Anexo inexistente
    # o de un expediente ajeno -> 403 (mismo mensaje, no revela ids).
    doc = await db.scalar(select(DocumentoAnexo).where(
        DocumentoAnexo.id == documento_id,
        DocumentoAnexo.etapa_ref_id == etapa_id,
    ))
    Model = ETAPA_MODELS.get(doc.etapa_tipo) if doc else None
    if not Model:
        raise HTTPException(status_code=403, detail="Sin permisos sobre este expediente")
    row = await _exigir_escritura_etapa(db, Model, etapa_id, user_id)
    await decrement_file_usage([doc.documento_anexo_id])
    await db.delete(doc)
    await db.flush()
    await insert_auditoria(db, "ELIMINAR_DOCUMENTO_ANEXO", "EXITOSO", user_id,
        row.id, row.radicado,
        detalle=f"Eliminación documento '{doc.nombre}'", datos_anteriores={"nombre": doc.nombre})
    await db.commit()
    return JSONResponse(content={"ok": True})


# ── AUDIT BATCH (compatibilidad frontend) ─────────────────────────────────────

@router.post("/audit/batch")
async def obtener_etapas_batch(request: Request, etapa_ids: list[int], db: AsyncSession = Depends(get_db_managed)):
    """Endpoint de compatibilidad — mapea IDs legacy a nombres de etapa."""
    verify_gateway_token(request)
    legacy_names = {ETAPA_LEGACY_ID[Model]: ETAPA_LABELS[Model] for Model in ETAPA_LABELS}
    return JSONResponse(content={"ok": True, "data": {str(i): legacy_names.get(i, f"Etapa {i}") for i in etapa_ids}})

"""Vínculos expediente ↔ involucrado (tabla ``expediente_involucrado``, plan §3).

Reutilizable para cualquier ``tipo_vinculo``: las rutas de solicitantes
(``routes/involucrados.py``) usan ``SOLICITANTE`` y las de tercero
interviniente (agente C) ``TERCERO_INTERVINIENTE``.

Los datos de la persona viven en app-involved (solo se guarda el id).
Ninguna función hace commit (lo hace la ruta). Todas las escrituras dejan
registro en ``auditoria`` (``utils/log.insert_log``), como app-infraction.

V14: si el involucrado tiene tipo de documento NIT, ``representante_id`` es
obligatorio. ``recurso_super_gestion`` omite esa validación (§2.1); los
``unique`` de la BD aplican siempre.
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

import services.involved as involved_svc
from core.acceso import Usuario
from db.models import Expediente, ExpedienteInvolucrado, Notificacion, TipoVinculo
from services.concurrencia import MSG_MODIFICADO, actualizar_versionado, integridad_a_409
from utils.log import insert_log

logger = logging.getLogger(__name__)

MSG_YA_VINCULADO = "El involucrado ya está vinculado a este expediente"
MSG_NIT_SIN_REPRESENTANTE = (
    "El involucrado es una empresa (NIT): es obligatorio vincular su representante legal"
)


def es_nit(info: dict | None) -> bool:
    return bool(info) and (info.get("tipo_documento") or "").strip().upper() == "NIT"


def datos_cliente(request: Request | None) -> dict:
    """ip y user-agent para auditoría (como app-infraction)."""
    if request is None:
        return {}
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


async def resolver_involucrados(ids: list[int]) -> dict[int, dict]:
    """Datos de app-involved por id. Estricto (para validar): 502 si
    app-involved no responde. Los ids inexistentes no aparecen en el dict."""
    ids = sorted({i for i in ids if i})
    if not ids:
        return {}
    try:
        data = await involved_svc.involved_client.bulk(ids)
    except Exception as e:
        logger.error(f"app-involved no respondió para {ids}: {e}")
        raise HTTPException(status_code=502, detail="No se pudo consultar app-involved, intenta de nuevo")
    return {d["id"]: d for d in data if isinstance(d, dict) and "id" in d}


def _validar_representante(
    involucrado_id: int, representante_id: int | None, mapa: dict[int, dict], usuario: Usuario
) -> None:
    if involucrado_id not in mapa:
        raise HTTPException(status_code=404, detail="Involucrado no encontrado en app-involved")
    if representante_id is not None and representante_id not in mapa:
        raise HTTPException(status_code=404, detail="Representante legal no encontrado en app-involved")
    # V14
    if representante_id is None and es_nit(mapa[involucrado_id]) and not usuario.super_gestion:
        raise HTTPException(status_code=400, detail=MSG_NIT_SIN_REPRESENTANTE)


def _resumen_persona(info: dict | None) -> dict | None:
    if not info:
        return None
    return {
        k: info.get(k)
        for k in ("id", "tipo_documento", "numero_documento", "digito_verificacion", "nombre")
    }


def serializar_vinculo(
    vinculo: ExpedienteInvolucrado, mapa: dict[int, dict], puede_gestionar: bool = False
) -> dict:
    """Vínculo con la persona y el representante resueltos (o ``{"id": ...}``
    si app-involved no respondió)."""
    info = mapa.get(vinculo.involucrado_id) or {"id": vinculo.involucrado_id}
    rep_id = vinculo.representante_id
    acciones: list[str] = []
    if puede_gestionar and vinculo.tipo_vinculo == TipoVinculo.SOLICITANTE:
        acciones = ["editar_representante", "desvincular"]
    return {
        "id": vinculo.id,
        "expediente_id": vinculo.expediente_id,
        "involucrado_id": vinculo.involucrado_id,
        "tipo_vinculo": vinculo.tipo_vinculo.value,
        "representante_id": rep_id,
        "acto_admin_id": vinculo.acto_admin_id,
        "fecha_vinculacion": vinculo.fecha_vinculacion.isoformat() if vinculo.fecha_vinculacion else None,
        "version": vinculo.version,
        "involucrado": info,
        "representante": (mapa.get(rep_id) or {"id": rep_id}) if rep_id else None,
        "requiere_representante": es_nit(info),
        "acciones_disponibles": acciones,
    }


async def serializar_vinculos(
    db: AsyncSession,
    expediente_id: int,
    tipo_vinculo: TipoVinculo | None = None,
    puede_gestionar: bool = False,
) -> list[dict]:
    """Vínculos del expediente resueltos contra app-involved (tolerante: si
    app-involved cae, cada persona queda como ``{"id": ...}``)."""
    stmt = select(ExpedienteInvolucrado).where(ExpedienteInvolucrado.expediente_id == expediente_id)
    if tipo_vinculo is not None:
        stmt = stmt.where(ExpedienteInvolucrado.tipo_vinculo == tipo_vinculo)
    vinculos = (await db.execute(
        stmt.order_by(ExpedienteInvolucrado.fecha_vinculacion, ExpedienteInvolucrado.id)
    )).scalars().all()
    if not vinculos:
        return []
    ids = {v.involucrado_id for v in vinculos} | {v.representante_id for v in vinculos if v.representante_id}
    personas = await involved_svc.get_involucrados_by_ids(db, sorted(ids))
    mapa = {p["id"]: p for p in personas if isinstance(p, dict) and "id" in p}
    return [serializar_vinculo(v, mapa, puede_gestionar) for v in vinculos]


async def obtener_vinculo(db: AsyncSession, vinculo_id: int) -> ExpedienteInvolucrado:
    vinculo = await db.get(ExpedienteInvolucrado, vinculo_id, populate_existing=True)
    if vinculo is None:
        raise HTTPException(status_code=404, detail="Vínculo no encontrado")
    return vinculo


async def vincular_involucrado(
    db: AsyncSession,
    *,
    expediente: Expediente,
    involucrado_id: int,
    usuario: Usuario,
    tipo_vinculo: TipoVinculo = TipoVinculo.SOLICITANTE,
    representante_id: int | None = None,
    request: Request | None = None,
) -> ExpedienteInvolucrado:
    """Crea el vínculo (valida existencia en app-involved y V14). 409 si la
    persona ya está vinculada al expediente (con cualquier ``tipo_vinculo``)."""
    mapa = await resolver_involucrados([involucrado_id, representante_id])
    _validar_representante(involucrado_id, representante_id, mapa, usuario)

    existente = await db.scalar(
        select(ExpedienteInvolucrado.id).where(
            ExpedienteInvolucrado.expediente_id == expediente.id,
            ExpedienteInvolucrado.involucrado_id == involucrado_id,
        )
    )
    if existente is not None:
        raise HTTPException(status_code=409, detail=MSG_YA_VINCULADO)

    vinculo = ExpedienteInvolucrado(
        expediente_id=expediente.id,
        involucrado_id=involucrado_id,
        tipo_vinculo=tipo_vinculo,
        representante_id=representante_id,
    )
    async with integridad_a_409(db, MSG_YA_VINCULADO):
        db.add(vinculo)
        await db.flush()

    audit = await insert_log(
        db=db,
        tipo_evento="VINCULAR_INVOLUCRADO",
        resultado="EXITOSO",
        usuario_id=usuario.user_id,
        expediente_id=expediente.id,
        expediente_radicado=expediente.radicado,
        detalle=(
            f"Vinculación de involucrado_id={involucrado_id} como {tipo_vinculo.value} "
            f"al expediente {expediente.expediente}"
        ),
        datos_nuevos={
            "tipo_vinculo": tipo_vinculo.value,
            "involucrado": _resumen_persona(mapa.get(involucrado_id)),
            "representante": _resumen_persona(mapa.get(representante_id)) if representante_id else None,
        },
        **datos_cliente(request),
    )
    if not audit["ok"]:
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")
    return vinculo


async def cambiar_representante(
    db: AsyncSession,
    *,
    vinculo: ExpedienteInvolucrado,
    expediente: Expediente,
    representante_id: int | None,
    version: int,
    usuario: Usuario,
    request: Request | None = None,
) -> int:
    """Edita ``representante_id`` con bloqueo optimista. Devuelve la versión nueva."""
    anterior = vinculo.representante_id
    mapa = await resolver_involucrados([vinculo.involucrado_id, representante_id, anterior])
    _validar_representante(vinculo.involucrado_id, representante_id, mapa, usuario)

    nueva = await actualizar_versionado(
        db, ExpedienteInvolucrado, vinculo.id, version, {"representante_id": representante_id}
    )
    audit = await insert_log(
        db=db,
        tipo_evento="UPDATE_REPRESENTANTE",
        resultado="EXITOSO",
        usuario_id=usuario.user_id,
        expediente_id=expediente.id,
        expediente_radicado=expediente.radicado,
        detalle=f"Cambio de representante legal de involucrado_id={vinculo.involucrado_id}",
        datos_anteriores={"representante": _resumen_persona(mapa.get(anterior)) if anterior else None},
        datos_nuevos={"representante": _resumen_persona(mapa.get(representante_id)) if representante_id else None},
        **datos_cliente(request),
    )
    if not audit["ok"]:
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")
    return nueva


async def desvincular_involucrado(
    db: AsyncSession,
    *,
    vinculo: ExpedienteInvolucrado,
    expediente: Expediente,
    version: int,
    usuario: Usuario,
    request: Request | None = None,
) -> None:
    """Borra el vínculo (bloqueo optimista con ``version``).

    TODO(negocio): app-infraction borra las notificaciones de la persona al
    desvincularla; aquí NO se borran documentos legales: si la persona ya tiene
    notificaciones registradas o un acto que la reconoce, se responde 409.
    Confirmar con el área qué debe pasar en esos casos.
    """
    if vinculo.acto_admin_id is not None:
        raise HTTPException(
            status_code=409,
            detail="No se puede desvincular: tiene un acto administrativo que lo reconoce",
        )
    from services.expediente_documentos import actos_del_expediente

    actos = await actos_del_expediente(db, expediente)
    if actos:
        notificado = await db.scalar(
            select(Notificacion.id).where(
                Notificacion.acto_admin_id.in_(actos),
                Notificacion.involucrado_id == vinculo.involucrado_id,
            ).limit(1)
        )
        if notificado is not None:
            raise HTTPException(
                status_code=409,
                detail="No se puede desvincular: tiene notificaciones registradas en este expediente",
            )

    mapa = await involved_svc.get_involucrados_by_ids(db, [vinculo.involucrado_id])
    persona = mapa[0] if mapa else {"id": vinculo.involucrado_id}

    resultado = await db.execute(
        delete(ExpedienteInvolucrado)
        .where(ExpedienteInvolucrado.id == vinculo.id, ExpedienteInvolucrado.version == version)
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount == 0:
        raise HTTPException(status_code=409, detail=MSG_MODIFICADO)

    audit = await insert_log(
        db=db,
        tipo_evento="DESVINCULAR_INVOLUCRADO",
        resultado="EXITOSO",
        usuario_id=usuario.user_id,
        expediente_id=expediente.id,
        expediente_radicado=expediente.radicado,
        detalle=(
            f"Desvinculación de involucrado_id={vinculo.involucrado_id} "
            f"({vinculo.tipo_vinculo.value}) del expediente {expediente.expediente}"
        ),
        datos_anteriores={
            "tipo_vinculo": vinculo.tipo_vinculo.value,
            "involucrado": _resumen_persona(persona),
            "representante_id": vinculo.representante_id,
        },
        **datos_cliente(request),
    )
    if not audit["ok"]:
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

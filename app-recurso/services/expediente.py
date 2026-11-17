"""Información base del expediente (plan §3): validaciones de catálogos,
unicidad, comprobante de pago y serialización para lectura.

Ninguna función hace commit (lo hace la ruta).
"""
from __future__ import annotations

import logging
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import (
    Expediente,
    Fuente,
    TipoFuente,
    Vereda,
)
from services.docs import get_file_info
from services.expediente_involucrados import serializar_vinculos

logger = logging.getLogger(__name__)

# Campos escalares de la tabla expediente que diligencia el usuario (§3).
CAMPOS_BASE = (
    "radicado",
    "fecha_radicado",
    "expediente",
    "numero_vital",
    "nombre_predio",
    "matricula_inmobiliaria",
    "codigo_catastral",
    "radicado_oficio_entrada",
    "fecha_oficio_entrada",
    "doc_comprobante_pago_id",
    "vereda_id",
    "tipo_fuente_id",
    "nombre_fuente",
)

MSG_UNICO = "Ya existe un expediente con ese radicado o número de expediente"


async def validar_catalogos(
    db: AsyncSession, vereda_id: int, tipo_fuente_id: int, fuente_ids: Iterable[int]
) -> None:
    """400 si la vereda, el tipo de fuente o alguna fuente no existen."""
    if await db.scalar(select(Vereda.id).where(Vereda.id == vereda_id)) is None:
        raise HTTPException(status_code=400, detail="La vereda no existe")
    if await db.scalar(select(TipoFuente.id).where(TipoFuente.id == tipo_fuente_id)) is None:
        raise HTTPException(status_code=400, detail="El tipo de fuente no existe")
    ids = set(fuente_ids)
    existentes = set((await db.execute(select(Fuente.id).where(Fuente.id.in_(ids)))).scalars().all())
    faltantes = sorted(ids - existentes)
    if faltantes:
        raise HTTPException(status_code=400, detail=f"Fuentes inexistentes: {faltantes}")


async def verificar_unicos(
    db: AsyncSession, radicado: str, expediente: str, excluir_id: int | None = None
) -> None:
    """409 con mensaje claro si el radicado o el número de expediente ya están
    en uso. La carrera entre dos creaciones la cierra el ``unique`` de la BD
    (la ruta envuelve el INSERT/UPDATE en ``integridad_a_409``)."""
    for columna, valor, etiqueta in (
        (Expediente.radicado, radicado, "radicado"),
        (Expediente.expediente, expediente, "número de expediente"),
    ):
        stmt = select(Expediente.id).where(columna == valor)
        if excluir_id is not None:
            stmt = stmt.where(Expediente.id != excluir_id)
        if await db.scalar(stmt) is not None:
            raise HTTPException(
                status_code=409, detail=f"Ya existe un expediente con el {etiqueta} {valor}"
            )


async def validar_comprobante_pago(file_id: int) -> None:
    """El comprobante de pago debe existir en app-docs y ser PDF (se une al PDF
    del expediente completo), igual que el radicado inicial de infraction."""
    info = await get_file_info(file_id)
    if not info.get("ok"):
        raise HTTPException(status_code=400, detail="No se encontró el comprobante de pago cargado")
    if info["data"].get("content_type") != "application/pdf":
        raise HTTPException(status_code=400, detail="El comprobante de pago debe cargarse en PDF")


async def cargar_expediente(db: AsyncSession, expediente_id: int) -> Expediente:
    """Expediente con vereda→municipio, tipo de fuente, fuentes y usos. 404 si no existe."""
    expediente = await db.scalar(
        select(Expediente)
        .where(Expediente.id == expediente_id)
        .options(
            selectinload(Expediente.vereda).selectinload(Vereda.municipio),
            selectinload(Expediente.tipo_fuente),
            selectinload(Expediente.fuentes),
            selectinload(Expediente.usos),
        )
        .execution_options(populate_existing=True)
    )
    if expediente is None:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    return expediente


def _iso(valor):
    return valor.isoformat() if valor is not None else None


def datos_auditables(expediente: Expediente) -> dict:
    """Foto de la información base para datos_anteriores/datos_nuevos de auditoría.
    Requiere el expediente cargado con ``cargar_expediente``."""
    return {
        "radicado": expediente.radicado,
        "fecha_radicado": _iso(expediente.fecha_radicado),
        "expediente": expediente.expediente,
        "numero_vital": expediente.numero_vital,
        "nombre_predio": expediente.nombre_predio,
        "matricula_inmobiliaria": expediente.matricula_inmobiliaria,
        "codigo_catastral": expediente.codigo_catastral,
        "radicado_oficio_entrada": expediente.radicado_oficio_entrada,
        "fecha_oficio_entrada": _iso(expediente.fecha_oficio_entrada),
        "doc_comprobante_pago_id": expediente.doc_comprobante_pago_id,
        "vereda": expediente.vereda.nombre if expediente.vereda else None,
        "municipio": expediente.vereda.municipio.nombre if expediente.vereda and expediente.vereda.municipio else None,
        "tipo_fuente": expediente.tipo_fuente.nombre if expediente.tipo_fuente else None,
        "nombre_fuente": expediente.nombre_fuente,
        "fuentes": sorted(f.nombre for f in expediente.fuentes),
        "usos": sorted(u.uso.value for u in expediente.usos),
    }


async def serializar_expediente(
    db: AsyncSession, expediente: Expediente, puede_gestionar: bool = False
) -> dict:
    """Información base completa (catálogos resueltos, fuentes, usos,
    involucrados resueltos contra app-involved y ``version``)."""
    vereda = expediente.vereda
    municipio = vereda.municipio if vereda else None
    return {
        "id": expediente.id,
        "version": expediente.version,
        "radicado": expediente.radicado,
        "fecha_radicado": _iso(expediente.fecha_radicado),
        "expediente": expediente.expediente,
        "numero_vital": expediente.numero_vital,
        "nombre_predio": expediente.nombre_predio,
        "matricula_inmobiliaria": expediente.matricula_inmobiliaria,
        "codigo_catastral": expediente.codigo_catastral,
        "radicado_oficio_entrada": expediente.radicado_oficio_entrada,
        "fecha_oficio_entrada": _iso(expediente.fecha_oficio_entrada),
        # El nombre del archivo no se guarda en app-docs: nombre fijo (como infraction).
        "comprobante_pago": {"file_id": expediente.doc_comprobante_pago_id, "nombre": "Comprobante de pago"},
        "doc_comprobante_pago_id": expediente.doc_comprobante_pago_id,
        "vereda": {"id": vereda.id, "nombre": vereda.nombre} if vereda else None,
        "municipio": {"id": municipio.id, "nombre": municipio.nombre} if municipio else None,
        "tipo_fuente": (
            {"id": expediente.tipo_fuente.id, "nombre": expediente.tipo_fuente.nombre}
            if expediente.tipo_fuente else None
        ),
        "nombre_fuente": expediente.nombre_fuente,
        "fuentes": sorted(
            ({"id": f.id, "nombre": f.nombre} for f in expediente.fuentes), key=lambda f: f["nombre"]
        ),
        "usos": sorted(u.uso.value for u in expediente.usos),
        "fecha_creacion": _iso(expediente.fecha_creacion),
        "involucrados": await serializar_vinculos(db, expediente.id, puede_gestionar=puede_gestionar),
    }


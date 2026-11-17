"""Mecanismos de concurrencia del plan §7. Ninguna función hace commit.

- ``bloquear_expediente``: bloqueo pesimista (``SELECT ... FOR UPDATE``) para
  transiciones críticas: crear etapa siguiente, cargar versión final, numerar,
  registrar decisión. Validar las reglas de §6 DESPUÉS de bloquear.
- ``actualizar_versionado``: bloqueo optimista sobre tablas con ``version``.
- ``asignar_encargado``: "Asignarme para diligenciar" atómico.
- ``integridad_a_409``: convierte un IntegrityError (unique de etapa) en 409.
"""
from contextlib import asynccontextmanager
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Expediente

MSG_MODIFICADO = "Fue modificado por otra persona, recarga"
MSG_ASIGNADO = "Ya fue asignado"
MSG_DUPLICADO = "Ya existe, otra persona lo creó al mismo tiempo. Recarga"


async def bloquear_expediente(db: AsyncSession, expediente_id: int) -> Expediente:
    expediente = await db.scalar(
        select(Expediente).where(Expediente.id == expediente_id).with_for_update()
    )
    if expediente is None:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    return expediente


async def actualizar_versionado(
    db: AsyncSession, modelo: type, id_: int, version: int, valores: dict[str, Any]
) -> int:
    """``UPDATE modelo SET valores, version = version + 1 WHERE id AND version``.
    Devuelve la versión nueva; 409 si otra persona lo modificó antes."""
    resultado = await db.execute(
        update(modelo)
        .where(modelo.id == id_, modelo.version == version)
        .values(**valores, version=modelo.version + 1)
        .returning(modelo.version)
        .execution_options(synchronize_session=False)
    )
    nueva = resultado.scalar_one_or_none()
    if nueva is None:
        existe = await db.scalar(select(modelo.id).where(modelo.id == id_))
        if existe is None:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        raise HTTPException(status_code=409, detail=MSG_MODIFICADO)
    return nueva


async def asignar_encargado(
    db: AsyncSession, modelo: type, id_: int, user_id: int, columna: str = "encargado_acto_id"
) -> None:
    """``UPDATE ... SET encargado = :yo WHERE id AND encargado IS NULL``; 0 filas → 409.
    Para filas que nacen con el encargado (NOT NULL) la atomicidad la da el
    ``unique`` de la etapa: usar ``integridad_a_409`` al crearlas."""
    col = getattr(modelo, columna)
    resultado = await db.execute(
        update(modelo)
        .where(modelo.id == id_, col.is_(None))
        .values({columna: user_id})
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount == 0:
        existe = await db.scalar(select(modelo.id).where(modelo.id == id_))
        if existe is None:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        raise HTTPException(status_code=409, detail=MSG_ASIGNADO)


@asynccontextmanager
async def integridad_a_409(db: AsyncSession, detalle: str = MSG_DUPLICADO):
    """``async with integridad_a_409(db): db.add(fila); await db.flush()``"""
    try:
        yield
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=detalle) from e

"""Dueños de los archivos (``file_uso``), registro de subidas (``file_subida``)
y la regla que impide asociar archivos ajenos.

``numero_usos`` sigue siendo lo que mira la limpieza durante la transición; con
el formato nuevo de increment/decrement se mueve solo cuando se crea o borra
una fila de ``file_uso``, así que repetir la misma asociación es idempotente.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.file_hash import FileHash
from db.models.file_uso import FileSubida, FileUso

logger = logging.getLogger(__name__)

BOGOTA = ZoneInfo("America/Bogota")

# off: no valida. log: valida y solo deja un WARNING con lo que rechazaría
# (para medir el impacto antes de cerrar). on: rechaza el lote con 403.
MODO_VALIDACION = os.getenv("ARCHIVOS_VALIDAR_ASOCIACION", "log").strip().lower()
# Cuánto después de subir un archivo puede el mismo usuario asociarlo.
VENTANA_SUBIDA_HORAS = float(os.getenv("ARCHIVOS_VENTANA_SUBIDA_HORAS", "24"))


class UsoArchivo(BaseModel):
    file_id: int
    entidad: str = Field(min_length=1, max_length=50)
    entidad_id: str = Field(min_length=1, max_length=64)

    @field_validator("entidad_id", mode="before")
    @classmethod
    def _a_texto(cls, v):
        return str(v) if isinstance(v, int) else v


def nombre_servicio(caller: str) -> str:
    """'infraction-service' -> 'infraction' (así se guarda en file_uso)."""
    return caller.removesuffix("-service")


async def registrar_subida(db: AsyncSession, file_id: int, usuario_id: Optional[int], servicio: str) -> None:
    db.add(FileSubida(file_id=file_id, usuario_id=usuario_id, servicio_origen=servicio, fecha=datetime.now(BOGOTA)))


async def _existentes(db: AsyncSession, file_ids: Iterable[int]) -> set[int]:
    ids = set(file_ids)
    if not ids:
        return set()
    return set((await db.execute(select(FileHash.id).where(FileHash.id.in_(ids)))).scalars().all())


async def validar_asociacion(
    db: AsyncSession, servicio: str, usos: list[UsoArchivo], usuario_id: Optional[int]
) -> list[int]:
    """file_ids que el usuario no puede asociar: no los subió él dentro de la
    ventana y tampoco pertenecen ya a esa misma entidad del servicio. Sin
    ``usuario_id`` (procesos sin usuario) no se valida."""
    if usuario_id is None or not usos:
        return []
    ids = {u.file_id for u in usos}
    desde = datetime.now(BOGOTA) - timedelta(hours=VENTANA_SUBIDA_HORAS)
    subidos = set((await db.execute(
        select(FileSubida.file_id).where(
            FileSubida.file_id.in_(ids), FileSubida.usuario_id == usuario_id, FileSubida.fecha >= desde,
        )
    )).scalars().all())
    claves = {(u.file_id, u.entidad, u.entidad_id) for u in usos if u.file_id not in subidos}
    if not claves:
        return []
    ya_suyos = {tuple(fila) for fila in (await db.execute(
        select(FileUso.file_id, FileUso.entidad, FileUso.entidad_id).where(
            FileUso.servicio == servicio,
            tuple_(FileUso.file_id, FileUso.entidad, FileUso.entidad_id).in_(list(claves)),
        )
    )).all()}
    return sorted({c[0] for c in claves if c not in ya_suyos})


async def aplicar_usos(
    db: AsyncSession,
    servicio: str,
    usos: list[UsoArchivo],
    usuario_id: Optional[int],
    *,
    mover_contador: bool = True,
) -> dict:
    """Upsert de ``file_uso``. Con ``mover_contador`` suma 1 a ``numero_usos``
    por cada fila nueva. No hace commit."""
    existentes = await _existentes(db, (u.file_id for u in usos))
    nuevos: dict[int, int] = {}
    for uso in usos:
        if uso.file_id not in existentes:
            continue
        creado = (await db.execute(
            pg_insert(FileUso)
            .values(
                file_id=uso.file_id, servicio=servicio, entidad=uso.entidad,
                entidad_id=uso.entidad_id, usuario_id=usuario_id, creado_en=datetime.now(BOGOTA),
            )
            .on_conflict_do_nothing(constraint="uq_file_uso")
            .returning(FileUso.id)
        )).first()
        if creado is not None:
            nuevos[uso.file_id] = nuevos.get(uso.file_id, 0) + 1
    if mover_contador:
        for file_id, veces in nuevos.items():
            await db.execute(
                update(FileHash).where(FileHash.id == file_id).values(numero_usos=FileHash.numero_usos + veces)
            )
    return {
        "registrados": sum(nuevos.values()),
        "no_encontrados": sorted({u.file_id for u in usos} - existentes),
    }


async def quitar_usos(db: AsyncSession, servicio: str, usos: list[UsoArchivo]) -> int:
    """Borra esas filas de ``file_uso`` del servicio y resta 1 a ``numero_usos``
    por cada fila borrada (nunca baja de 0). No hace commit."""
    borrados: dict[int, int] = {}
    for uso in usos:
        fila = (await db.execute(
            delete(FileUso)
            .where(
                FileUso.file_id == uso.file_id, FileUso.servicio == servicio,
                FileUso.entidad == uso.entidad, FileUso.entidad_id == uso.entidad_id,
            )
            .returning(FileUso.file_id)
        )).first()
        if fila is not None:
            borrados[uso.file_id] = borrados.get(uso.file_id, 0) + 1
    for file_id, veces in borrados.items():
        await db.execute(
            update(FileHash).where(FileHash.id == file_id)
            .values(numero_usos=func.greatest(FileHash.numero_usos - veces, 0))
        )
    return sum(borrados.values())

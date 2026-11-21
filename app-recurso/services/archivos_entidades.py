"""Dónde guarda recurso los archivos de app-docs y cómo se nombra su dueño.

Cada columna con un ``file_id`` de app-docs se registra en ``file_uso`` como
(``entidad``, ``entidad_id``) = (nombre de la tabla, id de la fila). El
servicio lo pone app-docs a partir del service-token.

- Al asociar: ``usos(fila, file_ids)`` -> ``etapas.registrar_archivos`` /
  ``actos._incrementar`` (antes del commit, con el usuario).
- Al reemplazar: ``usos_liberados(fila, anteriores)`` solo libera los que ya
  no están en ninguna columna de la fila (app-docs borra la asociación entera:
  si la citación y la notificación son el mismo PDF, cambiar una no lo suelta).
- Al borrar una fila: ``usos_de_fila(fila)``.

Las versiones y adjuntos del proceso de revisión (``DocumentoProcesoVersion``,
``DocumentoProcesoRevision``) siguen con el formato anterior (solo
``file_ids``): los maneja el servicio de revisión compartido con infracción.
Por eso no están en ``COLUMNAS_ARCHIVO`` ni en la carga inicial.

``filas_usos`` recorre todas las columnas para la carga inicial, que se corre
una vez dentro del contenedor (idempotente, se puede repetir)::

    python -m services.archivos_entidades
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    ActoAdministrativo,
    ActoAdmite,
    Comunicacion,
    ConceptoTecnico,
    DocumentoAnexo,
    Expediente,
    InformeUsuario,
    MemoriasCalculo,
    Notificacion,
    RecursoReposicion,
    Requerimiento,
    Subsanacion,
)
import services.docs as docs_svc

logger = logging.getLogger(__name__)

LOTE = 1000  # máximo de app-docs por llamada a /files/registrar-usos

# (modelo, columnas con file_id). Al agregar una columna de archivo nueva, va aquí.
COLUMNAS_ARCHIVO: tuple[tuple[type, tuple[str, ...]], ...] = (
    (Expediente, ("doc_comprobante_pago_id",)),
    (ActoAdministrativo, ("documento_acto_administrativo_id",)),
    (Comunicacion, ("documento_comunicacion_id",)),
    (Notificacion, ("documento_citacion_id", "documento_notificacion_id")),
    (ActoAdmite, ("doc_oficio_alcaldia_id", "doc_fijacion_aviso_id", "doc_constancia_fijacion_aviso_id")),
    (ConceptoTecnico, ("doc_concepto_tecnico_id",)),
    (Requerimiento, ("doc_oficio_entrada_id",)),
    (RecursoReposicion, ("doc_recurso_id",)),
    (MemoriasCalculo, ("doc_planos_id",)),
    (Subsanacion, ("doc_planos_ajustados_id",)),
    (InformeUsuario, ("doc_informe_usuario_id",)),
    (DocumentoAnexo, ("documento_anexo_id",)),
)
_COLUMNAS = {modelo: columnas for modelo, columnas in COLUMNAS_ARCHIVO}


def uso(fila, file_id: int) -> dict:
    """Uso de ``file_id`` por ``fila`` (cualquier modelo de ``COLUMNAS_ARCHIVO``)."""
    return {"file_id": int(file_id), "entidad": fila.__tablename__, "entidad_id": fila.id}


def usos(fila, file_ids: Iterable[Optional[int]]) -> list[dict]:
    """Usos de ``file_ids`` por ``fila`` (sin vacíos ni repetidos). La fila ya
    debe tener ``id`` (después del ``flush``)."""
    vistos: list[int] = []
    for f in file_ids:
        if f and int(f) not in vistos:
            vistos.append(int(f))
    return [uso(fila, f) for f in vistos]


def archivos_de_fila(fila) -> set[int]:
    """``file_id`` que la fila referencia hoy en sus columnas de archivo."""
    return {v for c in _COLUMNAS.get(type(fila), ()) if (v := getattr(fila, c, None))}


def usos_liberados(
    fila, anteriores: Iterable[Optional[int]], actuales: Optional[Iterable[Optional[int]]] = None,
) -> list[dict]:
    """Usos de los ``anteriores`` que la fila ya no referencia. ``actuales``:
    los archivos de la fila cuando el objeto no refleja el UPDATE (p. ej.
    ``actualizar_versionado``)."""
    quedan = {int(f) for f in actuales if f} if actuales is not None else archivos_de_fila(fila)
    return usos(fila, (f for f in anteriores if f and int(f) not in quedan))


def usos_de_fila(fila) -> list[dict]:
    """Todos los usos de una fila que se va a borrar."""
    return usos(fila, sorted(archivos_de_fila(fila)))


@dataclass
class Liberacion:
    """Lo que se suelta en app-docs DESPUÉS del commit: ``usos`` (con dueño) y
    ``file_ids`` de versiones/adjuntos del proceso de revisión (formato anterior)."""

    usos: list[dict] = field(default_factory=list)
    file_ids: list[int] = field(default_factory=list)

    def agregar(self, otra: Any) -> "Liberacion":
        """Suma otra ``Liberacion`` o una lista de usos."""
        if isinstance(otra, Liberacion):
            self.usos += otra.usos
            self.file_ids += otra.file_ids
        elif otra:
            self.usos += list(otra)
        return self

    def __len__(self) -> int:
        return len(self.usos) + len(self.file_ids)


def como_liberacion(valor: Any) -> Liberacion:
    """``Liberacion``, lista de usos o ``None`` -> ``Liberacion``."""
    return valor if isinstance(valor, Liberacion) else Liberacion().agregar(valor)


async def filas_usos(db: AsyncSession) -> AsyncIterator[dict]:
    """Todos los usos de archivos que hay hoy en recurso (sin repetir)."""
    vistos: set[tuple[int, str, int]] = set()
    for modelo, columnas in COLUMNAS_ARCHIVO:
        cols = [getattr(modelo, c) for c in columnas]
        for fila in (await db.execute(select(modelo.id, *cols))).all():
            for file_id in fila[1:]:
                clave = (file_id, modelo.__tablename__, fila[0])
                if file_id and clave not in vistos:
                    vistos.add(clave)
                    yield {"file_id": file_id, "entidad": modelo.__tablename__, "entidad_id": fila[0]}


async def cargar_usos_existentes(db: AsyncSession) -> int:
    """Registra en app-docs los dueños de todos los archivos que ya usa
    recurso (``/files/registrar-usos``, no toca ``numero_usos``). Devuelve
    cuántos usos envió."""
    lote: list[dict] = []
    total = 0
    async for u in filas_usos(db):
        lote.append(u)
        if len(lote) == LOTE:
            await docs_svc.files_client.registrar_usos(lote)
            total += len(lote)
            lote = []
    if lote:
        await docs_svc.files_client.registrar_usos(lote)
        total += len(lote)
    logger.info("Usos de archivos registrados en app-docs: %d", total)
    return total


async def _main() -> None:
    from db.database import SessionLocal

    async with SessionLocal() as db:
        print(f"Usos registrados en app-docs: {await cargar_usos_existentes(db)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())

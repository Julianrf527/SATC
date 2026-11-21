"""Dónde guarda recurso los archivos de app-docs y cómo se nombra su dueño.

Cada columna con un ``file_id`` de app-docs se registra en ``file_uso`` como
(``entidad``, ``entidad_id``) = (nombre de la tabla, id de la fila). El
servicio lo pone app-docs a partir del service-token.

``filas_usos`` recorre todas las columnas para la carga inicial, que se corre
una vez dentro del contenedor (idempotente, se puede repetir)::

    python -m services.archivos_entidades
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    ActoAdministrativo,
    ActoAdmite,
    Comunicacion,
    ConceptoTecnico,
    DocumentoAnexo,
    DocumentoProcesoRevision,
    DocumentoProcesoVersion,
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
    (DocumentoProcesoVersion, ("file_id",)),
    (DocumentoProcesoRevision, ("adjunto_file_id",)),
)


def uso(fila, file_id: int) -> dict:
    """Uso de ``file_id`` por ``fila`` (cualquier modelo de ``COLUMNAS_ARCHIVO``)."""
    return {"file_id": file_id, "entidad": fila.__tablename__, "entidad_id": fila.id}


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

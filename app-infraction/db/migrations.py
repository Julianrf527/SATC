"""Migración idempotente del esquema de infracciones_db, ejecutada en cada arranque.

El repo no usa Alembic: ``init_db`` crea las tablas con ``create_all``, que NO
altera tablas existentes. Los cambios sobre tablas de producción se aplican
aquí con DDL idempotente (``IF NOT EXISTS``); correrla N veces deja el mismo
resultado.

Cambios:
  1. ``expediente.radicado_inicial_file_id`` (INTEGER, NULL): documento PDF
     "Radicado inicial" del expediente. Es el id de ``file_hash`` en app-docs
     (otra BD), así que no lleva FK real.

No hay transformación de datos: la columna nace NULL (expediente sin radicado
inicial adjunto).

Corre en la transacción de ``init_db`` con ``pg_advisory_xact_lock`` para que
varios workers de Gunicorn arrancando a la vez no ejecuten el DDL en paralelo.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

_LOCK_KEY = "app-infraction:migraciones"

# asyncpg no admite varias sentencias en un execute: una por elemento.
_DDL = (
    "ALTER TABLE expediente ADD COLUMN IF NOT EXISTS radicado_inicial_file_id INTEGER",
)


async def _columna_existe(conn: AsyncConnection, tabla: str, columna: str) -> bool:
    return bool(await conn.scalar(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = :t AND column_name = :c"
    ), {"t": tabla, "c": columna}))


async def aplicar_migraciones(conn: AsyncConnection) -> dict:
    """Aplica la migración sobre ``conn`` (dentro de una transacción abierta).
    Devuelve un resumen de lo hecho (para logs y tests)."""
    await conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": _LOCK_KEY})

    resumen = {"radicado_inicial_file_id_agregada": not await _columna_existe(
        conn, "expediente", "radicado_inicial_file_id")}
    for sql in _DDL:
        await conn.execute(text(sql))

    logger.info("Migración app-infraction aplicada: %s", resumen)
    print(f"Migración app-infraction aplicada: {resumen}")
    return resumen

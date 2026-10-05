"""Migración idempotente del esquema de expedientes_db, ejecutada en cada arranque.

El repo no usa Alembic: ``init_db`` crea las tablas con ``create_all``, que NO
altera tablas existentes. Los cambios sobre tablas de producción se aplican
aquí con DDL idempotente (``IF NOT EXISTS``); correrla N veces deja el mismo
resultado.

Cambios:
  1. ``etapa_probatoria_recurso.acto_decision_id`` (FK a acto_administrativo,
     ON DELETE SET NULL) + índice: el acto de decisión del recurso (acto
     auxiliar de la etapa). Antes no existía columna y el frontend no podía
     crearlo (el backend respondía 400 "El acto administrativo ya existe").

No hay transformación de datos: ninguna fila guardada tiene una forma que el
contrato actual de las etapas no entienda (los nombres de columna no cambian).

Todo corre en la transacción de ``init_db`` con ``pg_advisory_xact_lock`` para
que varios workers de Gunicorn arrancando a la vez no ejecuten el DDL en paralelo.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

_LOCK_KEY = "app-sancionatoria:migraciones"

# asyncpg no admite varias sentencias en un execute: una por elemento.
_DDL = (
    "ALTER TABLE etapa_probatoria_recurso ADD COLUMN IF NOT EXISTS acto_decision_id INTEGER "
    "REFERENCES acto_administrativo(id) ON DELETE SET NULL",
    "CREATE INDEX IF NOT EXISTS ix_etapa_probatoria_recurso_acto_decision_id "
    "ON etapa_probatoria_recurso (acto_decision_id)",
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

    resumen = {"acto_decision_id_agregada": not await _columna_existe(
        conn, "etapa_probatoria_recurso", "acto_decision_id")}
    for sql in _DDL:
        await conn.execute(text(sql))

    logger.info("Migración app-sancionatoria aplicada: %s", resumen)
    print(f"Migración app-sancionatoria aplicada: {resumen}")
    return resumen

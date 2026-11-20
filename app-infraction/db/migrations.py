"""Migración idempotente del esquema de infracciones_db, ejecutada en cada arranque.

El repo no usa Alembic: ``init_db`` crea las tablas con ``create_all``, que NO
altera tablas existentes. Los cambios sobre tablas de producción se aplican
aquí con DDL idempotente (``IF NOT EXISTS``); correrla N veces deja el mismo
resultado.

Cambios:
  1. ``expediente.radicado_inicial_file_id`` (INTEGER, NULL): documento PDF
     "Radicado inicial" del expediente. Es el id de ``file_hash`` en app-docs
     (otra BD), así que no lleva FK real.
  2. Tabla única de procesos de revisión (``documento_proceso*``, la crea
     ``create_all``): reemplaza a ``informe_proceso*``, que se BORRAN sin
     migrar datos (eran datos de prueba, decisión de negocio 2026-11-19). Los
     informes en FLUJO que tenían proceso quedan sin proceso vigente y se
     vuelven a asignar desde Informes.
  3. ``solicitud_informacion.radicado_respuesta`` (VARCHAR(11)),
     ``fecha_radicado_respuesta`` (VARCHAR(10)) y ``archivo_respuesta_id``
     (INTEGER), todas NULL: respuesta del usuario a la solicitud de
     información (opcional; si se registra, van las tres).

No hay transformación de datos.

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
    "ALTER TABLE solicitud_informacion ADD COLUMN IF NOT EXISTS radicado_respuesta VARCHAR(11)",
    "ALTER TABLE solicitud_informacion ADD COLUMN IF NOT EXISTS fecha_radicado_respuesta VARCHAR(10)",
    "ALTER TABLE solicitud_informacion ADD COLUMN IF NOT EXISTS archivo_respuesta_id INTEGER",
    "DROP TABLE IF EXISTS informe_proceso_auditoria",
    "DROP TABLE IF EXISTS informe_proceso_revision",
    "DROP TABLE IF EXISTS informe_proceso_version",
    "DROP TABLE IF EXISTS informe_proceso_revisor",
    "DROP TABLE IF EXISTS informe_proceso",
)


async def _columna_existe(conn: AsyncConnection, tabla: str, columna: str) -> bool:
    return bool(await conn.scalar(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = :t AND column_name = :c"
    ), {"t": tabla, "c": columna}))


async def _tabla_existe(conn: AsyncConnection, tabla: str) -> bool:
    return bool(await conn.scalar(text(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = :t"
    ), {"t": tabla}))


async def aplicar_migraciones(conn: AsyncConnection) -> dict:
    """Aplica la migración sobre ``conn`` (dentro de una transacción abierta).
    Devuelve un resumen de lo hecho (para logs y tests)."""
    await conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": _LOCK_KEY})

    resumen = {
        "radicado_inicial_file_id_agregada": not await _columna_existe(
            conn, "expediente", "radicado_inicial_file_id"),
        "informe_proceso_eliminada": await _tabla_existe(conn, "informe_proceso"),
        "respuesta_solicitud_agregada": not await _columna_existe(
            conn, "solicitud_informacion", "archivo_respuesta_id"),
    }
    for sql in _DDL:
        await conn.execute(text(sql))

    logger.info("Migración app-infraction aplicada: %s", resumen)
    print(f"Migración app-infraction aplicada: {resumen}")
    return resumen

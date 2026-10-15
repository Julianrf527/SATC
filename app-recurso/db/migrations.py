"""Migración idempotente del esquema de recurso_db, ejecutada en cada arranque.

El repo no usa Alembic: ``init_db`` crea las tablas con ``create_all``, que NO
altera tablas existentes. Los cambios sobre tablas ya creadas se aplican aquí
con DDL idempotente; correrla N veces deja el mismo resultado.

Cambios:
  1. ``acto_administrativo.clase_acto`` (VARCHAR(4), NULL, CHECK AUTO/RES):
     forma del acto (Auto o Resolución) que elige quien lo carga o corrige.
     Las filas anteriores quedan en NULL hasta que alguien edite el acto.
  2. ``comunicacion.fecha_creacion`` (TIMESTAMPTZ, NULL): cuándo se registró la
     comunicación. El ORM la llena en filas nuevas (hora America/Bogota); las
     filas anteriores quedan en NULL.
  3. ``encargado_acto_id`` de ``acto_admite``, ``requerimiento`` y ``decision``
     pasa a admitir NULL (desviación del DBML, ver DISENO_TECNICO.md): el
     cargue histórico de super gestión puede dejar la etapa sin abogado
     encargado. El flujo normal ("Asignarme") siempre lo llena.

Corre en la transacción de ``init_db`` con ``pg_advisory_xact_lock`` para que
varios workers de Gunicorn arrancando a la vez no ejecuten el DDL en paralelo.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

_LOCK_KEY = "app-recurso:migraciones"

# asyncpg no admite varias sentencias en un execute: una por elemento.
_DDL = (
    "ALTER TABLE acto_administrativo ADD COLUMN IF NOT EXISTS clase_acto VARCHAR(4)",
    """
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_acto_admin_clase_acto') THEN
            ALTER TABLE acto_administrativo
                ADD CONSTRAINT ck_acto_admin_clase_acto CHECK (clase_acto IN ('AUTO', 'RES'));
        END IF;
    END $$
    """,
    "ALTER TABLE comunicacion ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP WITH TIME ZONE",
    # DROP NOT NULL es idempotente (no falla si la columna ya admite NULL).
    "ALTER TABLE acto_admite ALTER COLUMN encargado_acto_id DROP NOT NULL",
    "ALTER TABLE requerimiento ALTER COLUMN encargado_acto_id DROP NOT NULL",
    "ALTER TABLE decision ALTER COLUMN encargado_acto_id DROP NOT NULL",
)


async def aplicar_migraciones(conn: AsyncConnection) -> None:
    """Aplica la migración sobre ``conn`` (dentro de una transacción abierta)."""
    await conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": _LOCK_KEY})
    for sql in _DDL:
        await conn.execute(text(sql))
    logger.info("Migración app-recurso aplicada")

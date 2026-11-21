"""Migración idempotente del esquema de documentos_db, ejecutada en cada arranque.

El repo no usa Alembic: la BD se inicializa con ``create_all`` en ``init_db``.
``create_all`` crea tablas nuevas pero NO altera las existentes, así que los
cambios sobre tablas de producción se aplican aquí con DDL idempotente
(``IF [NOT] EXISTS``). Correrla N veces deja el mismo resultado.

Cambios (flujo genérico sobre satc_shared.review_process, origen fuera de app-docs):
  1. ``DROP VIEW`` de ``vista_documentos_detalle`` (depende de ``documentos.origen``).
  2. Columnas nuevas: ``versiones_documento.file_id``, ``revisiones.adjunto_file_id``,
     ``revisiones.adjunto_size`` (+ ``archivo_adjunto_url/nombre`` por si la VM
     aún no tiene el ALTER del adjunto, que se hizo a mano solo en local).
  3. Backfill de ``file_id``/``adjunto_file_id``/``adjunto_size`` cruzando la URL
     con ``file_hash.file_url`` (solo filas con el id en NULL).
  4. ``DROP COLUMN documentos.origen`` (y su índice) — SOLO si no quedan filas con
     ``origen`` no nulo; si las hay se omite y se registra un WARNING: borrarlas
     es una decisión de negocio, no de la migración.
  5. ``file_hash.ultima_subida`` (periodo de gracia de la limpieza), rellenada
     con ``created_at`` en las filas existentes.
  6. Dueños (``file_uso``) de los archivos del módulo Documentos.
  7. Recrea la vista sin ``origen`` y con los nombres del contrato
     (``creador_id``; sin el duplicado ``documento_id``). Como el paso 1 la
     borra antes, ``CREATE OR REPLACE`` puede renombrar/quitar columnas.

Todo corre en una transacción con ``pg_advisory_xact_lock`` para que varios
workers arrancando a la vez no ejecuten el DDL en paralelo.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

_LOCK_KEY = "app-docs:migraciones"

VISTA_DOCUMENTOS_DETALLE_SQL = """
CREATE OR REPLACE VIEW vista_documentos_detalle AS
SELECT
    d.id,
    d.nombre,
    d.descripcion,
    d.tipo_archivo,
    d.estado,
    d.version_actual,
    d.numero_devoluciones,
    d.usuario_creador_id AS creador_id,
    d.fecha_creacion,
    d.fecha_ultima_actualizacion,
    COALESCE(rev_count.total_revisiones, 0) AS total_revisiones,
    COALESCE(asig_count.total_revisores, 0) AS total_revisores
FROM documentos d
LEFT JOIN (
    SELECT documento_id, COUNT(*) AS total_revisiones
    FROM revisiones
    GROUP BY documento_id
) rev_count ON rev_count.documento_id = d.id
LEFT JOIN (
    SELECT documento_id, COUNT(*) AS total_revisores
    FROM asignaciones_revisores
    GROUP BY documento_id
) asig_count ON asig_count.documento_id = d.id
"""

# asyncpg no admite varias sentencias en un execute: una por elemento.
_DDL_COLUMNAS = (
    "DROP VIEW IF EXISTS vista_documentos_detalle",
    "ALTER TABLE versiones_documento ADD COLUMN IF NOT EXISTS file_id INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_versiones_documento_file_id ON versiones_documento (file_id)",
    "ALTER TABLE revisiones ADD COLUMN IF NOT EXISTS archivo_adjunto_url VARCHAR(500)",
    "ALTER TABLE revisiones ADD COLUMN IF NOT EXISTS archivo_adjunto_nombre VARCHAR(255)",
    "ALTER TABLE revisiones ADD COLUMN IF NOT EXISTS adjunto_file_id INTEGER",
    "ALTER TABLE revisiones ADD COLUMN IF NOT EXISTS adjunto_size BIGINT",
    "ALTER TABLE file_hash ADD COLUMN IF NOT EXISTS ultima_subida TIMESTAMPTZ",
)

_BACKFILL = (
    """
    UPDATE versiones_documento v
    SET file_id = fh.id
    FROM file_hash fh
    WHERE v.file_id IS NULL AND v.archivo_url = fh.file_url
    """,
    """
    UPDATE revisiones r
    SET adjunto_file_id = fh.id,
        adjunto_size = COALESCE(r.adjunto_size, fh.file_size)
    FROM file_hash fh
    WHERE r.adjunto_file_id IS NULL
      AND r.archivo_adjunto_url IS NOT NULL
      AND r.archivo_adjunto_url = fh.file_url
    """,
    # Periodo de gracia de la limpieza: los archivos previos parten de su creación.
    "UPDATE file_hash SET ultima_subida = created_at WHERE ultima_subida IS NULL",
)


# Dueños de los archivos del propio módulo Documentos (servicio "docs"). Las
# tablas file_uso/file_subida las crea create_all; los demás módulos registran
# los suyos con POST /files/registrar-usos.
_BACKFILL_USOS_DOCS = """
INSERT INTO file_uso (file_id, servicio, entidad, entidad_id, creado_en)
SELECT DISTINCT u.file_id, 'docs', 'documento', u.documento_id::text, now()
FROM (
    SELECT file_id, documento_id FROM versiones_documento WHERE file_id IS NOT NULL
    UNION
    SELECT adjunto_file_id, documento_id FROM revisiones WHERE adjunto_file_id IS NOT NULL
) u
JOIN file_hash fh ON fh.id = u.file_id
ON CONFLICT ON CONSTRAINT uq_file_uso DO NOTHING
"""


async def _columna_existe(conn: AsyncConnection, tabla: str, columna: str) -> bool:
    return bool(await conn.scalar(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = :t AND column_name = :c"
    ), {"t": tabla, "c": columna}))


async def aplicar_migraciones(conn: AsyncConnection) -> dict:
    """Aplica la migración sobre ``conn`` (dentro de una transacción abierta).
    Devuelve un resumen con lo hecho (útil para logs y tests)."""
    await conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": _LOCK_KEY})

    for sql in _DDL_COLUMNAS:
        await conn.execute(text(sql))

    resumen = {"versiones_backfill": 0, "revisiones_backfill": 0, "origen_eliminado": False}
    resumen["versiones_backfill"] = (await conn.execute(text(_BACKFILL[0]))).rowcount or 0
    resumen["revisiones_backfill"] = (await conn.execute(text(_BACKFILL[1]))).rowcount or 0
    await conn.execute(text(_BACKFILL[2]))
    resumen["usos_docs_backfill"] = (await conn.execute(text(_BACKFILL_USOS_DOCS))).rowcount or 0

    if await _columna_existe(conn, "documentos", "origen"):
        pendientes = await conn.scalar(text("SELECT COUNT(*) FROM documentos WHERE origen IS NOT NULL"))
        if pendientes:
            logger.warning(
                "Migración app-docs: NO se elimina documentos.origen, quedan %s documento(s) con "
                "origen no nulo (procesos de otras apps). Bórralos o migra su flujo y reinicia app-docs.",
                pendientes,
            )
        else:
            await conn.execute(text("DROP INDEX IF EXISTS ix_documentos_origen"))
            await conn.execute(text("ALTER TABLE documentos DROP COLUMN IF EXISTS origen"))
            resumen["origen_eliminado"] = True

    await conn.execute(text(VISTA_DOCUMENTOS_DETALLE_SQL))
    logger.info("Migración app-docs aplicada: %s", resumen)
    return resumen

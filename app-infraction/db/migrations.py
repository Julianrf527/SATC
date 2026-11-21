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
  4. ``etapa_acoger_concepto.instancia`` (VARCHAR(15), NOT NULL, por defecto
     ``'VISITA'``): distingue el acoger concepto de la visita (etapa 3) del de
     la visita de seguimiento (etapa 5). Las filas existentes quedan como
     ``VISITA``. Índice único ``(expediente_id, instancia)``; si hubiera
     expedientes con dos conceptos (datos viejos) no se crea y se avisa en el
     log en lugar de abortar el arranque.
  5. ``informe_tecnico.fecha_asignacion`` (DATE, NULL): día en que el informe
     quedó por primera vez con técnico Y fecha de programación de la visita
     (inicio de la alerta "primera versión del concepto técnico"; reasignar no
     la cambia). Al agregarla se rellena en los informes ya asignados con la
     fecha de su primer proceso de revisión (o, sin proceso, la de creación
     del informe), en hora de Bogotá.

Solo el punto 5 transforma datos, y solo la vez en que se agrega la columna.

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
    "ALTER TABLE etapa_acoger_concepto ADD COLUMN IF NOT EXISTS instancia VARCHAR(15) NOT NULL DEFAULT 'VISITA'",
    "ALTER TABLE informe_tecnico ADD COLUMN IF NOT EXISTS fecha_asignacion DATE",
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


async def _indice_unico_instancia(conn: AsyncConnection) -> str:
    """Índice único ``(expediente_id, instancia)`` del acoger concepto. No se
    crea si hay duplicados (se avisa): devuelve 'existe', 'creado' u 'omitido'."""
    if await conn.scalar(text(
        "SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() "
        "AND indexname = 'uq_etapa_acoger_concepto_instancia'"
    )):
        return "existe"
    duplicados = await conn.scalar(text(
        "SELECT count(*) FROM (SELECT 1 FROM etapa_acoger_concepto "
        "GROUP BY expediente_id, instancia HAVING count(*) > 1) d"
    ))
    if duplicados:
        logger.warning(
            "No se crea uq_etapa_acoger_concepto_instancia: %s expediente(s) con conceptos repetidos", duplicados
        )
        return "omitido"
    await conn.execute(text(
        "CREATE UNIQUE INDEX uq_etapa_acoger_concepto_instancia ON etapa_acoger_concepto (expediente_id, instancia)"
    ))
    return "creado"


_RELLENO_FECHA_ASIGNACION = """
UPDATE informe_tecnico i
SET fecha_asignacion = COALESCE(
    (SELECT MIN(timezone('America/Bogota', p.fecha_creacion))::date
     FROM documento_proceso p
     WHERE p.etapa_tipo = 'informe_tecnico' AND p.etapa_ref_id = i.id),
    timezone('America/Bogota', i.fecha_creacion)::date
)
WHERE i.fecha_asignacion IS NULL
  AND i.profesional_asignado_id IS NOT NULL
  AND i.fecha_programacion_visita IS NOT NULL
"""


async def _rellenar_fecha_asignacion(conn: AsyncConnection) -> int:
    """Rellena ``fecha_asignacion`` de los informes ya asignados (punto 5)."""
    if not await _tabla_existe(conn, "documento_proceso"):
        return 0
    return (await conn.execute(text(_RELLENO_FECHA_ASIGNACION))).rowcount


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
        "instancia_concepto_agregada": not await _columna_existe(conn, "etapa_acoger_concepto", "instancia"),
        "fecha_asignacion_agregada": not await _columna_existe(conn, "informe_tecnico", "fecha_asignacion"),
    }
    for sql in _DDL:
        await conn.execute(text(sql))
    resumen["indice_instancia_concepto"] = await _indice_unico_instancia(conn)
    resumen["fecha_asignacion_rellenadas"] = (
        await _rellenar_fecha_asignacion(conn) if resumen["fecha_asignacion_agregada"] else 0
    )

    logger.info("Migración app-infraction aplicada: %s", resumen)
    print(f"Migración app-infraction aplicada: {resumen}")
    return resumen

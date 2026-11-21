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
  4. ``concepto_tecnico.accion`` (VARCHAR(10), NULL, CHECK DECIDE/REQUIERE):
     acción del concepto de la etapa 2. Los conceptos de etapa 2 ya cargados
     y sin acción se completan una vez: REQUIERE si el expediente tiene
     requerimiento (etapa 3); si no, DECIDE si tiene decisión; si no tiene
     ninguno de los dos, REQUIERE.
  5. Práctica de pruebas del recurso de reposición:
     ``recurso_reposicion.requiere_pruebas`` (BOOLEAN NOT NULL DEFAULT false;
     los recursos ya creados quedan en «No») y la tabla ``practica_pruebas``
     (la crea ``create_all``).
  6. ``acto_administrativo.medio`` (VARCHAR(10) NOT NULL, CHECK
     COMUNICA/NOTIFICA) reemplaza a ``tipo_acto`` (ENUM): qué acto es lo dice
     la etapa que lo referencia; la columna solo guarda cómo se da a conocer.
     Si ``tipo_acto`` existe se convierte una vez (AUTO_ADMITE,
     RECONOCE_TERCERO y AUTO_PRUEBAS → COMUNICA; el resto → NOTIFICA) y se
     elimina con su tipo ENUM. El índice ``(tipo_acto, numerado)`` pasa a
     ``(clase_acto, numerado)``: cada clase (Auto / Resolución) tiene su
     propia numeración.
  7. Fechas para las alertas de las etapas 3, 4 y del recurso:
     ``recurso_reposicion.fecha_creacion`` (TIMESTAMPTZ NOT NULL DEFAULT now()),
     ``concepto_tecnico.fecha_version_final`` y
     ``requerimiento.fecha_registro_respuesta`` (TIMESTAMPTZ, NULL). Las dos
     últimas las llena un trigger la primera vez que se pone el PDF
     (``doc_concepto_tecnico_id`` / ``doc_oficio_entrada_id``) por cualquier
     camino (ORM o UPDATE directo); reemplazar el PDF no las cambia y quitarlo
     las deja en NULL. Las filas existentes se completan una vez: el recurso con
     su auditoría ``CREAR_RECURSO`` o, si no hay, ``fecha_radicado``; el concepto
     con su última versión subida o, si no hay, ``fecha_aceptacion``; la
     respuesta con su auditoría ``RESPUESTA_REQUERIMIENTO`` o, si no hay,
     ``fecha_oficio_entrada``.
  8. Búsqueda parcial (``ILIKE '%texto%'``) del listado de expedientes:
     extensión ``pg_trgm`` e índices GIN trigram en ``expediente.radicado``,
     ``expediente.expediente`` y ``expediente.numero_vital``.

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
    "ALTER TABLE concepto_tecnico ADD COLUMN IF NOT EXISTS accion VARCHAR(10)",
    """
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_concepto_tecnico_accion') THEN
            ALTER TABLE concepto_tecnico
                ADD CONSTRAINT ck_concepto_tecnico_accion CHECK (accion IN ('DECIDE', 'REQUIERE'));
        END IF;
    END $$
    """,
    # Idempotente: solo toca conceptos de etapa 2 cargados que aún no tienen acción.
    """
    UPDATE concepto_tecnico c SET accion = CASE
        WHEN EXISTS (SELECT 1 FROM requerimiento r WHERE r.expediente_id = c.expediente_id) THEN 'REQUIERE'
        WHEN EXISTS (SELECT 1 FROM decision d WHERE d.expediente_id = c.expediente_id) THEN 'DECIDE'
        ELSE 'REQUIERE'
    END
    WHERE c.expediente_id IS NOT NULL AND c.doc_concepto_tecnico_id IS NOT NULL AND c.accion IS NULL
    """,
    "ALTER TABLE recurso_reposicion ADD COLUMN IF NOT EXISTS requiere_pruebas BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE acto_administrativo ADD COLUMN IF NOT EXISTS medio VARCHAR(10)",
    # Conversión única desde tipo_acto (EXECUTE: la columna puede ya no existir).
    """
    DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'acto_administrativo' AND column_name = 'tipo_acto') THEN
            EXECUTE $q$
                UPDATE acto_administrativo SET medio = CASE
                    WHEN tipo_acto::text IN ('AUTO_ADMITE', 'RECONOCE_TERCERO', 'AUTO_PRUEBAS') THEN 'COMUNICA'
                    ELSE 'NOTIFICA'
                END
                WHERE medio IS NULL
            $q$;
            ALTER TABLE acto_administrativo DROP COLUMN tipo_acto;
        END IF;
    END $$
    """,
    "DROP TYPE IF EXISTS tipo_acto",
    "ALTER TABLE acto_administrativo ALTER COLUMN medio SET NOT NULL",
    """
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_acto_admin_medio') THEN
            ALTER TABLE acto_administrativo
                ADD CONSTRAINT ck_acto_admin_medio CHECK (medio IN ('COMUNICA', 'NOTIFICA'));
        END IF;
    END $$
    """,
    "DROP INDEX IF EXISTS ix_acto_admin_tipo_numerado",
    "CREATE INDEX IF NOT EXISTS ix_acto_admin_clase_numerado ON acto_administrativo (clase_acto, numerado)",
    # 7. Fechas de las alertas. Sin DEFAULT al agregar: las filas existentes se completan abajo.
    "ALTER TABLE recurso_reposicion ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP WITH TIME ZONE",
    """
    UPDATE recurso_reposicion r SET fecha_creacion = COALESCE(
        (SELECT min(a.fecha) FROM auditoria a JOIN decision d ON d.expediente_id = a.expediente_id
          WHERE d.id = r.decision_id AND a.tipo_evento = 'CREAR_RECURSO'),
        r.fecha_radicado::timestamp AT TIME ZONE 'America/Bogota')
    WHERE r.fecha_creacion IS NULL
    """,
    "ALTER TABLE recurso_reposicion ALTER COLUMN fecha_creacion SET DEFAULT now()",
    "ALTER TABLE recurso_reposicion ALTER COLUMN fecha_creacion SET NOT NULL",
    "ALTER TABLE concepto_tecnico ADD COLUMN IF NOT EXISTS fecha_version_final TIMESTAMP WITH TIME ZONE",
    """
    UPDATE concepto_tecnico c SET fecha_version_final = COALESCE(
        (SELECT max(v.fecha_subida) FROM documento_proceso_version v
           JOIN documento_proceso p ON p.id = v.proceso_id
          WHERE p.etapa_tipo = 'concepto_tecnico' AND p.etapa_ref_id = c.id),
        c.fecha_aceptacion::timestamp AT TIME ZONE 'America/Bogota')
    WHERE c.doc_concepto_tecnico_id IS NOT NULL AND c.fecha_version_final IS NULL
    """,
    "ALTER TABLE requerimiento ADD COLUMN IF NOT EXISTS fecha_registro_respuesta TIMESTAMP WITH TIME ZONE",
    """
    UPDATE requerimiento r SET fecha_registro_respuesta = COALESCE(
        (SELECT min(a.fecha) FROM auditoria a
          WHERE r.expediente_id IS NOT NULL AND a.expediente_id = r.expediente_id
            AND a.tipo_evento = 'RESPUESTA_REQUERIMIENTO'),
        r.fecha_oficio_entrada::timestamp AT TIME ZONE 'America/Bogota')
    WHERE r.doc_oficio_entrada_id IS NOT NULL AND r.fecha_registro_respuesta IS NULL
    """,
    # Triggers: la fecha nace con el primer PDF (también vía UPDATE directo, que no pasa por el ORM).
    """
    CREATE OR REPLACE FUNCTION trg_concepto_fecha_version_final() RETURNS trigger AS $$
    BEGIN
        IF NEW.doc_concepto_tecnico_id IS NULL THEN
            NEW.fecha_version_final := NULL;
        ELSIF TG_OP = 'INSERT' OR OLD.doc_concepto_tecnico_id IS NULL THEN
            NEW.fecha_version_final := COALESCE(NEW.fecha_version_final, now());
        END IF;
        RETURN NEW;
    END $$ LANGUAGE plpgsql
    """,
    """
    CREATE OR REPLACE TRIGGER concepto_fecha_version_final
        BEFORE INSERT OR UPDATE OF doc_concepto_tecnico_id ON concepto_tecnico
        FOR EACH ROW EXECUTE FUNCTION trg_concepto_fecha_version_final()
    """,
    """
    CREATE OR REPLACE FUNCTION trg_requerimiento_fecha_respuesta() RETURNS trigger AS $$
    BEGIN
        IF NEW.doc_oficio_entrada_id IS NULL THEN
            NEW.fecha_registro_respuesta := NULL;
        ELSIF TG_OP = 'INSERT' OR OLD.doc_oficio_entrada_id IS NULL THEN
            NEW.fecha_registro_respuesta := COALESCE(NEW.fecha_registro_respuesta, now());
        END IF;
        RETURN NEW;
    END $$ LANGUAGE plpgsql
    """,
    """
    CREATE OR REPLACE TRIGGER requerimiento_fecha_respuesta
        BEFORE INSERT OR UPDATE OF doc_oficio_entrada_id ON requerimiento
        FOR EACH ROW EXECUTE FUNCTION trg_requerimiento_fecha_respuesta()
    """,
    # 8. Índices trigram para la búsqueda parcial del listado.
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE INDEX IF NOT EXISTS ix_expediente_radicado_trgm ON expediente USING gin (radicado gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_expediente_expediente_trgm ON expediente USING gin (expediente gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_expediente_numero_vital_trgm ON expediente USING gin (numero_vital gin_trgm_ops)",
)


async def aplicar_migraciones(conn: AsyncConnection) -> None:
    """Aplica la migración sobre ``conn`` (dentro de una transacción abierta)."""
    await conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": _LOCK_KEY})
    for sql in _DDL:
        await conn.execute(text(sql))
    logger.info("Migración app-recurso aplicada")

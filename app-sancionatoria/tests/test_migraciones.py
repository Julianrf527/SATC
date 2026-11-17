"""db/migrations.py: idempotente y agrega acto_decision_id a una tabla de producción que no la tiene."""
from sqlalchemy import text

from conftest import engine
from db.migrations import aplicar_migraciones


async def _tiene_columna(conn) -> bool:
    return bool(await conn.scalar(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'etapa_probatoria_recurso' AND column_name = 'acto_decision_id'"
    )))


async def test_migracion_agrega_columna_y_es_idempotente():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE etapa_probatoria_recurso DROP COLUMN IF EXISTS acto_decision_id"))
        assert not await _tiene_columna(conn)

        assert await aplicar_migraciones(conn) == {"acto_decision_id_agregada": True}
        assert await _tiene_columna(conn)
        assert await aplicar_migraciones(conn) == {"acto_decision_id_agregada": False}
        assert await _tiene_columna(conn)

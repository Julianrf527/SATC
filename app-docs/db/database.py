from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

engine = create_async_engine(
    DATABASE_URL,
    connect_args={
        "server_settings": {"client_encoding": "utf8"}
    },
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    from . import models
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

        # create_all no crea vistas, hay que emitir el DDL a mano.
        await conn.execute(text("""
            CREATE OR REPLACE VIEW vista_documentos_detalle AS
            SELECT
                d.id,
                d.id AS documento_id,
                d.nombre,
                d.descripcion,
                d.tipo_archivo,
                d.estado,
                d.version_actual,
                d.numero_devoluciones,
                d.usuario_creador_id,
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
        """))

    print("Vista vista_documentos_detalle creada/actualizada correctamente")
